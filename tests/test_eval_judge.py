"""Evaluation dataset verification and rules fallback routing tests."""
import json
import logging
from pathlib import Path

from starlette.testclient import TestClient

from src.core.graph import OrchestrationGraph

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


def test_rules_fallback_routing_on_dataset(orchestrator: OrchestrationGraph):
    """Verify expected tool routing on the evaluation dataset using the rules engine."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    for item in dataset:
        q_id = item["id"]
        question = item["question"]
        expected_tool = item["expected_tool"]

        state = orchestrator.run_sync(
            user_id="rules_evaluator",
            message=question,
            session_id=f"session-{q_id}"
        )

        if expected_tool == "none_guardrail":
            assert not state.is_safe, f"[{q_id}] Expected guardrail block, but message was safe"
        elif expected_tool == "escalate_to_human":
            assert "escalate_to_human" in state.tools_used or state.escalate_to_human, (
                f"[{q_id}] Expected escalation, got {state.tools_used}"
            )
        else:
            assert expected_tool in state.tools_used, (
                f"[{q_id}] Expected tool '{expected_tool}' in {state.tools_used}"
            )


def test_x_api_key_security_header(client: TestClient):
    """
    Test X-API-Key security header enforcement:
    1. Valid key 'getnet-dev-key' returns HTTP 200.
    2. Omitted header returns HTTP 200 (frictionless local development).
    3. Unauthorized key returns HTTP 401 Unauthorized.
    """
    # 1. Valid key
    res_valid = client.post(
        "/chat",
        headers={"X-API-Key": "getnet-dev-key"},
        json={"message": "Qual a diferença entre Get Clássica e Get Smart?", "user_id": "sec_test"}
    )
    assert res_valid.status_code == 200

    # 2. Omitted header
    res_omitted = client.post(
        "/chat",
        json={"message": "Qual a diferença entre Get Clássica e Get Smart?", "user_id": "sec_test"}
    )
    assert res_omitted.status_code == 200

    # 3. Unauthorized key
    res_invalid = client.post(
        "/chat",
        headers={"X-API-Key": "malicious-hacker-key-999"},
        json={"message": "Qual a diferença entre Get Clássica e Get Smart?", "user_id": "sec_test"}
    )
    assert res_invalid.status_code == 401
    assert "inválida" in res_invalid.json()["detail"].lower()
