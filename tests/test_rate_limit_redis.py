"""Offline tests for the Redis shared sliding-window rate limiter using fakeredis."""
from __future__ import annotations

import logging
import re

import fakeredis
import pytest
import redis.exceptions
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import src.core.graph as graph_mod
from src.config import settings
from src.core import auth, metrics
from src.core import rate_limit as rl
from src.core.graph import OrchestrationGraph
from tests.fakes import ScriptedChatModel


def _rate_limit_error_count() -> int:
    m = re.search(r"^getnet_rate_limit_backend_errors_total (\d+)$", metrics.render(), re.MULTILINE)
    return int(m.group(1)) if m else 0


def test_redis_rate_limiter_shared_window_across_replicas() -> None:
    server = fakeredis.FakeServer()
    clock = [1_000_000.0]
    lim_a = rl.RedisRateLimiter(fakeredis.FakeRedis(server=server), 3, clock=lambda: clock[0])
    lim_b = rl.RedisRateLimiter(fakeredis.FakeRedis(server=server), 3, clock=lambda: clock[0])

    assert [lim_a.hit("k1"), lim_b.hit("k1"), lim_a.hit("k1")] == [None, None, None]
    wait = lim_b.hit("k1")
    assert wait is not None and 0 < wait <= 60.0
    assert lim_a.backend == "redis"


def test_redis_rate_limiter_rejected_hit_does_not_consume_quota() -> None:
    server = fakeredis.FakeServer()
    clock = [2_000_000.0]
    client = fakeredis.FakeRedis(server=server)
    lim = rl.RedisRateLimiter(client, 2, prefix="test:rl:", clock=lambda: clock[0])

    assert lim.hit("k1") is None
    clock[0] += 30.0
    assert lim.hit("k1") is None
    assert lim.hit("k1") is not None
    assert client.zcard("test:rl:k1") == 2

    clock[0] += 31.0
    assert lim.hit("k1") is None


def test_redis_rate_limiter_keys_are_independent() -> None:
    server = fakeredis.FakeServer()
    clock = [3_000_000.0]
    lim = rl.RedisRateLimiter(fakeredis.FakeRedis(server=server), 1, clock=lambda: clock[0])

    assert lim.hit("key-a") is None
    assert lim.hit("key-a") is not None
    assert lim.hit("key-b") is None


def test_redis_rate_limiter_window_resets_after_61_seconds() -> None:
    server = fakeredis.FakeServer()
    clock = [4_000_000.0]
    lim = rl.RedisRateLimiter(fakeredis.FakeRedis(server=server), 2, clock=lambda: clock[0])

    assert lim.hit("k1") is None
    assert lim.hit("k1") is None
    assert lim.hit("k1") is not None

    clock[0] += 61.0
    assert lim.hit("k1") is None


def test_redis_rate_limiter_degrades_on_error_records_metric_and_recovers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = {"count": 0, "fail": True}
    real_server = fakeredis.FakeServer()
    real_client = fakeredis.FakeRedis(server=real_server)
    clock = [5_000_000.0]

    class FlakyPipe:
        def __init__(self) -> None:
            self._inner = real_client.pipeline(transaction=True)

        def __getattr__(self, name: str):
            return getattr(self._inner, name)

        def execute(self):
            if calls["fail"]:
                raise redis.exceptions.ConnectionError("secret-redis-host-detail")
            return self._inner.execute()

    class FlakyRedis:
        def pipeline(self, *args, **kwargs):
            calls["count"] += 1
            return FlakyPipe()

        def zrem(self, *args, **kwargs):
            return real_client.zrem(*args, **kwargs)

    metrics.reset()
    before_err = _rate_limit_error_count()
    lim = rl.RedisRateLimiter(FlakyRedis(), 2, clock=lambda: clock[0])

    with caplog.at_level(logging.WARNING, logger="multiagent.rate_limit"):
        assert lim.hit("secret-key-abc") is None
        assert lim.degraded is True
        assert lim.backend == "redis_degraded"
        assert _rate_limit_error_count() == before_err + 1
        assert calls["count"] == 1

        # Within 5 seconds cooldown, Redis must not be retried and local limiter enforces limit
        clock[0] += 1.0
        assert lim.hit("secret-key-abc") is None
        assert lim.hit("secret-key-abc") is not None
        assert calls["count"] == 1

        assert "secret-key-abc" not in caplog.text
        assert "secret-redis-host-detail" not in caplog.text

        # After 5 seconds cooldown, recovery succeeds cleanly
        calls["fail"] = False
        clock[0] += 5.0
        assert lim.hit("secret-key-abc") is None
        assert lim.degraded is False
        assert lim.backend == "redis"
        assert calls["count"] == 2


def test_get_rate_limiter_selection_and_rate_limit_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "REDIS_URL", "")
    auth.reset_rate_limiter()
    assert type(auth.get_rate_limiter()) is rl.RateLimiter
    assert rl.rate_limit_backend() == "memory"

    monkeypatch.setattr(settings, "REDIS_URL", "redis://127.0.0.1:6399/0")
    auth.reset_rate_limiter()
    assert isinstance(auth.get_rate_limiter(), rl.RedisRateLimiter)
    assert rl.rate_limit_backend() == "redis"
    assert auth.RateLimiter is rl.RateLimiter


def test_chat_endpoint_returns_429_with_retry_after_over_fakeredis(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = fakeredis.FakeServer()
    clock = [6_000_000.0]
    lim = rl.RedisRateLimiter(fakeredis.FakeRedis(server=server), 2, clock=lambda: clock[0])
    monkeypatch.setattr(auth, "_rate_limiter_instance", lim)
    monkeypatch.setattr(
        graph_mod,
        "_orchestrator_instance",
        OrchestrationGraph(
            chat_model=ScriptedChatModel(
                responses=[AIMessage(content="ok 1"), AIMessage(content="ok 2")]
            )
        ),
    )

    headers = {"X-API-Key": "getnet-dev-key"}
    assert client.post("/chat", json={"message": "oi 1", "session_id": "s-rl"}, headers=headers).status_code == 200
    assert client.post("/chat", json={"message": "oi 2", "session_id": "s-rl"}, headers=headers).status_code == 200

    limited = client.post("/chat", json={"message": "oi 3", "session_id": "s-rl"}, headers=headers)
    assert limited.status_code == 429
    assert int(limited.headers.get("Retry-After", "0")) >= 1
