"""Persistent repository for human escalation tickets over PostgreSQL or SQLite via SQLAlchemy Core."""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import and_, insert, select, update

from src.config import settings
from src.core import metrics
from src.core.db import ensure_schema, make_engine, tickets

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
    """Manages SQLite or PostgreSQL storage and lifecycle for customer escalation tickets."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        self.engine = make_engine(self.db_path, pool_size=settings.DB_POOL_SIZE)
        ensure_schema(self.engine)
        logger.info("Tickets repository initialized")

    def create_ticket(
        self,
        user_id: str,
        reason: str,
        priority: str = "standard",
        session_id: str | None = None,
        transcript: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create and persist a new customer support escalation ticket."""
        if not user_id or not str(user_id).strip():
            raise ValueError("user_id cannot be empty")
        clean_user_id = str(user_id).strip()

        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{priority}': must be one of {VALID_PRIORITIES}")

        clean_reason = reason.strip() if reason and reason.strip() else "Solicitação de atendimento humano."
        transcript_json = json.dumps(transcript or [], ensure_ascii=False)
        now = datetime.now(UTC).isoformat()
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:10].upper()
        ticket_id = f"GET-TKT-{date_str}-{suffix}"

        stmt = insert(tickets).values(
            ticket_id=ticket_id,
            user_id=clean_user_id,
            session_id=session_id,
            reason=clean_reason,
            status="open",
            priority=priority,
            channel="ai_chat",
            transcript=transcript_json,
            created_at=now,
            updated_at=now,
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

        logger.info(f"Persisted escalation ticket {ticket_id}")
        metrics.inc_escalation()

        message = (
            f"Chamado registrado com sucesso sob o protocolo **{ticket_id}**. "
            f"O status pode ser consultado a qualquer momento via endpoint `GET /tickets/{ticket_id}`."
        )

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "user_id": clean_user_id,
            "session_id": session_id,
            "ticket_status": "open",
            "priority": priority,
            "created_at": now,
            "reason": clean_reason,
            "tracking_endpoint": f"/tickets/{ticket_id}",
            "message": message,
        }

    def _row_to_dict(self, row: Mapping[str, Any]) -> dict[str, Any]:
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
        stmt = select(tickets).where(tickets.c.ticket_id == ticket_id)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
            if row is not None:
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
        stmt = select(tickets)
        conditions = []
        if user_id:
            conditions.append(tickets.c.user_id == user_id)
        if status:
            conditions.append(tickets.c.status == status)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(tickets.c.id.desc()).limit(clamped_limit)

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
            return [self._row_to_dict(row) for row in rows]

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
        values: dict[str, Any] = {
            "status": new_status,
            "operator_id": operator_id,
            "updated_at": now,
        }
        if clean_reply is not None:
            values["operator_reply"] = clean_reply
            values["answered_at"] = now

        stmt = (
            update(tickets)
            .where(and_(tickets.c.ticket_id == ticket_id, tickets.c.status == curr_status))
            .values(**values)
        )
        with self.engine.begin() as conn:
            res = conn.execute(stmt)
            if (res.rowcount or 0) == 0:
                raise TicketTransitionError(
                    f"Ticket {ticket_id} status changed concurrently (expected '{curr_status}')"
                )

        return self.get_ticket(ticket_id)

    def mark_delivered(self, ticket_id: str) -> bool:
        """Mark ticket as delivered to the user in the chat session. Returns True only if marked now."""
        now = datetime.now(UTC).isoformat()
        stmt = (
            update(tickets)
            .where(and_(tickets.c.ticket_id == ticket_id, tickets.c.delivered_at.is_(None)))
            .values(delivered_at=now)
        )
        with self.engine.begin() as conn:
            res = conn.execute(stmt)
            return (res.rowcount or 0) > 0

    def record_notification(self, ticket_id: str, status: str) -> bool:
        """Record the operator webhook notification outcome; sets notified_at only when status == 'sent'."""
        values: dict[str, Any] = {"notification_status": status}
        if status == "sent":
            values["notified_at"] = datetime.now(UTC).isoformat()
        stmt = update(tickets).where(tickets.c.ticket_id == ticket_id).values(**values)
        with self.engine.begin() as conn:
            res = conn.execute(stmt)
            return (res.rowcount or 0) > 0

    def append_customer_message(self, ticket_id: str, content: str) -> bool:
        """Append a user message to the ticket's transcript inside one locked transaction."""
        clean_content = content[:2000]
        now = datetime.now(UTC).isoformat()

        with self.engine.begin() as conn:
            row = conn.execute(
                select(tickets.c.transcript)
                .where(tickets.c.ticket_id == ticket_id)
                .with_for_update()
            ).mappings().first()
            if row is None:
                return False

            raw_tr = row.get("transcript")
            if isinstance(raw_tr, str):
                try:
                    transcript = list(json.loads(raw_tr) or [])
                except (json.JSONDecodeError, TypeError):
                    transcript = []
            elif isinstance(raw_tr, list):
                transcript = list(raw_tr)
            else:
                transcript = []

            transcript.append({"role": "user", "content": clean_content})
            tr_json = json.dumps(transcript, ensure_ascii=False)

            res = conn.execute(
                update(tickets)
                .where(tickets.c.ticket_id == ticket_id)
                .values(transcript=tr_json, updated_at=now)
            )
            return (res.rowcount or 0) > 0


_tickets_repo: TicketsRepository | None = None


def get_tickets_repository() -> TicketsRepository:
    """Dependency getter for tickets repository singleton."""
    global _tickets_repo
    if _tickets_repo is None:
        target = settings.DATABASE_URL.strip() or settings.TICKETS_DB_PATH
        _tickets_repo = TicketsRepository(target)
    return _tickets_repo


def reset_tickets_repository() -> None:
    """Reset tickets repository singleton."""
    global _tickets_repo
    if _tickets_repo is not None:
        engine = getattr(_tickets_repo, "engine", None)
        if engine is not None:
            engine.dispose()
    _tickets_repo = None
