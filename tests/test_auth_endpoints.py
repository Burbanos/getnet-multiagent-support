"""Integration tests for /auth/token, /auth/refresh, /auth/revoke, and Bearer enforcement."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.core.auth import hash_api_key
from src.core.tickets_db import reset_tickets_repository
from src.main import app

_PROD_KEY_SIGN = "prod-signing-secret-material-00000000001"


def _configure_db(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "auth_test.db"))
    reset_tickets_repository()


def test_token_exchange_and_bearer_access(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _configure_db(monkeypatch, tmp_path)
    raw_key = "merchant-secret-exchange-01"
    op_key = "operator-secret-exchange-01"
    monkeypatch.setattr(
        settings,
        "API_KEYS",
        f"{hash_api_key(raw_key)}:merchant_ex:customer;{hash_api_key(op_key)}:op_ex:operator",
    )

    with TestClient(app) as client:
        r = client.post("/auth/token", headers={"X-API-Key": raw_key})
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == settings.ACCESS_TOKEN_TTL_S
        assert body["refresh_expires_in"] == settings.REFRESH_TOKEN_TTL_S
        assert body["access_token"] and body["refresh_token"]

        hist = client.get(
            "/sessions/sess_bearer_ok/messages",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert hist.status_code == 200

        r_op = client.post("/auth/token", headers={"X-API-Key": op_key})
        assert r_op.status_code == 200
        op_tok = r_op.json()["access_token"]
        tix = client.get("/tickets", headers={"Authorization": f"Bearer {op_tok}"})
        assert tix.status_code == 200


def test_refresh_endpoint_rotates_and_reuse_revokes_family(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _configure_db(monkeypatch, tmp_path)
    raw_key = "merchant-secret-refresh-01"
    monkeypatch.setattr(settings, "API_KEYS", f"{hash_api_key(raw_key)}:merchant_rf:customer")

    with TestClient(app) as client:
        ex = client.post("/auth/token", headers={"X-API-Key": raw_key}).json()
        r1 = client.post("/auth/refresh", json={"refresh_token": ex["refresh_token"]})
        assert r1.status_code == 200
        rot = r1.json()
        assert rot["access_token"] != ex["access_token"]
        assert rot["refresh_token"] != ex["refresh_token"]

        # Replay of spent refresh token -> 401 and entire family revoked
        r_reuse = client.post("/auth/refresh", json={"refresh_token": ex["refresh_token"]})
        assert r_reuse.status_code == 401

        r_new_after_reuse = client.post("/auth/refresh", json={"refresh_token": rot["refresh_token"]})
        assert r_new_after_reuse.status_code == 401


def test_revoke_endpoint_returns_204_and_invalidates_family(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _configure_db(monkeypatch, tmp_path)
    raw_key = "merchant-secret-revoke-01"
    monkeypatch.setattr(settings, "API_KEYS", f"{hash_api_key(raw_key)}:merchant_rv:customer")

    with TestClient(app) as client:
        ex = client.post("/auth/token", headers={"X-API-Key": raw_key}).json()
        r_rev = client.post("/auth/revoke", json={"refresh_token": ex["refresh_token"]})
        assert r_rev.status_code == 204
        assert r_rev.text == ""

        r_after = client.post("/auth/refresh", json={"refresh_token": ex["refresh_token"]})
        assert r_after.status_code == 401

        r_unknown = client.post("/auth/revoke", json={"refresh_token": "never-existed"})
        assert r_unknown.status_code == 204


def test_production_rejects_direct_api_key_on_protected_routes(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _configure_db(monkeypatch, tmp_path)
    op_key = "operator-secret-prod-01"
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "API_KEYS", f"{hash_api_key(op_key)}:op_prod:operator")
    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", f"pk1:{_PROD_KEY_SIGN}")
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "pk1")
    monkeypatch.setattr("src.main.validate_state_config", lambda: None)

    with TestClient(app) as client:
        direct = client.get("/tickets", headers={"X-API-Key": op_key})
        assert direct.status_code == 401
        assert "/auth/token" in direct.json()["detail"]

        tok = client.post("/auth/token", headers={"X-API-Key": op_key})
        assert tok.status_code == 200
        ok = client.get("/tickets", headers={"Authorization": f"Bearer {tok.json()['access_token']}"})
        assert ok.status_code == 200


def test_expired_api_key_rejected_at_token_exchange(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _configure_db(monkeypatch, tmp_path)
    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    raw_key = "expired-secret-key-01"
    monkeypatch.setattr(settings, "API_KEYS", f"{hash_api_key(raw_key)}:merchant_exp:customer:{yesterday}")

    with TestClient(app) as client:
        r = client.post("/auth/token", headers={"X-API-Key": raw_key})
        assert r.status_code == 401
        assert "expired" in r.json()["detail"].lower()


def test_auth_endpoints_have_separate_rate_limit_bucket(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _configure_db(monkeypatch, tmp_path)
    raw_key = "merchant-secret-rl-01"
    monkeypatch.setattr(settings, "API_KEYS", f"{hash_api_key(raw_key)}:merchant_rl:customer")
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 3)
    from src.core.auth import reset_rate_limiter

    reset_rate_limiter()
    with TestClient(app) as client:
        tokens = []
        for _ in range(3):
            r = client.post("/auth/token", headers={"X-API-Key": raw_key})
            assert r.status_code == 200
            tokens.append(r.json()["access_token"])

        r4 = client.post("/auth/token", headers={"X-API-Key": raw_key})
        assert r4.status_code == 429
        assert "Retry-After" in r4.headers

        # Regular request bucket must remain independent of auth bucket exhaustion
        for _ in range(3):
            h = client.get(
                "/sessions/sess_rl_ok/messages",
                headers={"Authorization": f"Bearer {tokens[0]}"},
            )
            assert h.status_code == 200


def test_development_allows_direct_api_key_and_never_logs_tokens(
    monkeypatch: pytest.MonkeyPatch, tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    _configure_db(monkeypatch, tmp_path)
    caplog.set_level(logging.DEBUG)

    with TestClient(app) as client:
        r_direct = client.get("/sessions/sess_dev_compat/messages", headers={"X-API-Key": "getnet-dev-key"})
        assert r_direct.status_code == 200

        ex = client.post("/auth/token", headers={"X-API-Key": "getnet-dev-key"}).json()
        rot = client.post("/auth/refresh", json={"refresh_token": ex["refresh_token"]}).json()
        assert client.post("/auth/revoke", json={"refresh_token": rot["refresh_token"]}).status_code == 204

    logs = caplog.text
    assert ex["access_token"] not in logs
    assert ex["refresh_token"] not in logs
    assert rot["access_token"] not in logs
    assert rot["refresh_token"] not in logs
