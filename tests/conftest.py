"""Pytest fixtures and configuration."""
import os
import sys
import tempfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure test environment variables are set before importing app
_test_tmp_dir = tempfile.mkdtemp(prefix="getnet_test_tickets_")
os.environ["TICKETS_DB_PATH"] = str(Path(_test_tmp_dir) / "tickets.db")
os.environ["LLM_PROVIDER"] = "mock"
os.environ["APP_ENV"] = "testing"
os.environ["ENABLE_GUARDRAILS"] = "true"

from src.agents.knowledge import get_retriever
from src.core.graph import get_orchestrator
from src.core.mock_db import get_mock_db
from src.main import app


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient session fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def orchestrator():
    """Singleton multi-agent orchestrator fixture."""
    return get_orchestrator()


@pytest.fixture(scope="session")
def mock_db():
    """Database fixture."""
    return get_mock_db()


@pytest.fixture(scope="session")
def retriever():
    """Knowledge retriever fixture."""
    return get_retriever()


@pytest.fixture(autouse=True)
def mock_web_search(monkeypatch):
    """Mock web search tool across all tests so no tests perform network I/O."""
    from src.tools import agent_tools, web_search

    def fake_web_search(query: str, max_results: int = 3):
        lower = query.lower()
        if "porto alegre" in lower:
            results = [{
                "title": "Previsão do Tempo em Porto Alegre",
                "snippet": "A previsão do tempo em Porto Alegre para amanhã indica sol com algumas nuvens e máxima de 28°C.",
                "url": "https://weather.example.com/porto-alegre"
            }]
        elif "euro" in lower:
            results = [{
                "title": "Cotação do Euro Hoje",
                "snippet": "O Euro comercial está cotado a R$ 6,10 para compra e R$ 6,12 para venda.",
                "url": "https://finance.example.com/euro"
            }]
        else:
            results = [{
                "title": f"Resultado de busca: {query}",
                "snippet": f"Informações atualizadas sobre {query}.",
                "url": "https://search.example.com"
            }]
        return {
            "status": "success",
            "query": query,
            "count": len(results),
            "results": results
        }

    monkeypatch.setattr(web_search, "web_search_tool", fake_web_search)
    monkeypatch.setattr(agent_tools, "web_search_tool", fake_web_search)
