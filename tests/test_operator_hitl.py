"""Offline unit and integration tests for Phase 12C operator HITL, resume, and history trim."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from starlette.testclient import TestClient

import src.core.notifier as notifier_mod
import src.tools.agent_tools as agent_tools_mod
from src.config import settings
from src.core import metrics
from src.core.checkpointer import build_sqlite_checkpointer
from src.core.graph import (
    HANDOFF_REPLY_PREFIX,
    OPERATOR_MESSAGE_PREFIX,
    OrchestrationGraph,
)
from src.core.llm import LLMUnavailableError
from src.core.notifier import NotificationResult, OperatorNotifier, build_payload, reset_notifier
from src.core.tickets_db import TicketsRepository
from src.main import app
from tests.fakes import ScriptedChatModel


def _make_isolated_env(tmp_path: Path, monkeypatch, model: ScriptedChatModel):
    """Wire isolated SQLite ticket DB, checkpointer, and scripted chat model for offline tests."""
    repo = TicketsRepository(tmp_path / "tickets.db")
    saver = build_sqlite_checkpointer(tmp_path / "checkpoints.db")
    orch = OrchestrationGraph(chat_model=model, checkpointer=saver)

    monkeypatch.setattr("src.core.tickets_db.get_tickets_repository", lambda: repo)
    monkeypatch.setattr("src.tools.agent_tools.get_tickets_repository", lambda: repo)
    monkeypatch.setattr("src.core.graph.get_tickets_repository", lambda: repo)
    monkeypatch.setattr("src.main.get_tickets_repository", lambda: repo)
    monkeypatch.setattr("src.main.get_orchestrator", lambda: orch)

    return repo, saver, orch


@pytest.fixture(autouse=True)
def _clean_notifier_and_metrics():
    reset_notifier()
    metrics.reset()
    yield
    reset_notifier()


def test_notifier_disabled_when_url_empty(monkeypatch):
    monkeypatch.setattr(settings, "OPERATOR_WEBHOOK_URL", "")
    notifier = OperatorNotifier()
    res = notifier.notify(
        {"ticket_id": "GET-TKT-1", "priority": "standard", "created_at": "2026-11-12T00:00:00Z"}
    )
    assert res == NotificationResult(status="disabled", error_type=None, http_status=None)
    assert 'getnet_operator_notifications_total{status="disabled"} 1' in metrics.render()


def test_notifier_sent_200_and_excludes_sensitive_fields(monkeypatch):
    captured: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://ops.example.com/")
    client = httpx.Client(transport=httpx.MockTransport(handler))
    notifier = OperatorNotifier(url="https://hooks.example.com/notify", timeout_s=2.0, client=client)

    ticket = {
        "ticket_id": "GET-TKT-20261112-ABC",
        "priority": "high",
        "created_at": "2026-11-12T10:00:00Z",
        "reason": "merchant secret reason 12345",
        "transcript": [{"role": "user", "content": "meu CPF e 123.456.789-00"}],
        "user_id": "cliente-privado",
    }
    res = notifier.notify(ticket)

    assert res == NotificationResult(status="sent", error_type=None, http_status=200)
    assert len(captured) == 1
    payload = captured[0]
    assert payload["ticket_id"] == "GET-TKT-20261112-ABC"
    assert payload["priority"] == "high"
    assert payload["created_at"] == "2026-11-12T10:00:00Z"
    assert payload["url"] == "https://ops.example.com/tickets/GET-TKT-20261112-ABC"
    assert "reason" not in payload
    assert "transcript" not in payload
    assert "user_id" not in payload
    assert 'getnet_operator_notifications_total{status="sent"} 1' in metrics.render()


def test_notifier_handles_http_error_and_timeout_without_raising(monkeypatch):
    monkeypatch.setattr(settings, "OPERATOR_WEBHOOK_URL", "https://hooks.example.com/fail")

    client_500 = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(500, text="error"))
    )
    res_500 = OperatorNotifier(client=client_500).notify({"ticket_id": "GET-TKT-1"})
    assert res_500 == NotificationResult(status="failed", error_type="http_500", http_status=500)

    def timeout_handler(req: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=req)

    client_timeout = httpx.Client(transport=httpx.MockTransport(timeout_handler))
    res_to = OperatorNotifier(client=client_timeout).notify({"ticket_id": "GET-TKT-2"})
    assert res_to == NotificationResult(
        status="failed", error_type="TimeoutException", http_status=None
    )
    assert 'getnet_operator_notifications_total{status="failed"} 2' in metrics.render()


def test_build_payload_handles_empty_base_url(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "")
    payload = build_payload(
        {"ticket_id": "GET-TKT-99", "priority": "standard", "created_at": "2026-11-12T00:00:00Z"}
    )
    assert payload["url"] == "/tickets/GET-TKT-99"
    assert "GET-TKT-99" in payload["text"]


def test_tickets_db_migration_and_record_notification(tmp_path):
    db_file = tmp_path / "legacy_tickets.db"
    with sqlite3.connect(str(db_file)) as conn:
        conn.execute(
            """
            CREATE TABLE tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                channel TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

    repo = TicketsRepository(str(db_file))
    with sqlite3.connect(str(db_file)) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(tickets)").fetchall()}
    assert {"notified_at", "notification_status"}.issubset(cols)

    created = repo.create_ticket(user_id="cliente1988", reason="teste migracao")
    assert repo.record_notification(created["ticket_id"], "failed") is True
    failed_loaded = repo.get_ticket(created["ticket_id"])
    assert failed_loaded is not None
    assert failed_loaded["notification_status"] == "failed"
    assert failed_loaded["notified_at"] is None

    assert repo.record_notification(created["ticket_id"], "sent") is True
    assert repo.record_notification("GET-TKT-MISSING", "sent") is False

    loaded = repo.get_ticket(created["ticket_id"])
    assert loaded is not None
    assert loaded["notified_at"] is not None
    assert loaded["notification_status"] == "sent"


