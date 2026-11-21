"""Offline tests for plan_coverage gate and delegate display in supervisor prompt."""
from __future__ import annotations

import uuid
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.config import settings
from src.core import metrics, tracing
from src.core.graph import OrchestrationGraph
from src.core.tickets_db import _get_message_text, reset_tickets_repository
from tests.fakes import ScriptedChatModel


def _tc(name: str, args: dict[str, Any]) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"}])


def _plan_msg(
    steps: list[dict[str, str]],
    *,
    lang: str = "pt",
    scope: str = "support",
    esc: str = "none",
) -> AIMessage:
    return _tc(
        "TurnPlan",
        {
            "reply_language": lang,
            "scope": scope,
            "escalation_request": esc,
            "action_confirmation": "none",
            "steps": steps,
        },
    )


def _pass_verifier(n_steps: int) -> ScriptedChatModel:
    verdicts = [{"step": i, "verdict": "answered", "note": ""} for i in range(1, n_steps + 1)]
    return ScriptedChatModel(responses=[_tc("Verification", {"verdicts": verdicts})])


def test_supervisor_plan_prompt_shows_delegate() -> None:
    sup = ScriptedChatModel(
        responses=[
            _tc("ask_knowledge_agent", {"question": "Explicar Pix"}),
            _tc("search_knowledge_base", {"query": "pix"}),
            AIMessage(content="Pix gera QR Code dinâmico."),
            AIMessage(content="O Pix na maquininha usa QR Code dinâmico."),
        ]
    )
    planner = ScriptedChatModel(
        responses=[
            _plan_msg(
                [
                    {"goal": "Explain how Pix works", "delegate": "knowledge"},
                    {"goal": "Thank the merchant", "delegate": "none"},
                ]
            )
        ]
    )
    orch = OrchestrationGraph(
        chat_model=sup,
        planner_model=planner,
        verifier_model=_pass_verifier(2),
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync("cliente1988", "Como funciona o Pix? Obrigado!", session_id="s-cov-prompt")

    sys_prompt = _get_message_text(sup.received[0][0])
    plan_section = sys_prompt.split("[Plan for this turn]")[-1]
    assert "1. [knowledge] Explain how Pix works" in plan_section
    assert "2. [none] Thank the merchant" in plan_section
    assert st.coverage == {"status": "complete", "missing": [], "retries": 0}


def test_plan_coverage_triggers_once_and_marks_corrected() -> None:
    sup = ScriptedChatModel(
        responses=[
            AIMessage(content="RASCUNHO-SEM-CONSULTA-1"),
            _tc("ask_knowledge_agent", {"question": "Get Tap requisitos"}),
            _tc("search_knowledge_base", {"query": "Get Tap"}),
            AIMessage(content="Exige celular Android com NFC."),
            AIMessage(content="O Get Tap exige celular Android com NFC conforme a página oficial."),
        ]
    )
    planner = ScriptedChatModel(responses=[_plan_msg([{"goal": "Check Get Tap", "delegate": "knowledge"}])])
    orch = OrchestrationGraph(
        chat_model=sup,
        planner_model=planner,
        verifier_model=_pass_verifier(1),
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync("cliente1988", "Como usar o Get Tap?", session_id="s-cov-corr")

    assert st.coverage == {"status": "corrected", "missing": [1], "retries": 1}
    assert "RASCUNHO-SEM-CONSULTA-1" not in (st.agent_response or "")
    retry_sys = _get_message_text(sup.received[1][0])
    assert "[Plan coverage]" in retry_sys
    assert "step 1 [knowledge]: Check Get Tap" in retry_sys

    snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:s-cov-corr"}})
    history = "\n".join(_get_message_text(m) for m in (snap.values or {}).get("messages") or [])
    assert "RASCUNHO-SEM-CONSULTA-1" not in history


def test_plan_coverage_incomplete_stops_after_single_retry() -> None:
    sup = ScriptedChatModel(
        responses=[
            AIMessage(content="Primeiro rascunho sem especialista."),
            AIMessage(content="Segundo rascunho também sem especialista."),
        ]
    )
    planner = ScriptedChatModel(
        responses=[
            _plan_msg(
                [
                    {"goal": "Check debit rate", "delegate": "knowledge"},
                    {"goal": "Greet merchant", "delegate": "none"},
                ]
            )
        ]
    )
    ver = _pass_verifier(2)
    orch = OrchestrationGraph(
        chat_model=sup,
        planner_model=planner,
        verifier_model=ver,
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync("cliente1988", "Bom dia! Qual a taxa do débito?", session_id="s-cov-inc")

    assert st.coverage == {"status": "incomplete", "missing": [1], "retries": 1}
    assert len(sup.received) == 2
    assert len(ver.received) == 1
    assert st.agent_response == "Segundo rascunho também sem especialista."


def test_plan_coverage_skipped_for_ticket_no_steps_or_no_plan(monkeypatch: Any) -> None:
    reset_tickets_repository()
    # 1. Ticket opened in turn -> skipped
    sup_tkt = ScriptedChatModel(
        responses=[
            _tc("escalate_to_human", {"reason": "pedido do lojista", "priority": "standard"}),
            AIMessage(content="Chamado aberto para o atendimento humano."),
        ]
    )
    pl_tkt = ScriptedChatModel(
        responses=[
            _plan_msg(
                [{"goal": "Escalate", "delegate": "none"}, {"goal": "Explain fee", "delegate": "knowledge"}],
                esc="asked_for_human",
            )
        ]
    )
    st_tkt = OrchestrationGraph(
        chat_model=sup_tkt,
        planner_model=pl_tkt,
        verifier_model=_pass_verifier(2),
        checkpointer=MemorySaver(),
    ).run_sync("cliente1988", "Quero atendente.", session_id="s-cov-tkt")
    assert st_tkt.coverage == {"status": "skipped", "missing": [], "retries": 0}

    # 2. Empty steps -> skipped
    st_empty = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content="Olá!")]),
        planner_model=ScriptedChatModel(responses=[_plan_msg([])]),
        checkpointer=MemorySaver(),
    ).run_sync("cliente1988", "Oi!", session_id="s-cov-empty")
    assert st_empty.coverage == {"status": "skipped", "missing": [], "retries": 0}

    # 3. No valid plan -> skipped
    monkeypatch.setattr(settings, "PLANNER_ENABLED", False)
    st_noplan = OrchestrationGraph(
        chat_model=ScriptedChatModel(responses=[AIMessage(content="Sem plano.")]),
        checkpointer=MemorySaver(),
    ).run_sync("cliente1988", "Qual a taxa?", session_id="s-cov-np")
    assert st_noplan.coverage == {"status": "skipped", "missing": [], "retries": 0}


