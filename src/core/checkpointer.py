"""Checkpointer builders for LangGraph conversation persistence (PostgreSQL or SQLite)."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from src.config import settings
from src.core.db import is_postgres_url


def build_sqlite_checkpointer(path: str | Path) -> SqliteSaver:
    """Build a persistent SqliteSaver at the given file path."""
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    return SqliteSaver(conn)


def _psycopg_conninfo(url: str) -> str:
    clean = str(url).strip()
    if clean.startswith("postgresql+psycopg://"):
        return "postgresql://" + clean[len("postgresql+psycopg://") :]
    return clean


def build_postgres_checkpointer(url: str, pool_size: int = 5) -> PostgresSaver:
    """Build and initialize a persistent PostgresSaver backed by a psycopg connection pool."""
    pool = ConnectionPool(
        conninfo=_psycopg_conninfo(url),
        max_size=pool_size,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    saver = PostgresSaver(pool)
    saver.setup()
    return saver


def checkpoint_backend() -> str:
    """Return active checkpointer backend name ('postgres' or 'sqlite')."""
    return "postgres" if is_postgres_url(settings.DATABASE_URL) else "sqlite"


def checkpointer_label() -> str:
    """Return human-readable checkpointer descriptor for API introspection."""
    if checkpoint_backend() == "postgres":
        return "PostgresSaver (thread user_id:session_id)"
    return "SqliteSaver (thread user_id:session_id)"


def build_checkpointer() -> Any:
    """Select and initialize the configured LangGraph checkpointer."""
    if is_postgres_url(settings.DATABASE_URL):
        return build_postgres_checkpointer(settings.DATABASE_URL, pool_size=settings.DB_POOL_SIZE)
    return build_sqlite_checkpointer(settings.CHECKPOINT_DB_PATH)