def test_escalate_to_human_survives_webhook_failure(tmp_path, monkeypatch):
    repo = TicketsRepository(tmp_path / "tickets.db")
    monkeypatch.setattr("src.tools.agent_tools.get_tickets_repository", lambda: repo)

    failing_client = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(503, text="unavailable"))
    )
    failing_notifier = OperatorNotifier(url="https://hooks.example.com/down", client=failing_client)
    monkeypatch.setattr(notifier_mod, "get_notifier", lambda: failing_notifier)

    raw_json = agent_tools_mod.escalate_to_human.invoke(
        {"reason": "maquininha com erro grave", "priority": "high"},
        config={"configurable": {"user_id": "cliente1988", "session_id": "sess-esc", "transcript": []}},
    )
    parsed = json.loads(raw_json)
    assert parsed["status"] == "success"
    stored = repo.get_ticket(parsed["ticket_id"])
    assert stored is not None
    assert stored["notification_status"] == "failed"

    class ExplodingNotifier:
        def notify(self, ticket):
            raise RuntimeError("unexpected boom")

    monkeypatch.setattr(notifier_mod, "get_notifier", lambda: ExplodingNotifier())
    raw_json2 = agent_tools_mod.escalate_to_human.invoke(
        {"reason": "segundo chamado", "priority": "standard"},
        config={"configurable": {"user_id": "cliente1988", "session_id": "sess-esc", "transcript": []}},
    )
    parsed2 = json.loads(raw_json2)
    assert parsed2["status"] == "success"


def test_resume_after_operator_happy_path_and_pii_masking(tmp_path, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "escalate_to_human",
                        "args": {"reason": "ajuste de cadastro", "priority": "high"},
                        "id": "call-esc-1",
                    }
                ],
            ),
            AIMessage(content="Vou encaminhar seu caso para o time humano."),
            AIMessage(content="O atendente confirmou a atualização cadastral para você."),
            AIMessage(content="Posso ajudar em mais alguma dúvida hoje!"),
        ]
    )
    repo, saver, orch = _make_isolated_env(tmp_path, monkeypatch, model)
    try:
        turn1 = orch.run_sync(user_id="cliente1988", message="Preciso alterar meu cadastro.", session_id="sess-hitl")
        tid = turn1.escalation_ticket_id
        assert tid is not None

        repo.update_ticket(
            tid,
            reply="Cadastro atualizado; documento 123.456.789-00 validado.",
            operator_id="op_maria",
        )
        res = orch.resume_after_operator(tid)
        assert res["status"] == "resumed"
        assert "atualização cadastral" in res["final_response"]

        # Verify PII was masked in the HumanMessage passed to the supervisor
        op_turn_msgs = model.received[2]
        assert any(
            isinstance(m, HumanMessage)
            and "123.456.789-00" not in str(m.content)
            and OPERATOR_MESSAGE_PREFIX.format(ticket_id=tid).splitlines()[0] in str(m.content)
            for m in op_turn_msgs
        )

        updated_ticket = repo.get_ticket(tid)
        assert updated_ticket is not None
        assert updated_ticket["delivered_at"] is not None

        snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:sess-hitl"}})
        assert snap.values.get("pending_ticket_id") is None

        # Next customer turn goes straight to supervisor without pending block
        turn2 = orch.run_sync(user_id="cliente1988", message="Obrigado!", session_id="sess-hitl")
        assert turn2.agent_response == "Posso ajudar em mais alguma dúvida hoje!"
    finally:
        saver.conn.close()


