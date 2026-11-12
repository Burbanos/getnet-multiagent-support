"""Outgoing webhook notifier for human escalation tickets (never includes transcript or user_id)."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from src.config import settings
from src.core import metrics

logger = logging.getLogger("multiagent.notifier")


@dataclass(frozen=True)
class NotificationResult:
    """Result of an operator webhook notification attempt."""

    status: str
    error_type: str | None
    http_status: int | None


def build_payload(ticket: Mapping[str, Any]) -> dict[str, Any]:
    """Build webhook JSON payload without reason, transcript, or user_id."""
    ticket_id = str(ticket.get("ticket_id") or "")
    priority = str(ticket.get("priority") or "")
    created_at = str(ticket.get("created_at") or "")
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    url = f"{base}/tickets/{ticket_id}"
    return {
        "text": f"Novo chamado {ticket_id} (prioridade {priority}) aguardando o atendimento humano: {url}",
        "ticket_id": ticket_id,
        "priority": priority,
        "created_at": created_at,
        "url": url,
    }


class OperatorNotifier:
    """Sends best-effort webhook notifications when a human escalation ticket is created."""

    def __init__(
        self,
        url: str | None = None,
        timeout_s: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.url = settings.OPERATOR_WEBHOOK_URL if url is None else url
        self.timeout_s = (
            settings.OPERATOR_WEBHOOK_TIMEOUT_S if timeout_s is None else float(timeout_s)
        )
        self._client = client

    def notify(self, ticket: Mapping[str, Any]) -> NotificationResult:
        """Notify the configured operator webhook about a ticket. Never raises."""
        if not self.url or not self.url.strip():
            metrics.inc_notification("disabled")
            logger.info("operator notification", extra={"status": "disabled"})
            return NotificationResult(status="disabled", error_type=None, http_status=None)

        payload = build_payload(ticket)
        try:
            if self._client is not None:
                response = self._client.post(self.url, json=payload, timeout=self.timeout_s)
            else:
                with httpx.Client(timeout=self.timeout_s) as client:
                    response = client.post(self.url, json=payload)

            if 200 <= response.status_code < 300:
                result = NotificationResult(
                    status="sent",
                    error_type=None,
                    http_status=response.status_code,
                )
            else:
                result = NotificationResult(
                    status="failed",
                    error_type=f"http_{response.status_code}",
                    http_status=response.status_code,
                )
        except Exception as exc:  # noqa: BLE001 - best-effort webhook notification must never raise
            result = NotificationResult(
                status="failed",
                error_type=type(exc).__name__,
                http_status=None,
            )

        metrics.inc_notification(result.status)
        logger.info("operator notification", extra={"status": result.status})
        return result


_notifier_instance: OperatorNotifier | None = None


def get_notifier() -> OperatorNotifier:
    """Return cached singleton OperatorNotifier initialized from current settings."""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = OperatorNotifier()
    return _notifier_instance


def reset_notifier() -> None:
    """Clear cached singleton OperatorNotifier (for tests/configuration reload)."""
    global _notifier_instance
    _notifier_instance = None
