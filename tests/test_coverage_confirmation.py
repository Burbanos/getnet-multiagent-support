"""Tests for skipping the plan_coverage gate on confirmation/refusal turns."""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.config import settings
from src.core.graph import OrchestrationGraph
from tests.fakes import ScriptedChatModel


def _plan_msg(ac: str, steps: list[dict[str, str]]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "TurnPlan",
                "args": {
                    "reply_language": "pt",
                    "scope": "support",
                    "escalation_request": "none",
                    "action_confirmation": ac,
                    "steps": steps,
                },
                "id": "call_plan_cov",
            }
        ],
    )


def test_plan_coverage_skipped_on_confirmation_and_declined_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PLAN_COVERAGE_ENABLED", True)
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(settings, "VERIFIER_ENABLED", False)

    for ac in ("declined", "confirmed"):
        supervisor = ScriptedChatModel(
            responses=[AIMessage(content="Tudo bem, registrado conforme sua confirmação agora.")]
        )
        planner = ScriptedChatModel(
            responses=[_plan_msg(ac, [{"goal": "Handle merchant confirmation", "delegate": "support"}])]
        )
        orch = OrchestrationGraph(chat_model=supervisor, planner_model=planner, checkpointer=MemorySaver())
        state = orch.run_sync(
            user_id="cliente1988",
            session_id=f"sess_cov_{ac}",
            message="Não, pode cancelar.",
        )
        assert state.coverage == {"status": "skipped", "missing": [], "retries": 0}
        assert len(supervisor.received) == 1


def test_plan_coverage_still_enforces_ordinary_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "PLAN_COVERAGE_ENABLED", True)
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(settings, "VERIFIER_ENABLED", False)

    supervisor = ScriptedChatModel(
        responses=[
            AIMessage(content="Primeira resposta sem chamar o especialista."),
            AIMessage(content="Segunda resposta sem chamar o especialista."),
        ]
    )
    planner = ScriptedChatModel(
        responses=[_plan_msg("none", [{"goal": "Check recent sales", "delegate": "support"}])]
    )
    orch = OrchestrationGraph(chat_model=supervisor, planner_model=planner, checkpointer=MemorySaver())
    state = orch.run_sync(
        user_id="cliente1988",
        session_id="sess_cov_none",
        message="Quanto vendi ontem?",
    )
    assert state.coverage["status"] == "incomplete"
    assert len(supervisor.received) == 2
