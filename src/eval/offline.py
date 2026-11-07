"""Offline evaluation runner with zero-network forbidden chat model."""
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

from src.core.graph import OrchestrationGraph


class ForbiddenChatModel(BaseChatModel):
    """Chat model that strictly blocks any network LLM generation and records call counts."""

    calls: int = 0

    def bind_tools(self, tools: Any, **kwargs: Any) -> Any:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.calls += 1
        raise RuntimeError("ForbiddenChatModel: LLM call attempted in offline mode")

    @property
    def _llm_type(self) -> str:
        return "forbidden"


def run_offline(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Execute evaluation cases through the full OrchestrationGraph using ForbiddenChatModel.
    Ensures deterministic, zero-network execution for local regression tests.
    """
    results: list[dict[str, Any]] = []

    for case in cases:
        model = ForbiddenChatModel()
        graph = OrchestrationGraph(chat_model=model)
        session_id = f"offline-{case['id']}"
        user_id = "cliente1988"

        turns: list[dict[str, Any]] = []
        status = "ok"
        error_type = None

        for msg in case.get("turns", []):
            t0 = time.perf_counter()
            try:
                res = graph.run_sync(
                    user_id=user_id,
                    message=msg,
                    session_id=session_id,
                )
                lat_ms = round((time.perf_counter() - t0) * 1000, 1)

                ticket_dict = res.ticket if isinstance(res.ticket, dict) else {}
                ticket_id = ticket_dict.get("ticket_id") or res.escalation_ticket_id
                ticket_priority = ticket_dict.get("priority")

                turns.append({
                    "message": msg,
                    "response": res.agent_response or "",
                    "agents_used": res.agents_used or [],
                    "tools_used": res.tools_used or [],
                    "sources": res.sources or [],
                    "retrieved_docs": [],
                    "ticket_id": ticket_id,
                    "ticket_priority": ticket_priority,
                    "is_safe": res.is_safe,
                    "handoff": res.handoff,
                    "llm_model": res.llm_model,
                    "tokens": res.tokens,
                    "latency_ms": lat_ms,
                })
            except Exception as exc:  # noqa: BLE001
                status = "error"
                error_type = type(exc).__name__
                break

        results.append({
            "id": case["id"],
            "status": status,
            "error_type": error_type,
            "turns": turns,
            "model_calls": model.calls,
        })

    return results
