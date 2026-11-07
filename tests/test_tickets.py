"""Tests for ticket lifecycle, transcript snapshot, operator reply API, and robust persistence."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from src.config import settings
from src.core import auth
from src.core.graph import OrchestrationGraph
from src.core.tickets_db import (
    TicketsRepository,
    TicketTransitionError,
    get_tickets_repository,
    reset_tickets_repository,
    transcript_snapshot,
)
from src.main import app
from src.tools import agent_tools
from tests.fakes import ScriptedChatModel


def test_create_ticket_with_session_and_transcript(tmp_path: Path) -> None:
    """create_ticket stores session_id, priority, and transcript without false promises."""
    db_path = tmp_path / "tickets.db"
    repo = TicketsRepository(str(db_path))

    tr = [
        {"role": "user", "content": "preciso de suporte com cancelamento"},
        {"role": "assistant", "content": "qual o número da transação?"},
    ]
    ticket = repo.create_ticket(
        user_id="merchant_alpha",
        reason="  estorno de venda não caiu  ",
        priority="high",
        session_id="sess-alpha-001",
        transcript=tr,
    )

    assert ticket["status"] == "success"
    assert ticket["ticket_id"].startswith("GET-TKT-")
    assert ticket["user_id"] == "merchant_alpha"
    assert ticket["session_id"] == "sess-alpha-001"
    assert ticket["priority"] == "high"
    assert ticket["reason"] == "estorno de venda não caiu"
    assert ticket["ticket_status"] == "open"
    assert "GET-TKT-" in ticket["message"]
    assert "minutos" not in ticket["message"].lower()
    assert "fila" not in ticket["message"].lower()

    persisted = repo.get_ticket(ticket["ticket_id"])
    assert persisted is not None
    assert persisted["ticket_id"] == ticket["ticket_id"]
    assert persisted["session_id"] == "sess-alpha-001"
    assert persisted["priority"] == "high"
    assert persisted["status"] == "open"
    assert persisted["transcript"] == tr
    assert persisted["operator_reply"] is None
    assert persisted["operator_id"] is None
    assert persisted["answered_at"] is None


def test_create_ticket_invalid_priority_raises(tmp_path: Path) -> None:
    """Invalid priority value raises ValueError."""
    repo = TicketsRepository(str(tmp_path / "t.db"))
    with pytest.raises(ValueError):
        repo.create_ticket(user_id="m1", reason="x", priority="urgent")


def test_tickets_repository_migrates_old_schema(tmp_path: Path) -> None:
    """TicketsRepository applies ALTER TABLE to migrate pre-5A database schemas without data loss."""
    old_db = tmp_path / "old_tickets.db"
    with sqlite3.connect(old_db) as conn:
        conn.execute("""
            CREATE TABLE tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                priority TEXT NOT NULL DEFAULT 'standard',
                channel TEXT NOT NULL DEFAULT 'ai_chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO tickets (ticket_id, user_id, reason, created_at, updated_at)
            VALUES ('GET-TKT-LEGACY', 'user_old', 'motivo antigo', '2026-01-01', '2026-01-01')
        """)

    repo = TicketsRepository(str(old_db))
    legacy = repo.get_ticket("GET-TKT-LEGACY")
    assert legacy is not None
    assert legacy["ticket_id"] == "GET-TKT-LEGACY"
    assert legacy["session_id"] is None
    assert legacy["transcript"] == []
    assert legacy["status"] == "open"

    new_t = repo.create_ticket(user_id="user_new", reason="novo motivo", session_id="s-migrated")
    assert repo.get_ticket(new_t["ticket_id"]) is not None


def test_tickets_repository_unusable_path_raises(tmp_path: Path) -> None:
    """TicketsRepository fails loudly when the target database path is unusable."""
    blocker = tmp_path / "regular_file"
    blocker.write_text("blocked", encoding="utf-8")
    before_files = set(tmp_path.iterdir())

    with pytest.raises((sqlite3.OperationalError, OSError)):
        TicketsRepository(str(blocker / "sub" / "t.db"))

    assert set(tmp_path.iterdir()) == before_files


def test_ticket_lifecycle_transitions(tmp_path: Path) -> None:
    """Tickets follow strict open -> in_progress -> answered -> closed transitions."""
    repo = TicketsRepository(str(tmp_path / "lifecycle.db"))
    t = repo.create_ticket(user_id="user_life", reason="solicitação inicial")
    tid = t["ticket_id"]

    # 1. open -> in_progress
    u1 = repo.update_ticket(tid, status="in_progress", operator_id="op_1")
    assert u1 is not None and u1["status"] == "in_progress"

    # 2. in_progress -> answered (via reply)
    u2 = repo.update_ticket(tid, reply="O estorno foi aprovado.", operator_id="op_1")
    assert u2 is not None and u2["status"] == "answered"
    assert u2["operator_reply"] == "O estorno foi aprovado."
    assert u2["operator_id"] == "op_1"
    assert bool(u2["answered_at"])

    # 3. answered -> closed
    u3 = repo.update_ticket(tid, status="closed", operator_id="op_2")
    assert u3 is not None and u3["status"] == "closed"

    # 4. Prohibited transitions from closed
    with pytest.raises(TicketTransitionError):
        repo.update_ticket(tid, status="in_progress", operator_id="op_1")
    with pytest.raises(TicketTransitionError):
        repo.update_ticket(tid, reply="reabertura", operator_id="op_1")
    with pytest.raises(TicketTransitionError):
        repo.update_ticket(tid, status="open", operator_id="op_1")

    # 5. Invalid arguments
    t2 = repo.create_ticket(user_id="user_life", reason="t2")
    with pytest.raises(ValueError):
        repo.update_ticket(t2["ticket_id"], status="answered", operator_id="op_1")
    with pytest.raises(ValueError):
        repo.update_ticket(t2["ticket_id"], status="invalid_status", operator_id="op_1")
    with pytest.raises(ValueError):
        repo.update_ticket(t2["ticket_id"], operator_id="op_1")

    # 6. Non-existent ticket
    assert repo.get_ticket("GET-TKT-DOES-NOT-EXIST") is None
    assert repo.update_ticket("GET-TKT-DOES-NOT-EXIST", status="closed", operator_id="op_1") is None


def test_transcript_snapshot_extraction_and_clamping() -> None:
    """transcript_snapshot extracts clean user/assistant messages and clamps count and length."""
    msgs = [HumanMessage(content=f"msg_{i}") for i in range(25)]
    msgs.extend([
        AIMessage(content="", tool_calls=[{"name": "lookup", "args": {}, "id": "c1"}]),
        ToolMessage(content='{"data": 123}', tool_call_id="c1", name="lookup"),
        AIMessage(content=[{"type": "text", "text": "resultado do atendimento"}]),
        HumanMessage(content="X" * 3500),
    ])

    snap = transcript_snapshot(msgs, limit=20, max_chars=2000)
    assert len(snap) == 20
    assert snap[-2] == {"role": "assistant", "content": "resultado do atendimento"}
    assert snap[-1]["role"] == "user"
    assert len(snap[-1]["content"]) == 2000
    assert all(x["role"] in ("user", "assistant") for x in snap)


def test_graph_escalation_flow_masked_transcript(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """OrchestrationGraph escalation persists ticket with session_id, priority, and masked transcript."""
    tickets_db_file = tmp_path / "flow_tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tickets_db_file))
    reset_tickets_repository()

    card_pan = "4111 1111 1111 1111"
    fake = ScriptedChatModel(responses=[
        AIMessage(
            content="",
            tool_calls=[{
                "name": "escalate_to_human",
                "args": {"reason": "reclamação no Procon sobre cartão", "priority": "high"},
                "id": "e_flow",
            }],
        ),
        AIMessage(content="Encaminhado com sucesso."),
    ])

    graph = OrchestrationGraph(chat_model=fake)
    state = graph.run_sync(
        user_id="merchant_flow",
        message=f"Quero abrir chamado no Procon, meu cartão {card_pan} foi cobrado indevidamente",
        session_id="sess-flow-99",
    )

    assert state.escalate_to_human is True
    assert state.escalation_ticket_id is not None

    repo = get_tickets_repository()
    tk = repo.get_ticket(state.escalation_ticket_id)
    assert tk is not None
    assert tk["user_id"] == "merchant_flow"
    assert tk["session_id"] == "sess-flow-99"
    assert tk["priority"] == "high"

    raw_transcript = json.dumps(tk["transcript"], ensure_ascii=False)
    assert "Procon" in raw_transcript
    assert card_pan not in raw_transcript
    assert "4111111111111111" not in raw_transcript


def test_graph_persistence_failure_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Persistence failure in escalate_to_human does not set state.ticket and does not leak errors."""
    class FailingRepo:
        def create_ticket(self, *args, **kwargs):
            raise sqlite3.OperationalError("disk I/O error simulated")

    monkeypatch.setattr(agent_tools, "get_tickets_repository", lambda: FailingRepo())

    fake = ScriptedChatModel(responses=[
        AIMessage(
            content="",
            tool_calls=[{"name": "escalate_to_human", "args": {"reason": "transbordo"}, "id": "e_fail"}],
        ),
        AIMessage(content="Atendimento concluído."),
    ])

    graph = OrchestrationGraph(chat_model=fake)
    state = graph.run_sync(user_id="user_fail", message="falar com atendente", session_id="s-fail")

    assert state.ticket is None
    assert state.escalate_to_human is False
    assert state.escalation_ticket_id is None

    # Verify tool response message
    tool_msg = next((m for call in fake.received for m in call if isinstance(m, ToolMessage) and m.name == "escalate_to_human"), None)
    assert tool_msg is not None
    payload = json.loads(tool_msg.content)
    assert payload.get("status") == "error"
    assert payload.get("error") == "ticket_persistence_failed"
    assert "disk I/O" not in tool_msg.content