def test_plan_coverage_complete_for_support_delegate() -> None:
    sup = ScriptedChatModel(
        responses=[
            _tc("ask_support_agent", {"request": "Vendas de ontem"}),
            _tc("get_settlement_status", {}),
            AIMessage(content="Vendas de ontem: R$ 3.367,20."),
            AIMessage(content="Suas vendas de ontem foram de R$ 3.367,20."),
        ]
    )
    planner = ScriptedChatModel(responses=[_plan_msg([{"goal": "Check settlement", "delegate": "support"}])])
    st = OrchestrationGraph(
        chat_model=sup,
        planner_model=planner,
        verifier_model=_pass_verifier(1),
        checkpointer=MemorySaver(),
    ).run_sync("cliente1988", "Quanto vendi ontem?", session_id="s-cov-sup")

    assert st.coverage == {"status": "complete", "missing": [], "retries": 0}
    assert "get_settlement_status" in st.tools_used


def test_plan_coverage_disabled_and_metrics_and_span(monkeypatch: Any) -> None:
    metrics.reset()
    exporter = InMemorySpanExporter()
    tracing.configure_tracing(exporter, simple=True)
    try:
        monkeypatch.setattr(settings, "PLAN_COVERAGE_ENABLED", False)
        sup_off = ScriptedChatModel(responses=[AIMessage(content="Direto.")])
        st_off = OrchestrationGraph(
            chat_model=sup_off,
            planner_model=ScriptedChatModel(responses=[_plan_msg([{"goal": "Answer fee", "delegate": "knowledge"}])]),
            verifier_model=_pass_verifier(1),
            checkpointer=MemorySaver(),
        ).run_sync("cliente1988", "Qual a taxa?", session_id="s-cov-off")
        assert st_off.coverage == {"status": "disabled", "missing": [], "retries": 0}
        assert len(sup_off.received) == 1

        monkeypatch.setattr(settings, "PLAN_COVERAGE_ENABLED", True)
        sup_on = ScriptedChatModel(
            responses=[
                _tc("ask_knowledge_agent", {"question": "pix"}),
                _tc("search_knowledge_base", {"query": "pix"}),
                AIMessage(content="Pix cai na hora."),
                AIMessage(content="O Pix na maquininha cai na hora."),
            ]
        )
        OrchestrationGraph(
            chat_model=sup_on,
            planner_model=ScriptedChatModel(responses=[_plan_msg([{"goal": "Explain Pix", "delegate": "knowledge"}])]),
            verifier_model=_pass_verifier(1),
            checkpointer=MemorySaver(),
        ).run_sync("cliente1988", "Como cai o Pix?", session_id="s-cov-on")

        rendered = metrics.render()
        assert 'getnet_plan_coverage_total{status="disabled"} 1' in rendered
        assert 'getnet_plan_coverage_total{status="complete"} 1' in rendered

        cov_spans = [s for s in exporter.get_finished_spans() if s.name == "graph.node.plan_coverage"]
        assert {s.attributes.get("coverage.status") for s in cov_spans} >= {"disabled", "complete"}
        for s in exporter.get_finished_spans():
            assert set(s.attributes or {}) <= tracing.ALLOWED_ATTRIBUTES
    finally:
        tracing.shutdown_tracing()


@pytest.fixture(autouse=True)
def _verifier_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests exercise the verifier, which is off by default since the Phase 15 ablation."""
    monkeypatch.setattr(settings, "VERIFIER_ENABLED", True)
