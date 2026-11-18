"""Offline tests verifying per-case SQLite isolation and config restoration in src.eval.runner."""
from __future__ import annotations

from pathlib import Path

import pytest

import src.core.actions_db as adb
import src.core.tickets_db as tdb
from src.config import settings
from src.core.llm import LLMNotConfiguredError
from src.eval.runner import run_eval


def test_eval_isolates_actions_and_tickets_db_per_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen_confirm_statuses: list[str] = []
    seen_db_paths: list[str] = []

    class _FakeOrchestrator:
        def run_sync(self, user_id: str, message: str, session_id: str | None = None, trace_id: str | None = None):
            arepo = adb.get_actions_repository()
            trepo = tdb.get_tickets_repository()
            assert arepo.db_path == trepo.db_path
            seen_db_paths.append(arepo.db_path)

            prop = arepo.propose_terminal_replacement(user_id, session_id or "s", "GET-883921", "quebrada", "t1")
            assert prop["status"] == "pending_confirmation"
            conf = arepo.confirm(user_id, session_id or "s", "t2")
            seen_confirm_statuses.append(conf["status"])
            return {"agent_response": "ok", "tools_used": [], "agents_used": ["SupervisorAgent"]}

    outer_db = str(tmp_path / "outer.db")
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", outer_db)
    monkeypatch.setattr(settings, "DATABASE_URL", "")
    tdb.reset_tickets_repository()

    cases = [{"id": f"act_{i}", "turns": ["Quero trocar GET-883921."]} for i in range(3)]
    summary = run_eval(
        cases,
        tmp_path / "run.jsonl",
        "iso-test",
        orchestrator_factory=_FakeOrchestrator,
        sleep_s=0,
    )

    assert summary["ok"] == 3
    assert seen_confirm_statuses == ["executed", "executed", "executed"]
    assert len(set(seen_db_paths)) == 3
    assert all(p != outer_db for p in seen_db_paths)
    tdb.reset_tickets_repository()


def test_eval_ignores_database_url_and_restores_settings_on_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed_urls: list[str] = []

    class _FakeOrchestrator:
        def run_sync(self, user_id: str, message: str, session_id: str | None = None, trace_id: str | None = None):
            observed_urls.append(settings.DATABASE_URL)
            arepo = adb.get_actions_repository()
            assert not str(arepo.db_path).startswith("postgresql")
            return {"agent_response": "ok", "tools_used": [], "agents_used": ["SupervisorAgent"]}

    orig_path = str(tmp_path / "orig.db")
    orig_url = "postgresql://user:pass@127.0.0.1:5432/prod_db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", orig_path)
    monkeypatch.setattr(settings, "DATABASE_URL", orig_url)
    tdb.reset_tickets_repository()

    try:
        summary = run_eval(
            [{"id": "c1", "turns": ["oi"]}, {"id": "c2", "turns": ["tchau"]}],
            tmp_path / "run.jsonl",
            "iso-url",
            orchestrator_factory=_FakeOrchestrator,
            sleep_s=0,
        )
        assert summary["ok"] == 2
        assert observed_urls == ["", ""]
        assert settings.TICKETS_DB_PATH == orig_path
        assert settings.DATABASE_URL == orig_url
    finally:
        monkeypatch.setattr(settings, "DATABASE_URL", "")
        tdb.reset_tickets_repository()


def test_eval_restores_settings_even_when_case_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _ExplodingOrchestrator:
        def run_sync(self, user_id: str, message: str, session_id: str | None = None, trace_id: str | None = None):
            raise LLMNotConfiguredError("missing key")

    orig_path = str(tmp_path / "orig_err.db")
    orig_url = "postgresql://user:pass@127.0.0.1:5432/err_db"
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", orig_path)
    monkeypatch.setattr(settings, "DATABASE_URL", orig_url)
    tdb.reset_tickets_repository()

    try:
        with pytest.raises(LLMNotConfiguredError):
            run_eval(
                [{"id": "boom", "turns": ["oi"]}],
                tmp_path / "run_err.jsonl",
                "iso-err",
                orchestrator_factory=_ExplodingOrchestrator,
                sleep_s=0,
            )
        assert settings.TICKETS_DB_PATH == orig_path
        assert settings.DATABASE_URL == orig_url
    finally:
        monkeypatch.setattr(settings, "DATABASE_URL", "")
        tdb.reset_tickets_repository()
