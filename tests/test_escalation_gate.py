"""Offline tests for the Escalation Gate on escalate_to_human calls (Phase 13B)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from src.config import settings
from src.core.graph import OrchestrationGraph
from src.core.tickets_db import get_tickets_repository, reset_tickets_repository
from tests.fakes import ScriptedChatModel


def _plan_msg(esc: str = "none", steps: list[dict[str, str]] | None = None) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "TurnPlan",
                "args": {
                    "reply_language": "pt",
                    "scope": "support",
                    "escalation_request": esc,
                    "steps": [{"goal": "Handle merchant inquiry", "delegate": "knowledge"}]
                    if steps is None
                    else steps,
                },
                "id": "call_plan_gate",
            }
        ],
    )


def _esc_call(reason: str = "duvida sem resposta", priority: str = "standard") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "escalate_to_human", "args": {"reason": reason, "priority": priority}, "id": "call_esc_1"}
        ],
    )


def _run_allowed_gate(esc_value: str, message: str, session_id: str) -> None:
    repo = get_tickets_repository()
    before = len(repo.list_tickets(user_id="cliente1988"))

    sup = ScriptedChatModel(
        responses=[
            _esc_call(reason=f"escalation ({esc_value})"),
            AIMessage(content="Seu pedido foi registrado para a equipe de atendimento humano."),
        ]
    )
    orch = OrchestrationGraph(
        chat_model=sup,
        planner_model=ScriptedChatModel(responses=[_plan_msg(esc_value, steps=[])]),
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync(user_id="cliente1988", session_id=session_id, message=message)

    after = len(repo.list_tickets(user_id="cliente1988"))
    assert after == before + 1
    assert st.ticket is not None and st.ticket.get("ticket_id")
    assert "escalate_to_human" in st.tools_used
    assert st.escalation_gate == {"decision": "allowed", "escalation_request": esc_value}


def test_escalation_gate_rejects_when_plan_says_none() -> None:
    repo = get_tickets_repository()
    before = len(repo.list_tickets(user_id="cliente1988"))

    sup = ScriptedChatModel(
        responses=[
            _esc_call(),
            AIMessage(content="Não encontrei essa informação. Se quiser, posso abrir um chamado."),
        ]
    )
    orch = OrchestrationGraph(
        chat_model=sup,
        planner_model=ScriptedChatModel(responses=[_plan_msg("none")]),
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync(user_id="cliente1988", session_id="s-gate-rej", message="Preciso de CNPJ para ter maquininha?")

    after = len(repo.list_tickets(user_id="cliente1988"))
    assert after == before
    assert st.ticket is None
    assert st.escalate_to_human is False
    assert "escalate_to_human" not in st.tools_used
    assert st.escalation_gate == {"decision": "rejected", "escalation_request": "none"}

    snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:s-gate-rej"}})
    t_msgs = [m for m in (snap.values or {}).get("messages") or [] if isinstance(m, ToolMessage)]
    assert len(t_msgs) == 1
    payload = json.loads(str(t_msgs[0].content))
    assert payload["status"] == "needs_merchant_request"


def test_escalation_gate_allows_asked_for_human() -> None:
    _run_allowed_gate("asked_for_human", "Quero falar com um atendente humano agora.", "s-gate-human")


def test_escalation_gate_allows_formal_complaint() -> None:
    _run_allowed_gate("formal_complaint", "Vou registrar uma reclamação no Procon sobre essa cobrança.", "s-gate-procon")


def test_escalation_gate_allows_accepted_offer() -> None:
    _run_allowed_gate("accepted_offer", "Sim, pode abrir o chamado por favor.", "s-gate-accepted")


def test_escalation_gate_allows_when_no_plan_is_available() -> None:
    repo = get_tickets_repository()
    before = len(repo.list_tickets(user_id="cliente1988"))

    sup = ScriptedChatModel(
        responses=[
            _esc_call(reason="merchant requested human"),
            AIMessage(content="Chamado aberto para atendimento."),
        ]
    )
    orch = OrchestrationGraph(chat_model=sup, checkpointer=MemorySaver())
    st = orch.run_sync(user_id="cliente1988", session_id="s-gate-noplan", message="Quero falar com um atendente.")

    after = len(repo.list_tickets(user_id="cliente1988"))
    assert after == before + 1
    assert st.ticket is not None and st.ticket.get("ticket_id")
    assert st.escalation_gate == {"decision": "allowed_no_plan", "escalation_request": None}


def test_auto_escalation_after_abstentions_bypasses_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "tickets_abs.db"))
    monkeypatch.setattr(settings, "ESCALATE_AFTER_ABSTENTIONS", 2)
    reset_tickets_repository()
    try:
        sup = ScriptedChatModel(
            responses=[
                AIMessage(content="", tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "q1"}, "id": "k1"}]),
                AIMessage(content="Não encontrei nas fontes oficiais."),
                AIMessage(content="", tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "q2"}, "id": "k2"}]),
                AIMessage(content="Ainda não encontrei nas fontes oficiais."),
            ]
        )
        planner = ScriptedChatModel(responses=[_plan_msg("none"), _plan_msg("none")])
        orch = OrchestrationGraph(chat_model=sup, planner_model=planner, checkpointer=MemorySaver())
        monkeypatch.setattr(
            orch.knowledge_agent,
            "run",
            lambda question, user_id="", trace_id="": {
                "agent": "KnowledgeAgent",
                "status": "abstained",
                "answer": "Sem fontes.",
                "tools_used": [],
                "sources": [],
                "retrieved_docs": [],
                "web_results": [],
                "api_results": [],
                "web_guardrail": [],
                "usage": None,
            },
        )

        st1 = orch.run_sync(user_id="cliente1988", session_id="s-auto-esc", message="Pergunta coberta 1?")
        assert st1.ticket is None

        st2 = orch.run_sync(user_id="cliente1988", session_id="s-auto-esc", message="Pergunta coberta 2?")
        assert st2.ticket is not None and st2.ticket.get("ticket_id")
        assert st2.escalation_gate is None
        assert "escalate_to_human" in st2.tools_used
    finally:
        reset_tickets_repository()
