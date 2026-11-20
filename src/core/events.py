"""In-memory and Redis pub/sub event brokers for real-time merchant SSE notifications."""
from __future__ import annotations

import hashlib
import json
import logging
import queue
import threading
import time
from contextlib import suppress
from typing import Any, Protocol

import redis

from src.config import settings

logger = logging.getLogger("multiagent.events")


def event_channel(user_id: str, session_id: str) -> str:
    """Return the deterministic Redis/in-memory channel name without exposing raw user_id."""
    digest = hashlib.sha256(f"{user_id}:{session_id}".encode()).hexdigest()[:32]
    return f"getnet:events:{digest}"


class EventSubscription(Protocol):
    """Protocol for an active per-session event subscription."""

    def get(self, timeout: float = 1.0) -> dict[str, Any] | None: ...

    def close(self) -> None: ...


class EventBroker(Protocol):
    """Protocol for session-scoped merchant event publish/subscribe brokers."""

    def publish(self, user_id: str, session_id: str, event: dict[str, Any]) -> bool: ...

    def subscribe(self, user_id: str, session_id: str) -> EventSubscription: ...


class _InMemorySubscription:
    def __init__(self, broker: InMemoryEventBroker, channel: str, q: queue.Queue[dict[str, Any]]) -> None:
        self._broker = broker
        self._channel = channel
        self._q = q
        self._closed = False

    def get(self, timeout: float = 1.0) -> dict[str, Any] | None:
        if self._closed:
            return None
        try:
            return self._q.get(timeout=max(0.0, float(timeout)))
        except queue.Empty:
            return None

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._broker._remove(self._channel, self._q)


class InMemoryEventBroker:
    """Thread-safe in-process pub/sub broker used outside Redis deployments."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._channels: dict[str, set[queue.Queue[dict[str, Any]]]] = {}

    def subscribe(self, user_id: str, session_id: str) -> _InMemorySubscription:
        channel = event_channel(user_id, session_id)
        q: queue.Queue[dict[str, Any]] = queue.Queue()
        with self._lock:
            self._channels.setdefault(channel, set()).add(q)
        return _InMemorySubscription(self, channel, q)

    def _remove(self, channel: str, q: queue.Queue[dict[str, Any]]) -> None:
        with self._lock:
            subs = self._channels.get(channel)
            if subs is not None:
                subs.discard(q)
                if not subs:
                    del self._channels[channel]

    def publish(self, user_id: str, session_id: str, event: dict[str, Any]) -> bool:
        channel = event_channel(user_id, session_id)
        with self._lock:
            targets = list(self._channels.get(channel, ()))
        for q in targets:
            q.put(dict(event))
        return True


class _RedisSubscription:
    def __init__(self, pubsub: Any, channel: str) -> None:
        self._pubsub = pubsub
        self._channel = channel
        self._closed = False

    def get(self, timeout: float = 1.0) -> dict[str, Any] | None:
        if self._closed:
            return None
        deadline = time.monotonic() + max(0.0, float(timeout))
        while not self._closed:
            rem = deadline - time.monotonic()
            if rem <= 0.0:
                msg = self._pubsub.get_message(ignore_subscribe_messages=True, timeout=0.0)
                parsed = self._decode_message(msg)
                if parsed is not None:
                    return parsed
                return None
            t0 = time.monotonic()
            try:
                msg = self._pubsub.get_message(ignore_subscribe_messages=True, timeout=min(rem, 1.0))
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Redis pub/sub read failed: {type(exc).__name__}")
                return None
            parsed = self._decode_message(msg)
            if parsed is not None:
                return parsed
            elapsed = time.monotonic() - t0
            if msg is None and elapsed < 0.01:
                time.sleep(min(0.02, max(0.0, deadline - time.monotonic())))
        return None

    @staticmethod
    def _decode_message(msg: Any) -> dict[str, Any] | None:
        if not isinstance(msg, dict) or msg.get("type") != "message":
            return None
        raw = msg.get("data")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        if not isinstance(raw, str):
            return None
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return loaded if isinstance(loaded, dict) else None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        with suppress(Exception):
            self._pubsub.unsubscribe(self._channel)
        with suppress(Exception):
            self._pubsub.close()


class RedisEventBroker:
    """Cross-replica Redis pub/sub event broker for merchant SSE notifications."""

    def __init__(self, client: Any) -> None:
        self.client = client

    def subscribe(self, user_id: str, session_id: str) -> _RedisSubscription:
        channel = event_channel(user_id, session_id)
        pubsub = self.client.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(channel)
        return _RedisSubscription(pubsub, channel)

    def publish(self, user_id: str, session_id: str, event: dict[str, Any]) -> bool:
        channel = event_channel(user_id, session_id)
        payload = json.dumps(dict(event), ensure_ascii=False)
        try:
            self.client.publish(channel, payload)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Redis event publish failed: {type(exc).__name__}")
            return False


_broker_lock = threading.Lock()
_event_broker: EventBroker | None = None


def get_event_broker() -> EventBroker:
    """Return singleton EventBroker (Redis when REDIS_URL is set, else in-memory)."""
    global _event_broker
    with _broker_lock:
        if _event_broker is None:
            redis_url = settings.REDIS_URL.strip()
            if redis_url:
                client = redis.Redis.from_url(redis_url, socket_connect_timeout=1.0)
                _event_broker = RedisEventBroker(client)
            else:
                _event_broker = InMemoryEventBroker()
        return _event_broker


def reset_event_broker() -> None:
    """Reset the global EventBroker singleton."""
    global _event_broker
    with _broker_lock:
        _event_broker = None
