"""Database engine construction, schema management, and health checks (PostgreSQL & SQLite)."""
from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

import psycopg
from sqlalchemy import (
    Column,
    Engine,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import URL

from src.config import settings

metadata = MetaData()

tickets = Table(
    "tickets",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ticket_id", Text, unique=True, nullable=False),
    Column("user_id", Text, nullable=False),
    Column("session_id", Text, nullable=True),
    Column("reason", Text, nullable=False),
    Column("status", Text, nullable=False, server_default=text("'open'")),
    Column("priority", Text, nullable=False, server_default=text("'standard'")),
    Column("channel", Text, nullable=False, server_default=text("'ai_chat'")),
    Column("transcript", Text, nullable=False, server_default=text("'[]'")),
    Column("operator_reply", Text, nullable=True),
    Column("operator_id", Text, nullable=True),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
    Column("answered_at", Text, nullable=True),
    Column("delivered_at", Text, nullable=True),
    Column("notified_at", Text, nullable=True),
    Column("notification_status", Text, nullable=True),
)

pending_actions = Table(
    "pending_actions",
    metadata,
    Column("action_id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("session_id", Text, nullable=False),
    Column("action_type", Text, nullable=False),
    Column("serial_number", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("proposed_trace_id", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    Column("expires_at", Text, nullable=False),
    Column("resolved_at", Text, nullable=True),
    Column("request_id", Text, nullable=True),
)

terminal_replacements = Table(
    "terminal_replacements",
    metadata,
    Column("request_id", Text, primary_key=True),
    Column("user_id", Text, nullable=False),
    Column("serial_number", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("status", Text, nullable=False, server_default=text("'requested'")),
    Column("action_id", Text, nullable=False),
    Column("created_at", Text, nullable=False),
    Index(
        "ix_terminal_replacements_open_serial",
        "serial_number",
        unique=True,
        sqlite_where=text("status = 'requested'"),
        postgresql_where=text("status = 'requested'"),
    ),
)

audit_events = Table(
    "audit_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", Text, nullable=False),
    Column("actor_type", Text, nullable=False),
    Column("actor_hash", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("target_type", Text, nullable=False),
    Column("target_id", Text, nullable=False),
    Column("outcome", Text, nullable=False),
    Column("details", Text, nullable=False, server_default=text("'{}'")),
    Column("otel_trace_id", Text, nullable=True),
)

refresh_tokens = Table(
    "refresh_tokens",
    metadata,
    Column("token_hash", Text, primary_key=True),
    Column("family_id", Text, nullable=False),
    Column("user_id", Text, nullable=False),
    Column("role", Text, nullable=False),
    Column("key_id", Text, nullable=False),
    Column("issued_at", Text, nullable=False),
    Column("expires_at", Text, nullable=False),
    Column("used_at", Text, nullable=True),
    Column("revoked_at", Text, nullable=True),
    Index("ix_refresh_tokens_family_id", "family_id"),
)


def is_postgres_url(target: str) -> bool:
    """Return True if target uses a postgresql:// or postgresql+psycopg:// scheme."""
    clean = str(target or "").strip()
    return clean.startswith(("postgresql://", "postgresql+psycopg://"))


def normalize_postgres_psycopg_url(url: str) -> str:
    """Normalize a PostgreSQL URL to the postgresql+psycopg:// SQLAlchemy driver scheme."""
    clean = str(url).strip()
    if clean.startswith("postgresql://"):
        return "postgresql+psycopg://" + clean[len("postgresql://") :]
    return clean


def make_engine(target: str, pool_size: int = 5) -> Engine:
    """Create a SQLAlchemy Engine for PostgreSQL or a local SQLite database file path."""
    clean = str(target).strip()
    if is_postgres_url(clean):
        return create_engine(
            normalize_postgres_psycopg_url(clean),
            pool_pre_ping=True,
            pool_size=pool_size,
        )

    db_file = clean.removeprefix("sqlite:///")
    if db_file and db_file != ":memory:":
        path_obj = Path(db_file)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        url = URL.create("sqlite", database=str(path_obj))
    else:
        url = URL.create("sqlite", database=":memory:")

    return create_engine(
        url,
        connect_args={"timeout": 10.0, "check_same_thread": False},
    )


SCHEMA_LOCK_KEY = 918273645


def _raw_postgres_conninfo(target: str) -> str:
    clean = str(target).strip()
    if clean.startswith("postgresql+psycopg://"):
        return "postgresql://" + clean.removeprefix("postgresql+psycopg://")
    return clean


@contextmanager
def schema_lock(target: str, timeout_seconds: float = 60.0) -> Iterator[None]:
    """Serialize DDL and checkpointer setup across concurrent PostgreSQL workers."""
    if not is_postgres_url(target):
        yield
        return

    conninfo = _raw_postgres_conninfo(target)
    deadline = time.monotonic() + timeout_seconds
    with psycopg.connect(conninfo, autocommit=True) as conn:
        acquired = False
        while True:
            row = conn.execute("SELECT pg_try_advisory_lock(%s)", (SCHEMA_LOCK_KEY,)).fetchone()
            if row and bool(row[0]):
                acquired = True
                break
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting {timeout_seconds}s for Postgres schema lock")
            time.sleep(0.1)
        try:
            yield
        finally:
            if acquired:
                with suppress(Exception):
                    conn.execute("SELECT pg_advisory_unlock(%s)", (SCHEMA_LOCK_KEY,))


def ensure_schema(engine: Engine) -> None:
    """Create missing tables and add any missing columns to existing tables."""
    target_url = engine.url.render_as_string(hide_password=False)
    with schema_lock(target_url):
        metadata.create_all(engine)
        inspector = inspect(engine)
        dialect = engine.dialect

        for table in metadata.sorted_tables:
            existing_cols = {col["name"] for col in inspector.get_columns(table.name)}
            missing_cols = [col for col in table.columns if col.name not in existing_cols]
            if not missing_cols:
                continue

            with engine.begin() as conn:
                for col in missing_cols:
                    col_type = col.type.compile(dialect=dialect)
                    default_clause = ""
                    if col.server_default is not None and getattr(col.server_default, "arg", None) is not None:
                        arg = col.server_default.arg
                        compiled_default = arg.compile(dialect=dialect) if hasattr(arg, "compile") else str(arg)
                        default_clause = f" DEFAULT {compiled_default}"
                    null_clause = " NOT NULL" if not col.nullable else ""
                    stmt = text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}{null_clause}{default_clause}")
                    conn.execute(stmt)


def ping(engine: Any) -> bool:
    """Return True if the database responds to SELECT 1, False otherwise (never logs error details)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


def validate_state_config() -> None:
    """Fail fast in production if distributed PostgreSQL or Redis configuration is missing."""
    if settings.APP_ENV.lower() != "production":
        return
    if not is_postgres_url(settings.DATABASE_URL):
        raise RuntimeError("DATABASE_URL must be configured with a PostgreSQL URL when APP_ENV=production.")
    if not settings.REDIS_URL.strip():
        raise RuntimeError("REDIS_URL must be configured when APP_ENV=production.")
