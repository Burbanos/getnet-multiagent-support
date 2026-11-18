"""Persistent repository for confirmed write actions (terminal replacements) and audit events."""
from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import and_, insert, select, update
from sqlalchemy.exc import IntegrityError

from src.config import settings
from src.core.db import audit_events, ensure_schema, make_engine, pending_actions, terminal_replacements
from src.core.log_context import user_hash
from src.core.pii import sanitize_pii
from src.core.tracing import current_trace_id

logger = logging.getLogger("multiagent.actions_db")

AUDIT_DETAILS_ALLOWLIST: frozenset[str] = frozenset({
    "serial_number",
    "status",
    "request_id",
    "priority",
    "reason_code",
})


def _sanitize_details(details: Mapping[str, Any] | None) -> str:
    if not details:
        return "{}"
    filtered: dict[str, str | int | float | bool] = {}
    for k, v in details.items():
        if k in AUDIT_DETAILS_ALLOWLIST and v is not None and isinstance(v, (str, int, float, bool)):
            filtered[k] = v
    return json.dumps(filtered, ensure_ascii=False)


def _audit_values(
    actor_type: str,
    actor_id: str,
    action: str,
    target_type: str,
    target_id: str,
    outcome: str,
    details: Mapping[str, Any] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    otel_tid = current_trace_id() or trace_id
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "actor_type": actor_type,
        "actor_hash": user_hash(str(actor_id or actor_type or "system")),
        "action": action,
        "target_type": target_type,
        "target_id": str(target_id),
        "outcome": outcome,
        "details": _sanitize_details(details),
        "otel_trace_id": otel_tid,
    }


