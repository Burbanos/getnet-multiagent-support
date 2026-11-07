"""Tests for Phase 2D: specialist sub-agents (KnowledgeAgent, SupportAgent) and supervisor delegation."""
import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from langchain_core.exceptions import ModelRateLimitError
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

import src.core.graph as graph_mod
from src.config import settings
from src.core.graph import OrchestrationGraph
from tests.fakes import ScriptedChatModel


class StepFake(ScriptedChatModel):
    """Scripted model supporting sequence of AIMessages and exceptions."""

    responses: list[Any] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        if not self.responses:
            raise RuntimeError("StepFake: no scripted responses left")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return ChatResult(generations=[ChatGeneration(message=item)])


def call(name: str, args: dict, cid: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": cid}])


def tool_payload(msgs: list) -> dict:
    for m in msgs:
        if isinstance(m, ToolMessage):
            try:
                return json.loads(m.content)
            except (TypeError, ValueError):
                return {}
    return {}


def test_support_flow():
    """Verify delegation from Supervisor to SupportAgent and synthesis of final response."""
    fake = StepFake(responses=[
        call("ask_support_agent", {"request": "Check yesterday's settlement"}, "s1"),
        call("get_settlement_status", {}, "s2"),
        AIMessage(content="Extrato consultado: R$ 3.367,20 a receber hoje."),
        AIMessage(content="Seu depósito de ontem está agendado para cair até as 20h."),
    ])
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="Quando cai o dinheiro de ontem?", session_id="test-sup-flow")

    assert state.agent_response == "Seu depósito de ontem está agendado para cair até as 20h."
    assert state.tools_used == ["get_settlement_status"]
    assert state.agents_used == ["SupervisorAgent", "SupportAgent"]


def test_knowledge_flow_with_sources():
    """Verify delegation from Supervisor to KnowledgeAgent collecting sources and documents."""
    fake = StepFake(responses=[
        call("ask_knowledge_agent", {"question": "Como funciona o Pix na maquininha?"}, "k1"),
        call("search_knowledge_base", {"query": "Pix conta bancária"}, "k2"),
        AIMessage(content="O Pix na maquininha gera QR Code dinâmico."),
        AIMessage(content="Você pode receber Pix na maquininha com taxa de 0,99%."),
    ])
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="Como funciona o Pix?", session_id="test-kno-flow")

    assert state.agent_response == "Você pode receber Pix na maquininha com taxa de 0,99%."
    assert state.tools_used == ["search_knowledge_base"]
    assert state.agents_used == ["SupervisorAgent", "KnowledgeAgent"]
    assert len(state.sources) > 0


def test_two_specialists_same_turn():
    """Verify supervisor can invoke both specialist agents sequentially in the same conversational turn."""
    fake = StepFake(responses=[
        call("ask_support_agent", {"request": "settlement status"}, "m1"),
        call("get_settlement_status", {}, "m2"),
        AIMessage(content="Saldo apurado com sucesso."),
        call("ask_knowledge_agent", {"question": "regras de antecipação"}, "m3"),
        call("search_knowledge_base", {"query": "antecipação"}, "m4"),
        AIMessage(content="Regras de antecipação consultadas."),
        AIMessage(content="Seu saldo de ontem é R$ 3.367,20 e a antecipação permite receber em D+1."),
    ])
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="Qual meu saldo e como antecipo?", session_id="test-two-spec")

    assert state.agents_used == ["SupervisorAgent", "SupportAgent", "KnowledgeAgent"]
    assert state.tools_used == ["get_settlement_status", "search_knowledge_base"]
    assert state.agent_response == "Seu saldo de ontem é R$ 3.367,20 e a antecipação permite receber em D+1."


def test_specialist_isolated_context():
    """Verify specialist sub-agent receives isolated context containing only its system prompt and task."""
    support_prompt = Path("src/prompts/support_agent.md").read_text(encoding="utf-8").strip()
    fake = StepFake(responses=[
        call("ask_support_agent", {"request": "Verifique o terminal"}, "i1"),
        call("diagnose_terminal", {}, "i2"),
        AIMessage(content="Terminal operando normalmente."),
        AIMessage(content="Seu terminal está com sinal 4G ativo."),
    ])
    orch = OrchestrationGraph(chat_model=fake)
    orch.run_sync(user_id="cliente1988", message="Minha maquininha está lenta", session_id="test-isolated-ctx")

    spec_in = fake.received[1]
    assert len(spec_in) == 2
    assert isinstance(spec_in[0], SystemMessage)
    assert isinstance(spec_in[1], HumanMessage)
    assert spec_in[0].content.strip() == support_prompt
    assert spec_in[1].content == "Verifique o terminal"


