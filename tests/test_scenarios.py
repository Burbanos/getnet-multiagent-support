"""Integration test suite for benchmark evaluation scenarios."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("scenario", [
    {
        "id": 1,
        "message": "What's the difference between the Get Clássica and the Get Smart?",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "search_knowledge_base",
        "expected_keywords": ["Clássica", "Smart", "Android", "impressora"]
    },
    {
        "id": 2,
        "message": "What's the weather forecast in Porto Alegre tomorrow?",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "search_web",
        "expected_keywords": ["Porto Alegre"]
    },
    {
        "id": 3,
        "message": "When will the money from yesterday's sales be deposited?",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "get_settlement_status",
        "expected_keywords": ["depósito", "hoje", "Santander"]
    },
    {
        "id": 4,
        "message": "Do I need a bank account to receive my sales via Pix?",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "search_knowledge_base",
        "expected_keywords": ["conta bancária", "Pix", "QR Code"]
    },
    {
        "id": 5,
        "message": "My card machine won't connect to the internet, what should I do?",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "diagnose_terminal",
        "expected_keywords": ["Wi-Fi", "chip", "reiniciar"]
    },
    {
        "id": 6,
        "message": "How does receivables advance (antecipação) work with Getnet?",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "search_knowledge_base",
        "expected_keywords": ["Antecipação", "Automática", "Avulsa", "prazo"]
    },
    {
        "id": 7,
        "message": "What's the euro exchange rate today?",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "search_web",
        "expected_keywords": ["Euro"]
    },
    {
        "id": 8,
        "message": "My card machine is showing a transaction decline error.",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "diagnose_declined_transaction",
        "expected_keywords": ["51", "saldo", "banco emissor"]
    },
    {
        "id": 9,
        "message": "How many installments can I split a sale into with the crediário?",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "search_knowledge_base",
        "expected_keywords": ["Crediário", "24x", "36x"]
    },
    {
        "id": 10,
        "message": "Can I sell through WhatsApp using the Payment Link?",
        "expected_agent": "SupervisorAgent",
        "expected_tool": "search_knowledge_base",
        "expected_keywords": ["WhatsApp", "Link de Pagamento", "App Getnet"]
    },
])
def test_evaluation_scenarios(client: TestClient, scenario):
    """Execute end-to-end integration test for benchmark scenario."""
    payload = {
        "message": scenario["message"],
        "user_id": "cliente1988"
    }

    response = client.post("/chat", json=payload)
    assert response.status_code == 200, f"Scenario {scenario['id']} failed with status {response.status_code}"

    data = response.json()
    assert data["agent"] in ["SupervisorAgent", scenario["expected_agent"]], (
        f"Scenario {scenario['id']} expected agent SupervisorAgent or {scenario['expected_agent']}, got {data['agent']}"
    )

    metadata = data["metadata"]
    assert scenario["expected_tool"] in metadata["tools_used"], (
        f"Scenario {scenario['id']} expected tool {scenario['expected_tool']} in {metadata['tools_used']}"
    )

    reply = data["response"].lower()
    for kw in scenario["expected_keywords"]:
        assert kw.lower() in reply, (
            f"Scenario {scenario['id']} response did not contain expected keyword '{kw}'. Response: {data['response']}"
        )
