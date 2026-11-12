"""LLM-based passage reranker using structured tool calling."""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from src.agents.injection_classifier import CONFIG_EXCEPTIONS
from src.config import settings
from src.core.llm import (
    LLMConfigurationError,
    LLMNotConfiguredError,
    extract_model_name,
    get_chat_model,
)
from src.core.log_context import exc_brief

logger = logging.getLogger("multiagent.rag.reranker")

PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "reranker.md"


class PassageRelevance(BaseModel):
    """Relevance judgment (0-3) for a single numbered candidate passage."""

    index: int
    relevance: int = Field(ge=0, le=3)


class RerankVerdict(BaseModel):
    """Relevance of each passage to the merchant's question (see src/prompts/reranker.md)."""

    scores: list[PassageRelevance]


@dataclass(frozen=True)
class RerankResult:
    """Outcome of a single reranker invocation."""

    status: Literal["ok", "invalid", "error"]
    relevance: list[int] | None
    error_type: str | None
    latency_ms: float
    usage: dict[str, int] | None
    model: str | None

    def as_metadata(self) -> dict[str, Any]:
        """Return compact metadata dictionary (without token usage or passage contents)."""
        return {
            "status": self.status,
            "error_type": self.error_type,
            "latency_ms": self.latency_ms,
            "model": self.model,
        }


def load_reranker_prompt() -> str:
    """Load the static reranker system prompt from disk."""
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def _escape_tags(text: str) -> str:
    """Escape angle brackets to isolate untrusted text from prompt XML tags."""
    return text.replace("<", "&lt;").replace(">", "&gt;")


def format_rerank_input(query: str, passages: Sequence[Mapping[str, Any]]) -> str:
    """Format query and candidate passages with XML tags without a trailing newline."""
    parts = [
        "<query>",
        _escape_tags(query),
        "</query>",
    ]
    for idx, passage in enumerate(passages):
        title = str(passage.get("title") or "")
        text = str(passage.get("text") or "")
        parts.extend(
            [
                f'<passage index="{idx}">',
                _escape_tags(title),
                _escape_tags(text),
                "</passage>",
            ]
        )
    return "\n".join(parts)


def _extract_usage(response: Any) -> dict[str, int] | None:
    """Extract normalized token usage dictionary from an AIMessage response."""
    raw = getattr(response, "usage_metadata", None)
    if not isinstance(raw, dict) or not raw:
        return None
    inp = raw.get("input_tokens")
    out = raw.get("output_tokens")
    if inp is None and out is None:
        return None
    inp_i = int(inp or 0)
    out_i = int(out or 0)
    tot = raw.get("total_tokens")
    tot_i = int(tot) if tot is not None else inp_i + out_i
    return {
        "input_tokens": inp_i,
        "output_tokens": out_i,
        "total_tokens": tot_i,
    }


class LLMReranker:
    """Scores candidate passages for relevance to a query using a tool-bound LLM."""

    def __init__(self, model: BaseChatModel | None = None) -> None:
        self._model = model
        self._bound: Any | None = None
        self._prompt: str | None = None

    def _ensure_bound_model(self) -> Any:
        """Lazily initialize the chat model and bind the RerankVerdict tool."""
        if self._bound is None:
            if self._model is None:
                self._model = get_chat_model(
                    settings.RAG_RERANK_MODEL or None,
                    timeout_s=settings.RAG_RERANK_TIMEOUT_S,
                    max_retries=0,
                )
            self._bound = self._model.bind_tools([RerankVerdict], tool_choice="RerankVerdict")
        return self._bound

    def _get_prompt(self) -> str:
        """Lazily load and cache the system prompt."""
        if self._prompt is None:
            self._prompt = load_reranker_prompt()
        return self._prompt

    def rerank(self, query: str, passages: Sequence[Mapping[str, Any]]) -> RerankResult:
        """Score each passage in [0..3] for query relevance, preserving input order."""
        n = len(passages)
        if n == 0:
            return RerankResult(
                status="ok",
                relevance=[],
                error_type=None,
                latency_ms=0.0,
                usage=None,
                model=None,
            )

        t0 = time.perf_counter()
        active_model_name = (
            extract_model_name(self._model)
            if self._model is not None
            else (settings.RAG_RERANK_MODEL or settings.LLM_MODEL)
        )

        try:
            bound = self._ensure_bound_model()
            active_model_name = extract_model_name(bound)
            messages = [
                SystemMessage(content=self._get_prompt()),
                HumanMessage(content=format_rerank_input(query, passages)),
            ]
            response = bound.invoke(messages)
        except (LLMNotConfiguredError, LLMConfigurationError):
            raise
        except CONFIG_EXCEPTIONS as exc:
            raise LLMConfigurationError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - non-config errors degrade cleanly to status='error'
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            logger.warning(f"Reranker invocation failed: {exc_brief(exc)}")
            return RerankResult(
                status="error",
                relevance=None,
                error_type=type(exc).__name__,
                latency_ms=latency_ms,
                usage=None,
                model=active_model_name,
            )

        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        usage = _extract_usage(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        matching_call = next(
            (tc for tc in tool_calls if isinstance(tc, dict) and tc.get("name") == "RerankVerdict"),
            None,
        )
        if matching_call is None:
            return RerankResult(
                status="invalid",
                relevance=None,
                error_type="no_verdict_call",
                latency_ms=latency_ms,
                usage=usage,
                model=active_model_name,
            )

        raw_args = matching_call.get("args")
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args)
            except json.JSONDecodeError:
                raw_args = None

        if not isinstance(raw_args, dict):
            return RerankResult(
                status="invalid",
                relevance=None,
                error_type="invalid_arguments",
                latency_ms=latency_ms,
                usage=usage,
                model=active_model_name,
            )

        try:
            verdict = RerankVerdict.model_validate(raw_args)
        except ValidationError:
            return RerankResult(
                status="invalid",
                relevance=None,
                error_type="invalid_arguments",
                latency_ms=latency_ms,
                usage=usage,
                model=active_model_name,
            )

        if len(verdict.scores) != n or {item.index for item in verdict.scores} != set(range(n)):
            return RerankResult(
                status="invalid",
                relevance=None,
                error_type="bad_indexes",
                latency_ms=latency_ms,
                usage=usage,
                model=active_model_name,
            )

        ordered = [0] * n
        for item in verdict.scores:
            ordered[item.index] = item.relevance

        return RerankResult(
            status="ok",
            relevance=ordered,
            error_type=None,
            latency_ms=latency_ms,
            usage=usage,
            model=active_model_name,
        )
