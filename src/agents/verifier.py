"""Pre-send draft answer verifier against turn plan steps and current-turn evidence."""
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

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "verifier.md"


class StepVerdict(BaseModel):
    """Verification judgment for one step of the turn plan."""

    step: int
    verdict: Literal["answered", "evidence_does_not_apply", "unsupported_claim", "not_answered"]
    note: str = ""


class Verification(BaseModel):
    """Structured verification response covering every step in 1..n order."""

    verdicts: list[StepVerdict]


@dataclass(frozen=True)
class VerifierResult:
    """Outcome of a Verifier invocation."""

    status: str  # "ok" | "invalid" | "error"
    verdicts: list[dict[str, Any]]
    failures: list[dict[str, Any]]
    error_type: str | None
    latency_ms: float
    usage: dict[str, int] | None
    model: str | None


def load_verifier_prompt(path: Path | None = None) -> str:
    """Load the verifier system prompt from markdown."""
    target = path or PROMPT_PATH
    return target.read_text(encoding="utf-8").strip()


def _escape_brackets(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def format_verifier_input(
    message: str,
    steps: list[dict[str, Any]],
    evidence: str,
    draft: str,
) -> str:
    """Escape delimiters and format message, numbered plan steps, evidence, and draft."""
    step_lines = [
        f"{idx}. [{_escape_brackets(str(s.get('delegate', 'none')))}] {_escape_brackets(str(s.get('goal', '')))}"
        for idx, s in enumerate(steps, start=1)
    ]
    steps_block = "\n".join(step_lines)
    return (
        f"<message>\n{_escape_brackets(message)}\n</message>\n"
        f"<plan_steps>\n{steps_block}\n</plan_steps>\n"
        f"<evidence>\n{_escape_brackets(evidence)}\n</evidence>\n"
        f"<draft>\n{_escape_brackets(draft)}\n</draft>"
    )


def _extract_usage(response: Any) -> dict[str, int] | None:
    raw = getattr(response, "usage_metadata", None)
    if not isinstance(raw, dict):
        return None
    inp = int(raw.get("input_tokens") or 0)
    out = int(raw.get("output_tokens") or 0)
    tot = int(raw.get("total_tokens") if raw.get("total_tokens") is not None else (inp + out))
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": tot}


class Verifier:
    """Lazy LLM verifier validating a draft response per planned step before sending."""

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
            raw_model = get_chat_model(
                settings.LLM_MODEL,
                timeout_s=settings.LLM_TIMEOUT_S,
                max_retries=0,
            )
        self._model_name = extract_model_name(raw_model)
        try:
            self._bound_model = raw_model.bind_tools([Verification], tool_choice="Verification")
        except CONFIG_EXCEPTIONS as exc:
            raise LLMConfigurationError(type(exc).__name__) from exc

    def verify(
        self,
        message: str,
        steps: list[dict[str, Any]],
        evidence: str,
        draft: str,
    ) -> VerifierResult:
        """Check whether a draft answer satisfies every plan step using only the supplied evidence."""
        self._ensure_bound_model()
        messages = [
            SystemMessage(content=load_verifier_prompt(self.prompt_path)),
            HumanMessage(content=format_verifier_input(message, steps, evidence, draft)),
        ]

        t0 = time.perf_counter()
        with span(
            "llm.call",
            {
                "llm.caller": "Verifier",
                "llm.model": self._model_name,
                "llm.fallback_used": False,
            },
        ):
            try:
                response = self._bound_model.invoke(messages)
            except (LLMNotConfiguredError, LLMConfigurationError):
                set_attributes({"llm.status": "error"})
                raise
            except CONFIG_EXCEPTIONS as exc:
                set_attributes({"llm.status": "error"})
                raise LLMConfigurationError(type(exc).__name__) from exc
            except Exception as exc:  # noqa: BLE001
                latency = round((time.perf_counter() - t0) * 1000, 2)
                set_attributes({"llm.status": "error"})
                return VerifierResult(
                    status="error",
                    verdicts=[],
                    failures=[],
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
        tool_calls = getattr(response, "tool_calls", None) or []
        verdict_call = next((tc for tc in tool_calls if tc.get("name") == "Verification"), None)
        if not verdict_call:
            return VerifierResult(
                status="invalid",
                verdicts=[],
                failures=[],
                error_type="no_verification_call",
                latency_ms=latency,
                usage=usage,
                model=self._model_name,
            )

        args = verdict_call.get("args") or {}
        try:
            parsed = Verification(**args)
        except Exception:  # noqa: BLE001
            return VerifierResult(
                status="invalid",
                verdicts=[],
                failures=[],
                error_type="invalid_arguments",
                latency_ms=latency,
                usage=usage,
                model=self._model_name,
            )

        expected_steps = list(range(1, len(steps) + 1))
        actual_steps = [v.step for v in parsed.verdicts]
        if len(parsed.verdicts) != len(steps) or actual_steps != expected_steps:
            return VerifierResult(
                status="invalid",
                verdicts=[],
                failures=[],
                error_type="step_mismatch",
                latency_ms=latency,
                usage=usage,
                model=self._model_name,
            )

        verdict_dicts = [{"step": v.step, "verdict": v.verdict, "note": v.note} for v in parsed.verdicts]
        failures = [d for d in verdict_dicts if d["verdict"] != "answered"]
        return VerifierResult(
            status="ok",
            verdicts=verdict_dicts,
            failures=failures,
            error_type=None,
            latency_ms=latency,
            usage=usage,
            model=self._model_name,
        )
