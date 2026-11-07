"""Tests for SQLite checkpointer, persistence across restarts, user isolation, and fail-fast configuration."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

import src.core.graph as graph_mod
from src.config import settings
from src.core import auth
from src.core.checkpointer import build_sqlite_checkpointer
from src.core.graph import OrchestrationGraph
from src.main import app
from tests.fakes import ScriptedChatModel


def _extract_seen_text(model: ScriptedChatModel, start_idx: int = 0) -> str:
    """Helper to join all message contents received by the chat model from a given call index."""
    return " ".join(str(m.content) for call in model.received[start_idx:] for m in call)


def test_build_sqlite_checkpointer_creates_dirs_and_file(tmp_path: Path) -> None:
    """build_sqlite_checkpointer creates parent directories and returns SqliteSaver."""
    db_path = tmp_path / "nested" / "dir" / "checkpoints.db"
    saver = build_sqlite_checkpointer(db_path)
    assert isinstance(saver, SqliteSaver)
    assert db_path.parent.is_dir()

    conn = getattr(saver, "conn", None)
    assert conn is not None
    rows = conn.execute("PRAGMA database_list").fetchall()
    main_db = next((r[2] for r in rows if r[1] == "main"), "")
    assert os.path.samefile(main_db, str(db_path))


def test_build_sqlite_checkpointer_unusable_path_raises(tmp_path: Path) -> None:
    """build_sqlite_checkpointer raises error loudly if parent is a regular file."""
    blocker = tmp_path / "plain_file"
    blocker.write_text("blocked", encoding="utf-8")
    before_files = set(tmp_path.iterdir())

    with pytest.raises((sqlite3.OperationalError, OSError)):
        build_sqlite_checkpointer(blocker / "sub" / "cp.db")

    # Ensure no fallback files were created
    assert set(tmp_path.iterdir()) == before_files


def test_orchestration_graph_memory_survives_restart(tmp_path: Path) -> None:
    """A new OrchestrationGraph instance over the same SQLite file retains prior conversational turns."""
    db_file = tmp_path / "checkpoints.db"

    # Turn 1: merchant_a stores a secret
    m1 = ScriptedChatModel(responses=[AIMessage(content="Entendido, código anotado.")])
    g1 = OrchestrationGraph(chat_model=m1, checkpointer=build_sqlite_checkpointer(db_file))
    g1.run_sync(user_id="merchant_a", message="Meu código secreto é SEGREDO-RESTART-42", session_id="sess-restart-1")

    # Turn 2: Simulate process restart by building a completely new graph over the same DB
    m2 = ScriptedChatModel(responses=[AIMessage(content="Seu código é SEGREDO-RESTART-42.")])
    g2 = OrchestrationGraph(chat_model=m2, checkpointer=build_sqlite_checkpointer(db_file))
    g2.run_sync(user_id="merchant_a", message="Qual era o meu código secreto?", session_id="sess-restart-1")

    # The prompt received by m2 must contain the secret from turn 1
    seen_text = _extract_seen_text(m2)
    assert "SEGREDO-RESTART-42" in seen_text

    # Verify state in checkpointer
    state = g2.graph.get_state({"configurable": {"thread_id": "merchant_a:sess-restart-1"}})
    assert bool(state.values)
    assert len(state.values.get("messages", [])) >= 4


def test_orchestration_graph_user_isolation_sqlite(tmp_path: Path) -> None:
    """Users sharing the same session_id are isolated by composite thread_id user_id:session_id."""
    db_file = tmp_path / "checkpoints.db"

    # Turn 1: user_a with session 'shared-sid'
    m1 = ScriptedChatModel(responses=[AIMessage(content="Anotado para user_a.")])
    g1 = OrchestrationGraph(chat_model=m1, checkpointer=build_sqlite_checkpointer(db_file))
    g1.run_sync(user_id="user_a", message="Meu segredo pessoal é ALICE-SECRET-777", session_id="shared-sid")

    # Turn 2: user_b with the exact same session_id 'shared-sid'
    m2 = ScriptedChatModel(responses=[AIMessage(content="Olá user_b, como posso ajudar?")])
    g2 = OrchestrationGraph(chat_model=m2, checkpointer=build_sqlite_checkpointer(db_file))
    g2.run_sync(user_id="user_b", message="O que eu te disse antes?", session_id="shared-sid")

    # user_b must NOT see user_a's secret
    seen_text = _extract_seen_text(m2)
    assert "ALICE-SECRET-777" not in seen_text

    # Check distinct threads on disk
    with sqlite3.connect(db_file) as conn:
        threads = {r[0] for r in conn.execute("SELECT DISTINCT thread_id FROM checkpoints")}
    assert threads == {"user_a:shared-sid", "user_b:shared-sid"}


def test_orchestration_graph_default_in_memory() -> None:
    """OrchestrationGraph() without checkpointer defaults to in-memory MemorySaver."""
    g = OrchestrationGraph()
    assert isinstance(g.checkpointer, MemorySaver)


def test_malformed_api_keys_fail_fast_and_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed API_KEYS causes 503 on /chat, 'invalid' auth_mode on /health, and failure on app startup."""
    monkeypatch.setattr(settings, "API_KEYS", "invalid-hash:user:customer")

    with pytest.raises(ValueError):
        auth.validate_auth_config()

    client = TestClient(app)
    response = client.post("/chat", json={"message": "olá"}, headers={"X-API-Key": "some-key"})
    assert response.status_code == 503
    assert "API_KEYS" in response.text

    health = client.get("/health").json()
    assert health.get("auth_mode") == "invalid"

    # Startup via lifespan fails loudly
    with pytest.raises(ValueError), TestClient(app):
        pass


def test_startup_fails_on_unusable_checkpoint_db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifespan refuses to start the application if CHECKPOINT_DB_PATH cannot be opened."""
    blocker = tmp_path / "plain_file"
    blocker.write_text("blocker", encoding="utf-8")
    unusable_path = str(blocker / "sub" / "checkpoints.db")

    monkeypatch.setattr(settings, "CHECKPOINT_DB_PATH", unusable_path)
    monkeypatch.setattr(graph_mod, "_orchestrator_instance", None)

    with pytest.raises((sqlite3.OperationalError, OSError)), TestClient(app):
        pass
