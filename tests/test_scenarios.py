"""Integration test suite for benchmark evaluation scenarios."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("scenario", [
    {
        "id": 1,
        "message": "What's the difference between the Get Clássica and the Get Smart?",
        "expected_agent": "KnowledgeAgent",
        "expected_tool": "knowledge_retriever",
        "expected_keywords": ["Clássica", "Smart", "Android", "impressora"]
    },
    {
        "id": 2,
        "message": "What's the weather forecast in Porto Alegre tomorrow?",
        "expected_agent": "KnowledgeAgent",
        "expected_tool": "web_search_tool",
        "expected_keywords": ["Porto Alegre"]
    },
    {
        "id": 3,
        "message": "When will the money from yesterday's sales be deposited?",
        "expected_agent": "CustomerSupportAgent",
        "expected_tool": "get_settlement_and_sales_status",
        "expected_keywords": ["depósito", "hoje", "3.367,20", "Santander"]
    },
    {
        "id": 4,
        "message": "Do I need a bank account to receive my sales via Pix?",
        "expected_agent": "KnowledgeAgent",
        "expected_tool": "knowledge_retriever",
        "expected_keywords": ["conta bancária", "Pix", "QR Code"]
    },
    {
        "id": 5,
        "message": "My card machine won't connect to the internet, what should I do?",
        "expected_agent": "CustomerSupportAgent",
        "expected_tool": "diagnose_terminal_connectivity",
        "expected_keywords": ["Wi-Fi", "chip", "reiniciar", "Get Smart"]
    },
    {
        "id": 6,
        "message": "How does receivables advance (antecipação) work with Getnet?",
        "expected_agent": "KnowledgeAgent",
        "expected_tool": "knowledge_retriever",
        "expected_keywords": ["Antecipação", "Automática", "Avulsa", "prazo"]
    },
    {
        "id": 7,
        "message": "What's the euro exchange rate today?",
        "expected_agent": "KnowledgeAgent",
        "expected_tool": "web_search_tool",
        "expected_keywords": ["Euro"]
    },
    {
        "id": 8,
        "message": "My card machine is showing a transaction decline error.",
        "expected_agent": "CustomerSupportAgent",
        "expected_tool": "get_declined_transaction_details",
        "expected_keywords": ["51", "saldo", "banco emissor"]
    },
    {
        "id": 9,
        "message": "How many installments can I split a sale into with the crediário?",
        "expected_agent": "KnowledgeAgent",
        "expected_tool": "knowledge_retriever",
        "expected_keywords": ["Crediário", "24x", "36x"]
    },
    {
        "id": 10,
        "message": "Can I sell through WhatsApp using the Payment Link?",
        "expected_agent": "KnowledgeAgent",
        "expected_tool": "knowledge_retriever",
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
    assert data["agent"] == scenario["expected_agent"], (
        f"Scenario {scenario['id']} expected agent {scenario['expected_agent']}, got {data['agent']}"
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
