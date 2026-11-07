"""Unit tests for authentication, authorization, session isolation, and rate limiting."""
from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.config import settings
from src.core import auth
from src.core import graph as graph_mod
from src.core.graph import OrchestrationGraph
from src.core.tickets_db import get_tickets_repository
from tests.fakes import ScriptedChatModel


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def test_parse_api_keys_valid_and_invalid() -> None:
    # 1. Valid specification
    k1 = _sha("key1")
    k2 = _sha("key2")
    spec = f"  {k1}:user1:customer ; {k2}:ops1:operator ; "
    table = auth.parse_api_keys(spec)
    assert len(table) == 2
    assert table[k1].user_id == "user1"
    assert table[k1].role == "customer"
    assert table[k1].key_id == k1[:12]
    assert table[k2].user_id == "ops1"
    assert table[k2].role == "operator"

    # 2. Invalid specifications
    bad_specs = [
        "short_hash:user:customer",
        f"{_sha('k').upper()}:user:customer",
        f"{_sha('k')}:user",
        f"{_sha('k')}:user:customer:extra",
        f"{_sha('k')}::customer",
        f"{_sha('k')}:user:admin",
        f"{_sha('dup')}:u1:customer;{_sha('dup')}:u2:operator",
    ]
    for bad in bad_specs:
        with pytest.raises(ValueError):
            auth.parse_api_keys(bad)


def test_auth_missing_or_invalid_key_401(client: TestClient) -> None:
    # Missing header
    r_no_key = client.post("/chat", json={"message": "oi"})
    assert r_no_key.status_code == 401
    assert "Missing or invalid API key" in r_no_key.json()["detail"]

    # Wrong header
    bad_key = "completely-wrong-secret-key-12345"
    r_bad_key = client.post("/chat", json={"message": "oi"}, headers={"X-API-Key": bad_key})
    assert r_bad_key.status_code == 401
    assert bad_key not in r_bad_key.text

    # Tickets endpoint also requires authentication
    r_tickets = client.get("/tickets")
    assert r_tickets.status_code == 401


def test_dev_keys_allowed_in_development_rejected_in_production(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    model = ScriptedChatModel(responses=[AIMessage(content="Olá, lojista!")])
    monkeypatch.setattr(graph_mod, "_orchestrator_instance", OrchestrationGraph(chat_model=model))

    # In development with empty API_KEYS: dev keys work
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "API_KEYS", "")
    r_dev = client.post("/chat", json={"message": "oi"}, headers={"X-API-Key": "getnet-dev-key"})
    assert r_dev.status_code == 200
    assert r_dev.json()["user_id"] == "cliente1988"

    # Health check reflects auth_mode
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["auth_mode"] == "development_defaults"

    # In production with empty API_KEYS: dev keys are rejected (auth_mode is none)
    monkeypatch.setattr(settings, "APP_ENV", "production")
    r_prod = client.post("/chat", json={"message": "oi"}, headers={"X-API-Key": "getnet-dev-key"})
    assert r_prod.status_code == 401

    r_health_prod = client.get("/health")
    assert r_health_prod.json()["auth_mode"] == "none"


