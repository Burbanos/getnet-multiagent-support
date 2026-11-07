"""Plumbing tests with a scripted model; routing quality with the real model is measured in Phase 6."""
import pytest
from langchain_core.messages import AIMessage, ToolMessage

from src.core.graph import OrchestrationGraph
from tests.fakes import ScriptedChatModel

SCENARIOS = [
    {
        "id": 1,
        "message": "What's the difference between the Get Clássica and the Get Smart?",
        "expected_tool": "search_knowledge_base",
        "tool_args": {"query": "Get Classica Get Smart"},
        "expected_data_keywords": ["Smart", "Clássica"],
        "user_id": "cliente1988",
    },
    {
        "id": 2,
        "message": "What's the weather forecast in Porto Alegre tomorrow?",
        "expected_tool": "search_web",
        "tool_args": {"query": "weather Porto Alegre"},
        "expected_data_keywords": ["Porto Alegre"],
        "user_id": "cliente1988",
    },
    {
        "id": 3,
        "message": "When will the money from yesterday's sales be deposited?",
        "expected_tool": "get_settlement_status",
        "tool_args": {},
        "expected_data_keywords": ["cliente1988", "yesterday_sales", "Santander"],
        "user_id": "cliente1988",
    },
    {
        "id": 4,
        "message": "Do I need a bank account to receive my sales via Pix?",
        "expected_tool": "search_knowledge_base",
        "tool_args": {"query": "pix conta bancaria"},
        "expected_data_keywords": ["pix"],
        "user_id": "cliente1988",
    },
    {
        "id": 5,
        "message": "My card machine won't connect to the internet, what should I do?",
        "expected_tool": "diagnose_terminal",
        "tool_args": {},
        "expected_data_keywords": ["cliente1988", "Get Smart", "Wi-Fi"],
        "user_id": "cliente1988",
    },
    {
        "id": 6,
        "message": "How does receivables advance (antecipação) work with Getnet?",
        "expected_tool": "search_knowledge_base",
        "tool_args": {"query": "antecipação de recebíveis"},
        "expected_data_keywords": ["antecipação"],
        "user_id": "cliente1988",
    },
    {
        "id": 7,
        "message": "What's the euro exchange rate today?",
        "expected_tool": "search_web",
        "tool_args": {"query": "cotacao euro hoje"},
        "expected_data_keywords": ["euro"],
        "user_id": "cliente1988",
    },
    {
        "id": 8,
        "message": "My card machine is showing a transaction decline error.",
        "expected_tool": "diagnose_declined_transaction",
        "tool_args": {"error_code": "51"},
        "expected_data_keywords": ["cliente1988", "51"],
        "user_id": "cliente1988",
    },
    {
        "id": 9,
        "message": "How many installments can I split a sale into with the crediário?",
        "expected_tool": "search_knowledge_base",
        "tool_args": {"query": "crediario parcelamento"},
        "expected_data_keywords": ["crediário"],
        "user_id": "cliente1988",
    },
    {
        "id": 10,
        "message": "Can I sell through WhatsApp using the Payment Link?",
        "expected_tool": "search_knowledge_base",
        "tool_args": {"query": "link pagamento whatsapp"},
        "expected_data_keywords": ["link"],
        "user_id": "cliente1988",
    },
]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[f"scenario-{s['id']}" for s in SCENARIOS])
def test_evaluation_scenarios_plumbing(scenario):
    """Verify tool execution and observation wiring for official benchmark scenarios via specialists."""
    if scenario["expected_tool"] in {"search_knowledge_base", "search_web"}:
        sup_tool = "ask_knowledge_agent"
        sup_args = {"question": scenario["message"]}
    else:
        sup_tool = "ask_support_agent"
        sup_args = {"request": scenario["message"]}

    call_sup_id = f"call-sup-{scenario['id']}"
    call_tool_id = f"call-tool-{scenario['id']}"

    fake = ScriptedChatModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": sup_tool, "args": sup_args, "id": call_sup_id}]),
            AIMessage(content="", tool_calls=[{"name": scenario["expected_tool"], "args": scenario["tool_args"], "id": call_tool_id}]),
            AIMessage(content=f"Specialist reply for scenario {scenario['id']}"),
            AIMessage(content=f"Final synthesized reply for scenario {scenario['id']}"),
        ]
    )

    orch = OrchestrationGraph(chat_model=fake)
    state = orch.run_sync(
        user_id=scenario["user_id"],
        message=scenario["message"],
        session_id=f"session-scen-{scenario['id']}",
    )

    assert state.tools_used == [scenario["expected_tool"]]
    assert state.agent_response == f"Final synthesized reply for scenario {scenario['id']}"

    assert len(fake.received) == 4
    # Step 3 in fake.received (index 2) is the specialist receiving the ToolMessage from the executed tool
    step2_messages = fake.received[2]
    tool_msgs = [m for m in step2_messages if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 1
    assert tool_msgs[0].name == scenario["expected_tool"]

    content_lower = str(tool_msgs[0].content).lower()
    for kw in scenario["expected_data_keywords"]:
        assert kw.lower() in content_lower, (
            f"Scenario {scenario['id']} expected '{kw}' in ToolMessage: {tool_msgs[0].content}"
        )
