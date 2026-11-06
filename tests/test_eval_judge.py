"""Evaluation dataset verification and security header tests."""
import json
import logging
from pathlib import Path

from langchain_core.messages import AIMessage
from starlette.testclient import TestClient

import src.core.graph as graph_mod
from src.core.graph import OrchestrationGraph
from tests.fakes import ScriptedChatModel

logger = logging.getLogger("multiagent.eval_dataset")

DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "eval_dataset.json"


def test_eval_dataset_schema():
    """Verify that eval_dataset.json exists and adheres to the evaluation specification."""
    assert DATASET_PATH.exists(), f"Evaluation dataset not found at {DATASET_PATH}"
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 12, f"Expected 12 labeled test pairs, found {len(data)}"

    required_keys = {"id", "question", "expected_tool", "ground_truth_context", "ideal_answer"}
    for item in data:
        assert required_keys.issubset(item.keys()), f"Missing keys in {item}"
        assert len(item["question"]) > 5
        assert len(item["ground_truth_context"]) > 5
        assert len(item["ideal_answer"]) > 5


def test_x_api_key_security_header(client: TestClient):
    """
    Test X-API-Key security header enforcement:
    1. Valid key 'getnet-dev-key' returns HTTP 200.
    2. Omitted header returns HTTP 200 (frictionless local development).
    3. Unauthorized key returns HTTP 401 Unauthorized.
    """
    saved = graph_mod._orchestrator_instance
    try:
        graph_mod._orchestrator_instance = OrchestrationGraph(
            chat_model=ScriptedChatModel(responses=[AIMessage(content="ok"), AIMessage(content="ok")])
        )

        # 1. Valid key
        res_valid = client.post(
            "/chat",
            headers={"X-API-Key": "getnet-dev-key"},
            json={"message": "Qual a diferença entre Get Clássica e Get Smart?", "user_id": "sec_test"},
        )
        assert res_valid.status_code == 200

        # 2. Omitted header
        res_omitted = client.post(
            "/chat",
            json={"message": "Qual a diferença entre Get Clássica e Get Smart?", "user_id": "sec_test"},
        )
        assert res_omitted.status_code == 200

        # 3. Unauthorized key
        res_invalid = client.post(
            "/chat",
            headers={"X-API-Key": "malicious-hacker-key-999"},
            json={"message": "Qual a diferença entre Get Clássica e Get Smart?", "user_id": "sec_test"},
        )
        assert res_invalid.status_code == 401
        assert "inválida" in res_invalid.json()["detail"].lower()
    finally:
        graph_mod._orchestrator_instance = saved
