"""Pytest fixtures and configuration."""
import os
import sys
from pathlib import Path
import pytest
from starlette.testclient import TestClient

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure test environment variables are set before importing app
os.environ["LLM_PROVIDER"] = "mock"
os.environ["APP_ENV"] = "testing"
os.environ["ENABLE_GUARDRAILS"] = "true"

from src.main import app
from src.core.mock_db import get_mock_db
from src.core.graph import get_orchestrator
from src.agents.knowledge import get_retriever


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
