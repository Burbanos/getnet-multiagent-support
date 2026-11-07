"""Tests for token usage accounting and tools without invented values (Phase 2E)."""
import json
from unittest.mock import patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import src.core.graph as graph_mod
from src.core.graph import OrchestrationGraph
from src.core.mock_db import get_mock_db
from src.main import app
from src.tools.balance_tools import get_declined_transaction_details
from src.tools.terminal_tools import diagnose_terminal_connectivity
from tests.fakes import ScriptedChatModel


def _usage(i: int, o: int) -> dict[str, int]:
    return {"input_tokens": i, "output_tokens": o, "total_tokens": i + o}


def _ai(content: str = "", calls: list | None = None, u: dict | None = None) -> AIMessage:
    kw = {"usage_metadata": u} if u else {}
    return AIMessage(content=content, tool_calls=calls or [], **kw)


def _call(name: str, args: dict, cid: str) -> list[dict]:
    return [{"name": name, "args": args, "id": cid}]


def test_token_accumulation_supervisor_and_support():
    """Supervisor and SupportAgent token usage sums correctly into tokens and tokens_by_agent."""
    fake = ScriptedChatModel(responses=[
        _ai(calls=_call("ask_support_agent", {"request": "settlement"}, "t1"), u=_usage(100, 10)),
        _ai(calls=_call("get_settlement_status", {}, "t2"), u=_usage(50, 5)),
        _ai("S", u=_usage(60, 20)),
        _ai("FINAL", u=_usage(130, 40)),
    ])
    orch = OrchestrationGraph(chat_model=fake)
    st = orch.run_sync(user_id="cliente1988", message="extrato", session_id="tok-turn1")

    assert st.tokens == {"input_tokens": 340, "output_tokens": 75, "total_tokens": 415}
    assert st.tokens_by_agent == {
        "SupervisorAgent": _usage(230, 50),
        "SupportAgent": _usage(110, 25),
    }
    assert st.estimated_cost_usd is None


def test_tokens_per_turn_counts_only_current_turn():
    """Tokens are reset per turn and count only AIMessages produced in the current turn."""
    fake = ScriptedChatModel(responses=[
        _ai("Turn 1 response", u=_usage(100, 20)),
        _ai("Turn 2 response", u=_usage(250, 15)),
    ])
    orch = OrchestrationGraph(chat_model=fake)
    st1 = orch.run_sync(user_id="cliente1988", message="primeira", session_id="tok-multiturn")
    assert st1.tokens == {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}

    st2 = orch.run_sync(user_id="cliente1988", message="segunda", session_id="tok-multiturn")
    assert st2.tokens == {"input_tokens": 250, "output_tokens": 15, "total_tokens": 265}
    assert st2.tokens_by_agent == {"SupervisorAgent": _usage(250, 15)}


def test_tokens_null_when_unmeasured():
    """When no AIMessage carries usage_metadata, tokens and tokens_by_agent are None."""
    fake = ScriptedChatModel(responses=[_ai("sem metadata de tokens")])
    orch = OrchestrationGraph(chat_model=fake)
    st = orch.run_sync(user_id="cliente1988", message="oi", session_id="tok-none")

    assert st.tokens is None
    assert st.tokens_by_agent is None
    assert st.estimated_cost_usd is None


def test_chat_endpoint_reports_tokens_in_metadata():
    """FastAPI /chat endpoint exposes tokens and tokens_by_agent in response metadata."""
    fake = ScriptedChatModel(responses=[_ai("tudo certo", u=_usage(15, 5))])
    with patch.object(graph_mod, "_orchestrator_instance", OrchestrationGraph(chat_model=fake)):
        client = TestClient(app)
        res = client.post("/chat", json={"message": "ola", "user_id": "cliente1988"}, headers={"X-API-Key": "getnet-dev-key"})
        assert res.status_code == 200
        meta = res.json().get("metadata", {})
        assert meta.get("tokens") == {"input_tokens": 15, "output_tokens": 5, "total_tokens": 20}
        assert meta.get("tokens_by_agent") == {"SupervisorAgent": _usage(15, 5)}
        assert meta.get("estimated_cost_usd") is None


