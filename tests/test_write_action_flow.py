"""Offline end-to-end graph tests for proposal/confirmation write action flow (Phase 13C)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.config import settings
from src.core.actions_db import get_actions_repository
from src.core.graph import OrchestrationGraph
from src.core.tickets_db import reset_tickets_repository
from src.eval.runner import observe_turn
from tests.fakes import ScriptedChatModel


def _plan(
    lang: str = "pt",
    scope: str = "support",
    ac: str = "none",
    steps: list[dict[str, str]] | None = None,
) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "TurnPlan",
                "args": {
                    "reply_language": lang,
                    "scope": scope,
                    "escalation_request": "none",
                    "action_confirmation": ac,
                    "steps": [{"goal": "Handle terminal replacement", "delegate": "support"}]
                    if steps is None
                    else steps,
                },
                "id": "call_plan_act",
            }
        ],
    )


def _tc(name: str, args: dict[str, Any], cid: str = "tc_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])


def _propose_sequence(serial: str = "GET-883921") -> list[AIMessage]:
    return [
        _tc("ask_support_agent", {"request": f"Trocar maquininha {serial}"}, "c1"),
        _tc("request_terminal_replacement", {"serial_number": serial, "reason": "tela quebrada"}, "c2"),
        AIMessage(content=f"Proposta criada para {serial}; confirme na próxima mensagem."),
        AIMessage(content=f"Posso solicitar a troca da maquininha {serial}? Confirme na próxima mensagem."),
    ]


def test_propose_then_confirm_next_turn_executes(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t1.db"))
    reset_tickets_repository()
    try:
        sup = ScriptedChatModel(
            responses=_propose_sequence()
            + [_tc("confirm_pending_action", {}, "c3"), AIMessage(content="Pedido de troca confirmado.")]
        )
        planner = ScriptedChatModel(responses=[_plan(), _plan(ac="confirmed")])
        orch = OrchestrationGraph(chat_model=sup, planner_model=planner, checkpointer=MemorySaver())

        st1 = orch.run_sync("cliente1988", "Quero trocar a GET-883921.", session_id="s-act-1")
        st2 = orch.run_sync("cliente1988", "Sim, pode confirmar.", session_id="s-act-1")

        assert st1.action is not None and st1.action["status"] == "pending_confirmation"
        assert "request_terminal_replacement" in st1.tools_used
        assert "confirm_pending_action" not in st1.tools_used

        assert st2.action is not None and st2.action["status"] == "executed"
        assert str(st2.action["request_id"]).startswith("GET-TRC-")
        assert "confirm_pending_action" in st2.tools_used
        assert len(get_actions_repository().list_replacements("cliente1988")) == 1
    finally:
        reset_tickets_repository()


def test_confirmation_in_same_turn_does_not_execute(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t2.db"))
    reset_tickets_repository()
    try:
        sup = ScriptedChatModel(
            responses=_propose_sequence()[:3]
            + [_tc("confirm_pending_action", {}, "c3"), AIMessage(content="Confirme apenas no próximo turno.")]
        )
        orch = OrchestrationGraph(
            chat_model=sup,
            planner_model=ScriptedChatModel(responses=[_plan(ac="confirmed")]),
            checkpointer=MemorySaver(),
        )
        st = orch.run_sync("cliente1988", "Troca a GET-883921 e já confirmo agora.", session_id="s-same-turn")
        assert st.action is not None and st.action["status"] == "same_turn"
        assert "confirm_pending_action" not in st.tools_used
        assert get_actions_repository().list_replacements() == []
    finally:
        reset_tickets_repository()


def test_confirm_blocked_when_action_confirmation_is_none(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t3.db"))
    reset_tickets_repository()
    try:
        sup = ScriptedChatModel(
            responses=[_tc("confirm_pending_action", {}, "c1"), AIMessage(content="Não há solicitação pendente.")]
        )
        orch = OrchestrationGraph(
            chat_model=sup,
            planner_model=ScriptedChatModel(responses=[_plan(ac="none")]),
            checkpointer=MemorySaver(),
        )
        st = orch.run_sync("cliente1988", "Sim!", session_id="s-gate-none")
        assert st.action == {
            "tool": "confirm_pending_action",
            "status": "needs_merchant_confirmation",
            "action_id": None,
            "request_id": None,
        }
        assert "confirm_pending_action" not in st.tools_used
    finally:
        reset_tickets_repository()


def test_confirm_rejected_without_planner_fail_closed(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t4.db"))
    reset_tickets_repository()
    try:
        sup = ScriptedChatModel(
            responses=[_tc("confirm_pending_action", {}, "c1"), AIMessage(content="Não foi possível confirmar.")]
        )
        orch = OrchestrationGraph(chat_model=sup, checkpointer=MemorySaver())
        st = orch.run_sync("cliente1988", "Sim, confirmo.", session_id="s-no-plan")
        assert st.plan is not None and st.plan["status"] == "disabled"
        assert st.action is not None and st.action["status"] == "needs_merchant_confirmation"
        assert "confirm_pending_action" not in st.tools_used
        assert get_actions_repository().list_replacements() == []
    finally:
        reset_tickets_repository()


def test_decline_in_next_turn_resolves_proposal(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t5.db"))
    reset_tickets_repository()
    try:
        sup = ScriptedChatModel(responses=_propose_sequence() + [AIMessage(content="Tudo bem, cancelei.")])
        planner = ScriptedChatModel(responses=[_plan(), _plan(ac="declined")])
        orch = OrchestrationGraph(chat_model=sup, planner_model=planner, checkpointer=MemorySaver())

        orch.run_sync("cliente1988", "Trocar GET-883921", session_id="s-decl")
        st2 = orch.run_sync("cliente1988", "Não, deixa pra lá.", session_id="s-decl")
        assert st2.action is not None
        assert st2.action["tool"] == "decline_pending_action"
        assert st2.action["status"] == "declined"
        assert "confirm_pending_action" not in st2.tools_used
    finally:
        reset_tickets_repository()


def test_other_merchant_or_unknown_serial_returns_not_found(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t6.db"))
    reset_tickets_repository()
    try:
        sup = ScriptedChatModel(responses=_propose_sequence(serial="GET-000000"))
        orch = OrchestrationGraph(
            chat_model=sup,
            planner_model=ScriptedChatModel(responses=[_plan()]),
            checkpointer=MemorySaver(),
        )
        st = orch.run_sync("cliente1988", "Trocar GET-000000", session_id="s-bad-serial")
        assert st.action is not None and st.action["status"] == "not_found"
        assert any(a["outcome"] == "not_found" for a in get_actions_repository().list_audit())
    finally:
        reset_tickets_repository()


def test_tools_used_contains_confirm_only_on_accepted_confirmation(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t7.db"))
    reset_tickets_repository()
    try:
        sup = ScriptedChatModel(
            responses=[_tc("confirm_pending_action", {}, "c1"), AIMessage(content="Não encontrei proposta pendente.")]
        )
        orch = OrchestrationGraph(
            chat_model=sup,
            planner_model=ScriptedChatModel(responses=[_plan(ac="confirmed")]),
            checkpointer=MemorySaver(),
        )
        st = orch.run_sync("cliente1988", "Sim", session_id="s-empty-conf")
        assert st.action is not None and st.action["status"] == "no_pending_action"
        assert "confirm_pending_action" not in st.tools_used
    finally:
        reset_tickets_repository()


def test_observe_turn_records_action_field(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t8.db"))
    reset_tickets_repository()
    try:
        orch = OrchestrationGraph(
            chat_model=ScriptedChatModel(responses=_propose_sequence()),
            planner_model=ScriptedChatModel(responses=[_plan()]),
            checkpointer=MemorySaver(),
        )
        st = orch.run_sync("cliente1988", "Trocar GET-883921", session_id="s-rec")
        obs = observe_turn(st, "Trocar GET-883921", 12.0)
        assert "action" in obs
        assert obs["action"] is not None
        assert obs["action"]["tool"] == "request_terminal_replacement"
        assert obs["action"]["status"] == "pending_confirmation"
    finally:
        reset_tickets_repository()
