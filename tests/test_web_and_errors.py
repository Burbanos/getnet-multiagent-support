"""Tests for web search recording, internal error handling, and bilingual fixed messages (Phase 7D)."""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

import src.core.tickets_db as tdb
from src.core.graph import FORCED_ESCALATION_MESSAGE, INSTABILITY_MESSAGE, OrchestrationGraph
from src.eval.judge import build_judge_input
from src.eval.runner import observe_turn, run_case
from src.tools import agent_tools
from tests.fakes import ScriptedChatModel


class _StepFake(ScriptedChatModel):
    responses: list[Any] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])


def _call(name: str, args: dict, cid: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])


CANNED_WEB = {
    "status": "success",
    "query": "previsão tempo",
    "count": 2,
    "results": [
        {
            "title": "Clima POA",
            "snippet": "Previsão para amanhã: máxima de 24 graus e sol. " + "y" * 800,
            "url": "https://tempo.example/poa",
        },
        {
            "title": "Notícias Clima",
            "snippet": "Sem chuva prevista para a região metropolitana.",
            "url": "https://tempo.example/noticias",
        },
    ],
}


def test_search_web_populates_state_web_results() -> None:
    """A turn invoking search_web must populate state.web_results with normalized keys."""
    with patch.object(agent_tools, "web_search_tool", lambda query, max_results=3: CANNED_WEB):
        fake = _StepFake(
            responses=[
                _call("ask_knowledge_agent", {"question": "Como está o tempo em Porto Alegre?"}, "w1"),
                _call("search_web", {"query": "tempo Porto Alegre"}, "w2"),
                AIMessage(content="Máxima de 24 graus e sol."),
                AIMessage(content="Previsão: máxima de 24 graus e sol amanhã."),
            ]
        )
        graph = OrchestrationGraph(chat_model=fake)
        state = graph.run_sync(user_id="cliente1988", message="Previsão do tempo?", session_id="test_web_1")

    wr = getattr(state, "web_results", None) or []
    assert len(wr) == 2
    assert wr[0]["url"] == "https://tempo.example/poa"
    assert wr[0]["title"] == "Clima POA"
    assert wr[0]["snippet"].startswith("Previsão para amanhã: máxima de 24 graus")
    assert set(wr[0].keys()) == {"url", "title", "snippet"}
    assert set(wr[1].keys()) == {"url", "title", "snippet"}


def test_observe_turn_and_judge_input_include_web_results() -> None:
    """observe_turn must truncate web snippets to 600 chars and build_judge_input must format passages."""
    fake_state = SimpleNamespace(
        user_id="cliente1988",
        message="Qual a cotação?",
        session_id="test_web_2",
        agent_response="Cotação atual do euro.",
        agents_used=["SupervisorAgent", "KnowledgeAgent"],
        tools_used=["ask_knowledge_agent", "search_web"],
        sources=["https://tempo.example/poa"],
        retrieved_docs=[],
        web_results=[
            {
                "url": "https://tempo.example/poa",
                "title": "Clima POA",
                "snippet": "Z" * 900,
            }
        ],
        tool_results=[],
        ticket=None,
        escalation_ticket_id=None,
        is_safe=True,
        handoff=None,
        llm_model="gemini-3.5-flash-lite",
        tokens=None,
    )

    turn = observe_turn(fake_state, "Qual a cotação?", 12.5)
    assert "web_results" in turn
    assert len(turn["web_results"]) == 1
    w0 = turn["web_results"][0]
    assert set(w0.keys()) == {"url", "title", "snippet"}
    assert len(w0["snippet"]) == 600

    case = {"id": "off07", "turns": ["Qual a cotação do euro hoje?"]}
    result = {"id": "off07", "status": "ok", "turns": [turn]}
    judge_payload_str = build_judge_input(case, result)
    judge_payload = json.loads(judge_payload_str)

    passages = judge_payload.get("passages", [])
    assert any(p.get("url") == "https://tempo.example/poa" for p in passages)
    match = next(p for p in passages if p.get("url") == "https://tempo.example/poa")
    assert match["text"].startswith("Clima POA\nZZZZZZ")
    assert set(match.keys()) == {"url", "text"}


def test_internal_exception_flags_error_and_eval_runner() -> None:
    """Graph unexpected exception flags error='internal_error', uses INSTABILITY_MESSAGE, and run_case returns error."""
    graph = OrchestrationGraph(chat_model=_StepFake(responses=[]))

    def fail_invoke(*args, **kwargs):
        raise RuntimeError("CRITICAL_DATABASE_CRASH_XYZ")

    graph.graph.invoke = fail_invoke
    state = graph.run_sync(user_id="cliente1988", message="olá", session_id="test_err_1")

    assert getattr(state, "error", None) == "internal_error"
    assert state.agent_response == INSTABILITY_MESSAGE
    assert "CRITICAL_DATABASE_CRASH_XYZ" not in (state.agent_response or "")

    class _WrapperOrch:
        def run_sync(self, user_id, message, session_id, trace_id=None):
            return graph.run_sync(user_id=user_id, message=message, session_id=session_id)

    case = {"id": "k01", "turns": ["Pergunta de teste"]}
    eval_res = run_case(case, _WrapperOrch(), "eval_err_run")
    assert eval_res.get("status") == "error"
    assert eval_res.get("error_type") == "internal_error"
    assert len(eval_res.get("turns", [])) == 1


def test_forced_escalation_uses_bilingual_constant() -> None:
    """Forced escalation when step limit is hit must format FORCED_ESCALATION_MESSAGE with ticket_id."""
    tdb.reset_tickets_repository()
    try:
        loop_calls = [_call("ask_support_agent", {"request": "step"}, f"call_{i}") for i in range(20)]
        fake = _StepFake(responses=[x for c in loop_calls for x in (c, AIMessage(content="spec answer"))])
        graph = OrchestrationGraph(chat_model=fake)
        state = graph.run_sync(user_id="cliente1988", message="loop steps", session_id="test_force_esc")

        ticket_id = state.escalation_ticket_id
        assert ticket_id is not None
        assert ticket_id.startswith("GET-TKT-")
        expected_msg = FORCED_ESCALATION_MESSAGE.format(ticket_id=ticket_id)
        assert state.agent_response == expected_msg
    finally:
        tdb.reset_tickets_repository()
