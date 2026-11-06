"""Persistent SQLite repository for human escalation tickets."""
import logging
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("multiagent.tickets_db")

DEFAULT_DB_PATH = os.path.join(os.getcwd(), "data", "tickets.db")


class TicketsRepository:
    """Manages SQLite storage and retrieval for customer escalation tickets."""

    def __init__(self, db_path: str | None = None):
        target_path = db_path or os.environ.get("TICKETS_DB_PATH", DEFAULT_DB_PATH)
        self.db_path = target_path
        db_dir = os.path.dirname(os.path.abspath(self.db_path))

        # Ensure directory exists and attempt to ensure write permissions
        try:
            os.makedirs(db_dir, exist_ok=True)
            try:
                os.chmod(db_dir, 0o777)
                if os.path.exists(self.db_path):
                    os.chmod(self.db_path, 0o666)
            except OSError as chmod_err:
                logger.debug(f"Could not chmod tickets db directory or file: {chmod_err}")
        except OSError as e:
            logger.warning(f"Could not prepare tickets db directory '{db_dir}': {e}")

        # Check writability; if directory or file is read-only, fallback to /tmp
        if not self._is_writable(self.db_path, db_dir):
            fallback_dir = "/tmp" if os.name != "nt" else os.environ.get("TEMP", os.getcwd())
            self.db_path = os.path.join(fallback_dir, "tickets.db")
            logger.warning(
                f"Configured database path '{target_path}' is not writable. Redirecting to writable fallback '{self.db_path}'."
            )

        self._init_db()

    @staticmethod
    def _is_writable(file_path: str, dir_path: str) -> bool:
        """Check if SQLite database and parent directory have write permissions."""
        try:
            if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
                return False
            if os.path.exists(dir_path) and not os.access(dir_path, os.W_OK):
                return False
            # Verify SQLite can open without readonly lock
            test_conn = sqlite3.connect(file_path, timeout=1.0)
            test_conn.execute("PRAGMA schema_version;")
            test_conn.close()
            return True
        except (sqlite3.Error, OSError):
            return False

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
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize tickets database at {self.db_path}: {e}")

    def create_ticket(
        self,
        user_id: str,
        reason: str,
        priority: str = "standard"
    ) -> dict[str, Any]:
        """Create and persist a new customer support escalation ticket."""
        now = datetime.now(UTC).isoformat()
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:4].upper()
        ticket_id = f"GET-TKT-{date_str}-{suffix}"

        clean_reason = reason.strip() if reason else "Solicitação de atendimento humano."

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tickets (ticket_id, user_id, reason, status, priority, channel, created_at, updated_at)
                    VALUES (?, ?, ?, 'open', ?, 'ai_chat', ?, ?)
                """, (ticket_id, user_id, clean_reason, priority, now, now))
                conn.commit()
        except sqlite3.OperationalError as e:
            if "readonly" in str(e).lower() and not self.db_path.startswith("/tmp"):
                fallback_dir = "/tmp" if os.name != "nt" else os.environ.get("TEMP", os.getcwd())
                fallback_path = os.path.join(fallback_dir, "tickets.db")
                logger.warning(
                    f"Database at {self.db_path} threw readonly OperationalError ({e}). Falling back to {fallback_path}."
                )
                self.db_path = fallback_path
                self._init_db()
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO tickets (ticket_id, user_id, reason, status, priority, channel, created_at, updated_at)
                        VALUES (?, ?, ?, 'open', ?, 'ai_chat', ?, ?)
                    """, (ticket_id, user_id, clean_reason, priority, now, now))
                    conn.commit()
            else:
                raise

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

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
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

        if self.db_path != DEFAULT_DB_PATH and os.path.exists(DEFAULT_DB_PATH):
            try:
                with sqlite3.connect(DEFAULT_DB_PATH, timeout=5.0) as alt_conn:
                    alt_conn.row_factory = sqlite3.Row
                    cur = alt_conn.cursor()
                    cur.execute("""
                        SELECT id, ticket_id, user_id, reason, status, priority, channel, created_at, updated_at
                        FROM tickets WHERE ticket_id = ?
                    """, (ticket_id,))
                    alt_row = cur.fetchone()
                    if alt_row:
                        return dict(alt_row)
            except sqlite3.Error as alt_err:
                logger.debug(f"Fallback ticket lookup failed for {DEFAULT_DB_PATH}: {alt_err}")

        return None

    def list_tickets(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
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


_tickets_repo: TicketsRepository | None = None


def get_tickets_repository() -> TicketsRepository:
    """Dependency getter for tickets repository singleton."""
    global _tickets_repo
    if _tickets_repo is None:
        _tickets_repo = TicketsRepository()
    return _tickets_repo
