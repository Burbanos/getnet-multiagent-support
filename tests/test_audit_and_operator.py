"""Tests for /audit, /replacements, ticket auditing, and /operator console (Phase 13C)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

import src.main as app_main
from src.config import settings
from src.core.actions_db import get_actions_repository
from src.core.graph import OrchestrationGraph
from src.core.tickets_db import get_tickets_repository, reset_tickets_repository
from tests.fakes import ScriptedChatModel

CUST_HDR = {"X-API-Key": "getnet-dev-key"}
OP_HDR = {"X-API-Key": "getnet-dev-operator"}


def test_audit_endpoint_forbids_customer_and_hides_raw_user_ids(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t_aud1.db"))
    reset_tickets_repository()
    try:
        get_tickets_repository().create_ticket("cliente1988", "duvida qualquer", session_id="s1")
        client = TestClient(app_main.app)

        cust_resp = client.get("/audit", headers=CUST_HDR)
        assert cust_resp.status_code == 403

        op_resp = client.get("/audit", headers=OP_HDR)
        assert op_resp.status_code == 200
        assert "cliente1988" not in op_resp.text
        events = op_resp.json()["events"]
        assert len(events) >= 1
        assert all(ev["actor_hash"].startswith("u_") for ev in events)
    finally:
        reset_tickets_repository()


def test_audit_endpoint_filters_by_action_and_target_id(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t_aud2.db"))
    reset_tickets_repository()
    try:
        t1 = get_tickets_repository().create_ticket("cliente1988", "m1", session_id="s1")["ticket_id"]
        get_tickets_repository().create_ticket("cliente1988", "m2", session_id="s2")
        client = TestClient(app_main.app)

        resp = client.get("/audit", headers=OP_HDR, params={"action": "ticket_created", "target_id": t1})
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) == 1
        assert events[0]["target_id"] == t1
    finally:
        reset_tickets_repository()


def test_replacements_endpoint_enforces_role_scoping(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t_rep.db"))
    reset_tickets_repository()
    try:
        repo = get_actions_repository()
        repo.propose_terminal_replacement("cliente1988", "s1", "GET-883921", "quebrada", "t1")
        repo.confirm("cliente1988", "s1", "t2")
        repo.propose_terminal_replacement("outro_lojista", "s2", "GET-999999", "bateria", "t3")
        repo.confirm("outro_lojista", "s2", "t4")

        client = TestClient(app_main.app)
        c_self = client.get("/replacements", headers=CUST_HDR)
        assert c_self.status_code == 200
        assert len(c_self.json()["replacements"]) == 1
        assert c_self.json()["replacements"][0]["user_id"] == "cliente1988"

        c_other = client.get("/replacements", headers=CUST_HDR, params={"user_id": "outro_lojista"})
        assert c_other.status_code == 403

        op_all = client.get("/replacements", headers=OP_HDR)
        assert op_all.status_code == 200
        assert len(op_all.json()["replacements"]) == 2
    finally:
        reset_tickets_repository()


def test_ticket_lifecycle_audits_created_updated_replied_and_delivered(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t_life.db"))
    reset_tickets_repository()
    try:
        orch = OrchestrationGraph(
            chat_model=ScriptedChatModel(
                responses=[
                    AIMessage(
                        content="",
                        tool_calls=[{"name": "escalate_to_human", "args": {"reason": "pedido"}, "id": "e1"}],
                    ),
                    AIMessage(content="Chamado registrado."),
                    AIMessage(content="Repassando a resposta da equipe humana."),
                ]
            ),
            checkpointer=MemorySaver(),
        )
        old_get = app_main.get_orchestrator
        app_main.get_orchestrator = lambda: orch
        try:
            st = orch.run_sync("cliente1988", "Quero falar com humano", session_id="s-life")
            tid = (st.ticket or {})["ticket_id"]

            client = TestClient(app_main.app)
            p1 = client.patch(f"/tickets/{tid}", json={"status": "in_progress"}, headers=OP_HDR)
            assert p1.status_code == 200

            p2 = client.patch(f"/tickets/{tid}", json={"reply": "Tudo resolvido!"}, headers=OP_HDR)
            assert p2.status_code == 200

            aud = client.get("/audit", headers=OP_HDR, params={"target_id": tid})
            assert aud.status_code == 200
            actions = {ev["action"] for ev in aud.json()["events"]}
            assert {"ticket_created", "ticket_updated", "ticket_replied", "ticket_reply_delivered"} <= actions
        finally:
            app_main.get_orchestrator = old_get
    finally:
        reset_tickets_repository()


def test_operator_console_html_is_self_contained_and_safe() -> None:
    client = TestClient(app_main.app)
    resp = client.get("/operator")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    html = resp.text

    assert not re.findall(r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//""", html, re.IGNORECASE)
    assert "localStorage" not in html
    assert "sessionStorage" not in html
    assert "innerHTML" not in html
    assert "document.cookie" not in html
    assert re.search(r"""type\s*=\s*["']password["']""", html) is not None
    assert all(tok in html for tok in ("/tickets", "/replacements", "/audit", "X-API-Key"))


def test_root_and_demo_link_to_operator_console() -> None:
    client = TestClient(app_main.app)
    root = client.get("/")
    assert root.status_code == 200
    assert root.json().get("operator_console") == "/operator"

    demo = client.get("/demo")
    assert demo.status_code == 200
    assert "/operator" in demo.text


def test_root_metrics_include_new_write_action_tools(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t_met.db"))
    reset_tickets_repository()
    try:
        from src.core import metrics

        metrics.reset()
        metrics.inc_tool("request_terminal_replacement", "ok")
        metrics.inc_tool("confirm_pending_action", "ok")
        rendered = metrics.render()
        assert 'getnet_tool_calls_total{tool="request_terminal_replacement",status="ok"} 1' in rendered
        assert 'getnet_tool_calls_total{tool="confirm_pending_action",status="ok"} 1' in rendered
    finally:
        reset_tickets_repository()


def test_forced_escalation_records_system_actor_in_audit(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "t_sys.db"))
    monkeypatch.setattr(settings, "MAX_SUPERVISOR_STEPS", 1)
    reset_tickets_repository()
    try:
        orch = OrchestrationGraph(
            chat_model=ScriptedChatModel(
                responses=[
                    AIMessage(
                        content="",
                        tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "oi"}, "id": "k1"}],
                    )
                ]
            ),
            checkpointer=MemorySaver(),
        )
        st = orch.run_sync("cliente1988", "Qualquer coisa", session_id="s-force-aud")
        tid = (st.ticket or {})["ticket_id"]
        events = get_actions_repository().list_audit(target_id=tid)
        assert any(ev["action"] == "ticket_created" and ev["actor_type"] == "system" for ev in events)
        assert "cliente1988" not in json.dumps(events)
    finally:
        reset_tickets_repository()
