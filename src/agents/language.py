"""Reply language detection, preserved-token extraction, and constrained language rewriting."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.exceptions import (
    ModelAuthenticationError,
    ModelInvalidRequestError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langdetect import DetectorFactory, detect_langs

from src.config import settings
from src.core.llm import (
    LLMConfigurationError,
    LLMNotConfiguredError,
    extract_model_name,
    get_chat_model,
)
from src.core.tickets_db import _get_message_text
from src.core.tracing import set_attributes, span

DetectorFactory.seed = 0

CONFIG_EXCEPTIONS = (
    ModelNotFoundError,
    ModelAuthenticationError,
    ModelPermissionDeniedError,
    ModelInvalidRequestError,
)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "language_rewrite.md"

_URL_RE = re.compile(r"https?://\S+")
_TICKET_RE = re.compile(r"GET-TKT-[0-9A-Z-]+")
_NUM_TOKEN_RE = re.compile(r"\d[\d.,]*\d")
_DIGITS_RE = re.compile(r"\d+")
_MD_RE = re.compile(r"[*_`#>\[\]()~|]+")
_URL_TRAILING = ")]}>.,;:!?\"'*`"
_MIN_LETTERS = 20
_MIN_CONFIDENCE = 0.80


@dataclass(frozen=True)
class RewriteResult:
    """Outcome of a LanguageRewriter invocation."""

    status: str  # "ok" | "error"
    text: str | None
    error_type: str | None
    latency_ms: float
    usage: dict[str, int] | None
    model: str | None


def load_rewrite_prompt(target: str, path: Path | None = None) -> str:
    """Load the language rewrite prompt formatted for the target language ('pt' or 'en')."""
    target_path = path or PROMPT_PATH
    lang_name = "English" if target == "en" else "Brazilian Portuguese"
    return target_path.read_text(encoding="utf-8").strip().replace("{language}", lang_name)


def detect_reply_language(text: str) -> str:
    """Detect whether text is reliably Portuguese ('pt'), English ('en'), 'other', or 'undetermined'."""
    if not text:
        return "undetermined"
    cleaned = _URL_RE.sub(" ", text)
    cleaned = _TICKET_RE.sub(" ", cleaned)
    cleaned = _DIGITS_RE.sub(" ", cleaned)
    cleaned = _MD_RE.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split())
    if sum(1 for ch in cleaned if ch.isalpha()) < _MIN_LETTERS:
        return "undetermined"
    try:
        candidates = detect_langs(cleaned)
    except Exception:  # noqa: BLE001
        return "undetermined"
    if not candidates:
        return "undetermined"
    top = candidates[0]
    if float(top.prob) >= _MIN_CONFIDENCE:
        return top.lang if top.lang in ("pt", "en") else "other"
    return "undetermined"


def preserved_tokens(text: str) -> set[str]:
    """Return URLs, ticket IDs, and 2+ digit numbers that must be preserved verbatim."""
    tokens: set[str] = set()
    for raw_url in _URL_RE.findall(text):
        for part in raw_url.split("]("):
            if not part.startswith(("http://", "https://")):
                continue
            clean_url = part.rstrip(_URL_TRAILING)
            if len(clean_url) > 8:
                tokens.add(clean_url)
    for tid in _TICKET_RE.findall(text):
        clean_tid = tid.rstrip("-")
        if clean_tid:
            tokens.add(clean_tid)
    without_refs = _TICKET_RE.sub(" ", _URL_RE.sub(" ", text))
    tokens.update(_NUM_TOKEN_RE.findall(without_refs))
    return tokens


def _extract_usage(response: Any) -> dict[str, int] | None:
    raw = getattr(response, "usage_metadata", None)
    if not isinstance(raw, dict):
        return None
    inp = int(raw.get("input_tokens") or 0)
    out = int(raw.get("output_tokens") or 0)
    tot = int(raw.get("total_tokens") if raw.get("total_tokens") is not None else (inp + out))
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": tot}


class LanguageRewriter:
    """Lazy LLM translator rewriting an answer into the merchant's language without altering facts."""

    def __init__(self, model: BaseChatModel | None = None, prompt_path: Path | None = None) -> None:
        self._model = model
        self.prompt_path = prompt_path
        self._ready_model: BaseChatModel | None = None
        self._model_name: str | None = None

    def _ensure_model(self) -> None:
        if self._ready_model is not None:
            return
        raw_model = self._model
        if raw_model is None:
            raw_model = get_chat_model(
                settings.LLM_MODEL,
                timeout_s=settings.LLM_TIMEOUT_S,
                max_retries=0,
            )
        self._ready_model = raw_model
        self._model_name = extract_model_name(raw_model)

    def rewrite(self, text: str, target: str) -> RewriteResult:
        """Translate/rewrite text into target language ('pt' or 'en') without tool calls."""
        self._ensure_model()
        assert self._ready_model is not None
        messages = [
            SystemMessage(content=load_rewrite_prompt(target, self.prompt_path)),
            HumanMessage(content=text),
        ]

        t0 = time.perf_counter()
        with span(
            "llm.call",
            {
                "llm.caller": "LanguageRewriter",
                "llm.model": self._model_name,
                "llm.fallback_used": False,
            },
        ):
            try:
                response = self._ready_model.invoke(messages)
            except (LLMNotConfiguredError, LLMConfigurationError):
                set_attributes({"llm.status": "error"})
                raise
            except CONFIG_EXCEPTIONS as exc:
                set_attributes({"llm.status": "error"})
                raise LLMConfigurationError(type(exc).__name__) from exc
            except Exception as exc:  # noqa: BLE001
                latency = round((time.perf_counter() - t0) * 1000, 2)
                set_attributes({"llm.status": "error"})
                return RewriteResult(
                    status="error",
                    text=None,
                    error_type=type(exc).__name__,
                    latency_ms=latency,
                    usage=None,
                    model=self._model_name,
                )

            usage = _extract_usage(response)
            span_attrs: dict[str, Any] = {"llm.status": "ok"}
            if usage:
                span_attrs["llm.input_tokens"] = usage["input_tokens"]
                span_attrs["llm.output_tokens"] = usage["output_tokens"]
            set_attributes(span_attrs)

        latency = round((time.perf_counter() - t0) * 1000, 2)
        rewritten = _get_message_text(response).strip()
        return RewriteResult(
            status="ok",
            text=rewritten,
            error_type=None,
            latency_ms=latency,
            usage=usage,
            model=self._model_name,
        )
