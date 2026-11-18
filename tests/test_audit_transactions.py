"""Offline unit tests for transactional ticket audit, system actor escalation, and fail-closed action errors."""
from __future__ import annotations

import json
import logging
from contextlib import suppress
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

import src.core.actions_db as adb
import src.core.tickets_db as tdb
import src.rag.retriever as rag_retriever
from src.config import settings
from src.core.graph import OrchestrationGraph
from tests.fakes import ScriptedChatModel


def _tool_call_msg(name: str, args: dict, call_id: str = "call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def _plan_msg(
    *,
    scope: str = "support",
    lang: str = "pt",
    esc: str = "none",
    ac: str = "none",
    steps: list[dict] | None = None,
) -> AIMessage:
    return _tool_call_msg(
        "TurnPlan",
        {
            "reply_language": lang,
            "scope": scope,
            "escalation_request": esc,
            "action_confirmation": ac,
            "steps": steps if steps is not None else [{"goal": "Handle request", "delegate": "none"}],
        },
        call_id="plan_1",
    )


def test_ticket_audit_failures_roll_back_ticket_mutations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DATABASE_URL", "")
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "tickets.db"))
    tdb.reset_tickets_repository()
    try:
        repo = tdb.get_tickets_repository()
        monkeypatch.setattr(adb, "user_hash", lambda _u: (_ for _ in ()).throw(RuntimeError("audit boom")))
        with pytest.raises(RuntimeError, match="audit boom"):
            repo.create_ticket(user_id="cliente1988", reason="falha criação", session_id="s-1")
        assert repo.list_tickets(limit=50) == []

        monkeypatch.undo()
        monkeypatch.setattr(settings, "DATABASE_URL", "")
        monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "tickets.db"))
        created = repo.create_ticket(user_id="cliente1988", reason="sucesso", session_id="s-2")
        tid = created["ticket_id"]

        monkeypatch.setattr(adb, "user_hash", lambda _u: (_ for _ in ()).throw(RuntimeError("audit boom")))
        with pytest.raises(RuntimeError, match="audit boom"):
            repo.update_ticket(tid, status="in_progress", operator_id="op-1")
        assert (repo.get_ticket(tid) or {}).get("status") == "open"

        monkeypatch.undo()
        monkeypatch.setattr(settings, "DATABASE_URL", "")
        monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "tickets.db"))
        repo.update_ticket(tid, reply="Resposta do operador.", operator_id="op-1")

        monkeypatch.setattr(adb, "user_hash", lambda _u: (_ for _ in ()).throw(RuntimeError("audit boom")))
        with pytest.raises(RuntimeError, match="audit boom"):
            repo.mark_delivered(tid)
        assert (repo.get_ticket(tid) or {}).get("delivered_at") is None
    finally:
        tdb.reset_tickets_repository()


def test_ticket_lifecycle_happy_path_writes_all_four_audit_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DATABASE_URL", "")
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "tickets.db"))
    tdb.reset_tickets_repository()
    try:
        repo = tdb.get_tickets_repository()
        created = repo.create_ticket(user_id="cliente_privado", reason="dúvida taxas", session_id="s-ok")
        tid = created["ticket_id"]
        repo.update_ticket(tid, status="in_progress", operator_id="operador_1")
        repo.update_ticket(tid, reply="Segue resposta detalhada.", operator_id="operador_1")
        assert repo.mark_delivered(tid) is True
        assert repo.mark_delivered(tid) is False

        events = adb.get_actions_repository().list_audit(limit=50, target_id=tid)
        actions = sorted(str(ev["action"]) for ev in events)
        assert actions == [
            "ticket_created",
            "ticket_replied",
            "ticket_reply_delivered",
            "ticket_updated",
            "ticket_updated",
        ]
        blob = json.dumps(events, ensure_ascii=False, default=str)
        assert "cliente_privado" not in blob
        assert "operador_1" not in blob
    finally:
        tdb.reset_tickets_repository()


def test_repeated_abstention_auto_escalation_audits_system_actor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _AbstainRetriever:
        def search(self, query: str) -> dict:
            return {"status": "abstain", "query": query, "documents": [], "min_score": 0.6}

    monkeypatch.setattr(settings, "DATABASE_URL", "")
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "auto.db"))
    monkeypatch.setattr(settings, "ESCALATE_AFTER_ABSTENTIONS", 2)
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: _AbstainRetriever())
    tdb.reset_tickets_repository()
    try:
        def _turn(text: str) -> list[AIMessage]:
            return [
                _tool_call_msg("ask_knowledge_agent", {"question": "q"}, call_id="c1"),
                _tool_call_msg("search_knowledge_base", {"query": "q"}, call_id="c2"),
                AIMessage(content="Não encontrei nas fontes."),
                AIMessage(content=text),
            ]

        g = OrchestrationGraph(chat_model=ScriptedChatModel(responses=_turn("R1") + _turn("R2")))
        g.run_sync(user_id="cliente1988", session_id="s-auto", message="Pergunta 1")
        state2 = g.run_sync(user_id="cliente1988", session_id="s-auto", message="Pergunta 2")
        tid = state2.escalation_ticket_id
        assert tid is not None
        events = adb.get_actions_repository().list_audit(limit=20, target_id=tid, action="ticket_created")
        assert [ev["actor_type"] for ev in events] == ["system"]
    finally:
        tdb.reset_tickets_repository()


def test_confirm_and_decline_db_errors_fail_closed_without_leaking_error_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(self, *args, **kwargs):
        raise RuntimeError("sensitive-db-connection-secret")

    monkeypatch.setattr(adb.ActionsRepository, "confirm", _boom)
    monkeypatch.setattr(adb.ActionsRepository, "decline", _boom)

    captured_logs: list[str] = []

    class _MemHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            with suppress(Exception):
                captured_logs.append(self.format(record))

    logger = logging.getLogger("multiagent")
    handler = _MemHandler()
    logger.addHandler(handler)
    try:
        g_confirm = OrchestrationGraph(
            chat_model=ScriptedChatModel(
                responses=[
                    _tool_call_msg("confirm_pending_action", {}),
                    AIMessage(content="Instabilidade ao confirmar; tente novamente."),
                ]
            ),
            planner_model=ScriptedChatModel(responses=[_plan_msg(ac="confirmed")]),
            checkpointer=MemorySaver(),
        )
        res_confirm = g_confirm.run_sync(user_id="cliente1988", session_id="s-c", message="Sim, pode trocar.")

        g_decline = OrchestrationGraph(
            chat_model=ScriptedChatModel(responses=[AIMessage(content="Certo, pedido cancelado.")]),
            planner_model=ScriptedChatModel(responses=[_plan_msg(ac="declined")]),
            checkpointer=MemorySaver(),
        )
        res_decline = g_decline.run_sync(user_id="cliente1988", session_id="s-d", message="Não quero mais.")
    finally:
        logger.removeHandler(handler)

    assert res_confirm.action == {
        "tool": "confirm_pending_action",
        "status": "error",
        "action_id": None,
        "request_id": None,
    }
    assert "confirm_pending_action" not in res_confirm.tools_used
    assert res_confirm.error is None
    assert "Instabilidade ao confirmar" in res_confirm.agent_response

    assert res_decline.action == {
        "tool": "decline_pending_action",
        "status": "error",
        "action_id": None,
        "request_id": None,
    }
    assert res_decline.error is None
    assert "Certo" in res_decline.agent_response

    combined = "\n".join(captured_logs) + res_confirm.agent_response + res_decline.agent_response
    assert "sensitive-db-connection-secret" not in combined
