"""Unit tests for opaque SHA-256 refresh tokens, rotation, and reuse detection."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from src.config import settings
from src.core.auth import Principal
from src.core.db import audit_events, refresh_tokens
from src.core.refresh_tokens import RefreshTokenRepository
from src.core.tokens import TokenError


def test_issue_hashes_token_and_audits(tmp_path) -> None:
    repo = RefreshTokenRepository(tmp_path / "rt.db")
    principal = Principal(user_id="merchant_rt_1", role="customer", key_id="key_rt_1")
    now = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)

    raw_token, ttl = repo.issue(principal, now=now)
    assert ttl == settings.REFRESH_TOKEN_TTL_S
    expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    with repo.engine.connect() as conn:
        rows = conn.execute(select(refresh_tokens)).mappings().all()
        audits = conn.execute(select(audit_events)).mappings().all()

    assert len(rows) == 1
    row = rows[0]
    assert row["token_hash"] == expected_hash
    assert row["token_hash"] != raw_token
    assert raw_token not in str(dict(row))
    assert row["used_at"] is None
    assert row["revoked_at"] is None
    assert row["user_id"] == "merchant_rt_1"
    assert audits[-1]["action"] == "auth.token_issued"


def test_rotate_returns_new_token_and_marks_old_used(tmp_path) -> None:
    repo = RefreshTokenRepository(tmp_path / "rt.db")
    principal = Principal(user_id="merchant_rt_2", role="customer", key_id="key_rt_2")
    t0 = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)

    tok1, _ = repo.issue(principal, now=t0)
    out_principal, tok2, ttl2 = repo.rotate(tok1, now=t0 + timedelta(seconds=60))

    assert out_principal == principal
    assert tok2 != tok1
    assert ttl2 == settings.REFRESH_TOKEN_TTL_S

    with repo.engine.connect() as conn:
        rows = conn.execute(select(refresh_tokens).order_by(refresh_tokens.c.issued_at)).mappings().all()
        audits = conn.execute(select(audit_events).order_by(audit_events.c.id)).mappings().all()

    assert len(rows) == 2
    assert rows[0]["used_at"] is not None
    assert rows[0]["revoked_at"] is None
    assert rows[1]["used_at"] is None
    assert rows[0]["family_id"] == rows[1]["family_id"]
    assert audits[-1]["action"] == "auth.refresh_rotated"


def test_reuse_detection_revokes_entire_family_and_persists_audit(tmp_path) -> None:
    repo = RefreshTokenRepository(tmp_path / "rt.db")
    principal = Principal(user_id="merchant_rt_3", role="customer", key_id="key_rt_3")
    t0 = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)

    tok1, _ = repo.issue(principal, now=t0)
    _, tok2, _ = repo.rotate(tok1, now=t0 + timedelta(seconds=30))

    with pytest.raises(TokenError) as exc_reuse:
        repo.rotate(tok1, now=t0 + timedelta(seconds=60))
    assert exc_reuse.value.reason == "reused"

    with repo.engine.connect() as conn:
        rows = conn.execute(select(refresh_tokens).order_by(refresh_tokens.c.issued_at)).mappings().all()
        actions = [r["action"] for r in conn.execute(select(audit_events).order_by(audit_events.c.id)).mappings().all()]

    assert all(r["revoked_at"] is not None for r in rows)
    assert "auth.refresh_reuse_detected" in actions

    with pytest.raises(TokenError) as exc_rev:
        repo.rotate(tok2, now=t0 + timedelta(seconds=90))
    assert exc_rev.value.reason == "revoked"


def test_revoke_family_invalidates_active_tokens(tmp_path) -> None:
    repo = RefreshTokenRepository(tmp_path / "rt.db")
    principal = Principal(user_id="merchant_rt_4", role="operator", key_id="key_rt_4")
    t0 = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)

    tok1, _ = repo.issue(principal, now=t0)
    _, tok2, _ = repo.rotate(tok1, now=t0 + timedelta(seconds=10))

    assert repo.revoke_family("nonexistent-token", now=t0 + timedelta(seconds=20)) is False
    assert repo.revoke_family(tok2, now=t0 + timedelta(seconds=20)) is True

    with repo.engine.connect() as conn:
        actions = [r["action"] for r in conn.execute(select(audit_events)).mappings().all()]
    assert "auth.refresh_revoked" in actions

    with pytest.raises(TokenError) as exc_rev:
        repo.rotate(tok2, now=t0 + timedelta(seconds=30))
    assert exc_rev.value.reason == "revoked"


def test_expired_refresh_token_rejected(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "REFRESH_TOKEN_TTL_S", 120)
    repo = RefreshTokenRepository(tmp_path / "rt.db")
    principal = Principal(user_id="merchant_rt_5", role="customer", key_id="key_rt_5")
    t0 = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)

    tok1, _ = repo.issue(principal, now=t0)
    with pytest.raises(TokenError) as exc_exp:
        repo.rotate(tok1, now=t0 + timedelta(seconds=121))
    assert exc_exp.value.reason == "expired"


def test_unknown_and_blank_tokens_rejected(tmp_path) -> None:
    repo = RefreshTokenRepository(tmp_path / "rt.db")
    for raw in ("", "   ", "unknown-refresh-token-value"):
        with pytest.raises(TokenError) as exc_unk:
            repo.rotate(raw)
        assert exc_unk.value.reason == "unknown"


def test_peek_key_id_does_not_mutate_token(tmp_path) -> None:
    repo = RefreshTokenRepository(tmp_path / "rt.db")
    principal = Principal(user_id="merchant_rt_6", role="customer", key_id="key_rt_6_id")
    tok, _ = repo.issue(principal)

    assert repo.peek_key_id(tok) == "key_rt_6_id"
    assert repo.peek_key_id("unknown-token") is None
    assert repo.peek_key_id("") is None

    out_p, _, _ = repo.rotate(tok)
    assert out_p == principal
