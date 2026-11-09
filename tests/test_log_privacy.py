"""Offline tests verifying that conversation and exception text are never logged (Phase 9F)."""
from __future__ import annotations

import logging
import sys
import types
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

import src.main as app_main
import src.rag.retriever as rag_retriever
from src.config import JsonFormatter, logger, settings
from src.core import tickets_db
from src.core.graph import OrchestrationGraph
from src.core.llm import LLMUnavailableError
from src.core.log_context import exc_brief
from src.tools import agent_tools
from tests.fakes import ScriptedChatModel

MARK = "ZQXLOGMARK"


class _Capture(logging.Handler):
    def __init__(self, fmt: logging.Formatter) -> None:
        super().__init__(logging.DEBUG)
        self.setFormatter(fmt)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


@pytest.fixture
def log_capture() -> Generator[list[str], None, None]:
    root_mp = logging.getLogger("multiagent")
    cap = _Capture(JsonFormatter())
    old_level = root_mp.level
    root_mp.addHandler(cap)
    root_mp.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(cap)
    try:
        yield cap.lines
    finally:
        root_mp.removeHandler(cap)
        logging.getLogger().removeHandler(cap)
        root_mp.setLevel(old_level)


class RaisingFake(ScriptedChatModel):
    responses: list[Any] = Field(default_factory=list)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.received.append(list(messages))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return ChatResult(generations=[ChatGeneration(message=r)])


def test_exc_brief_has_no_message(log_capture: list[str]) -> None:
    try:
        raise RuntimeError(f"fatal error: {MARK}")
    except RuntimeError as exc:
        brief = exc_brief(exc)
        logger.error(f"Captured: {brief}")
    assert brief.startswith("RuntimeError")
    assert MARK not in brief
    assert len(log_capture) > 0
    assert all(MARK not in line for line in log_capture)


def test_tool_logs_have_no_conversation_text(
    log_capture: list[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class BadRetriever:
        def search(self, q: str) -> None:
            raise RuntimeError(f"embedding failed for '{q}'")

    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: BadRetriever())

    class RaisingDDGS:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def text(self, q: str, max_results: int = 3) -> None:
            raise RuntimeError(f"https://html.duckduckgo.com/html?q={q}")

    ddgs_mod = types.ModuleType("ddgs")
    ddgs_mod.DDGS = RaisingDDGS  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ddgs", ddgs_mod)

    monkeypatch.setattr(settings, "TICKETS_DB_PATH", str(tmp_path / "tickets.db"))
    tickets_db.reset_tickets_repository()

    try:
        cfg = {"configurable": {"user_id": "cliente1988", "session_id": "s", "transcript": []}}

        agent_tools.search_knowledge_base.invoke({"query": f"taxa {MARK}"})
        agent_tools.search_web.invoke({"query": f"clima {MARK}"})
        agent_tools.diagnose_declined_transaction.invoke({"error_code": MARK}, config=cfg)
        agent_tools.diagnose_terminal.invoke({"serial_number": MARK}, config=cfg)
        agent_tools.escalate_to_human.invoke({"reason": f"cliente pediu {MARK}", "priority": "standard"}, config=cfg)

        assert len(log_capture) > 0
        assert all(MARK not in line for line in log_capture)
        joined = "\n".join(log_capture)
        assert "query_chars=" in joined
        assert "reason_chars=" in joined
    finally:
        tickets_db.reset_tickets_repository()


def test_provider_error_text_not_logged(log_capture: list[str]) -> None:
    primary = RaisingFake(responses=[RuntimeError(f"primary failure {MARK}")])
    fallback = RaisingFake(responses=[RuntimeError(f"fallback failure {MARK}")])
    orch = OrchestrationGraph(chat_model=primary, fallback_model=fallback)
    with pytest.raises(LLMUnavailableError):
        orch.run_sync(user_id="cliente1988", session_id="s1", message="oi")
    assert len(log_capture) > 0
    assert all(MARK not in line for line in log_capture)


def test_internal_error_text_not_logged(log_capture: list[str]) -> None:
    call = AIMessage(content="", tool_calls=[{"name": "ask_support_agent", "id": "s1", "args": {"request": "saldo"}}])
    orch = OrchestrationGraph(chat_model=RaisingFake(responses=[call]))

    def boom(*a: Any, **k: Any) -> None:
        raise KeyError(f"lookup {MARK}")

    orch.support_agent.run = boom
    st = orch.run_sync(user_id="cliente1988", session_id="g4", message="saldo?")
    assert st.error == "internal_error"
    assert len(log_capture) > 0
    assert all(MARK not in line for line in log_capture)
    joined = "\n".join(log_capture)
    assert "KeyError at " in joined


def test_api_unhandled_error_text_not_logged(
    log_capture: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "API_KEYS", "")

    class BrokenOrchestrator:
        def run_sync(self, *a: Any, **k: Any) -> None:
            raise RuntimeError(f"unexpected {MARK}")

    monkeypatch.setattr(app_main, "get_orchestrator", lambda: BrokenOrchestrator())
    with TestClient(app_main.app, raise_server_exceptions=False) as client:
        resp = client.post("/chat", json={"message": "oi"}, headers={"X-API-Key": "getnet-dev-key"})
    assert resp.status_code == 500
    assert len(log_capture) > 0
    assert all(MARK not in line for line in log_capture)