def test_configured_api_keys_replaces_dev_defaults(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    my_key = "custom-prod-secret"
    k_hash = _sha(my_key)
    monkeypatch.setattr(settings, "API_KEYS", f"{k_hash}:prod_merchant:customer")

    model = ScriptedChatModel(responses=[AIMessage(content="Resposta personalizada")])
    monkeypatch.setattr(graph_mod, "_orchestrator_instance", OrchestrationGraph(chat_model=model))

    # Configured key works
    r_cfg = client.post("/chat", json={"message": "oi"}, headers={"X-API-Key": my_key})
    assert r_cfg.status_code == 200
    assert r_cfg.json()["user_id"] == "prod_merchant"

    # Dev keys are rejected when API_KEYS is explicitly configured
    r_dev = client.post("/chat", json={"message": "oi"}, headers={"X-API-Key": "getnet-dev-key"})
    assert r_dev.status_code == 401

    assert client.get("/health").json()["auth_mode"] == "configured"


def test_body_user_id_mismatch_403(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    model = ScriptedChatModel(responses=[AIMessage(content="Resposta válida")])
    monkeypatch.setattr(graph_mod, "_orchestrator_instance", OrchestrationGraph(chat_model=model))

    # Mismatch between credential and body user_id -> 403
    r_mismatch = client.post(
        "/chat",
        json={"message": "oi", "user_id": "other_impostor"},
        headers={"X-API-Key": "getnet-dev-key"},
    )
    assert r_mismatch.status_code == 403
    assert "user_id does not match the authenticated credential" in r_mismatch.json()["detail"]

    # Matching user_id or omitted user_id -> 200
    r_matching = client.post(
        "/chat",
        json={"message": "oi", "user_id": "cliente1988"},
        headers={"X-API-Key": "getnet-dev-key"},
    )
    assert r_matching.status_code == 200


def test_session_isolation_per_user_and_thread_id(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    k_a = _sha("key-a")
    k_b = _sha("key-b")
    monkeypatch.setattr(settings, "API_KEYS", f"{k_a}:user_a:customer;{k_b}:user_b:customer")

    model = ScriptedChatModel(responses=[
        AIMessage(content="Anotado segredo A"),
        AIMessage(content="Sou usuário B"),
        AIMessage(content="Confirmando segredo A"),
    ])
    orch = OrchestrationGraph(chat_model=model)
    monkeypatch.setattr(graph_mod, "_orchestrator_instance", orch)

    # User A sends secret in session "shared-sess"
    r1 = client.post(
        "/chat",
        json={"message": "Meu código secreto é SEGREDO-999", "session_id": "shared-sess"},
        headers={"X-API-Key": "key-a"},
    )
    assert r1.status_code == 200

    # User B queries the same session_id "shared-sess"
    n_before = len(model.received)
    r2 = client.post(
        "/chat",
        json={"message": "Qual é o segredo do outro usuário?", "session_id": "shared-sess"},
        headers={"X-API-Key": "key-b"},
    )
    assert r2.status_code == 200
    b_received = " ".join(str(m.content) for call in model.received[n_before:] for m in call)
    assert "SEGREDO-999" not in b_received

    # User A queries again in "shared-sess"
    n_before = len(model.received)
    r3 = client.post(
        "/chat",
        json={"message": "Qual era meu segredo?", "session_id": "shared-sess"},
        headers={"X-API-Key": "key-a"},
    )
    assert r3.status_code == 200
    a_received = " ".join(str(m.content) for call in model.received[n_before:] for m in call)
    assert "SEGREDO-999" in a_received

    # Verify checkpointer thread_id format: user_id:session_id
    state_a = orch.graph.get_state({"configurable": {"thread_id": "user_a:shared-sess"}})
    assert bool(state_a.values)

    # Empty user_id in run_sync raises ValueError
    with pytest.raises(ValueError, match="user_id is required"):
        orch.run_sync(user_id="", message="hello", session_id="s1")


def test_tickets_authorization_by_role_and_owner(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    k_cust_a = _sha("cust-a")
    k_ops = _sha("ops-key")
    monkeypatch.setattr(settings, "API_KEYS", f"{k_cust_a}:merchant_alpha:customer;{k_ops}:operator_1:operator")

    repo = get_tickets_repository()
    t_a = repo.create_ticket(user_id="merchant_alpha", reason="Ticket Alpha")
    t_b = repo.create_ticket(user_id="merchant_beta", reason="Ticket Beta")

    # Customer Alpha lists tickets: sees only Alpha tickets
    r_list_cust = client.get("/tickets", headers={"X-API-Key": "cust-a"})
    assert r_list_cust.status_code == 200
    for t in r_list_cust.json()["tickets"]:
        assert t["user_id"] == "merchant_alpha"

    # Customer Alpha attempting to filter by another user -> 403
    r_filter_other = client.get("/tickets", params={"user_id": "merchant_beta"}, headers={"X-API-Key": "cust-a"})
    assert r_filter_other.status_code == 403

    # Customer Alpha accessing Beta's ticket directly -> 404 (not found)
    r_get_other = client.get(f"/tickets/{t_b['ticket_id']}", headers={"X-API-Key": "cust-a"})
    assert r_get_other.status_code == 404

    # Customer Alpha accessing own ticket -> 200
    r_get_own = client.get(f"/tickets/{t_a['ticket_id']}", headers={"X-API-Key": "cust-a"})
    assert r_get_own.status_code == 200

    # Operator can view any ticket and filter
    r_ops_get = client.get(f"/tickets/{t_b['ticket_id']}", headers={"X-API-Key": "ops-key"})
    assert r_ops_get.status_code == 200

    r_ops_list_b = client.get("/tickets", params={"user_id": "merchant_beta"}, headers={"X-API-Key": "ops-key"})
    assert r_ops_list_b.status_code == 200
    for t in r_ops_list_b.json()["tickets"]:
        assert t["user_id"] == "merchant_beta"


def test_rate_limiting_with_mock_clock(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 2)
    auth.reset_rate_limiter()
    limiter = auth.get_rate_limiter()

    clock_state = {"now": 5000.0}
    limiter.clock = lambda: clock_state["now"]

    headers = {"X-API-Key": "getnet-dev-operator"}

    # 1st request -> 200
    r1 = client.get("/tickets", headers=headers)
    assert r1.status_code == 200

    # 2nd request -> 200
    r2 = client.get("/tickets", headers=headers)
    assert r2.status_code == 200

    # 3rd request -> 429
    r3 = client.get("/tickets", headers=headers)
    assert r3.status_code == 429
    assert "Retry-After" in r3.headers
    retry_after = int(r3.headers["Retry-After"])
    assert retry_after >= 1

    # Advance clock by 61 seconds
    clock_state["now"] += 61.0

    # Request permitted again
    r4 = client.get("/tickets", headers=headers)
    assert r4.status_code == 200

    # Disabled limiter (limit <= 0)
    disabled_limiter = auth.RateLimiter(limit_per_minute=0)
    assert all(disabled_limiter.hit("any_key") is None for _ in range(100))
