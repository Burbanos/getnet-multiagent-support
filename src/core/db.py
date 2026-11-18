"""Database engine construction, schema management, and health checks (PostgreSQL & SQLite)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    Engine,
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


def ensure_schema(engine: Engine) -> None:
    """Create missing tables and add any missing columns to existing tables."""
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
