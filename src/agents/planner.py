"""Turn-level structured planner deciding language, scope, escalation request, and steps."""
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

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "planner.md"
MAX_PREVIOUS_REPLY_CHARS = 2000
MAX_PLAN_STEPS = 4


class PlanStep(BaseModel):
    """Single actionable sub-task in a turn plan."""

    goal: str
    delegate: Literal["knowledge", "support", "none"]


class TurnPlan(BaseModel):
    """Structured turn plan produced before supervisor execution."""

    reply_language: Literal["pt", "en"]
    scope: Literal["support", "out_of_scope"]
    escalation_request: Literal["none", "asked_for_human", "formal_complaint", "accepted_offer"]
    action_confirmation: Literal["none", "confirmed", "declined"] = "none"
    code_source: Literal["none", "declined_sale", "terminal_screen", "app", "unknown"] = "none"
    steps: list[PlanStep]


@dataclass(frozen=True)
class PlannerResult:
    """Outcome of a Planner invocation."""

    status: str  # "ok" | "invalid" | "error"
    plan: TurnPlan | None
    error_type: str | None
    latency_ms: float
    usage: dict[str, int] | None
    model: str | None

    def as_metadata(self) -> dict[str, Any]:
        """Return serializable metadata dictionary for graph state and turn records."""
        return {
            "status": self.status,
            "reply_language": self.plan.reply_language if self.plan else None,
            "scope": self.plan.scope if self.plan else None,
            "escalation_request": self.plan.escalation_request if self.plan else None,
            "action_confirmation": self.plan.action_confirmation if self.plan else None,
            "code_source": self.plan.code_source if self.plan else None,
            "steps": [{"goal": s.goal, "delegate": s.delegate} for s in self.plan.steps] if self.plan else None,
            "error_type": self.error_type,
            "latency_ms": self.latency_ms,
            "model": self.model,
        }


def load_planner_prompt(path: Path | None = None) -> str:
    """Load the planner system prompt from markdown."""
    target = path or PROMPT_PATH
    return target.read_text(encoding="utf-8").strip()


def _escape_brackets(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def format_planner_input(latest_message: str, previous_reply: str | None = None) -> str:
    """Escape delimiters and wrap optional previous reply (<=2000 chars) and latest message."""
    parts: list[str] = []
    if previous_reply:
        trimmed = previous_reply[:MAX_PREVIOUS_REPLY_CHARS]
        parts.append(f"<previous_reply>\n{_escape_brackets(trimmed)}\n</previous_reply>")
    parts.append(f"<message>\n{_escape_brackets(latest_message)}\n</message>")
    return "\n".join(parts)


def _extract_usage(response: Any) -> dict[str, int] | None:
    raw = getattr(response, "usage_metadata", None)
    if not isinstance(raw, dict):
        return None
    inp = int(raw.get("input_tokens") or 0)
    out = int(raw.get("output_tokens") or 0)
    tot = int(raw.get("total_tokens") if raw.get("total_tokens") is not None else (inp + out))
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": tot}


class Planner:
    """Lazy LLM planner returning a structured TurnPlan via forced tool calling."""

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
            self._bound_model = raw_model.bind_tools([TurnPlan], tool_choice="TurnPlan")
        except CONFIG_EXCEPTIONS as exc:
            raise LLMConfigurationError(type(exc).__name__) from exc

    def plan(self, latest_message: str, previous_reply: str | None = None) -> PlannerResult:
        """Produce a TurnPlan for one merchant turn."""
        self._ensure_bound_model()
        messages = [
            SystemMessage(content=load_planner_prompt(self.prompt_path)),
            HumanMessage(content=format_planner_input(latest_message, previous_reply)),
        ]

        t0 = time.perf_counter()
        with span(
            "llm.call",
            {
                "llm.caller": "Planner",
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
                return PlannerResult(
                    status="error",
                    plan=None,
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
        plan_call = next((tc for tc in tool_calls if tc.get("name") == "TurnPlan"), None)
        if not plan_call:
            return PlannerResult(
                status="invalid",
                plan=None,
                error_type="no_plan_call",
                latency_ms=latency,
                usage=usage,
                model=self._model_name,
            )

        args = plan_call.get("args") or {}
        try:
            parsed = TurnPlan(**args)
        except Exception:  # noqa: BLE001
            return PlannerResult(
                status="invalid",
                plan=None,
                error_type="invalid_arguments",
                latency_ms=latency,
                usage=usage,
                model=self._model_name,
            )

        if len(parsed.steps) > MAX_PLAN_STEPS:
            return PlannerResult(
                status="invalid",
                plan=None,
                error_type="too_many_steps",
                latency_ms=latency,
                usage=usage,
                model=self._model_name,
            )

        return PlannerResult(
            status="ok",
            plan=parsed,
            error_type=None,
            latency_ms=latency,
            usage=usage,
            model=self._model_name,
        )
