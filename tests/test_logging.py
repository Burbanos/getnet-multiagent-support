"""Unit tests for request-scoped structured logging, context binding, and PII hygiene."""
import io
import json
import logging
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from src.config import JsonFormatter, settings
from src.core import log_context as lc
from src.core.graph import OrchestrationGraph
from tests.fakes import ScriptedChatModel


def test_user_hash_stability_and_salting():
    """user_hash must be deterministic, change with LOG_HASH_SALT, and hide raw user_id."""
    raw_user = "lojista_prod_12345"
    h1 = lc.user_hash(raw_user)
    assert h1 == lc.user_hash(raw_user), "user_hash must be deterministic"
    assert raw_user not in h1, "user_hash must not contain raw user_id"
    assert h1.startswith("u_"), "user_hash must start with 'u_'"
    assert len(h1) >= 12, "user_hash length must be >= 12"

    h_diff = lc.user_hash("other_user")
    assert h1 != h_diff, "Different users must produce different hashes"

    old_salt = settings.LOG_HASH_SALT
    try:
        settings.LOG_HASH_SALT = "custom_secret_salt_xyz"
        h_salted = lc.user_hash(raw_user)
        assert h_salted != h1, "Salting must alter the computed hash"
        assert raw_user not in h_salted
    finally:
        settings.LOG_HASH_SALT = old_salt


def test_bind_sets_and_resets_context():
    """bind() context manager must populate ContextVars and cleanly restore them on exit."""
    assert lc.current() == {}, "Context must be empty outside bind()"

    trace = "trc-abc123456789"
    session = "sess-alpha-99"
    user = "merchant_test_user"
    expected_hash = lc.user_hash(user)

    with lc.bind(trace, session, user):
        ctx = lc.current()
        assert ctx.get("trace_id") == trace
        assert ctx.get("session_id") == session
        assert ctx.get("user_hash") == expected_hash
        assert user not in json.dumps(ctx), "Raw user_id must not leak into context dictionary"

    assert lc.current() == {}, "Context must be cleared after with-block exit"


class StepFakeChatModel(ScriptedChatModel):
    """Custom fake model capable of yielding sequential canned responses."""

    responses: list[Any] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])


def test_run_sync_logs_context_without_pii_or_raw_user():
    """run_sync must attach trace_id, session_id, and user_hash to logs without leaking PII or raw user_id."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    app_logger = logging.getLogger("multiagent")
    app_logger.addHandler(handler)
    old_level = app_logger.level
    app_logger.setLevel(logging.INFO)

    secret_user = "user-CONFIDENTIAL-999"
    card_number = "4111 1111 1111 1111"
    cpf_number = "123.456.789-09"
    msg = f"Meu cartão é {card_number} e meu CPF é {cpf_number}, preciso de ajuda"

    try:
        fake_model = StepFakeChatModel(responses=[AIMessage(content="Resposta assistente")])
        graph = OrchestrationGraph(chat_model=fake_model)
        graph.run_sync(
            user_id=secret_user,
            message=msg,
            session_id="sess-logging-test",
            trace_id="trc-logtest1234",
        )
    finally:
        app_logger.removeHandler(handler)
        app_logger.setLevel(old_level)

    raw_output = buf.getvalue()
    assert secret_user not in raw_output, "Raw user_id leaked into log records"
    assert "4111" not in raw_output, "Credit card leaked into log records"
    assert "123.456.789-09" not in raw_output, "CPF leaked into log records"

    lines = [ln.strip() for ln in raw_output.splitlines() if ln.strip()]
    assert len(lines) >= 3, "Expected multiple structured log lines"

    records = [json.loads(ln) for ln in lines]
    for r in records:
        assert r.get("trace_id") == "trc-logtest1234", f"Missing trace_id in record: {r}"
        assert r.get("session_id") == "sess-logging-test", f"Missing session_id in record: {r}"
        assert r.get("user_hash") == lc.user_hash(secret_user), f"Missing user_hash in record: {r}"
        assert "user_id" not in r, f"Raw user_id field found in record: {r}"


def test_node_and_tool_finished_events_with_latency():
    """Workflow execution must emit 'node finished' and 'tool finished' events with latency_ms."""
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JsonFormatter())
    app_logger = logging.getLogger("multiagent")
    app_logger.addHandler(handler)
    old_level = app_logger.level
    app_logger.setLevel(logging.INFO)

    def tool_call(name: str, args: dict, cid: str) -> AIMessage:
        return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])

    try:
        fake_model = StepFakeChatModel(
            responses=[
                tool_call("ask_support_agent", {"request": "saldo de ontem"}, "tc-1"),
                tool_call("get_settlement_status", {}, "tc-2"),
                AIMessage(content="Saldo apurado com sucesso."),
                AIMessage(content="Seu saldo de ontem foi R$ 3.367,20."),
            ]
        )
        graph = OrchestrationGraph(chat_model=fake_model)
        graph.run_sync(
            user_id="user_node_events_test",
            message="Qual meu saldo de ontem?",
            session_id="sess-events",
            trace_id="trc-events12345",
        )
    finally:
        app_logger.removeHandler(handler)
        app_logger.setLevel(old_level)

    lines = [ln.strip() for ln in buf.getvalue().splitlines() if ln.strip()]
    records = [json.loads(ln) for ln in lines]

    node_events = [r for r in records if r.get("message") == "node finished"]
    assert len(node_events) >= 3, f"Expected node finished events, got {len(node_events)}"
    nodes_logged = {r.get("node") for r in node_events}
    assert {"guardrail", "supervisor", "tools"} <= nodes_logged
    for ne in node_events:
        assert isinstance(ne.get("latency_ms"), (int, float)), f"Invalid latency_ms in node event: {ne}"

    tool_events = [r for r in records if r.get("message") == "tool finished"]
    assert len(tool_events) >= 2, f"Expected tool finished events, got {len(tool_events)}"
    tools_logged = {r.get("tool") for r in tool_events}
    assert {"ask_support_agent", "get_settlement_status"} <= tools_logged
    for te in tool_events:
        assert te.get("status") in ("ok", "error"), f"Invalid status in tool event: {te}"
        assert isinstance(te.get("latency_ms"), (int, float)), f"Invalid latency_ms in tool event: {te}"
