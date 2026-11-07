"""Security header and evaluation endpoint tests."""
import logging

from langchain_core.messages import AIMessage
from starlette.testclient import TestClient

import src.core.graph as graph_mod
from src.core.graph import OrchestrationGraph
from tests.fakes import ScriptedChatModel

logger = logging.getLogger("multiagent.eval_judge")


def test_x_api_key_security_header(client: TestClient):
    """
    Test X-API-Key security header enforcement:
    1. Valid key 'getnet-dev-key' returns HTTP 200.
    2. Omitted header returns HTTP 401 Unauthorized.
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
            json={"message": "Qual a diferença entre Get Clássica e Get Smart?"},
        )
        assert res_valid.status_code == 200

        # 2. Omitted header returns 401
        res_omitted = client.post(
            "/chat",
            json={"message": "Qual a diferença entre Get Clássica e Get Smart?"},
        )
        assert res_omitted.status_code == 401

        # 3. Unauthorized key
        res_invalid = client.post(
            "/chat",
            headers={"X-API-Key": "malicious-hacker-key-999"},
            json={"message": "Qual a diferença entre Get Clássica e Get Smart?"},
        )
        assert res_invalid.status_code == 401
        assert "invalid" in res_invalid.json()["detail"].lower()
    finally:
        graph_mod._orchestrator_instance = saved
