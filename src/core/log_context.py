"""Request-scoped logging context with ContextVar and user ID hashing."""
from __future__ import annotations

import hashlib
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)
_user_hash: ContextVar[str | None] = ContextVar("user_hash", default=None)


def user_hash(user_id: str) -> str:
    """
    Compute a truncated SHA-256 hash of user_id salted with settings.LOG_HASH_SALT.
    Format: 'u_' + hexdigest[:16]
    """
    from src.config import settings

    salt = settings.LOG_HASH_SALT
    raw = (salt + user_id).encode("utf-8")
    return "u_" + hashlib.sha256(raw).hexdigest()[:16]


@contextmanager
def bind(trace_id: str, session_id: str, user_id: str) -> Generator[None, None, None]:
    """
    Context manager that binds trace_id, session_id, and hashed user_id to ContextVars,
    restoring the previous state on exit.
    """
    uh = user_hash(user_id)
    t_tok = _trace_id.set(trace_id)
    s_tok = _session_id.set(session_id)
    u_tok = _user_hash.set(uh)
    try:
        yield
    finally:
        _trace_id.reset(t_tok)
        _session_id.reset(s_tok)
        _user_hash.reset(u_tok)


def current() -> dict[str, str]:
    """
    Return the current active logging context fields.
    Returns an empty dict when called outside a bound request.
    """
    ctx: dict[str, str] = {}
    t = _trace_id.get()
    if t is not None:
        ctx["trace_id"] = t
    s = _session_id.get()
    if s is not None:
        ctx["session_id"] = s
    u = _user_hash.get()
    if u is not None:
        ctx["user_hash"] = u
    return ctx