def test_patch_tickets_api_and_customer_view(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """PATCH /tickets/{id} enforces operator role, transitions state, and allows customer to view reply."""
    tickets_db_file = tmp_path / "api_tickets.db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tickets_db_file))
    reset_tickets_repository()

    # Configure API keys
    key_cust_a = "key-cust-a"
    key_cust_b = "key-cust-b"
    key_op = "key-operator"
    monkeypatch.setattr(
        settings,
        "API_KEYS",
        f"{hashlib.sha256(key_cust_a.encode()).hexdigest()}:alice:customer;"
        f"{hashlib.sha256(key_cust_b.encode()).hexdigest()}:bob:customer;"
        f"{hashlib.sha256(key_op.encode()).hexdigest()}:operador_1:operator",
    )
    auth.reset_rate_limiter()

    repo = get_tickets_repository()
    t = repo.create_ticket(user_id="alice", reason="suporte urgente", session_id="s-alice")
    tid = t["ticket_id"]

    client = TestClient(app)
    h_cust_a = {"X-API-Key": key_cust_a}
    h_cust_b = {"X-API-Key": key_cust_b}
    h_op = {"X-API-Key": key_op}

    # 1. Customer cannot PATCH
    r_cust_patch = client.patch(f"/tickets/{tid}", json={"status": "in_progress"}, headers=h_cust_a)
    assert r_cust_patch.status_code == 403

    # 2. Validation errors
    r_empty = client.patch(f"/tickets/{tid}", json={}, headers=h_op)
    assert r_empty.status_code == 422
    r_no_reply = client.patch(f"/tickets/{tid}", json={"status": "answered"}, headers=h_op)
    assert r_no_reply.status_code == 422

    # 3. Not found
    r_404 = client.patch("/tickets/GET-TKT-NONEXISTENT", json={"status": "closed"}, headers=h_op)
    assert r_404.status_code == 404

    # 4. Operator lifecycle: in_progress -> answered -> closed
    r_prog = client.patch(f"/tickets/{tid}", json={"status": "in_progress"}, headers=h_op)
    assert r_prog.status_code == 200 and r_prog.json()["status"] == "in_progress"

    r_ans = client.patch(f"/tickets/{tid}", json={"reply": "Seu terminal foi atualizado."}, headers=h_op)
    assert r_ans.status_code == 200
    ans_body = r_ans.json()
    assert ans_body["status"] == "answered"
    assert ans_body["operator_reply"] == "Seu terminal foi atualizado."
    assert ans_body["operator_id"] == "operador_1"

    r_close = client.patch(f"/tickets/{tid}", json={"status": "closed"}, headers=h_op)
    assert r_close.status_code == 200 and r_close.json()["status"] == "closed"

    # 5. Invalid transition (closed -> in_progress) returns 409
    r_reopen = client.patch(f"/tickets/{tid}", json={"status": "in_progress"}, headers=h_op)
    assert r_reopen.status_code == 409

    # 6. Customer can view ticket and operator reply; other customer cannot
    r_view_a = client.get(f"/tickets/{tid}", headers=h_cust_a)
    assert r_view_a.status_code == 200
    assert r_view_a.json()["operator_reply"] == "Seu terminal foi atualizado."

    r_view_b = client.get(f"/tickets/{tid}", headers=h_cust_b)
    assert r_view_b.status_code == 404

    # 7. List tickets by status
    r_list = client.get("/tickets", params={"status": "closed"}, headers=h_op)
    assert r_list.status_code == 200
    tickets_list = r_list.json().get("tickets", [])
    assert all(item["status"] == "closed" for item in tickets_list)