def test_declined_transaction_no_declines_and_no_code():
    """When merchant has no declined transaction and error_code is not given, return nulls."""
    db = get_mock_db()
    base = db.get_user("cliente1988") or {}
    no_declines = dict(base, recent_transactions=[t for t in base.get("recent_transactions", []) if t.get("status") != "DECLINED"])

    with patch.object(db, "get_user", return_value=no_declines):
        out = get_declined_transaction_details(user_id="cliente1988", error_code=None)
        assert out["status"] == "success"
        assert out["latest_declined_transaction"] is None
        assert out["queried_code"] is None
        assert out["code_known"] is None
        assert out["code_details"] is None


def test_declined_transaction_unknown_code():
    """Unknown code outside the catalog returns code_known=False and code_details=None."""
    out = get_declined_transaction_details(user_id="cliente1988", error_code="999")
    assert out["status"] == "success"
    assert out["queried_code"] == "999"
    assert out["code_known"] is False
    assert out["code_details"] is None


def test_declined_transaction_known_code():
    """Known code in catalog returns code_known=True and valid code_details."""
    out = get_declined_transaction_details(user_id="cliente1988", error_code="51")
    assert out["status"] == "success"
    assert out["queried_code"] == "51"
    assert out["code_known"] is True
    details = out["code_details"]
    assert details is not None
    assert details["error_code"] == "51"
    assert "Saldo" in details["title"]
    assert "banco emissor" in details["cause"].lower()
    assert len(details["recommended_action"]) > 10


def test_diagnose_terminal_healthy():
    """Healthy terminal reports no issues and does not hardcode other models or operators."""
    db = get_mock_db()
    base = db.get_user("cliente1988") or {}
    term = dict((base.get("terminals") or [{}])[0])
    healthy = dict(
        term,
        model="Get Mini",
        sim_operator="TIM",
        signal_level="forte",
        wifi_connected=True,
        sim_status="ativo",
        status="online",
        connection_type="Wi-Fi",
    )

    with patch.object(db, "get_user", return_value=dict(base, terminals=[healthy])):
        out = diagnose_terminal_connectivity(user_id="cliente1988")
        assert out["status"] == "success"
        assert out["terminal_model"] == "Get Mini"
        assert out["sim_operator"] == "TIM"
        assert out["diagnosis"] == "Nenhum problema de conectividade identificado na telemetria do terminal."
        serialized = json.dumps(out, ensure_ascii=False)
        for bad_word in ("Get Smart", "Claro", "Vivo", "instável", "fraco"):
            assert bad_word not in serialized


def test_diagnose_terminal_weak_signal_recommends_wifi():
    """Weak signal without Wi-Fi recommends Wi-Fi and the terminal's actual operator."""
    db = get_mock_db()
    base = db.get_user("cliente1988") or {}
    term = dict((base.get("terminals") or [{}])[0])
    weak = dict(
        term,
        model="Get Mini",
        sim_operator="TIM",
        signal_level="fraco",
        wifi_connected=False,
        sim_status="ativo",
    )

    with patch.object(db, "get_user", return_value=dict(base, terminals=[weak])):
        out = diagnose_terminal_connectivity(user_id="cliente1988")
        assert out["status"] == "success"
        assert out["terminal_model"] == "Get Mini"
        assert out["diagnosis"] == "Sinal móvel baixo e Wi-Fi desconectado."
        steps = " ".join(out.get("troubleshooting_steps") or [])
        assert "Wi-Fi" in steps
        assert "TIM" in steps
        serialized = json.dumps(out, ensure_ascii=False)
        for bad_word in ("Get Smart", "Claro", "Vivo"):
            assert bad_word not in serialized