def test_resume_after_operator_verbatim_fallback_and_closes_dangling_tool_calls(tmp_path, monkeypatch):
    class FailingResumeModel(ScriptedChatModel):
        fail_on_call_index: int = 2
        call_count: int = 0

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self.call_count += 1
            if self.call_count == self.fail_on_call_index:
                raise LLMUnavailableError("simulated outage")
            if self.call_count == 3:
                # Raise AFTER returning an unexecuted tool call in call 3? Tested separately via fail_on_call_index=2.
                pass
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

    model = FailingResumeModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "escalate_to_human",
                        "args": {"reason": "erro na taxa", "priority": "standard"},
                        "id": "call-esc-2",
                    }
                ],
            ),
            AIMessage(content="Chamado aberto para análise humana."),
            AIMessage(content="Continuamos disponíveis por aqui!"),
        ],
        fail_on_call_index=3,
    )
    repo, saver, orch = _make_isolated_env(tmp_path, monkeypatch, model)
    try:
        t1 = orch.run_sync(user_id="cliente1988", message="Minha taxa veio errada.", session_id="sess-fb")
        tid = t1.escalation_ticket_id
        assert tid is not None

        repo.update_ticket(tid, reply="Taxa corrigida para o CPF 111.222.333-44.", operator_id="op_joao")
        res = orch.resume_after_operator(tid)
        assert res["status"] == "delivered_verbatim"
        assert res["error_type"] == "LLMUnavailableError"

        snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:sess-fb"}})
        assert snap.values.get("pending_ticket_id") is None
        last_msg = snap.values["messages"][-1]
        assert isinstance(last_msg, AIMessage)
        assert HANDOFF_REPLY_PREFIX.format(ticket_id=tid) in str(last_msg.content)
        assert "111.222.333-44" not in str(last_msg.content)
        assert snap.values.get("handoff", {}).get("status") == "delivered"

        # Next turn still succeeds smoothly
        t2 = orch.run_sync(user_id="cliente1988", message="Valeu!", session_id="sess-fb")
        assert t2.agent_response == "Continuamos disponíveis por aqui!"
    finally:
        saver.conn.close()


def test_resume_closes_dangling_tool_calls_when_mid_turn_tool_loop_fails(tmp_path, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "escalate_to_human", "args": {"reason": "suporte", "priority": "standard"}, "id": "c1"}
                ],
            ),
            AIMessage(content="Aguarde nosso time."),
        ]
    )
    repo, saver, orch = _make_isolated_env(tmp_path, monkeypatch, model)
    try:
        t1 = orch.run_sync(user_id="cliente1988", message="Erro S920", session_id="sess-dangle")
        tid = t1.escalation_ticket_id
        assert tid is not None
        repo.update_ticket(tid, reply="Reinicie o terminal.", operator_id="op_1")

        # Simulate a graph invocation that emits a dangling tool_call and then fails
        def failing_invoke(*args, **kwargs):
            orch.graph.update_state(
                kwargs["config"],
                {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[{"name": "diagnose_terminal", "args": {}, "id": "tc-dangling-99"}],
                        )
                    ]
                },
                as_node="supervisor",
            )
            raise LLMUnavailableError("down mid tool")

        monkeypatch.setattr(orch.graph, "invoke", failing_invoke)

        res = orch.resume_after_operator(tid)
        assert res["status"] == "delivered_verbatim"
        snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:sess-dangle"}})
        msgs = snap.values["messages"]
        assert any(isinstance(m, ToolMessage) and m.tool_call_id == "tc-dangling-99" for m in msgs)
        assert isinstance(msgs[-1], AIMessage)
        assert HANDOFF_REPLY_PREFIX.format(ticket_id=tid) in str(msgs[-1].content)
    finally:
        saver.conn.close()