def test_user_id_injected_in_specialist_tool():
    """Verify authenticated merchant user_id is injected into tools called by specialists."""
    fake = StepFake(responses=[
        call("ask_support_agent", {"request": "Check settlement"}, "u1"),
        call("get_settlement_status", {}, "u2"),
        AIMessage(content="OK"),
        AIMessage(content="Final"),
    ])
    orch = OrchestrationGraph(chat_model=fake)
    orch.run_sync(user_id="cliente1988", message="oi", session_id="test-uid-inj")

    inner = fake.received[2]
    assert any(isinstance(m, ToolMessage) and '"cliente1988"' in str(m.content) for m in inner)


def test_specialist_tool_isolation_refuses_unauthorized_tool():
    """Verify specialist cannot execute tools outside its declared registry."""
    fake = StepFake(responses=[
        call("ask_support_agent", {"request": "settlement"}, "t1"),
        call("search_web", {"query": "euro"}, "t2"),
        AIMessage(content="Não consegui buscar dados web."),
        AIMessage(content="Ferramenta não permitida ao agente de suporte."),
    ])
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="oi", session_id="test-tool-iso")

    inner = fake.received[2]
    assert "search_web" not in state.tools_used
    assert any(isinstance(m, ToolMessage) and "error" in str(m.content).lower() for m in inner)


def test_escalate_to_human_direct_from_supervisor():
    """Verify supervisor executes escalate_to_human directly without invoking a specialist."""
    fake = StepFake(responses=[
        call("escalate_to_human", {"reason": "Lojista solicitou falar com pessoa"}, "e1"),
        AIMessage(content="Registrei seu chamado com a equipe humana."),
    ])
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="Quero falar com um humano", session_id="test-dir-esc")

    assert state.tools_used == ["escalate_to_human"]
    assert state.agents_used == ["SupervisorAgent"]
    assert bool((state.ticket or {}).get("ticket_id"))


def test_specialist_step_limit_enforced():
    """Verify specialist stops and returns step_limit when MAX_SPECIALIST_STEPS is reached."""
    old_steps = settings.MAX_SPECIALIST_STEPS
    settings.MAX_SPECIALIST_STEPS = 2
    try:
        fake = StepFake(responses=[
            call("ask_support_agent", {"request": "loop test"}, "l1"),
            call("get_settlement_status", {}, "l2"),
            call("get_settlement_status", {}, "l3"),
            AIMessage(content="Supervisor percebeu limite e encerrou."),
        ])
        orch = OrchestrationGraph(chat_model=fake)
        state = orch.run_sync(user_id="cliente1988", message="x", session_id="test-step-lim")

        payload = tool_payload(fake.received[3])
        assert payload.get("status") == "step_limit"
        assert len(fake.received) == 4
        assert state.agent_response == "Supervisor percebeu limite e encerrou."
    finally:
        settings.MAX_SPECIALIST_STEPS = old_steps


def test_specialist_llm_error_returns_503(client: TestClient):
    """Verify LLM failure inside specialist agent propagates to HTTP 503 on /chat."""
    saved = graph_mod._orchestrator_instance
    try:
        graph_mod._orchestrator_instance = OrchestrationGraph(
            chat_model=StepFake(responses=[
                call("ask_support_agent", {"request": "settlement"}, "err1"),
                ModelRateLimitError("Quota exceeded (429)"),
            ])
        )
        res = client.post("/chat", json={"message": "Quando cai?", "user_id": "cliente1988"})
        assert res.status_code == 503
        assert "unavailable" in res.text.lower()
    finally:
        graph_mod._orchestrator_instance = saved


def test_api_reports_agents_used(client: TestClient):
    """Verify API /chat response metadata accurately reports agents_used list."""
    saved = graph_mod._orchestrator_instance
    try:
        graph_mod._orchestrator_instance = OrchestrationGraph(
            chat_model=StepFake(responses=[
                call("ask_support_agent", {"request": "settlement"}, "a1"),
                call("get_settlement_status", {}, "a2"),
                AIMessage(content="Depósito agendado."),
                AIMessage(content="Seu depósito cai hoje."),
            ])
        )
        res = client.post("/chat", json={"message": "Quando cai?", "user_id": "cliente1988"})
        assert res.status_code == 200
        meta = res.json().get("metadata", {})
        assert meta.get("agents_used") == ["SupervisorAgent", "SupportAgent"]
    finally:
        graph_mod._orchestrator_instance = saved
