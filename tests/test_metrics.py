"""Unit and integration tests for Prometheus in-memory metrics (Phase 7C)."""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

import src.core.tickets_db as tdb
from src.core import metrics
from src.core.graph import OrchestrationGraph
from src.main import app
from tests.fakes import ScriptedChatModel


def _sample(text: str, name: str, labels: str = "") -> float | None:
    key = f"{name}{{{labels}}}" if labels else name
    for ln in text.splitlines():
        if ln.startswith(key + " "):
            return float(ln.split()[-1])
    return None


def test_render_format_and_cumulative_histogram() -> None:
    """render() must emit valid Prometheus 0.0.4 format with cumulative buckets, sum and count."""
    metrics.reset()
    initial = metrics.render()
    for name in (
        "getnet_requests_total",
        "getnet_request_latency_seconds",
        "getnet_tool_calls_total",
        "getnet_escalations_total",
        "getnet_abstentions_total",
        "getnet_llm_tokens_total",
    ):
        assert f"# HELP {name} " in initial
        assert f"# TYPE {name} " in initial

    assert 'getnet_request_latency_seconds_bucket{le="+Inf"} 0' in initial
    assert _sample(initial, "getnet_request_latency_seconds_count") == 0
    assert _sample(initial, "getnet_escalations_total") == 0
    assert _sample(initial, "getnet_abstentions_total") == 0

    metrics.inc_request(200, 0.4)
    metrics.inc_request(200, 1.2)
    metrics.inc_request(500, 6.5)

    rendered = metrics.render()
    assert _sample(rendered, "getnet_requests_total", 'status="200"') == 2
    assert _sample(rendered, "getnet_requests_total", 'status="500"') == 1
    assert _sample(rendered, "getnet_request_latency_seconds_bucket", 'le="0.5"') == 1
    assert _sample(rendered, "getnet_request_latency_seconds_bucket", 'le="1.0"') == 1
    assert _sample(rendered, "getnet_request_latency_seconds_bucket", 'le="2.0"') == 2
    assert _sample(rendered, "getnet_request_latency_seconds_bucket", 'le="5.0"') == 2
    assert _sample(rendered, "getnet_request_latency_seconds_bucket", 'le="10.0"') == 3
    assert _sample(rendered, "getnet_request_latency_seconds_bucket", 'le="+Inf"') == 3
    assert _sample(rendered, "getnet_request_latency_seconds_count") == 3
    assert abs((_sample(rendered, "getnet_request_latency_seconds_sum") or 0) - 8.1) < 1e-9


def test_unknown_tool_normalization_and_statuses() -> None:
    """Unrecognized tool names must be recorded under tool='unknown'."""
    metrics.reset()
    metrics.inc_tool("search_web", "ok")
    metrics.inc_tool("invented_tool_from_llm", "ok")
    metrics.inc_tool("diagnose_terminal", "error")

    rendered = metrics.render()
    assert "invented_tool_from_llm" not in rendered
    assert _sample(rendered, "getnet_tool_calls_total", 'tool="search_web",status="ok"') == 1
    assert _sample(rendered, "getnet_tool_calls_total", 'tool="unknown",status="ok"') == 1
    assert _sample(rendered, "getnet_tool_calls_total", 'tool="diagnose_terminal",status="error"') == 1


class _StepChatModel(ScriptedChatModel):
    responses: list[Any] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])


def test_turn_increments_tools_escalation_and_tokens() -> None:
    """OrchestrationGraph execution must increment tool counters, escalation and token counts."""
    metrics.reset()
    tdb.reset_tickets_repository()

    def call_msg(name: str, args: dict, cid: str) -> AIMessage:
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])

    usage = {"input_tokens": 150, "output_tokens": 45, "total_tokens": 195}
    fake = _StepChatModel(
        responses=[
            call_msg("escalate_to_human", {"reason": "test escalation", "priority": "standard"}, "call_1"),
            AIMessage(content="Final response", usage_metadata=usage),
        ]
    )

    try:
        graph = OrchestrationGraph(chat_model=fake)
        graph.run_sync(user_id="cliente1988", message="preciso de humano", session_id="test_m_sess")

        rendered = metrics.render()
        assert _sample(rendered, "getnet_tool_calls_total", 'tool="escalate_to_human",status="ok"') == 1
        assert _sample(rendered, "getnet_escalations_total") == 1
        assert (_sample(rendered, "getnet_llm_tokens_total", 'direction="input"') or 0) >= 150
        assert (_sample(rendered, "getnet_llm_tokens_total", 'direction="output"') or 0) >= 45
    finally:
        tdb.reset_tickets_repository()


def test_metrics_endpoint_and_chat_status_recording() -> None:
    """GET /metrics must serve Prometheus text 0.0.4 without auth, recording /chat statuses."""
    metrics.reset()

    with TestClient(app) as client:
        # /health is not /chat or /api/v1/chat -> must NOT be counted
        r_health = client.get("/health")
        assert r_health.status_code == 200

        # /chat without API key -> 401
        r_401 = client.post("/chat", json={"message": "oi"})
        assert r_401.status_code == 401

        # /chat with API key but no LLM key configured -> 503
        r_503 = client.post(
            "/chat",
            json={"message": "oi", "session_id": "test-sess"},
            headers={"X-API-Key": "getnet-dev-key"},
        )
        assert r_503.status_code == 503

        # GET /metrics
        r_metrics = client.get("/metrics")
        assert r_metrics.status_code == 200
        content_type = r_metrics.headers.get("content-type", "")
        assert content_type.startswith("text/plain")
        assert "version=0.0.4" in content_type

        txt = r_metrics.text
        assert _sample(txt, "getnet_requests_total", 'status="401"') == 1
        assert _sample(txt, "getnet_requests_total", 'status="503"') == 1
        assert _sample(txt, "getnet_requests_total", 'status="200"') is None
        assert _sample(txt, "getnet_request_latency_seconds_count") == 2
        assert "cliente1988" not in txt