def test_resume_after_operator_skips_not_pending_and_already_delivered(tmp_path, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "escalate_to_human", "args": {"reason": "duvida", "priority": "standard"}, "id": "c1"}
                ],
            ),
            AIMessage(content="Chamado aberto."),
            AIMessage(content="Resumo para o cliente."),
        ]
    )
    repo, saver, orch = _make_isolated_env(tmp_path, monkeypatch, model)
    try:
        assert orch.resume_after_operator("GET-TKT-NOPE") == {"status": "skipped", "reason": "no_reply"}

        # Ticket created outside an active checkpoint holding it
        orphan = repo.create_ticket(user_id="cliente1988", reason="avulso", session_id="sess-other")
        repo.update_ticket(orphan["ticket_id"], reply="Resposta", operator_id="op1")
        assert orch.resume_after_operator(orphan["ticket_id"]) == {"status": "skipped", "reason": "not_pending"}
        assert repo.get_ticket(orphan["ticket_id"])["delivered_at"] is None

        # Active ticket -> resume -> calling again returns already_delivered
        t1 = orch.run_sync(user_id="cliente1988", message="Preciso de ajuda", session_id="sess-dup")
        tid = t1.escalation_ticket_id
        repo.update_ticket(tid, reply="Aqui está a orientação.", operator_id="op1")
        assert orch.resume_after_operator(tid)["status"] == "resumed"
        assert orch.resume_after_operator(tid) == {"status": "skipped", "reason": "already_delivered"}
    finally:
        saver.conn.close()


def test_handoff_gate_releases_ticket_when_reply_already_delivered(tmp_path, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            AIMessage(content="Posso ajudar com outra questão agora."),
        ]
    )
    repo, saver, orch = _make_isolated_env(tmp_path, monkeypatch, model)
    try:
        ticket = repo.create_ticket(user_id="cliente1988", reason="teste", session_id="sess-rel")
        tid = ticket["ticket_id"]
        repo.update_ticket(tid, reply="Resposta já entregue", operator_id="op1")
        repo.mark_delivered(tid)

        # Simulate stale checkpoint still holding pending_ticket_id while delivered_at is already set
        orch.graph.update_state(
            {"configurable": {"thread_id": "cliente1988:sess-rel"}},
            {"pending_ticket_id": tid},
            as_node="tools",
        )

        turn = orch.run_sync(user_id="cliente1988", message="Nova pergunta", session_id="sess-rel")
        assert turn.agent_response == "Posso ajudar com outra questão agora."
        assert turn.handoff == {"ticket_id": tid, "status": "resumed"}
        snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:sess-rel"}})
        assert snap.values.get("pending_ticket_id") is None
    finally:
        saver.conn.close()


def test_trim_history_preserves_turn_boundaries_and_disables_on_zero(tmp_path, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            AIMessage(content="R1"),
            AIMessage(content="R2"),
            AIMessage(content="R3"),
            AIMessage(content="R4"),
        ]
    )
    _, saver, orch = _make_isolated_env(tmp_path, monkeypatch, model)
    try:
        # Disable trimming on first 2 turns
        monkeypatch.setattr(settings, "MAX_HISTORY_MESSAGES", 0)
        orch.run_sync(user_id="cliente1988", message="P1", session_id="sess-trim")
        orch.run_sync(user_id="cliente1988", message="P2", session_id="sess-trim")
        cfg = {"configurable": {"thread_id": "cliente1988:sess-trim"}}
        assert len(orch.graph.get_state(cfg).values["messages"]) == 4

        # Enable limit=4: run turn 3 (6 messages total -> trims turn 1 cleanly to start at HumanMessage P2)
        monkeypatch.setattr(settings, "MAX_HISTORY_MESSAGES", 4)
        orch.run_sync(user_id="cliente1988", message="P3", session_id="sess-trim")
        msgs = orch.graph.get_state(cfg).values["messages"]
        assert len(msgs) <= 4
        assert isinstance(msgs[0], HumanMessage)
        assert msgs[0].content == "P2"

        # Single large turn exceeding limit: must NOT trim below active turn's HumanMessage
        cfg_big = {"configurable": {"thread_id": "cliente1988:sess-big"}}
        orch.graph.update_state(
            cfg_big,
            {
                "messages": [
                    HumanMessage(content="Big turn prompt", id="h-big"),
                    AIMessage(
                        content="",
                        id="ai-tool",
                        tool_calls=[{"name": "diagnose_terminal", "args": {}, "id": "tc-1"}],
                    ),
                    ToolMessage(content="ok", tool_call_id="tc-1", id="tm-1"),
                    AIMessage(content="Done big", id="ai-end"),
                ]
            },
            as_node="abstention_check",
        )
        monkeypatch.setattr(settings, "MAX_HISTORY_MESSAGES", 2)
        removed = orch._trim_history(cfg_big)
        assert removed == 0
        assert len(orch.graph.get_state(cfg_big).values["messages"]) == 4
    finally:
        saver.conn.close()


