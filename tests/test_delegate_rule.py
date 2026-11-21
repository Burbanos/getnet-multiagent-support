"""Offline tests for Phase 15D delegation guarantee and graph integration."""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.agents.planner import (
    MAX_PLAN_STEPS,
    SUPPORT_STEP_GOALS,
    Planner,
    PlanStep,
    TurnPlan,
    apply_delegate_rule,
)
from src.config import settings
from src.core.graph import OrchestrationGraph
from tests.fakes import ScriptedChatModel


def _mk_plan(
    steps: list[tuple[str, str]],
    *,
    scope: str = "support",
    escalation_request: str = "none",
    code_source: str = "none",
    terminal_issue: str = "none",
) -> TurnPlan:
    return TurnPlan(
        reply_language="en",
        scope=scope,
        escalation_request=escalation_request,
        action_confirmation="none",
        code_source=code_source,
        terminal_issue=terminal_issue,
        steps=[PlanStep(goal=g, delegate=d) for g, d in steps],
    )


def _tc(name: str, args: dict[str, Any]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"}],
    )


def test_apply_delegate_rule_flips_first_knowledge_and_is_pure() -> None:
    orig = _mk_plan(
        [("Explain decline code 96", "knowledge"), ("Check installment rules", "knowledge")],
        code_source="declined_sale",
    )
    snapshot = orig.model_dump()
    updated, reason = apply_delegate_rule(orig)

    assert reason == "declined_sale"
    assert [s.delegate for s in updated.steps] == ["support", "knowledge"]
    assert updated.steps[0].goal == "Explain decline code 96"
    assert orig.model_dump() == snapshot


def test_apply_delegate_rule_terminal_not_working_flip_and_append() -> None:
    p_flip = _mk_plan(
        [("Explain Wi-Fi disconnect", "knowledge")],
        terminal_issue="not_working",
    )
    out_flip, reason_flip = apply_delegate_rule(p_flip)
    assert reason_flip == "terminal_not_working"
    assert [s.delegate for s in out_flip.steps] == ["support"]

    p_app = _mk_plan([("Acknowledge greeting", "none")], terminal_issue="not_working")
    out_app, reason_app = apply_delegate_rule(p_app)
    assert reason_app == "terminal_not_working"
    assert [s.delegate for s in out_app.steps] == ["none", "support"]
    assert out_app.steps[-1].goal == SUPPORT_STEP_GOALS["terminal_not_working"]


def test_apply_delegate_rule_noops_when_ineligible() -> None:
    cases = [
        _mk_plan([("Check deposits", "support"), ("Check fees", "knowledge")], code_source="declined_sale"),
        _mk_plan([("Transfer request", "knowledge")], code_source="declined_sale", escalation_request="asked_for_human"),
        _mk_plan([], scope="out_of_scope", code_source="declined_sale"),
        _mk_plan([("Explain terminal screen 05", "knowledge")], code_source="terminal_screen"),
        _mk_plan([("Step", "none")] * MAX_PLAN_STEPS, terminal_issue="not_working"),
    ]
    for plan in cases:
        before = plan.model_dump()
        out, reason = apply_delegate_rule(plan)
        assert reason is None
        assert out.model_dump() == before


def test_apply_delegate_rule_precedence_prefers_declined_sale() -> None:
    plan = _mk_plan(
        [("Diagnose issue", "knowledge")],
        code_source="declined_sale",
        terminal_issue="not_working",
    )
    out, reason = apply_delegate_rule(plan)
    assert reason == "declined_sale"
    assert [s.delegate for s in out.steps] == ["support"]


def test_planner_plan_and_disabled_planner_metadata() -> None:
    model = ScriptedChatModel(
        responses=[
            _tc(
                "TurnPlan",
                {
                    "reply_language": "pt",
                    "scope": "support",
                    "escalation_request": "none",
                    "action_confirmation": "none",
                    "code_source": "none",
                    "terminal_issue": "not_working",
                    "steps": [{"goal": "Diagnose offline terminal", "delegate": "knowledge"}],
                },
            )
        ]
    )
    res = Planner(model).plan("Minha maquininha parou de conectar")
    meta = res.as_metadata()
    assert res.status == "ok"
    assert meta["terminal_issue"] == "not_working"
    assert meta["delegate_rule"] == "terminal_not_working"
    assert meta["steps"] == [{"goal": "Diagnose offline terminal", "delegate": "support"}]

    orch_off = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content="Oi!")]),
        planner_model=None,
        checkpointer=MemorySaver(),
    )
    st_off = orch_off.run_sync(user_id="cliente1988", message="Oi", session_id=f"s-off-{uuid.uuid4().hex[:6]}")
    assert (st_off.plan or {})["terminal_issue"] is None
    assert (st_off.plan or {})["delegate_rule"] is None


def test_graph_executes_diagnose_declined_transaction_after_delegate_correction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)
    planner = ScriptedChatModel(
        responses=[
            _tc(
                "TurnPlan",
                {
                    "reply_language": "en",
                    "scope": "support",
                    "escalation_request": "none",
                    "action_confirmation": "none",
                    "code_source": "declined_sale",
                    "terminal_issue": "none",
                    "steps": [{"goal": "Explain decline code 96", "delegate": "knowledge"}],
                },
            )
        ]
    )
    chat = ScriptedChatModel(
        responses=[
            _tc("ask_support_agent", {"request": "Explain decline code 96 on the merchant's sale"}),
            _tc("diagnose_declined_transaction", {"code_context": "declined_sale", "error_code": "96"}),
            AIMessage(content="Code 96 explained from account records."),
            AIMessage(content="Your declined sale code 96 indicates an issuer malfunction; ask to retry."),
        ]
    )
    orch = OrchestrationGraph(chat_model=chat, planner_model=planner, checkpointer=MemorySaver())
    st = orch.run_sync(
        user_id="cliente1988",
        message="A card sale was declined with code 96.",
        session_id=f"s-del-{uuid.uuid4().hex[:6]}",
    )
    assert (st.plan or {}).get("delegate_rule") == "declined_sale"
    assert [s["delegate"] for s in (st.plan or {}).get("steps") or []] == ["support"]
    assert "diagnose_declined_transaction" in (st.tools_used or [])
    assert (st.verification or {}).get("status") == "disabled"
