"""Unit tests for ActionsRepository proposals, confirmations, idempotency, and audit logging (Phase 13C)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from src.core.actions_db import ActionsRepository


def _repo(tmp_path: Path, name: str = "actions.db") -> ActionsRepository:
    return ActionsRepository(tmp_path / name)


def test_propose_supersedes_previous_open_proposal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        p1 = repo.propose_terminal_replacement("cliente1988", "s1", "GET-883921", "tela trincada", "trc-1")
        p2 = repo.propose_terminal_replacement("cliente1988", "s1", "GET-883921", "leitor falhou", "trc-2")
        assert p1["status"] == "pending_confirmation"
        assert p1["action_id"].startswith("ACT-")
        assert p2["action_id"] != p1["action_id"]

        with repo.engine.connect() as conn:
            statuses = {
                r["action_id"]: r["status"]
                for r in conn.execute(sa.text("SELECT action_id, status FROM pending_actions")).mappings().all()
            }
        assert statuses[p1["action_id"]] == "superseded"
        assert statuses[p2["action_id"]] == "proposed"
    finally:
        repo.engine.dispose()


def test_confirm_executes_creates_replacement_and_audit(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        prop = repo.propose_terminal_replacement("cliente1988", "s1", "GET-883921", "sem sinal", "trc-1")
        res = repo.confirm("cliente1988", "s1", "trc-2")
        assert res["status"] == "executed"
        assert res["action_id"] == prop["action_id"]
        assert str(res["request_id"]).startswith("GET-TRC-")

        reps = repo.list_replacements("cliente1988")
        assert len(reps) == 1
        assert reps[0]["request_id"] == res["request_id"]
        audit = repo.list_audit(action="replacement_executed")
        assert len(audit) == 1
        assert audit[0]["outcome"] == "executed"
    finally:
        repo.engine.dispose()


def test_confirm_same_turn_keeps_proposal_pending(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        prop = repo.propose_terminal_replacement("cliente1988", "s1", "GET-883921", "tela", "trc-same")
        same = repo.confirm("cliente1988", "s1", "trc-same")
        assert same["status"] == "same_turn"
        assert same["action_id"] == prop["action_id"]
        assert repo.list_replacements() == []

        later = repo.confirm("cliente1988", "s1", "trc-next")
        assert later["status"] == "executed"
    finally:
        repo.engine.dispose()


def test_confirm_expired_proposal_marks_expired(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        prop = repo.propose_terminal_replacement(
            "cliente1988", "s1", "GET-883921", "bateria", "trc-1", ttl_minutes=0
        )
        res = repo.confirm("cliente1988", "s1", "trc-2")
        assert res["status"] == "expired"
        assert res["action_id"] == prop["action_id"]
        assert repo.list_replacements() == []
        assert any(ev["outcome"] == "expired" for ev in repo.list_audit())
    finally:
        repo.engine.dispose()


def test_confirm_without_pending_returns_no_pending_action(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        res = repo.confirm("cliente1988", "sess-empty", "trc-1")
        assert res == {"status": "no_pending_action", "action_id": None, "request_id": None}
        assert any(ev["outcome"] == "no_pending_action" for ev in repo.list_audit())
    finally:
        repo.engine.dispose()


def test_confirm_when_serial_already_requested_returns_existing(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        repo.propose_terminal_replacement("cliente1988", "s1", "GET-883921", "motivo 1", "trc-1")
        first = repo.confirm("cliente1988", "s1", "trc-2")

        repo.propose_terminal_replacement("cliente1988", "s2", "GET-883921", "motivo 2", "trc-3")
        second = repo.confirm("cliente1988", "s2", "trc-4")
        assert second["status"] == "already_requested"
        assert second["request_id"] == first["request_id"]
        assert len(repo.list_replacements()) == 1
    finally:
        repo.engine.dispose()


def test_decline_marks_declined_and_blocks_later_confirm(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        prop = repo.propose_terminal_replacement("cliente1988", "s1", "GET-883921", "nao liga", "trc-1")
        dec = repo.decline("cliente1988", "s1", "trc-2")
        assert dec["status"] == "declined"
        assert dec["action_id"] == prop["action_id"]
        assert repo.decline("cliente1988", "s1", "trc-3")["status"] == "no_pending_action"
        assert repo.confirm("cliente1988", "s1", "trc-4")["status"] == "no_pending_action"
    finally:
        repo.engine.dispose()


def test_partial_unique_index_prevents_two_open_requests_for_same_serial(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        repo.propose_terminal_replacement("cliente1988", "s1", "GET-883921", "defeito", "trc-1")
        repo.confirm("cliente1988", "s1", "trc-2")

        with pytest.raises(IntegrityError), repo.engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO terminal_replacements (request_id, user_id, serial_number, reason, status, "
                    "action_id, created_at) VALUES ('GET-TRC-DUP', 'cliente1988', 'GET-883921', 'x', "
                    "'requested', 'ACT-DUP', '2026-11-18T00:00:00+00:00')"
                )
            )
    finally:
        repo.engine.dispose()


def test_audit_never_stores_raw_user_id_or_free_text(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    raw_user = "lojista-secreto-9911"
    free_reason = "FREE_TEXT_MARKER_XYZ_8899"
    try:
        repo.propose_terminal_replacement(raw_user, "s1", "GET-883921", free_reason, "trc-1")
        repo.record_audit(
            actor_type="merchant",
            actor_id=raw_user,
            action="custom_event",
            target_type="ticket",
            target_id="GET-TKT-1",
            outcome="ok",
            details={"status": "ok", "free_text": free_reason, "reply": free_reason},
        )
        rows = repo.list_audit(limit=50)
        blob = json.dumps(rows, ensure_ascii=False)
        assert raw_user not in blob
        assert free_reason not in blob
        assert all(ev["actor_hash"].startswith("u_") for ev in rows)
    finally:
        repo.engine.dispose()


def test_list_replacements_and_list_audit_filter_and_limit(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    try:
        repo.propose_terminal_replacement("u1", "s1", "GET-111", "a", "t1")
        repo.confirm("u1", "s1", "t2")
        repo.propose_terminal_replacement("u2", "s2", "GET-222", "b", "t3")
        repo.confirm("u2", "s2", "t4")

        assert len(repo.list_replacements("u1")) == 1
        assert len(repo.list_replacements()) == 2
        assert len(repo.list_audit(action="replacement_executed")) == 2
        assert len(repo.list_audit(limit=1)) == 1
    finally:
        repo.engine.dispose()