def test_patch_ticket_endpoint_returns_resume_result_or_none(tmp_path, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "escalate_to_human", "args": {"reason": "suporte", "priority": "high"}, "id": "c1"}
                ],
            ),
            AIMessage(content="Chamado registrado."),
            AIMessage(content="Nosso atendente confirmou o ajuste."),
        ]
    )
    _, saver, _ = _make_isolated_env(tmp_path, monkeypatch, model)
    try:
        with TestClient(app) as client:
            chat_resp = client.post(
                "/chat",
                headers={"X-API-Key": "getnet-dev-key"},
                json={"message": "Preciso de suporte humano", "session_id": "sess-api"},
            )
            assert chat_resp.status_code == 200
            tid = chat_resp.json()["metadata"]["ticket"]["ticket_id"]

            # Status-only update: resume must be None
            p1 = client.patch(
                f"/tickets/{tid}",
                headers={"X-API-Key": "getnet-dev-operator"},
                json={"status": "in_progress"},
            )
            assert p1.status_code == 200
            assert p1.json()["resume"] is None

            # Reply update: resumes supervisor synchronously and updates delivered_at
            p2 = client.patch(
                f"/tickets/{tid}",
                headers={"X-API-Key": "getnet-dev-operator"},
                json={"reply": "Ajuste aplicado com sucesso."},
            )
            assert p2.status_code == 200
            body = p2.json()
            assert body["resume"]["status"] == "resumed"
            assert body["delivered_at"] is not None
    finally:
        saver.conn.close()


def test_session_messages_endpoint_auth_and_filtering(tmp_path, monkeypatch):
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "escalate_to_human", "args": {"reason": "dúvida", "priority": "standard"}, "id": "c1"}
                ],
            ),
            AIMessage(content="Abri seu chamado."),
            AIMessage(content="O atendente respondeu que seu link foi reativado."),
        ]
    )
    _, saver, _ = _make_isolated_env(tmp_path, monkeypatch, model)
    try:
        with TestClient(app) as client:
            # 401 without auth, 403 for operator, 422 for oversized session_id
            assert client.get("/sessions/sess-msg/messages").status_code == 401
            assert (
                client.get("/sessions/sess-msg/messages", headers={"X-API-Key": "getnet-dev-operator"}).status_code
                == 403
            )
            assert (
                client.get(
                    f"/sessions/{'x' * 65}/messages",
                    headers={"X-API-Key": "getnet-dev-key"},
                ).status_code
                == 422
            )

            # Empty unknown session
            empty_res = client.get("/sessions/sess-unknown/messages", headers={"X-API-Key": "getnet-dev-key"})
            assert empty_res.status_code == 200
            assert empty_res.json() == {"session_id": "sess-unknown", "messages": []}

            chat_res = client.post(
                "/chat",
                headers={"X-API-Key": "getnet-dev-key"},
                json={"message": "Meu link sumiu", "session_id": "sess-msg"},
            )
            tid = chat_res.json()["metadata"]["ticket"]["ticket_id"]

            client.patch(
                f"/tickets/{tid}",
                headers={"X-API-Key": "getnet-dev-operator"},
                json={"reply": "Link reativado."},
            )

            msg_res = client.get("/sessions/sess-msg/messages", headers={"X-API-Key": "getnet-dev-key"})
            assert msg_res.status_code == 200
            items = msg_res.json()["messages"]
            assert [m["role"] for m in items] == ["customer", "assistant", "assistant"]
            assert items[0]["content"] == "Meu link sumiu"
            assert "Abri seu chamado." in items[1]["content"]
            assert "reativado" in items[2]["content"]
            assert all("Resposta do atendente humano" not in m["content"] for m in items)
            assert all(m["id"] for m in items)
    finally:
        saver.conn.close()
