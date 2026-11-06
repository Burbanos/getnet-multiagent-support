"""Integration tests for LangGraph Supervisor with LLM function calling and ScriptedChatModel."""
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from starlette.testclient import TestClient

import src.core.graph as graph_mod
from src.core.graph import OrchestrationGraph
from src.tools.agent_tools import ALL_TOOLS
from tests.fakes import ScriptedChatModel


def test_single_tool_execution():
    """Verify single tool call execution flow via ScriptedChatModel."""
    fake = ScriptedChatModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "get_settlement_status", "args": {}, "id": "call-1"}]),
            AIMessage(content="Seu depósito de ontem está agendado para hoje."),
        ]
    )
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="Quando cai o dinheiro de ontem?", session_id="test-single-1")

    assert state.tools_used == ["get_settlement_status"]
    assert state.agent_response == "Seu depósito de ontem está agendado para hoje."
    assert len(fake.received) == 2
    # First message to model is supervisor system prompt
    assert isinstance(fake.received[0][0], SystemMessage)
    # Observation sent to model in step 2 is ToolMessage
    assert any(isinstance(m, ToolMessage) for m in fake.received[1])


def test_two_tools_sequence():
    """Verify sequential execution of two distinct tools before final response."""
    fake = ScriptedChatModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "get_settlement_status", "args": {}, "id": "call-seq-1"}]),
            AIMessage(content="", tool_calls=[{"name": "search_knowledge_base", "args": {"query": "antecipação"}, "id": "call-seq-2"}]),
            AIMessage(content="Extrato consultado e regras de antecipação verificadas."),
        ]
    )
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="Qual meu saldo e como funciona antecipação?", session_id="test-seq-1")

    assert state.tools_used == ["get_settlement_status", "search_knowledge_base"]
    assert state.agent_response == "Extrato consultado e regras de antecipação verificadas."
    assert len(fake.received) == 3


def test_direct_response_without_tool():
    """Verify direct response generation for small talk without tool invocation."""
    fake = ScriptedChatModel(
        responses=[
            AIMessage(content="Olá! Sou o assistente de suporte Getnet. Como posso ajudar?"),
        ]
    )
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="Olá, bom dia!", session_id="test-direct-1")

    assert state.tools_used == []
    assert "assistente de suporte Getnet" in state.agent_response
    assert len(fake.received) == 1


def test_tool_exception_returns_tool_message_error_to_model(monkeypatch):
    """Verify tool errors are captured in ToolMessage and sent back to supervisor."""
    def broken_settlement(*args, **kwargs):
        raise RuntimeError("Falha de conexão com o banco transacional")

    monkeypatch.setattr(
        "src.tools.agent_tools.get_settlement_and_sales_status",
        broken_settlement,
    )

    fake = ScriptedChatModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": "get_settlement_status", "args": {}, "id": "call-err-1"}]),
            AIMessage(content="Identifiquei uma instabilidade momentânea na consulta do extrato."),
        ]
    )
    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(user_id="cliente1988", message="Ver extrato", session_id="test-err-1")

    assert state.tools_used == ["get_settlement_status"]
    assert state.agent_response == "Identifiquei uma instabilidade momentânea na consulta do extrato."

    # Verify ToolMessage carried the error description to the model
    second_turn_msgs = fake.received[1]
    tool_msgs = [m for m in second_turn_msgs if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 1
    assert "Falha" in tool_msgs[0].content


def test_multi_turn_memory_same_session():
    """Verify LangGraph MemorySaver preserves conversational history across multiple turns."""
    fake = ScriptedChatModel(
        responses=[
            AIMessage(content="A Get Smart roda Android e tem tela touch."),
            AIMessage(content="Sim, ela também possui conexão Wi-Fi e chip 4G."),
        ]
    )
    orch = OrchestrationGraph(chat_model=fake)
    session_id = "multi-turn-test-session"

    state1 = orch.run_sync(user_id="cliente1988", message="Quais as características da Get Smart?", session_id=session_id)
    assert "Get Smart" in state1.agent_response

    state2 = orch.run_sync(user_id="cliente1988", message="Ela tem Wi-Fi?", session_id=session_id)
    assert "Wi-Fi" in state2.agent_response

    # Verify that the model input on turn 2 includes turn 1 question
    second_input = fake.received[1]
    second_text = " ".join(str(m.content) for m in second_input)
    assert "Quais as características da Get Smart?" in second_text


def test_credit_card_masked_before_model():
    """Verify PII (Luhn credit card) is sanitized before reaching the model."""
    fake = ScriptedChatModel(responses=[AIMessage(content="Entendido, vou verificar a recusa.")])
    orch = OrchestrationGraph(chat_model=fake)

    orch.run_sync(
        user_id="cliente1988",
        message="A venda no cartão 4111 1111 1111 1111 deu erro",
        session_id="test-pii-mask",
    )

    sent_text = " ".join(str(m.content) for m in fake.received[0])
    assert "4111 1111 1111 1111" not in sent_text
    assert "CARTAO_MASCARADO" in sent_text


def test_user_id_absent_from_all_model_visible_tool_schemas():
    """Verify user_id parameter is not model-visible in any tool schema."""
    for tool_fn in ALL_TOOLS:
        args_schema = tool_fn.args
        assert "user_id" not in args_schema, f"user_id leaked into schema of tool '{tool_fn.name}'"


def test_chat_endpoint_without_key_returns_503(client: TestClient):
    """Verify /chat endpoint returns HTTP 503 when GEMINI_API_KEY is not configured."""
    saved = graph_mod._orchestrator_instance
    try:
        graph_mod._orchestrator_instance = None
        res = client.post("/chat", json={"message": "Olá", "user_id": "cliente1988"})
        assert res.status_code == 503
        assert "LLM not configured: set GEMINI_API_KEY." in res.json()["detail"]
    finally:
        graph_mod._orchestrator_instance = saved


def test_chat_endpoint_model_exception_returns_503(client: TestClient):
    """Verify /chat endpoint returns HTTP 503 when LLM service times out or fails."""
    saved = graph_mod._orchestrator_instance

    class FailingChatModel(ScriptedChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise TimeoutError("External provider timed out")

    try:
        graph_mod._orchestrator_instance = OrchestrationGraph(chat_model=FailingChatModel())
        res = client.post("/chat", json={"message": "Olá", "user_id": "cliente1988"})
        assert res.status_code == 503
        assert "LLM provider unavailable, please retry." in res.json()["detail"]
    finally:
        graph_mod._orchestrator_instance = saved
