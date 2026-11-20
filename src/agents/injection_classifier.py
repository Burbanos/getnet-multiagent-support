"""LLM-based prompt injection and attack classifier using structured tool calling."""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from langchain_core.exceptions import (
    ModelAuthenticationError,
    ModelInvalidRequestError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.config import settings
from src.core import metrics
from src.core.llm import (
    LLMConfigurationError,
    LLMNotConfiguredError,
    extract_model_name,
    get_chat_model,
)
from src.core.tracing import set_attributes, span

CONFIG_EXCEPTIONS = (
    ModelNotFoundError,
    ModelAuthenticationError,
    ModelPermissionDeniedError,
    ModelInvalidRequestError,
)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "guardrail_classifier.md"
WEB_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "guardrail_web_classifier.md"


class GuardrailVerdict(BaseModel):
    """Verdict on one merchant message (see src/prompts/guardrail_classifier.md)."""

    verdict: Literal["block", "allow"]
    category: Literal["prompt_injection", "prompt_leak", "attack_request", "none"]


@dataclass(frozen=True)
class ClassifierResult:
    status: str  # "ok" | "invalid" | "error"
    verdict: str | None  # "block" | "allow"; "block" when invalid; None on error
    category: str | None  # None when invalid or error
    error_type: str | None  # None when ok; the reason when invalid; the exception class on error
    latency_ms: float
    usage: dict[str, int] | None  # input_tokens, output_tokens, total_tokens
    model: str | None

    def as_metadata(self) -> dict[str, Any]:
        """Return dict with status, verdict, category, error_type, latency_ms, model (no usage)."""
        return {
            "status": self.status,
            "verdict": self.verdict,
            "category": self.category,
            "error_type": self.error_type,
            "latency_ms": self.latency_ms,
            "model": self.model,
        }


def load_classifier_prompt(path: Path | None = None) -> str:
    """Load the guardrail classifier prompt from markdown template."""
    target = path or PROMPT_PATH
    return target.read_text(encoding="utf-8").strip()


def format_classifier_input(text: str) -> str:
    """Escape angle brackets and wrap text inside <message> tags."""
    escaped = text.replace("<", "&lt;").replace(">", "&gt;")
    return f"<message>\n{escaped}\n</message>"


class InjectionClassifier:
    """LLM classifier validating user messages against injection and attacks via GuardrailVerdict."""

    def __init__(self, model: BaseChatModel | None = None, prompt_path: Path | None = None) -> None:
        self._model = model
        self.prompt_path = prompt_path
        self._bound_model: Any = None
        self._model_name: str | None = None

    def _ensure_bound_model(self) -> None:
        if self._bound_model is not None:
            return
        raw_model = self._model
        if raw_model is None:
            model_name = settings.GUARDRAIL_CLASSIFIER_MODEL or None
            raw_model = get_chat_model(
                model_name,
                timeout_s=settings.GUARDRAIL_CLASSIFIER_TIMEOUT_S,
                max_retries=0,
            )
        self._model_name = extract_model_name(raw_model)
        try:
            self._bound_model = raw_model.bind_tools([GuardrailVerdict], tool_choice="GuardrailVerdict")
        except CONFIG_EXCEPTIONS as exc:
            raise LLMConfigurationError(type(exc).__name__) from exc

    def classify(self, text: str) -> ClassifierResult:
        """Classify input text using the bound LLM model and return ClassifierResult."""
        self._ensure_bound_model()

        messages = [
            SystemMessage(content=load_classifier_prompt(self.prompt_path)),
            HumanMessage(content=format_classifier_input(text)),
        ]

        t0 = time.perf_counter()
        caller_name = "WebGuardrailClassifier" if self.prompt_path == WEB_PROMPT_PATH else "InjectionClassifier"
        with span(
            "llm.call",
            {
                "llm.caller": caller_name,
                "llm.model": self._model_name,
                "llm.fallback_used": False,
            },
        ):
            try:
                response = self._bound_model.invoke(messages)
            except (LLMNotConfiguredError, LLMConfigurationError):
                metrics.inc_llm_call(caller_name, "error")
                if caller_name == "InjectionClassifier":
                    metrics.inc_guardrail_classifier("error")
                set_attributes({"llm.status": "error"})
                raise
            except CONFIG_EXCEPTIONS as exc:
                metrics.inc_llm_call(caller_name, "error")
                if caller_name == "InjectionClassifier":
                    metrics.inc_guardrail_classifier("error")
                set_attributes({"llm.status": "error"})
                raise LLMConfigurationError(type(exc).__name__) from exc
            except Exception as exc:  # noqa: BLE001
                latency = round((time.perf_counter() - t0) * 1000, 2)
                metrics.inc_llm_call(caller_name, "error")
                if caller_name == "InjectionClassifier":
                    metrics.inc_guardrail_classifier("error")
                set_attributes({"llm.status": "error"})
                return ClassifierResult(
                    status="error",
                    verdict=None,
                    category=None,
                    error_type=type(exc).__name__,
                    latency_ms=latency,
                    usage=None,
                    model=self._model_name,
                )

            metrics.inc_llm_call(caller_name, "ok")
            usage = getattr(response, "usage_metadata", None)
            span_attrs: dict[str, Any] = {"llm.status": "ok"}
            if isinstance(usage, dict):
                if usage.get("input_tokens") is not None:
                    span_attrs["llm.input_tokens"] = int(usage["input_tokens"])
                if usage.get("output_tokens") is not None:
                    span_attrs["llm.output_tokens"] = int(usage["output_tokens"])
            set_attributes(span_attrs)

        latency = round((time.perf_counter() - t0) * 1000, 2)

        tool_calls = getattr(response, "tool_calls", None) or []
        verdict_call = next((tc for tc in tool_calls if tc.get("name") == "GuardrailVerdict"), None)
        if not verdict_call:
            if caller_name == "InjectionClassifier":
                metrics.inc_guardrail_classifier("invalid")
            return ClassifierResult(
                status="invalid",
                verdict="block",
                category=None,
                error_type="no_verdict_call",
                latency_ms=latency,
                usage=usage,
                model=self._model_name,
            )

        args = verdict_call.get("args") or {}
        try:
            parsed = GuardrailVerdict(**args)
        except Exception:  # noqa: BLE001
            if caller_name == "InjectionClassifier":
                metrics.inc_guardrail_classifier("invalid")
            return ClassifierResult(
                status="invalid",
                verdict="block",
                category=None,
                error_type="invalid_arguments",
                latency_ms=latency,
                usage=usage,
                model=self._model_name,
            )

        if (parsed.verdict == "allow") != (parsed.category == "none"):
            if caller_name == "InjectionClassifier":
                metrics.inc_guardrail_classifier("invalid")
            return ClassifierResult(
                status="invalid",
                verdict="block",
                category=None,
                error_type="incoherent_verdict",
                latency_ms=latency,
                usage=usage,
                model=self._model_name,
            )

        if caller_name == "InjectionClassifier":
            metrics.inc_guardrail_classifier("ok")
        return ClassifierResult(
            status="ok",
            verdict=parsed.verdict,
            category=parsed.category,
            error_type=None,
            latency_ms=latency,
            usage=usage,
            model=self._model_name,
        )
