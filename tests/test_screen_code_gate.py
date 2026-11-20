"""Offline tests for planner code_source gate and diagnose_terminal screen_error_code."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from src.config import JsonFormatter, settings
from src.core.graph import OrchestrationGraph
from src.tools.agent_tools import diagnose_declined_transaction, diagnose_terminal
from tests.fakes import ScriptedChatModel


def _tc(name: str, args: dict[str, Any]) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"}])


def _plan(code_source: str | None = None, delegate: str = "support") -> AIMessage:
    args: dict[str, Any] = {
        "reply_language": "pt",
        "scope": "support",
        "escalation_request": "none",
        "action_confirmation": "none",
        "steps": [{"goal": "Investigate code", "delegate": delegate}],
    }
    if code_source is not None:
        args["code_source"] = code_source
    return _tc("TurnPlan", args)


def _run_code_turn(code_source: str | None, session_id: str, monkeypatch: Any):
    monkeypatch.setattr(settings, "VERIFIER_ENABLED", False)
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)
    seen_bound_tools: list[list[str]] = []

    class RecordingModel(ScriptedChatModel):
        def bind_tools(self, tools, **kwargs):
            seen_bound_tools.append([getattr(t, "name", str(t)) for t in tools])
            return self

    chat = RecordingModel(
        responses=[
            _tc("ask_support_agent", {"request": "Verifique o código 51 informado"}),
            _tc("diagnose_declined_transaction", {"code_context": "declined_sale", "error_code": "51"}),
            AIMessage(content="Consulta de suporte concluída."),
            AIMessage(content="Consultei o código informado nos registros de suporte."),
        ]
    )
    orch = OrchestrationGraph(
        chat_model=chat,
        planner_model=ScriptedChatModel(responses=[_plan(code_source)]),
        checkpointer=MemorySaver(),
    )
    st = orch.run_sync("cliente1988", "Apareceu o código 51, o que significa?", session_id=session_id)
    snap = orch.graph.get_state({"configurable": {"thread_id": f"cliente1988:{session_id}"}})
    ev_blob = json.dumps((snap.values or {}).get("turn_evidence") or [], ensure_ascii=False)
    return st, ev_blob, seen_bound_tools


def test_terminal_screen_and_app_hide_decline_tool_from_binding_and_execution(monkeypatch: Any) -> None:
    for src in ("terminal_screen", "app"):
        st, ev_blob, bound_calls = _run_code_turn(src, f"s-gate-{src}", monkeypatch)
        assert st.plan is not None and st.plan["code_source"] == src
        assert st.tool_gate == {
            "code_source": src,
            "removed_tools": ["diagnose_declined_transaction"],
        }
        # Supervisor bind + gated support bind (second bind_tools call)
        support_bound = bound_calls[-1]
        assert "diagnose_declined_transaction" not in support_bound
        assert "diagnose_terminal" in support_bound
        assert "not available" in ev_blob
        assert "falta de saldo" not in ev_blob
        assert "TXN-" not in ev_blob


def test_declined_sale_and_default_code_source_keep_decline_tool(monkeypatch: Any) -> None:
    st_sale, ev_sale, bound_sale = _run_code_turn("declined_sale", "s-gate-sale", monkeypatch)
    assert st_sale.tool_gate == {"code_source": "declined_sale", "removed_tools": []}
    assert "diagnose_declined_transaction" in bound_sale[-1]
    assert "falta de saldo" in ev_sale.lower()

    st_default, ev_default, bound_def = _run_code_turn(None, "s-gate-def", monkeypatch)
    assert (st_default.plan or {}).get("code_source") == "none"
    assert st_default.tool_gate == {"code_source": "none", "removed_tools": []}
    assert "diagnose_declined_transaction" in bound_def[-1]
    assert "falta de saldo" in ev_default.lower()


def test_no_valid_plan_sets_tool_gate_none_and_keeps_decline_tool(monkeypatch: Any) -> None:
    monkeypatch.setattr(settings, "PLANNER_ENABLED", False)
    monkeypatch.setattr(settings, "VERIFIER_ENABLED", False)
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)

    chat = ScriptedChatModel(
        responses=[
            _tc("ask_support_agent", {"request": "código 51"}),
            _tc("diagnose_declined_transaction", {"code_context": "declined_sale", "error_code": "51"}),
            AIMessage(content="Código 51 verificado."),
            AIMessage(content="Código 51 referente a venda recusada verificado."),
        ]
    )
    orch = OrchestrationGraph(chat_model=chat, checkpointer=MemorySaver())
    st = orch.run_sync("cliente1988", "Código 51?", session_id="s-gate-noplan")
    assert st.tool_gate is None
    assert "diagnose_declined_transaction" in st.tools_used


def test_diagnose_terminal_screen_error_code_and_log_privacy() -> None:
    cfg = {"configurable": {"user_id": "cliente1988"}}
    plain = json.loads(diagnose_terminal.invoke({}, config=cfg))
    assert "screen_error" not in plain

    secret_code = "SCR-ZQ-7821"
    logs: list[str] = []

    class _Cap(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            logs.append(JsonFormatter().format(record))

    lg = logging.getLogger("multiagent")
    cap = _Cap()
    lg.addHandler(cap)
    try:
        with_code = json.loads(diagnose_terminal.invoke({"screen_error_code": f" {secret_code} "}, config=cfg))
    finally:
        lg.removeHandler(cap)

    assert with_code["screen_error"] == {
        "code": secret_code,
        "catalogue": "not_available",
        "note": (
            "No catalogue of card machine screen codes is available to this assistant; "
            "the meaning of this code is unknown."
        ),
    }
    assert {k: v for k, v in with_code.items() if k != "screen_error"} == plain

    joined_logs = "\n".join(logs)
    assert "screen_error_code_given=True" in joined_logs
    assert secret_code not in joined_logs

    # Defense in depth still holds in diagnose_declined_transaction
    na = json.loads(
        diagnose_declined_transaction.invoke({"code_context": "terminal_screen", "error_code": "51"}, config=cfg)
    )
    assert na["status"] == "not_applicable"
