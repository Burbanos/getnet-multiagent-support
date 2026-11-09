"""Tests for GET /agents introspection endpoint generated from code."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.config import settings
from src.core.graph import KNOWLEDGE_TOOLS, SUPPORT_TOOLS
from src.tools.supervisor_tools import SUPERVISOR_TOOLS

BANNED_NAMES = [
    "HardwareSpecialist",
    "WebSearchSpecialist",
    "CustomerSupportSpecialist",
    "HumanOversightSpecialist",
    "KnowledgeSpecialist",
    "regex_safety_evaluator",
    "sanitize_pii",
    "Gemini Flash",
]


def test_agents_endpoint_tools_match_code_lists(client: TestClient) -> None:
    """Validate agents and tools in GET /agents match the actual code lists."""
    response = client.get("/agents")
    assert response.status_code == 200
    data = response.json()

    assert data.get("architecture") == "LangGraph supervisor with specialist sub-agents"
    assert data.get("checkpointer") == "SqliteSaver (thread user_id:session_id)"

    agents_by_name = {a["name"]: a for a in data.get("agents", [])}

    assert "SupervisorAgent" in agents_by_name
    assert agents_by_name["SupervisorAgent"]["tools"] == [t.name for t in SUPERVISOR_TOOLS]
    assert agents_by_name["SupervisorAgent"]["prompt"] == "src/prompts/supervisor.md"

    assert "KnowledgeAgent" in agents_by_name
    assert agents_by_name["KnowledgeAgent"]["tools"] == [t.name for t in KNOWLEDGE_TOOLS]
    assert agents_by_name["KnowledgeAgent"]["prompt"] == "src/prompts/knowledge_agent.md"

    assert "SupportAgent" in agents_by_name
    assert agents_by_name["SupportAgent"]["tools"] == [t.name for t in SUPPORT_TOOLS]
    assert agents_by_name["SupportAgent"]["prompt"] == "src/prompts/support_agent.md"

    assert "GuardrailAgent" in agents_by_name
    assert agents_by_name["GuardrailAgent"]["tools"] == []
    assert agents_by_name["GuardrailAgent"]["runs_before"] == "supervisor"
    assert agents_by_name["GuardrailAgent"]["uses_llm"] is settings.GUARDRAIL_CLASSIFIER_ENABLED

    all_tools = [*SUPERVISOR_TOOLS, *KNOWLEDGE_TOOLS, *SUPPORT_TOOLS]
    tools_rows = {t["name"]: t for t in data.get("tools", [])}
    assert set(tools_rows) == {t.name for t in all_tools}

    for t in all_tools:
        row = tools_rows[t.name]
        assert row["args"] == sorted(t.args)
        assert row["description"] == (t.description or "").strip().splitlines()[0]


def test_agents_endpoint_models_from_settings(client: TestClient) -> None:
    """Validate models reported by GET /agents come dynamically from settings."""
    response = client.get("/agents")
    assert response.status_code == 200
    data = response.json()

    models = data.get("models", {})
    assert models.get("primary") == settings.LLM_MODEL
    assert models.get("fallback") == (settings.LLM_FALLBACK_MODEL or None)


def test_agents_endpoint_no_fictional_names_or_memorysaver(client: TestClient) -> None:
    """Ensure no hand-written fictional names, MemorySaver, or data/ appear in /agents."""
    response = client.get("/agents")
    assert response.status_code == 200
    txt = response.text

    for banned in BANNED_NAMES:
        assert banned not in txt, f"Banned name {banned} found in /agents response"

    assert "MemorySaver" not in txt, "MemorySaver should not appear in /agents response"
    assert "data/" not in txt, "Path data/ should not appear in /agents response"
