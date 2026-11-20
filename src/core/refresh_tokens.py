"""Persistent opaque refresh token repository with family rotation and reuse detection."""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import and_, insert, select, update

from src.config import settings
from src.core.actions_db import insert_audit
from src.core.auth import Principal
from src.core.db import ensure_schema, make_engine, refresh_tokens
from src.core.tokens import TokenError

logger = logging.getLogger("multiagent.refresh_tokens")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc_datetime(now: float | datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if isinstance(now, datetime):
        return now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
    return datetime.fromtimestamp(float(now), UTC)


class RefreshTokenRepository:
    """Manages opaque SHA-256 hashed refresh tokens, rotation families, and revocation."""

    def __init__(self, target: str | Path) -> None:
        self.target = str(target)
        self.engine = make_engine(self.target, pool_size=settings.DB_POOL_SIZE)
        ensure_schema(self.engine)
        logger.info("Refresh token repository initialized")

    def issue(
        self,
        principal: Principal,
        now: float | datetime | None = None,
    ) -> tuple[str, int]:
        """Issue a new opaque refresh token in a new token family and persist only its SHA-256 hash."""
        now_dt = _as_utc_datetime(now)
        ttl = int(settings.REFRESH_TOKEN_TTL_S)
        issued_at = now_dt.isoformat()
        expires_at = (now_dt + timedelta(seconds=ttl)).isoformat()
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        family_id = f"RTF-{uuid.uuid4().hex[:16]}"

        with self.engine.begin() as conn:
            conn.execute(
                insert(refresh_tokens).values(
                    token_hash=token_hash,
                    family_id=family_id,
                    user_id=principal.user_id,
                    role=principal.role,
                    key_id=principal.key_id,
                    issued_at=issued_at,
                    expires_at=expires_at,
                    used_at=None,
                    revoked_at=None,
                )
            )
            insert_audit(
                conn,
                actor_type=principal.role,
                actor_id=principal.user_id,
                action="auth.token_issued",
                target_type="refresh_family",
                target_id=family_id,
                outcome="ok",
                details={"status": "issued"},
            )
        return raw_token, ttl

    def peek_key_id(self, token: str) -> str | None:
        """Return the owning credential key_id for rate limiting without mutating state."""
        if not isinstance(token, str) or not token.strip():
            return None
        token_hash = _hash_token(token.strip())
        with self.engine.connect() as conn:
            return conn.execute(
                select(refresh_tokens.c.key_id).where(refresh_tokens.c.token_hash == token_hash)
            ).scalar_one_or_none()

    def rotate(
        self,
        token: str,
        now: float | datetime | None = None,
        key_check: Callable[[Principal], str | None] | None = None,
    ) -> tuple[Principal, str, int]:
        """Rotate a valid refresh token, or revoke its whole family on reuse or credential failure."""
        if not isinstance(token, str) or not token.strip():
            raise TokenError("unknown")

        raw_token = token.strip()
        token_hash = _hash_token(raw_token)
        now_dt = _as_utc_datetime(now)
        now_iso = now_dt.isoformat()

        error_reason: str | None = None
        result: tuple[Principal, str, int] | None = None

        with self.engine.begin() as conn:
            row = (
                conn.execute(
                    select(refresh_tokens)
                    .where(refresh_tokens.c.token_hash == token_hash)
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            if row is None:
                error_reason = "unknown"
            elif row["used_at"] is not None:
                family_id = str(row["family_id"])
                conn.execute(
                    update(refresh_tokens)
                    .where(and_(refresh_tokens.c.family_id == family_id, refresh_tokens.c.revoked_at.is_(None)))
                    .values(revoked_at=now_iso)
                )
                insert_audit(
                    conn,
                    actor_type=str(row["role"]),
                    actor_id=str(row["user_id"]),
                    action="auth.refresh_reuse_detected",
                    target_type="refresh_family",
                    target_id=family_id,
                    outcome="revoked",
                    details={"status": "reused"},
                )
                error_reason = "reused"
            elif row["revoked_at"] is not None:
                error_reason = "revoked"
            elif now_dt >= datetime.fromisoformat(str(row["expires_at"])):
                error_reason = "expired"
            else:
                principal = Principal(
                    user_id=str(row["user_id"]),
                    role=str(row["role"]),
                    key_id=str(row["key_id"]),
                )
                problem = key_check(principal) if key_check is not None else None
                if problem:
                    family_id = str(row["family_id"])
                    conn.execute(
                        update(refresh_tokens)
                        .where(and_(refresh_tokens.c.family_id == family_id, refresh_tokens.c.revoked_at.is_(None)))
                        .values(revoked_at=now_iso)
                    )
                    insert_audit(
                        conn,
                        actor_type=str(row["role"]),
                        actor_id=str(row["user_id"]),
                        action="auth.refresh_revoked",
                        target_type="refresh_family",
                        target_id=family_id,
                        outcome="revoked",
                        details={"status": str(problem)},
                    )
                    error_reason = str(problem)
                else:
                    res = conn.execute(
                        update(refresh_tokens)
                        .where(
                            and_(
                                refresh_tokens.c.token_hash == token_hash,
                                refresh_tokens.c.used_at.is_(None),
                                refresh_tokens.c.revoked_at.is_(None),
                            )
                        )
                        .values(used_at=now_iso)
                    )
                    if (res.rowcount or 0) == 0:
                        error_reason = "reused"
                    else:
                        ttl = int(settings.REFRESH_TOKEN_TTL_S)
                        new_raw = secrets.token_urlsafe(32)
                        new_hash = _hash_token(new_raw)
                        new_expires = (now_dt + timedelta(seconds=ttl)).isoformat()
                        family_id = str(row["family_id"])
                        conn.execute(
                            insert(refresh_tokens).values(
                                token_hash=new_hash,
                                family_id=family_id,
                                user_id=str(row["user_id"]),
                                role=str(row["role"]),
                                key_id=str(row["key_id"]),
                                issued_at=now_iso,
                                expires_at=new_expires,
                                used_at=None,
                                revoked_at=None,
                            )
                        )
                        insert_audit(
                            conn,
                            actor_type=str(row["role"]),
                            actor_id=str(row["user_id"]),
                            action="auth.refresh_rotated",
                            target_type="refresh_family",
                            target_id=family_id,
                            outcome="ok",
                            details={"status": "rotated"},
                        )
                        result = (principal, new_raw, ttl)

        if error_reason is not None:
            raise TokenError(error_reason)
        assert result is not None
        return result

    def revoke_family(
        self,
        token: str,
        now: float | datetime | None = None,
    ) -> bool:
        """Revoke all tokens in the refresh token's family. Returns True when a known token was revoked."""
        if not isinstance(token, str) or not token.strip():
            return False
        token_hash = _hash_token(token.strip())
        now_iso = _as_utc_datetime(now).isoformat()

        with self.engine.begin() as conn:
            row = (
                conn.execute(select(refresh_tokens).where(refresh_tokens.c.token_hash == token_hash))
                .mappings()
                .first()
            )
            if row is None:
                return False
            family_id = str(row["family_id"])
            conn.execute(
                update(refresh_tokens)
                .where(and_(refresh_tokens.c.family_id == family_id, refresh_tokens.c.revoked_at.is_(None)))
                .values(revoked_at=now_iso)
            )
            insert_audit(
                conn,
                actor_type=str(row["role"]),
                actor_id=str(row["user_id"]),
                action="auth.refresh_revoked",
                target_type="refresh_family",
                target_id=family_id,
                outcome="revoked",
                details={"status": "revoked"},
            )
        return True


_refresh_repo: RefreshTokenRepository | None = None


def get_refresh_token_repository() -> RefreshTokenRepository:
    """Dependency getter for refresh token repository matching tickets storage target."""
    global _refresh_repo
    if _refresh_repo is None:
        target = settings.DATABASE_URL.strip() or settings.TICKETS_DB_PATH
        _refresh_repo = RefreshTokenRepository(target)
    return _refresh_repo


def reset_refresh_token_repository() -> None:
    """Reset the global refresh token repository singleton."""
    global _refresh_repo
    if _refresh_repo is not None:
        engine = getattr(_refresh_repo, "engine", None)
        if engine is not None:
            engine.dispose()
    _refresh_repo = None
