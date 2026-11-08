"""Tests verifying dangling tool calls are closed after a failed turn (Phase 9C)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from src.core.checkpointer import build_sqlite_checkpointer
from src.core.graph import OrchestrationGraph
from src.core.llm import LLMUnavailableError
from tests.fakes import ScriptedChatModel


class ExceptionRaisingFake(ScriptedChatModel):
    """Scripted model that raises an exception when the scripted item is an Exception."""

    responses: list[Any] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        if not self.responses:
            raise RuntimeError("ExceptionRaisingFake: no scripted responses left")
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return ChatResult(generations=[ChatGeneration(message=r)])


def _unanswered(messages: list[Any]) -> list[str]:
    """Return tool call ids from AIMessages that do not have a corresponding ToolMessage."""
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    return [
        call.get("id")
        for m in messages
        if isinstance(m, AIMessage)
        for call in (m.tool_calls or [])
        if call.get("id") and call.get("id") not in answered
    ]


def _tool_messages(orch: OrchestrationGraph, config: dict[str, Any]) -> dict[str, str]:
    msgs = orch.graph.get_state(config).values.get("messages", [])
    return {m.tool_call_id: str(m.content) for m in msgs if isinstance(m, ToolMessage)}


def test_provider_failure_closes_tool_call(tmp_path: Path):
    """Provider failure in a specialist closes dangling tool call with LLMUnavailableError."""
    call = AIMessage(content="", tool_calls=[{"name": "ask_support_agent", "id": "c1", "args": {"request": "saldo de ontem"}}])
    fake = ExceptionRaisingFake(responses=[call, RuntimeError("503 overloaded")])
    db_path = tmp_path / "checkpoints_p1.db"
    orch = OrchestrationGraph(chat_model=fake, checkpointer=build_sqlite_checkpointer(db_path))
    config = {"configurable": {"thread_id": "cliente1988:p1"}}

    with pytest.raises(LLMUnavailableError):
        orch.run_sync(user_id="cliente1988", session_id="p1", message="Quando recebo as vendas de ontem?")

    snap = orch.graph.get_state(config)
    msgs = snap.values.get("messages", [])
    assert _unanswered(msgs) == []
    assert snap.next == ()

    tm = _tool_messages(orch, config)
    assert "c1" in tm
    payload = json.loads(tm["c1"])
    assert payload.get("status") == "error"
    assert payload.get("error") == "LLMUnavailableError"


def test_next_turn_has_no_orphan(tmp_path: Path):
    """Subsequent turn after a failure does not send any orphan tool call to the model."""
    call = AIMessage(content="", tool_calls=[{"name": "ask_support_agent", "id": "c1", "args": {"request": "saldo"}}])
    fake = ExceptionRaisingFake(responses=[call, RuntimeError("503 overloaded")])
    db_path = tmp_path / "checkpoints_p2.db"
    orch = OrchestrationGraph(chat_model=fake, checkpointer=build_sqlite_checkpointer(db_path))
    config = {"configurable": {"thread_id": "cliente1988:p2"}}

    with pytest.raises(LLMUnavailableError):
        orch.run_sync(user_id="cliente1988", session_id="p2", message="Quando recebo?")

    # Next turn succeeds
    fake.responses = [AIMessage(content="ok")]
    fake.received.clear()

    st = orch.run_sync(user_id="cliente1988", session_id="p2", message="E agora?")
    assert st.agent_response == "ok"

    sent = fake.received[0]
    assert _unanswered(sent) == []
    assert isinstance(sent[-1], HumanMessage)

    snap = orch.graph.get_state(config)
    assert _unanswered(snap.values.get("messages", [])) == []
    assert snap.next == ()


def test_parallel_tool_calls_all_closed(tmp_path: Path):
    """Parallel tool calls where one specialist fails result in all calls being closed."""
    call = AIMessage(
        content="",
        tool_calls=[
            {"name": "ask_knowledge_agent", "id": "k1", "args": {"question": "O que é Get Smart?"}},
            {"name": "ask_support_agent", "id": "s1", "args": {"request": "saldo"}},
        ],
    )
    fake = ExceptionRaisingFake(responses=[call, AIMessage(content="A Get Smart é uma maquininha."), RuntimeError("503 overloaded")])
    db_path = tmp_path / "checkpoints_p3.db"
    orch = OrchestrationGraph(chat_model=fake, checkpointer=build_sqlite_checkpointer(db_path))
    config = {"configurable": {"thread_id": "cliente1988:p3"}}

    with pytest.raises(LLMUnavailableError):
        orch.run_sync(user_id="cliente1988", session_id="p3", message="Get Smart e meu saldo")

    snap = orch.graph.get_state(config)
    msgs = snap.values.get("messages", [])
    assert _unanswered(msgs) == []
    assert snap.next == ()

    tm = _tool_messages(orch, config)
    assert "k1" in tm
    assert "s1" in tm


def test_internal_error_closes_tool_call(tmp_path: Path):
    """Non-LLM internal error closes dangling tool call with internal_error and returns INSTABILITY_MESSAGE."""
    call = AIMessage(content="", tool_calls=[{"name": "ask_support_agent", "id": "c4", "args": {"request": "saldo"}}])
    fake = ExceptionRaisingFake(responses=[call])
    db_path = tmp_path / "checkpoints_p4.db"
    orch = OrchestrationGraph(chat_model=fake, checkpointer=build_sqlite_checkpointer(db_path))
    config = {"configurable": {"thread_id": "cliente1988:p4"}}

    def boom(*args, **kwargs):
        raise KeyError("unexpected error")

    orch.support_agent.run = boom

    st = orch.run_sync(user_id="cliente1988", session_id="p4", message="Meu saldo?")
    assert st.error == "internal_error"

    snap = orch.graph.get_state(config)
    msgs = snap.values.get("messages", [])
    assert _unanswered(msgs) == []
    assert snap.next == ()

    tm = _tool_messages(orch, config)
    assert "c4" in tm
    assert "internal_error" in tm["c4"]


def test_failure_before_any_tool_call_adds_nothing(tmp_path: Path):
    """Failure before any tool call occurs leaves history with only the turn's HumanMessage."""
    fake = ExceptionRaisingFake(responses=[RuntimeError("503 overloaded")])
    db_path = tmp_path / "checkpoints_p5.db"
    orch = OrchestrationGraph(chat_model=fake, checkpointer=build_sqlite_checkpointer(db_path))
    config = {"configurable": {"thread_id": "cliente1988:p5"}}

    with pytest.raises(LLMUnavailableError):
        orch.run_sync(user_id="cliente1988", session_id="p5", message="Oi")

    snap = orch.graph.get_state(config)
    msgs = snap.values.get("messages", [])
    assert [type(m).__name__ for m in msgs] == ["HumanMessage"]
