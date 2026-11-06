"""Tests for LLM robustness: timeouts, error classification, step limit, and trace IDs."""
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.exceptions import (
    ModelAuthenticationError,
    ModelInvalidRequestError,
    ModelNotFoundError,
    ModelPermissionDeniedError,
    ModelRateLimitError,
)
from langchain_core.messages import AIMessage, ToolMessage

import src.core.graph as graph_mod
from src.config import settings
from src.core.graph import OrchestrationGraph
from src.core.llm import LLMConfigurationError, get_chat_model
from tests.fakes import ScriptedChatModel


class RaisingChatModel(ScriptedChatModel):
    """Fake model that raises a specific exception upon generation."""

    exc: Any = None

    def __init__(self, exc: Any = None, **kwargs: Any):
        super().__init__(**kwargs)
        object.__setattr__(self, "exc", exc)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise self.exc


def test_get_chat_model_receives_timeout_and_max_retries():
    """Verify get_chat_model passes settings.LLM_TIMEOUT_S and settings.LLM_MAX_RETRIES."""
    saved_key = settings.GEMINI_API_KEY
    try:
        settings.GEMINI_API_KEY = "dummy-key-for-construction-test"
        model = get_chat_model()
        assert getattr(model, "timeout", None) == float(settings.LLM_TIMEOUT_S)
        assert getattr(model, "max_retries", None) == int(settings.LLM_MAX_RETRIES)
        assert "gemini-3.8-flash" in str(getattr(model, "model", ""))
    finally:
        settings.GEMINI_API_KEY = saved_key


def test_content_blocks_converted_to_plain_text():
    """Verify that multi-part content blocks in AIMessage are converted to text."""
    fake = ScriptedChatModel(
        responses=[AIMessage(content=[{"type": "text", "text": "Olá, sou o assistente Getnet."}])]
    )
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="oi", session_id="robust-text-1")
    assert state.agent_response == "Olá, sou o assistente Getnet."


def test_model_not_found_error_returns_503_misconfigured(client: TestClient):
    """Verify ModelNotFoundError results in HTTP 503 with 'misconfigured' and X-Trace-Id header."""
    saved = graph_mod._orchestrator_instance
    try:
        graph_mod._orchestrator_instance = OrchestrationGraph(
            chat_model=RaisingChatModel(ModelNotFoundError("Model 'gemini-invalid' not found"))
        )
        response = client.post("/chat", json={"message": "oi", "user_id": "cliente1988"})
        assert response.status_code == 503
        assert "misconfigured" in response.text.lower()
        assert "X-Trace-Id" in response.headers
        assert response.headers["X-Trace-Id"].startswith("trc-")
    finally:
        graph_mod._orchestrator_instance = saved


def test_direct_llm_configuration_error_propagated_by_run_sync():
    """Verify run_sync propagates LLMConfigurationError directly."""
    orch = OrchestrationGraph(chat_model=RaisingChatModel(LLMConfigurationError("Bad config")))
    with pytest.raises(LLMConfigurationError):
        orch.run_sync(user_id="cliente1988", message="oi", session_id="conf-err-test")


@pytest.mark.parametrize(
    "config_exc",
    [
        ModelAuthenticationError("Invalid API key"),
        ModelPermissionDeniedError("Permission denied for model"),
        ModelInvalidRequestError("Invalid request structure"),
    ],
    ids=["auth_error", "permission_error", "invalid_request"],
)
def test_other_config_errors_return_503_misconfigured(client: TestClient, config_exc):
    """Verify other non-retryable errors return HTTP 503 misconfigured."""
    saved = graph_mod._orchestrator_instance
    try:
        graph_mod._orchestrator_instance = OrchestrationGraph(chat_model=RaisingChatModel(config_exc))
        response = client.post("/chat", json={"message": "oi", "user_id": "cliente1988"})
        assert response.status_code == 503
        assert "misconfigured" in response.text.lower()
        assert bool(response.headers.get("X-Trace-Id"))
    finally:
        graph_mod._orchestrator_instance = saved


