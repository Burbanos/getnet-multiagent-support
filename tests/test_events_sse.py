"""Tests for InMemoryEventBroker, cross-replica RedisEventBroker, PATCH publish, and SSE stream."""
from __future__ import annotations

import json
import re
import threading
import time

import fakeredis
import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.core import metrics
from src.core.auth import hash_api_key
from src.core.events import (
    InMemoryEventBroker,
    RedisEventBroker,
    event_channel,
    get_event_broker,
    reset_event_broker,
)
from src.core.tickets_db import get_tickets_repository, reset_tickets_repository
from src.main import app


def _metric_value(text: str, name: str, labels: str = "") -> float:
    pat = (
        rf"^{re.escape(name)}\{{{re.escape(labels)}\}}\s+([0-9.eE+-]+)"
        if labels
        else rf"^{re.escape(name)}\s+([0-9.eE+-]+)"
    )
    m = re.search(pat, text, flags=re.MULTILINE)
    return float(m.group(1)) if m else 0.0


def test_inmemory_broker_session_isolation_and_hashed_channel() -> None:
    broker = InMemoryEventBroker()
    ch = event_channel("merchant_secret_uid", "sess_iso")
    assert "merchant_secret_uid" not in ch
    assert ch.startswith("getnet:events:")

    sub_a = broker.subscribe("merchant_one", "sess_alpha")
    sub_b = broker.subscribe("merchant_one", "sess_beta")
    try:
        broker.publish("merchant_one", "sess_alpha", {"type": "operator_reply", "ticket_id": "TCK-1"})
        ev_a = sub_a.get(timeout=0.5)
        ev_b = sub_b.get(timeout=0.05)
        assert ev_a is not None and ev_a["ticket_id"] == "TCK-1"
        assert ev_b is None
    finally:
        sub_a.close()
        sub_b.close()


def test_redis_broker_cross_replica_pubsub_with_fakeredis() -> None:
    srv = fakeredis.FakeServer()
    replica_api_sse = RedisEventBroker(fakeredis.FakeRedis(server=srv))
    replica_api_patch = RedisEventBroker(fakeredis.FakeRedis(server=srv))

    sub = replica_api_sse.subscribe("merchant_rep", "sess_rep")
    try:
        ok = replica_api_patch.publish(
            "merchant_rep",
            "sess_rep",
            {"type": "operator_reply", "ticket_id": "TCK-REP", "session_id": "sess_rep"},
        )
        assert ok is True
        received = sub.get(timeout=1.0)
        assert received == {"type": "operator_reply", "ticket_id": "TCK-REP", "session_id": "sess_rep"}
    finally:
        sub.close()


def test_patch_ticket_publishes_metadata_without_reply_text(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "sse_patch.db"))
    monkeypatch.setattr(settings, "API_KEYS", "")
    reset_tickets_repository()
    reset_event_broker()

    repo = get_tickets_repository()
    created = repo.create_ticket(
        user_id="cliente1988",
        session_id="sess_patch_meta",
        reason="manual_review",
    )
    ticket_id = created["ticket_id"]

    broker = get_event_broker()
    sub = broker.subscribe("cliente1988", "sess_patch_meta")
    secret_reply = "CONFIDENTIAL_OPERATOR_TEXT_DO_NOT_LEAK"
    before = _metric_value(metrics.render(), "getnet_merchant_notifications_total", 'status="published"')

    try:
        with TestClient(app) as client:
            resp = client.patch(
                f"/tickets/{ticket_id}",
                headers={"X-API-Key": "getnet-dev-operator"},
                json={"status": "resolved", "reply": secret_reply},
            )
            assert resp.status_code == 200

        ev = sub.get(timeout=0.5)
        assert ev is not None
        assert ev["type"] == "operator_reply"
        assert ev["ticket_id"] == ticket_id
        assert ev["session_id"] == "sess_patch_meta"
        assert ev["status"] == "answered"
        assert secret_reply not in json.dumps(ev)

        after = _metric_value(metrics.render(), "getnet_merchant_notifications_total", 'status="published"')
        assert after == before + 1.0
    finally:
        sub.close()


def test_sse_stream_delivers_heartbeat_and_operator_reply_across_replicas(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "sse_stream.db"))
    monkeypatch.setattr(settings, "SSE_HEARTBEAT_S", 0.05)
    monkeypatch.setattr(settings, "SSE_MAX_CONNECTION_S", 0.45)

    srv = fakeredis.FakeServer()
    fake_sse_client = fakeredis.FakeRedis(server=srv)
    fake_patch_client = fakeredis.FakeRedis(server=srv)
    reset_tickets_repository()
    reset_event_broker()
    monkeypatch.setattr("src.main.get_event_broker", lambda: RedisEventBroker(fake_sse_client))

    cust_key = "cust-sse-secret"
    monkeypatch.setattr(settings, "API_KEYS", f"{hash_api_key(cust_key)}:merchant_sse:customer")

    publisher = RedisEventBroker(fake_patch_client)
    secret_body = "HIDDEN_REPLY_BODY_SSE"

    def _delayed_publish() -> None:
        time.sleep(0.12)
        publisher.publish(
            "merchant_sse",
            "sess_sse_1",
            {
                "type": "operator_reply",
                "ticket_id": "TCK-SSE-1",
                "session_id": "sess_sse_1",
                "status": "resolved",
                "replied_at": "2026-11-20T12:00:00+00:00",
            },
        )

    with TestClient(app) as client:
        tok_resp = client.post("/auth/token", headers={"X-API-Key": cust_key})
        assert tok_resp.status_code == 200
        bearer = tok_resp.json()["access_token"]

        t = threading.Thread(target=_delayed_publish, daemon=True)
        t.start()
        with client.stream(
            "GET",
            "/sessions/sess_sse_1/events",
            headers={"Authorization": f"Bearer {bearer}"},
        ) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            chunks = [line for line in resp.iter_lines()]
        t.join(timeout=2.0)

    joined = "\n".join(chunks)
    assert ": ping" in joined
    assert "event: operator_reply" in joined
    assert "TCK-SSE-1" in joined
    assert secret_body not in joined
    assert _metric_value(metrics.render(), "getnet_sse_connections") == 0.0


def test_sse_stream_rejects_operator_with_403(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "sse_op_403.db"))
    reset_tickets_repository()
    with TestClient(app) as client:
        resp = client.get("/sessions/sess_any/events", headers={"X-API-Key": "getnet-dev-operator"})
        assert resp.status_code == 403
