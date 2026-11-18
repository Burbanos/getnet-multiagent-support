"""Offline unit tests for PostgreSQL/SQLite database helpers, schema migration, checkpointer, and /health."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.sqlite import SqliteSaver

from src.config import settings
from src.core import checkpointer as cp
from src.core import db
from src.core.tickets_db import TicketsRepository, TicketTransitionError, reset_tickets_repository
from src.main import app


def test_is_postgres_url_variants(tmp_path: Path) -> None:
    assert db.is_postgres_url("postgresql://user:pass@localhost:5432/db") is True
    assert db.is_postgres_url("postgresql+psycopg://user:pass@localhost:5432/db") is True
    assert db.is_postgres_url("sqlite:///local.db") is False
    assert db.is_postgres_url(str(tmp_path / "tickets.db")) is False
    assert db.is_postgres_url("") is False


def test_make_engine_sqlite_creates_parent_directory(tmp_path: Path) -> None:
    db_file = tmp_path / "nested" / "sub" / "tickets.db"
    assert not db_file.parent.exists()

    engine = db.make_engine(str(db_file))
    try:
        db.ensure_schema(engine)
        assert db_file.parent.exists()
        assert db_file.exists()
        assert db.ping(engine) is True
    finally:
        engine.dispose()


def test_ping_handles_healthy_and_broken_engines_without_raising(caplog: pytest.LogCaptureFixture) -> None:
    class BrokenEngine:
        def connect(self, *args, **kwargs):
            raise RuntimeError("secret-connection-string://pw")

    assert db.ping(BrokenEngine()) is False
    assert "secret-connection-string" not in caplog.text


def test_ensure_schema_migrates_legacy_tickets_table(tmp_path: Path) -> None:
    old_db = tmp_path / "legacy.db"
    with sqlite3.connect(old_db) as conn:
        conn.execute(
            "CREATE TABLE tickets ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "ticket_id TEXT UNIQUE NOT NULL, "
            "user_id TEXT NOT NULL, "
            "reason TEXT NOT NULL, "
            "status TEXT NOT NULL DEFAULT 'open', "
            "priority TEXT NOT NULL DEFAULT 'standard', "
            "channel TEXT NOT NULL DEFAULT 'ai_chat', "
            "created_at TEXT NOT NULL, "
            "updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO tickets (ticket_id, user_id, reason, created_at, updated_at) "
            "VALUES ('GET-TKT-LEGACY1', 'u-legacy', 'teste', '2026-01-01', '2026-01-01')"
        )

    engine = db.make_engine(str(old_db))
    try:
        db.ensure_schema(engine)
        with sqlite3.connect(old_db) as conn:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(tickets)")}
            assert {
                "session_id",
                "transcript",
                "operator_reply",
                "operator_id",
                "answered_at",
                "delivered_at",
                "notified_at",
                "notification_status",
            } <= cols
            row = conn.execute("SELECT ticket_id, transcript FROM tickets WHERE ticket_id = 'GET-TKT-LEGACY1'").fetchone()
            assert row == ("GET-TKT-LEGACY1", "[]")
    finally:
        engine.dispose()


def test_tickets_repository_sqlite_lifecycle_and_delivery(tmp_path: Path) -> None:
    repo = TicketsRepository(str(tmp_path / "repo" / "tickets.db"))
    try:
        created = repo.create_ticket(
            user_id="merchant-1",
            reason="dúvida de liquidação",
            priority="high",
            session_id="sess-1",
            transcript=[{"role": "user", "content": "oi"}],
        )
        tid = created["ticket_id"]
        assert created["status"] == "success"
        assert hasattr(repo, "engine")

        updated = repo.update_ticket(tid, status="in_progress", operator_id="op-1")
        assert updated is not None and updated["status"] == "in_progress"

        with pytest.raises(TicketTransitionError):
            repo.update_ticket(tid, status="open", operator_id="op-1")

        answered = repo.update_ticket(tid, reply="Resposta do atendente", operator_id="op-1")
        assert answered is not None and answered["status"] == "answered"

        assert repo.mark_delivered(tid) is True
        assert repo.mark_delivered(tid) is False

        assert repo.append_customer_message(tid, "obrigado") is True
        assert repo.append_customer_message("GET-TKT-MISSING", "x") is False
        fetched = repo.get_ticket(tid)
        assert fetched is not None
        assert [m["content"] for m in fetched["transcript"]] == ["oi", "obrigado"]
    finally:
        repo.engine.dispose()


def test_build_checkpointer_selects_sqlite_without_database_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DATABASE_URL", "")
    monkeypatch.setattr(settings, "CHECKPOINT_DB_PATH", str(tmp_path / "cp" / "checkpoints.db"))

    saver = cp.build_checkpointer()
    try:
        assert isinstance(saver, SqliteSaver)
        assert cp.checkpoint_backend() == "sqlite"
        assert cp.checkpointer_label() == "SqliteSaver (thread user_id:session_id)"
    finally:
        saver.conn.close()


def test_validate_state_config_production_fail_fast_without_leaking_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "DATABASE_URL", "")
    monkeypatch.setattr(settings, "REDIS_URL", "redis://secret-redis:6379/0")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db.validate_state_config()

    secret_sqlite = "sqlite:///secret-local-path/state.db"
    monkeypatch.setattr(settings, "DATABASE_URL", secret_sqlite)
    with pytest.raises(RuntimeError) as sqlite_exc:
        db.validate_state_config()
    assert "DATABASE_URL" in str(sqlite_exc.value)
    assert "secret-local-path" not in str(sqlite_exc.value)

    secret_pg = "postgresql://user:supersecretpw@pg.internal:5432/prod"
    monkeypatch.setattr(settings, "DATABASE_URL", secret_pg)
    monkeypatch.setattr(settings, "REDIS_URL", "")
    with pytest.raises(RuntimeError) as redis_exc:
        db.validate_state_config()
    assert "REDIS_URL" in str(redis_exc.value)
    assert "supersecretpw" not in str(redis_exc.value)


def test_health_endpoint_reports_backends_and_503_on_ping_failure(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "health_tickets.db"))
    monkeypatch.setattr(settings, "REPLICA_NAME", "app-a")
    reset_tickets_repository()

    ok_resp = client.get("/health")
    assert ok_resp.status_code == 200
    body = ok_resp.json()
    assert body["status"] == "healthy"
    assert body["state_backend"] == "sqlite"
    assert body["rate_limit_backend"] == "memory"
    assert body["tracing_exporter"] == "none"
    assert body["replica"] == "app-a"

    class DownEngine:
        def connect(self, *args, **kwargs):
            raise RuntimeError("db offline")

    from src.core.tickets_db import get_tickets_repository

    repo = get_tickets_repository()
    real_engine = repo.engine
    repo.engine = DownEngine()
    try:
        fail_resp = client.get("/health")
        assert fail_resp.status_code == 503
        fail_body = fail_resp.json()
        assert fail_body["status"] == "unhealthy"
        assert fail_body["state_backend"] == "sqlite"
        assert fail_body["rate_limit_backend"] == "memory"
    finally:
        repo.engine = real_engine


def test_agents_endpoint_names_postgres_without_exposing_url(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)
    assert client.get("/agents").json()["checkpointer"] == "SqliteSaver (thread user_id:session_id)"

    secret_url = "postgresql://user:secretpw@postgres:5432/getnet"
    monkeypatch.setattr(settings, "DATABASE_URL", secret_url)
    pg_resp = client.get("/agents")
    assert pg_resp.status_code == 200
    assert pg_resp.json()["checkpointer"] == "PostgresSaver (thread user_id:session_id)"
    assert "secretpw" not in pg_resp.text
    assert "postgresql://" not in pg_resp.text