def test_model_rate_limit_error_returns_503_unavailable(client: TestClient):
    """Verify ModelRateLimitError results in HTTP 503 with 'unavailable' and without 'misconfigured'."""
    saved = graph_mod._orchestrator_instance
    try:
        graph_mod._orchestrator_instance = OrchestrationGraph(
            chat_model=RaisingChatModel(ModelRateLimitError("Rate limit 429 quota exhausted"))
        )
        response = client.post("/chat", json={"message": "oi", "user_id": "cliente1988"})
        assert response.status_code == 503
        text_lower = response.text.lower()
        assert "unavailable" in text_lower
        assert "misconfigured" not in text_lower
        assert "X-Trace-Id" in response.headers
    finally:
        graph_mod._orchestrator_instance = saved


def test_generic_exception_returns_500_without_leak_and_with_trace_id(client: TestClient):
    """Verify unhandled exception returns 500 without leaking secret and includes X-Trace-Id."""
    class ExplodingGraph:
        def run_sync(self, *args, **kwargs):
            raise RuntimeError("DATABASE_SECRET_CREDENTIAL_STRING_98765")

    saved = graph_mod._orchestrator_instance
    try:
        graph_mod._orchestrator_instance = ExplodingGraph()
        response = client.post("/chat", json={"message": "oi", "user_id": "cliente1988"})
        assert response.status_code == 500
        assert "DATABASE_SECRET_CREDENTIAL_STRING_98765" not in response.text
        tid = response.headers.get("X-Trace-Id", "")
        assert bool(tid)
        assert tid in response.text
        assert "Internal error. Reference:" in response.text
    finally:
        graph_mod._orchestrator_instance = saved


def test_trace_id_header_consistency(client: TestClient):
    """Verify X-Trace-Id header is returned on 200 and matches metadata.trace_id."""
    saved = graph_mod._orchestrator_instance
    try:
        graph_mod._orchestrator_instance = OrchestrationGraph(
            chat_model=ScriptedChatModel(responses=[AIMessage(content="Resposta normal de atendimento.")])
        )
        response = client.post("/chat", json={"message": "oi", "user_id": "cliente1988"})
        assert response.status_code == 200
        header_tid = response.headers.get("X-Trace-Id")
        assert bool(header_tid)
        data = response.json()
        assert data["metadata"]["trace_id"] == header_tid
    finally:
        graph_mod._orchestrator_instance = saved


def test_supervisor_step_limit_forces_escalation_and_consistent_history():
    """
    Verify that when supervisor requests tools continuously and hits MAX_SUPERVISOR_STEPS:
    - Model is called exactly MAX_SUPERVISOR_STEPS times
    - Force escalation creates a real ticket in tickets.db
    - Response contains the ticket_id
    - Every tool call has a corresponding ToolMessage
    """
    old_max = settings.MAX_SUPERVISOR_STEPS
    try:
        settings.MAX_SUPERVISOR_STEPS = 3
        looping_model = ScriptedChatModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[{"name": "get_settlement_status", "args": {}, "id": f"call-loop-{i}"}],
                )
                for i in range(15)
            ]
        )
        orch = OrchestrationGraph(chat_model=looping_model)
        state = orch.run_sync(user_id="cliente1988", message="loop test", session_id="test-loop-session-1")

        # 1. Exactly 3 model calls
        assert len(looping_model.received) == 3

        # 2. Escalation executed
        assert state.tools_used[-1:] == ["escalate_to_human"]
        assert state.ticket is not None
        ticket_id = state.ticket.get("ticket_id", "")
        assert ticket_id.startswith("GET-TKT-")

        # 3. Response contains ticket_id
        assert ticket_id in (state.agent_response or "")
        assert "Não consegui concluir sua solicitação automaticamente." in state.agent_response

        # 4. History consistency: every tool_call in any AIMessage has a ToolMessage
        msgs = orch.graph.get_state({"configurable": {"thread_id": "test-loop-session-1"}}).values.get("messages", [])
        call_ids = {c["id"] for m in msgs if isinstance(m, AIMessage) for c in (m.tool_calls or [])}
        answered_ids = {m.tool_call_id for m in msgs if isinstance(m, ToolMessage)}
        assert call_ids <= answered_ids
    finally:
        settings.MAX_SUPERVISOR_STEPS = old_max
