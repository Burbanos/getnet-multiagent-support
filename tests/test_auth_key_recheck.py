"""Tests for credential re-checking on Bearer access tokens and refresh rotation."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.config import settings
from src.core.auth import Principal, credential_problem, reset_rate_limiter
from src.core.refresh_tokens import RefreshTokenRepository, get_refresh_token_repository, reset_refresh_token_repository
from src.core.tickets_db import reset_tickets_repository
from src.core.tokens import TokenError
from src.main import app

_SIGNING_KEYS = "kid_rec:" + "s" * 40


def _build_api_keys(entries: list[tuple[str, str, str, str | None]]) -> str:
    parts = []
    for raw, user_id, role, last_day in entries:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        parts.append(f"{digest}:{user_id}:{role}" + (f":{last_day}" if last_day else ""))
    return ";".join(parts)


def _setup_prod_env(monkeypatch: pytest.MonkeyPatch, tmp_path, api_keys: str) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "JWT_SIGNING_KEYS", _SIGNING_KEYS)
    monkeypatch.setattr(settings, "JWT_ACTIVE_KID", "kid_rec")
    monkeypatch.setattr(settings, "API_KEYS", api_keys)
    monkeypatch.setattr(settings, "DATABASE_URL", "")
    monkeypatch.setattr(settings, "REDIS_URL", "")
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "recheck.db"))
    monkeypatch.setattr("src.main.validate_state_config", lambda: None)
    reset_rate_limiter()
    reset_tickets_repository()
    reset_refresh_token_repository()


def test_credential_problem_valid_revoked_expired_and_mismatched(monkeypatch: pytest.MonkeyPatch) -> None:
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    raw_key = "rec-unit-key-" + uuid.uuid4().hex
    key_id = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:12]
    principal = Principal(user_id="merchant_rec", role="customer", key_id=key_id)

    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "API_KEYS", _build_api_keys([(raw_key, "merchant_rec", "customer", tomorrow)]))
    assert credential_problem(principal) is None

    monkeypatch.setattr(settings, "API_KEYS", "")
    assert credential_problem(principal) == "key_revoked"

    monkeypatch.setattr(settings, "API_KEYS", _build_api_keys([(raw_key, "merchant_rec", "operator", tomorrow)]))
    assert credential_problem(principal) == "key_revoked"

    monkeypatch.setattr(settings, "API_KEYS", _build_api_keys([(raw_key, "other_merchant", "customer", tomorrow)]))
    assert credential_problem(principal) == "key_revoked"

    monkeypatch.setattr(settings, "API_KEYS", _build_api_keys([(raw_key, "merchant_rec", "customer", yesterday)]))
    assert credential_problem(principal) == "key_expired"

    monkeypatch.setattr(settings, "API_KEYS", "malformed-spec")
    with pytest.raises(ValueError):
        credential_problem(principal)


def test_bearer_rejects_removed_key_immediately_and_recovers_if_restored(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
    key_a = "rec-a-" + uuid.uuid4().hex
    key_b = "rec-b-" + uuid.uuid4().hex
    spec_valid = _build_api_keys([(key_a, "merchant_rec_a", "customer", tomorrow), (key_b, "merchant_rec_b", "customer", None)])
    spec_removed = _build_api_keys([(key_b, "merchant_rec_b", "customer", None)])
    _setup_prod_env(monkeypatch, tmp_path, spec_valid)

    with TestClient(app) as client:
        tok = client.post("/auth/token", headers={"X-API-Key": key_a}).json()["access_token"]
        headers = {"Authorization": f"Bearer {tok}"}

        assert client.get("/sessions/sess_rec_1/messages", headers=headers).status_code == 200

        monkeypatch.setattr(settings, "API_KEYS", spec_removed)
        denied = client.get("/sessions/sess_rec_1/messages", headers=headers)
        assert denied.status_code == 401
        assert "key_revoked" in denied.json()["detail"]
        assert "bearer" in denied.headers.get("www-authenticate", "").lower()

        monkeypatch.setattr(settings, "API_KEYS", spec_valid)
        assert client.get("/sessions/sess_rec_1/messages", headers=headers).status_code == 200


def test_bearer_rejects_expired_key_and_role_or_user_mismatch(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    key_a = "rec-exp-" + uuid.uuid4().hex
    spec_valid = _build_api_keys([(key_a, "merchant_exp", "customer", tomorrow)])
    _setup_prod_env(monkeypatch, tmp_path, spec_valid)

    with TestClient(app) as client:
        tok = client.post("/auth/token", headers={"X-API-Key": key_a}).json()["access_token"]
        headers = {"Authorization": f"Bearer {tok}"}

        monkeypatch.setattr(settings, "API_KEYS", _build_api_keys([(key_a, "merchant_exp", "customer", yesterday)]))
        r_exp = client.get("/sessions/sess_rec_2/messages", headers=headers)
        assert r_exp.status_code == 401
        assert "key_expired" in r_exp.json()["detail"]
        assert "bearer" in r_exp.headers.get("www-authenticate", "").lower()

        monkeypatch.setattr(settings, "API_KEYS", _build_api_keys([(key_a, "merchant_exp", "operator", tomorrow)]))
        r_role = client.get("/sessions/sess_rec_2/messages", headers=headers)
        assert r_role.status_code == 401
        assert "key_revoked" in r_role.json()["detail"]

        monkeypatch.setattr(settings, "API_KEYS", _build_api_keys([(key_a, "renamed_merchant", "customer", tomorrow)]))
        r_user = client.get("/sessions/sess_rec_2/messages", headers=headers)
        assert r_user.status_code == 401
        assert "key_revoked" in r_user.json()["detail"]

        monkeypatch.setattr(settings, "API_KEYS", "invalid-spec")
        r_bad_cfg = client.get("/sessions/sess_rec_2/messages", headers=headers)
        assert r_bad_cfg.status_code == 503


def test_refresh_with_removed_key_revokes_family_permanently_and_audits(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
    key_a = "rec-rf-" + uuid.uuid4().hex
    key_b = "rec-rf-b-" + uuid.uuid4().hex
    spec_valid = _build_api_keys([(key_a, "merchant_rf", "customer", tomorrow), (key_b, "merchant_rf_b", "customer", None)])
    spec_removed = _build_api_keys([(key_b, "merchant_rf_b", "customer", None)])
    _setup_prod_env(monkeypatch, tmp_path, spec_valid)

    with TestClient(app) as client:
        pair = client.post("/auth/token", headers={"X-API-Key": key_a}).json()
        ref = pair["refresh_token"]

        monkeypatch.setattr(settings, "API_KEYS", spec_removed)
        r_revoked = client.post("/auth/refresh", json={"refresh_token": ref})
        assert r_revoked.status_code == 401
        assert "key_revoked" in r_revoked.json()["detail"]
        assert "bearer" in r_revoked.headers.get("www-authenticate", "").lower()

        # Restoring API_KEYS must NOT revive the already-revoked refresh family
        monkeypatch.setattr(settings, "API_KEYS", spec_valid)
        r_after_restore = client.post("/auth/refresh", json={"refresh_token": ref})
        assert r_after_restore.status_code == 401
        assert "key_revoked" not in r_after_restore.json()["detail"]
        assert "revoked" in r_after_restore.json()["detail"]

    repo = get_refresh_token_repository()
    with repo.engine.connect() as conn:
        audits = [
            (a, str(d))
            for a, d in conn.execute(text("SELECT action, details FROM audit_events"))
            if a == "auth.refresh_revoked"
        ]
    assert len(audits) == 1
    assert "key_revoked" in audits[0][1]


def test_refresh_with_expired_key_and_malformed_config(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    key_a = "rec-rf-exp-" + uuid.uuid4().hex
    spec_valid = _build_api_keys([(key_a, "merchant_rf_exp", "customer", tomorrow)])
    _setup_prod_env(monkeypatch, tmp_path, spec_valid)

    with TestClient(app) as client:
        ref = client.post("/auth/token", headers={"X-API-Key": key_a}).json()["refresh_token"]

        monkeypatch.setattr(settings, "API_KEYS", "broken-config")
        r_cfg = client.post("/auth/refresh", json={"refresh_token": ref})
        assert r_cfg.status_code == 503

        monkeypatch.setattr(settings, "API_KEYS", _build_api_keys([(key_a, "merchant_rf_exp", "customer", yesterday)]))
        r_exp = client.post("/auth/refresh", json={"refresh_token": ref})
        assert r_exp.status_code == 401
        assert "key_expired" in r_exp.json()["detail"]

    repo = get_refresh_token_repository()
    with repo.engine.connect() as conn:
        audits = [
            str(d)
            for a, d in conn.execute(text("SELECT action, details FROM audit_events"))
            if a == "auth.refresh_revoked"
        ]
    assert any("key_expired" in d for d in audits)


def test_refresh_repo_rotate_without_and_with_key_check(tmp_path) -> None:
    repo = RefreshTokenRepository(tmp_path / "repo_unit.db")
    principal = Principal(user_id="merchant_unit", role="customer", key_id="112233445566")

    tok1, _ = repo.issue(principal)
    out_p, tok2, _ = repo.rotate(tok1)
    assert out_p == principal

    seen: list[Principal] = []
    out_p2, tok3, _ = repo.rotate(tok2, key_check=lambda p: (seen.append(p) or None))
    assert seen == [principal]
    assert out_p2 == principal

    with pytest.raises(TokenError) as exc_fail:
        repo.rotate(tok3, key_check=lambda _p: "key_revoked")
    assert exc_fail.value.reason == "key_revoked"

    with pytest.raises(TokenError) as exc_subsequent:
        repo.rotate(tok3)
    assert exc_subsequent.value.reason == "revoked"
