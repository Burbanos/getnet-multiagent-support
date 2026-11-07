"""Persistent SQLite repository for human escalation tickets with lifecycle management."""
from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from src.config import settings

logger = logging.getLogger("multiagent.tickets_db")

VALID_PRIORITIES = ("standard", "high")
VALID_STATUSES = ("open", "in_progress", "answered", "closed")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "answered", "closed"},
    "in_progress": {"answered", "closed"},
    "answered": {"closed"},
    "closed": set(),
}


class TicketTransitionError(ValueError):
    """Raised when an illegal ticket status transition is attempted."""


def _get_message_text(msg: Any) -> str:
    """Extract clean text content from a message object or dict."""
    t = getattr(msg, "text", None)
    if isinstance(t, str) and t.strip():
        return t
    content = getattr(msg, "content", None)
    if content is None and isinstance(msg, dict):
        content = msg.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts: list[str] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                texts.append(part.get("text", ""))
            elif isinstance(part, str):
                texts.append(part)
        return "".join(texts)
    return ""


def transcript_snapshot(messages: list[Any], limit: int = 20, max_chars: int = 2000) -> list[dict[str, str]]:
    """
    Extract a sanitized snapshot of recent conversation messages for ticket escalation.
    Includes only user and assistant messages with non-empty text.
    """
    result: list[dict[str, str]] = []
    for msg in messages:
        if isinstance(msg, HumanMessage) or getattr(msg, "type", "") == "human":
            role = "user"
        elif isinstance(msg, AIMessage) or getattr(msg, "type", "") == "ai":
            role = "assistant"
        elif isinstance(msg, dict):
            r = msg.get("role", "")
            if r in ("user", "human"):
                role = "user"
            elif r in ("assistant", "ai"):
                role = "assistant"
            else:
                continue
        else:
            continue

        text = _get_message_text(msg).strip()
        if not text:
            continue

        result.append({"role": role, "content": text[:max_chars]})

    return result[-limit:]


class TicketsRepository:
    """Manages SQLite storage and lifecycle for customer escalation tickets."""

    def __init__(self, db_path: str) -> None:
        self.db_path = str(db_path)
        path_obj = Path(self.db_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    priority TEXT NOT NULL DEFAULT 'standard',
                    channel TEXT NOT NULL DEFAULT 'ai_chat',
                    transcript TEXT NOT NULL DEFAULT '[]',
                    operator_reply TEXT,
                    operator_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    answered_at TEXT
                )
            """)
            cursor = conn.cursor()
            existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(tickets)").fetchall()}
            if "session_id" not in existing_cols:
                cursor.execute("ALTER TABLE tickets ADD COLUMN session_id TEXT")
            if "transcript" not in existing_cols:
                cursor.execute("ALTER TABLE tickets ADD COLUMN transcript TEXT NOT NULL DEFAULT '[]'")
            if "operator_reply" not in existing_cols:
                cursor.execute("ALTER TABLE tickets ADD COLUMN operator_reply TEXT")
            if "operator_id" not in existing_cols:
                cursor.execute("ALTER TABLE tickets ADD COLUMN operator_id TEXT")
            if "answered_at" not in existing_cols:
                cursor.execute("ALTER TABLE tickets ADD COLUMN answered_at TEXT")
            conn.commit()
            logger.info(f"Tickets database initialized at: {self.db_path}")

    def create_ticket(
        self,
        user_id: str,
        reason: str,
        priority: str = "standard",
        session_id: str | None = None,
        transcript: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create and persist a new customer support escalation ticket."""
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{priority}': must be one of {VALID_PRIORITIES}")

        clean_reason = reason.strip() if reason and reason.strip() else "Solicitação de atendimento humano."
        transcript_json = json.dumps(transcript or [], ensure_ascii=False)
        now = datetime.now(UTC).isoformat()
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:4].upper()
        ticket_id = f"GET-TKT-{date_str}-{suffix}"

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tickets (
                    ticket_id, user_id, session_id, reason, status, priority,
                    channel, transcript, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'open', ?, 'ai_chat', ?, ?, ?)
            """, (ticket_id, user_id, session_id, clean_reason, priority, transcript_json, now, now))
            conn.commit()

        logger.info(f"Persisted escalation ticket {ticket_id} for user {user_id}")

        message = (
            f"Chamado registrado com sucesso sob o protocolo **{ticket_id}**. "
            f"O status pode ser consultado a qualquer momento via endpoint `GET /tickets/{ticket_id}`."
        )

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "user_id": user_id,
            "session_id": session_id,
            "ticket_status": "open",
            "priority": priority,
            "created_at": now,
            "reason": clean_reason,
            "tracking_endpoint": f"/tickets/{ticket_id}",
            "message": message,
        }

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        tr = data.get("transcript")
        if isinstance(tr, str):
            try:
                data["transcript"] = json.loads(tr)
            except (json.JSONDecodeError, TypeError):
                data["transcript"] = []
        elif tr is None:
            data["transcript"] = []
        return data

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        """Retrieve ticket details by ticket ID with decoded transcript."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
        return None

    def list_tickets(
        self,
        user_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List persisted tickets with optional filtering and clamped limit."""
        clamped_limit = max(1, min(200, limit))
        query = "SELECT * FROM tickets"
        conditions: list[str] = []
        params: list[Any] = []

        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if status:
            conditions.append("status = ?")
            params.append(status)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(clamped_limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def update_ticket(
        self,
        ticket_id: str,
        *,
        status: str | None = None,
        reply: str | None = None,
        operator_id: str,
    ) -> dict[str, Any] | None:
        """Update ticket status and operator reply following allowed state transitions."""
        current = self.get_ticket(ticket_id)
        if current is None:
            return None

        if status is None and reply is None:
            raise ValueError("Either status or reply must be provided for ticket update")

        if reply is not None:
            clean_reply = reply.strip()
            if not clean_reply:
                raise ValueError("Operator reply cannot be empty")
            new_status = "answered"
        else:
            clean_reply = None
            new_status = status

        if new_status not in VALID_STATUSES:
            raise ValueError(f"Unknown ticket status '{new_status}': must be one of {VALID_STATUSES}")

        if status == "answered" and reply is None:
            raise ValueError("Status 'answered' requires an operator reply")

        curr_status = current["status"]
        if new_status not in ALLOWED_TRANSITIONS.get(curr_status, set()):
            raise TicketTransitionError(
                f"Cannot transition ticket {ticket_id} from '{curr_status}' to '{new_status}'"
            )

        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            if clean_reply is not None:
                conn.execute("""
                    UPDATE tickets
                    SET status = ?, operator_reply = ?, operator_id = ?, answered_at = ?, updated_at = ?
                    WHERE ticket_id = ?
                """, (new_status, clean_reply, operator_id, now, now, ticket_id))
            else:
                conn.execute("""
                    UPDATE tickets
                    SET status = ?, operator_id = ?, updated_at = ?
                    WHERE ticket_id = ?
                """, (new_status, operator_id, now, ticket_id))
            conn.commit()

        return self.get_ticket(ticket_id)


_tickets_repo: TicketsRepository | None = None


def get_tickets_repository() -> TicketsRepository:
    """Dependency getter for tickets repository singleton."""
    global _tickets_repo
    if _tickets_repo is None:
        _tickets_repo = TicketsRepository(settings.TICKETS_DB_PATH)
    return _tickets_repo


def reset_tickets_repository() -> None:
    """Reset tickets repository singleton."""
    global _tickets_repo
    _tickets_repo = None
