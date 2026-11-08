"""Tests for pricing calculations and /chat error logs context."""
import io
import json
import logging

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from src.config import JsonFormatter
from src.core import log_context as lc
from src.core.graph import OrchestrationGraph
from src.core.pricing import cost_usd
from src.main import app
from tests.fakes import ScriptedChatModel


def test_cost_usd_supported_models():
    """Verify cost calculation for supported models with and without 'models/' prefix."""
    # gemini-3.5-flash-lite: $0.30 in / $2.50 out per 1M
    c1 = cost_usd("gemini-3.5-flash-lite", 1_000_000, 1_000_000)
    assert c1 == 2.80

    # with models/ prefix
    c2 = cost_usd("models/gemini-3.5-flash-lite", 2000, 500)
    assert c2 == round(2000 / 1e6 * 0.30 + 500 / 1e6 * 2.50, 8)
    assert c2 == 0.00185

    # gemini-3.1-flash-lite: $0.25 in / $1.50 out per 1M
    c3 = cost_usd("gemini-3.1-flash-lite", 1_000_000, 1_000_000)
    assert c3 == 1.75

    # gemini-embedding-2: $0.20 in / $0.0 out per 1M
    c4 = cost_usd("gemini-embedding-2", 1_000_000, 0)
    assert c4 == 0.20


def test_cost_usd_unlisted_models_and_none_tokens():
    """Verify that unlisted models and missing token counts evaluate to None."""
    assert cost_usd("gemini-3.5-flash", 1000, 1000) is None
    assert cost_usd("unknown-model", 1000, 1000) is None
    assert cost_usd(None, 1000, 1000) is None
    assert cost_usd("gemini-3.5-flash-lite", None, 1000) is None
    assert cost_usd("gemini-3.5-flash-lite", 1000, None) is None
    assert cost_usd("gemini-3.5-flash-lite", None, None) is None


class NamedModel(ScriptedChatModel):
    model: str = "custom"


def test_turn_cost_priced_vs_unpriced_model():
    """A turn with a priced model computes estimated_cost_usd; an unpriced model leaves it None."""
    usage = {"input_tokens": 4000, "output_tokens": 1000, "total_tokens": 5000}

    # Priced model
    fake_priced = NamedModel(model="gemini-3.5-flash-lite", responses=[AIMessage(content="ok", usage_metadata=usage)])
    res_priced = OrchestrationGraph(chat_model=fake_priced).run_sync(
        user_id="cliente1988", message="oi", session_id="test-cost-1"
    )
    expected_cost = round(4000 / 1e6 * 0.30 + 1000 / 1e6 * 2.50, 8)
    assert res_priced.estimated_cost_usd is not None
    assert abs(res_priced.estimated_cost_usd - expected_cost) < 1e-9

    # Unpriced model
    fake_unpriced = NamedModel(model="gemini-3.5-flash", responses=[AIMessage(content="ok", usage_metadata=usage)])
    res_unpriced = OrchestrationGraph(chat_model=fake_unpriced).run_sync(
        user_id="cliente1988", message="oi", session_id="test-cost-2"
    )
    assert res_unpriced.estimated_cost_usd is None
    assert res_unpriced.tokens == {"input_tokens": 4000, "output_tokens": 1000, "total_tokens": 5000}


def test_chat_error_logs_carry_request_context(monkeypatch):
    """When /chat fails (e.g. 503 no key), error logs carry trace_id, session_id and user_hash."""
    monkeypatch.setenv("GEMINI_API_KEY", "")

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    app_logger = logging.getLogger("multiagent")
    app_logger.addHandler(handler)
    old_level = app_logger.level
    app_logger.setLevel(logging.INFO)

    try:
        with TestClient(app) as client:
            resp = client.post(
                "/chat",
                json={"message": "ola", "session_id": "p4-sess-error"},
                headers={"X-API-Key": "getnet-dev-key"},
            )
        assert resp.status_code == 503
        trace_header = resp.headers.get("X-Trace-Id")
        assert trace_header is not None

        raw_logs = buf.getvalue()
        assert "cliente1988" not in raw_logs, "Raw user_id should not appear in log records"

        records = [json.loads(ln) for ln in raw_logs.splitlines() if ln.strip().startswith("{")]
        error_records = [r for r in records if r.get("level") == "ERROR"]
        assert len(error_records) >= 1

        for err in error_records:
            assert err.get("trace_id") == trace_header
            assert err.get("session_id") == "p4-sess-error"
            assert err.get("user_hash") == lc.user_hash("cliente1988")
    finally:
        app_logger.removeHandler(handler)
        app_logger.setLevel(old_level)
