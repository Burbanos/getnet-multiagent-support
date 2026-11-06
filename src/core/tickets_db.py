"""Persistent SQLite repository for human escalation tickets."""
import os
import sqlite3
import uuid
from datetime import datetime, timezone
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("multiagent.tickets_db")

DEFAULT_DB_PATH = os.path.join(os.getcwd(), "data", "tickets.db")


class TicketsRepository:
    """Manages SQLite storage and retrieval for customer escalation tickets."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("TICKETS_DB_PATH", DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ticket_id TEXT UNIQUE NOT NULL,
                        user_id TEXT NOT NULL,
                        reason TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'open',
                        priority TEXT NOT NULL DEFAULT 'standard',
                        channel TEXT NOT NULL DEFAULT 'ai_chat',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                conn.commit()
                logger.info(f"Tickets database initialized at: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize tickets database: {e}")

    def create_ticket(
        self,
        user_id: str,
        reason: str,
        priority: str = "standard"
    ) -> Dict[str, Any]:
        """Create and persist a new customer support escalation ticket."""
        now = datetime.now(timezone.utc).isoformat()
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:4].upper()
        ticket_id = f"GET-TKT-{date_str}-{suffix}"

        clean_reason = reason.strip() if reason else "Solicitação de atendimento humano."

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tickets (ticket_id, user_id, reason, status, priority, channel, created_at, updated_at)
                VALUES (?, ?, ?, 'open', ?, 'ai_chat', ?, ?)
            """, (ticket_id, user_id, clean_reason, priority, now, now))
            conn.commit()

        logger.info(f"Persisted escalation ticket {ticket_id} for user {user_id}")

        return {
            "status": "success",
            "ticket_id": ticket_id,
            "user_id": user_id,
            "ticket_status": "open",
            "priority": priority,
            "created_at": now,
            "reason": clean_reason,
            "tracking_endpoint": f"/tickets/{ticket_id}",
            "message": (
                f"Chamado registrado com sucesso sob o protocolo **{ticket_id}**. "
                f"O status pode ser consultado a qualquer momento via endpoint `GET /tickets/{ticket_id}`."
            )
        }

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve ticket details by its unique identifier."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, ticket_id, user_id, reason, status, priority, channel, created_at, updated_at
                FROM tickets WHERE ticket_id = ?
            """, (ticket_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def list_tickets(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List persisted tickets, optionally filtered by user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT id, ticket_id, user_id, reason, status, priority, channel, created_at, updated_at
                    FROM tickets WHERE user_id = ? ORDER BY id DESC LIMIT ?
                """, (user_id, limit))
            else:
                cursor.execute("""
                    SELECT id, ticket_id, user_id, reason, status, priority, channel, created_at, updated_at
                    FROM tickets ORDER BY id DESC LIMIT ?
                """, (limit,))
            return [dict(row) for row in cursor.fetchall()]


_tickets_repo: Optional[TicketsRepository] = None


def get_tickets_repository() -> TicketsRepository:
    """Dependency getter for tickets repository singleton."""
    global _tickets_repo
    if _tickets_repo is None:
        _tickets_repo = TicketsRepository()
    return _tickets_repo