class ActionsRepository:
    """Manages pending action proposals, confirmed terminal replacements, and audit events."""

    def __init__(self, target: str | Path) -> None:
        self.db_path = str(target)
        self.engine = make_engine(self.db_path, pool_size=settings.DB_POOL_SIZE)
        ensure_schema(self.engine)
        logger.info("Actions repository initialized")

    def record_audit(
        self,
        actor_type: str,
        actor_id: str,
        action: str,
        target_type: str,
        target_id: str,
        outcome: str,
        details: Mapping[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        """Persist a hashed, allowlisted audit event row."""
        vals = _audit_values(actor_type, actor_id, action, target_type, target_id, outcome, details, trace_id)
        with self.engine.begin() as conn:
            conn.execute(insert(audit_events).values(**vals))

    def get_open_replacement(self, serial_number: str) -> dict[str, Any] | None:
        """Return an open ('requested') replacement record for serial_number, or None."""
        stmt = select(terminal_replacements).where(
            and_(
                terminal_replacements.c.serial_number == serial_number,
                terminal_replacements.c.status == "requested",
            )
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
            return dict(row) if row is not None else None

    def propose_terminal_replacement(
        self,
        user_id: str,
        session_id: str,
        serial_number: str,
        reason: str,
        trace_id: str,
        ttl_minutes: int = 30,
    ) -> dict[str, Any]:
        """Supersede any prior open proposal in the session and create a new pending replacement proposal."""
        now_dt = datetime.now(UTC)
        now = now_dt.isoformat()
        expires_at = (now_dt + timedelta(minutes=ttl_minutes)).isoformat()
        date_str = now_dt.strftime("%Y%m%d")
        action_id = f"ACT-{date_str}-{uuid.uuid4().hex[:10].upper()}"
        safe_reason, _ = sanitize_pii(reason or "")
        clean_reason = safe_reason.strip()[:300] or "troca de maquininha"

        with self.engine.begin() as conn:
            sup_res = conn.execute(
                update(pending_actions)
                .where(
                    and_(
                        pending_actions.c.user_id == user_id,
                        pending_actions.c.session_id == session_id,
                        pending_actions.c.status == "proposed",
                    )
                )
                .values(status="superseded", resolved_at=now)
            )
            if (sup_res.rowcount or 0) > 0:
                conn.execute(
                    insert(audit_events).values(
                        **_audit_values(
                            "system",
                            user_id,
                            "replacement_superseded",
                            "session",
                            session_id,
                            "superseded",
                            {"serial_number": serial_number, "status": "superseded"},
                        )
                    )
                )

            conn.execute(
                insert(pending_actions).values(
                    action_id=action_id,
                    user_id=user_id,
                    session_id=session_id,
                    action_type="terminal_replacement",
                    serial_number=serial_number,
                    reason=clean_reason,
                    status="proposed",
                    proposed_trace_id=trace_id,
                    created_at=now,
                    expires_at=expires_at,
                )
            )
            conn.execute(
                insert(audit_events).values(
                    **_audit_values(
                        "merchant",
                        user_id,
                        "replacement_proposed",
                        "pending_action",
                        action_id,
                        "proposed",
                        {"serial_number": serial_number, "status": "proposed"},
                    )
                )
            )

        return {
            "status": "pending_confirmation",
            "action_id": action_id,
            "serial_number": serial_number,
            "expires_at": expires_at,
        }

    def confirm(self, user_id: str, session_id: str, trace_id: str) -> dict[str, Any]:
        """Confirm and execute the session's latest proposed replacement, enforcing turn & idempotency guards."""
        now_dt = datetime.now(UTC)
        now = now_dt.isoformat()

        with self.engine.begin() as conn:
            row = conn.execute(
                select(pending_actions)
                .where(
                    and_(
                        pending_actions.c.user_id == user_id,
                        pending_actions.c.session_id == session_id,
                        pending_actions.c.status == "proposed",
                    )
                )
                .order_by(pending_actions.c.created_at.desc(), pending_actions.c.action_id.desc())
                .limit(1)
                .with_for_update()
            ).mappings().first()

            if row is None:
                conn.execute(
                    insert(audit_events).values(
                        **_audit_values(
                            "merchant",
                            user_id,
                            "replacement_confirm_rejected",
                            "session",
                            session_id,
                            "no_pending_action",
                        )
                    )
                )
                return {"status": "no_pending_action", "action_id": None, "request_id": None}

            action_id = row["action_id"]
            serial_number = row["serial_number"]
            reason = row["reason"]

            if row["proposed_trace_id"] == trace_id:
                conn.execute(
                    insert(audit_events).values(
                        **_audit_values(
                            "merchant",
                            user_id,
                            "replacement_confirm_rejected",
                            "pending_action",
                            action_id,
                            "same_turn",
                            {"serial_number": serial_number, "status": "proposed"},
                        )
                    )
                )
                return {
                    "status": "same_turn",
                    "action_id": action_id,
                    "serial_number": serial_number,
                    "request_id": None,
                }

            expires_dt = datetime.fromisoformat(row["expires_at"])
            if now_dt >= expires_dt:
                conn.execute(
                    update(pending_actions)
                    .where(pending_actions.c.action_id == action_id)
                    .values(status="expired", resolved_at=now)
                )
                conn.execute(
                    insert(audit_events).values(
                        **_audit_values(
                            "system",
                            user_id,
                            "replacement_expired",
                            "pending_action",
                            action_id,
                            "expired",
                            {"serial_number": serial_number, "status": "expired"},
                        )
                    )
                )
                return {
                    "status": "expired",
                    "action_id": action_id,
                    "serial_number": serial_number,
                    "request_id": None,
                }

            existing_id = conn.execute(
                select(terminal_replacements.c.request_id).where(
                    and_(
                        terminal_replacements.c.serial_number == serial_number,
                        terminal_replacements.c.status == "requested",
                    )
                )
            ).scalar_one_or_none()
            if existing_id is not None:
                conn.execute(
                    update(pending_actions)
                    .where(pending_actions.c.action_id == action_id)
                    .values(status="executed", resolved_at=now, request_id=existing_id)
                )
                conn.execute(
                    insert(audit_events).values(
                        **_audit_values(
                            "merchant",
                            user_id,
                            "replacement_already_requested",
                            "terminal_replacement",
                            existing_id,
                            "already_requested",
                            {"serial_number": serial_number, "request_id": existing_id, "status": "requested"},
                        )
                    )
                )
                return {
                    "status": "already_requested",
                    "action_id": action_id,
                    "serial_number": serial_number,
                    "request_id": existing_id,
                }

            req_id = f"GET-TRC-{now_dt.strftime('%Y%m%d')}-{uuid.uuid4().hex[:10].upper()}"
            try:
                with conn.begin_nested():
                    conn.execute(
                        insert(terminal_replacements).values(
                            request_id=req_id,
                            user_id=user_id,
                            serial_number=serial_number,
                            reason=reason,
                            status="requested",
                            action_id=action_id,
                            created_at=now,
                        )
                    )
            except IntegrityError:
                winner_id = conn.execute(
                    select(terminal_replacements.c.request_id).where(
                        and_(
                            terminal_replacements.c.serial_number == serial_number,
                            terminal_replacements.c.status == "requested",
                        )
                    )
                ).scalar_one_or_none()
                conn.execute(
                    update(pending_actions)
                    .where(pending_actions.c.action_id == action_id)
                    .values(status="executed", resolved_at=now, request_id=winner_id)
                )
                conn.execute(
                    insert(audit_events).values(
                        **_audit_values(
                            "merchant",
                            user_id,
                            "replacement_already_requested",
                            "terminal_replacement",
                            winner_id or action_id,
                            "already_requested",
                            {"serial_number": serial_number, "request_id": winner_id, "status": "requested"},
                        )
                    )
                )
                return {
                    "status": "already_requested",
                    "action_id": action_id,
                    "serial_number": serial_number,
                    "request_id": winner_id,
                }

            conn.execute(
                update(pending_actions)
                .where(pending_actions.c.action_id == action_id)
                .values(status="executed", resolved_at=now, request_id=req_id)
            )
            conn.execute(
                insert(audit_events).values(
                    **_audit_values(
                        "merchant",
                        user_id,
                        "replacement_executed",
                        "terminal_replacement",
                        req_id,
                        "executed",
                        {"serial_number": serial_number, "request_id": req_id, "status": "requested"},
                    )
                )
            )
            return {
                "status": "executed",
                "action_id": action_id,
                "serial_number": serial_number,
                "request_id": req_id,
            }

    def decline(self, user_id: str, session_id: str, trace_id: str | None = None) -> dict[str, Any]:
        """Mark the session's latest proposed action as declined and record an audit event."""
        now = datetime.now(UTC).isoformat()
        with self.engine.begin() as conn:
            row = conn.execute(
                select(pending_actions)
                .where(
                    and_(
                        pending_actions.c.user_id == user_id,
                        pending_actions.c.session_id == session_id,
                        pending_actions.c.status == "proposed",
                    )
                )
                .order_by(pending_actions.c.created_at.desc(), pending_actions.c.action_id.desc())
                .limit(1)
                .with_for_update()
            ).mappings().first()

            if row is None:
                return {"status": "no_pending_action", "action_id": None}

            action_id = row["action_id"]
            serial_number = row["serial_number"]
            conn.execute(
                update(pending_actions)
                .where(pending_actions.c.action_id == action_id)
                .values(status="declined", resolved_at=now)
            )
            conn.execute(
                insert(audit_events).values(
                    **_audit_values(
                        "merchant",
                        user_id,
                        "replacement_declined",
                        "pending_action",
                        action_id,
                        "declined",
                        {"serial_number": serial_number, "status": "declined"},
                        trace_id=trace_id,
                    )
                )
            )
            return {
                "status": "declined",
                "action_id": action_id,
                "serial_number": serial_number,
            }

    def list_replacements(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """List confirmed terminal replacements filtered optionally by user_id."""
        clamped = max(1, min(200, limit))
        stmt = select(terminal_replacements)
        if user_id:
            stmt = stmt.where(terminal_replacements.c.user_id == user_id)
        stmt = stmt.order_by(terminal_replacements.c.created_at.desc()).limit(clamped)
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(stmt).mappings().all()]

    def list_audit(
        self,
        limit: int = 100,
        action: str | None = None,
        target_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List audit events (hashed actor, allowlisted details, never raw user IDs)."""
        clamped = max(1, min(200, limit))
        stmt = select(audit_events)
        conditions = []
        if action:
            conditions.append(audit_events.c.action == action)
        if target_id:
            conditions.append(audit_events.c.target_id == target_id)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(audit_events.c.id.desc()).limit(clamped)
        with self.engine.connect() as conn:
            out: list[dict[str, Any]] = []
            for row in conn.execute(stmt).mappings().all():
                item = dict(row)
                raw_details = item.get("details")
                if isinstance(raw_details, str):
                    try:
                        item["details"] = json.loads(raw_details)
                    except (json.JSONDecodeError, TypeError):
                        item["details"] = {}
                elif raw_details is None:
                    item["details"] = {}
                out.append(item)
            return out


_actions_repo: ActionsRepository | None = None


def get_actions_repository() -> ActionsRepository:
    """Dependency getter for actions repository singleton matching tickets storage target."""
    global _actions_repo
    if _actions_repo is None:
        target = settings.DATABASE_URL.strip() or settings.TICKETS_DB_PATH
        _actions_repo = ActionsRepository(target)
    return _actions_repo


def reset_actions_repository() -> None:
    """Reset actions repository singleton."""
    global _actions_repo
    if _actions_repo is not None:
        engine = getattr(_actions_repo, "engine", None)
        if engine is not None:
            engine.dispose()
    _actions_repo = None
