"""In-process and shared Redis sliding-window rate limiters."""
from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from typing import Any

import redis.exceptions

from src.config import settings
from src.core import metrics

logger = logging.getLogger("multiagent.rate_limit")


class RateLimiter:
    """Sliding-window rate limiter per key_id in local memory."""

    def __init__(
        self,
        limit_per_minute: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit_per_minute = limit_per_minute
        self.clock = clock
        self._hits: dict[str, list[float]] = {}

    def hit(self, key_id: str) -> float | None:
        """
        Record a request hit for key_id.
        Returns None if permitted, or remaining seconds until permitted if limit exceeded.
        limit_per_minute <= 0 disables the limiter.
        """
        if self.limit_per_minute <= 0:
            return None

        now = self.clock()
        window_start = now - 60.0

        timestamps = [t for t in self._hits.get(key_id, []) if t > window_start]
        if len(timestamps) >= self.limit_per_minute:
            self._hits[key_id] = timestamps
            oldest = timestamps[0]
            wait = 60.0 - (now - oldest)
            return max(wait, 0.0)

        timestamps.append(now)
        self._hits[key_id] = timestamps
        return None


class RedisRateLimiter:
    """Distributed sliding-window rate limiter backed by a Redis sorted set with local fallback."""

    def __init__(
        self,
        client: Any,
        limit_per_minute: int,
        *,
        prefix: str = "getnet:rl:",
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.client = client
        self.limit_per_minute = limit_per_minute
        self.prefix = prefix
        self.clock = clock
        self.degraded = False
        self._degraded_until = 0.0
        self._fallback = RateLimiter(limit_per_minute=limit_per_minute, clock=clock)

    @property
    def backend(self) -> str:
        """Return active backend label ('redis' or 'redis_degraded')."""
        return "redis_degraded" if self.degraded else "redis"

    def hit(self, key_id: str) -> float | None:
        """Record a hit in Redis sorted set window; degrade cleanly to local memory on Redis errors."""
        if self.limit_per_minute <= 0:
            return None

        now = float(self.clock())
        if self.degraded and now < self._degraded_until:
            return self._fallback.hit(key_id)

        zkey = f"{self.prefix}{key_id}"
        now_ms = int(now * 1000)
        window_start_ms = now_ms - 60_000
        member = f"{now_ms}:{uuid.uuid4().hex}"

        try:
            pipe = self.client.pipeline(transaction=True)
            pipe.zremrangebyscore(zkey, "-inf", window_start_ms)
            pipe.zadd(zkey, {member: now_ms})
            pipe.zcard(zkey)
            pipe.zrange(zkey, 0, 0, withscores=True)
            pipe.pexpire(zkey, 61_000)
            results = pipe.execute()

            self.degraded = False
            self._degraded_until = 0.0

            count = int(results[2])
            if count > self.limit_per_minute:
                self.client.zrem(zkey, member)
                oldest_entries = results[3] or []
                oldest_ms = float(oldest_entries[0][1]) if oldest_entries else float(now_ms)
                wait_s = (60_000.0 - (now_ms - oldest_ms)) / 1000.0
                return min(60.0, max(0.001, wait_s))
            return None
        except (redis.exceptions.RedisError, OSError):
            self.degraded = True
            self._degraded_until = now + 5.0
            metrics.inc_rate_limit_error()
            logger.warning("Redis rate limiter unavailable; degrading to local memory limiter for 5s")
            return self._fallback.hit(key_id)


def rate_limit_backend() -> str:
    """Return active rate limit backend identifier for /health telemetry."""
    if not settings.REDIS_URL.strip():
        return "memory"
    from src.core.auth import get_rate_limiter

    limiter = get_rate_limiter()
    return getattr(limiter, "backend", "redis")
