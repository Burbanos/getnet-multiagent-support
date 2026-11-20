"""Offline tests for eval turn layer metadata, layer_latency_ms, resume guards, and rejected_drafts isolation."""
from __future__ import annotations

import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import MemorySaver
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import src.main as app_main
from src.config import JsonFormatter, settings
from src.core import tracing
from src.core.graph import OrchestrationGraph
from src.eval.__main__ import main as eval_cli_main
from src.eval.runner import run_eval
from tests.fakes import ScriptedChatModel


def _tc(name: str, args: dict[str, Any]) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}"}])


def _plan(lang: str = "en", code_source: str = "none", delegate: str = "support") -> AIMessage:
    return _tc(
        "TurnPlan",
        {
            "reply_language": lang,
            "scope": "support",
            "escalation_request": "none",
            "action_confirmation": "none",
            "code_source": code_source,
            "steps": [{"goal": "Answer settlement", "delegate": delegate}],
        },
    )


def _ver_model(verdicts_seq: list[list[dict[str, Any]]]) -> ScriptedChatModel:
    return ScriptedChatModel(responses=[_tc("Verification", {"verdicts": vs}) for vs in verdicts_seq])


def test_run_eval_records_layers_latencies_coverage_gate_and_rejected_drafts(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(settings, "PLANNER_ENABLED", True)
    monkeypatch.setattr(settings, "VERIFIER_ENABLED", True)
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", True)
    monkeypatch.setattr(settings, "PLAN_COVERAGE_ENABLED", True)

    case = {
        "id": "e_layers_1",
        "category": "support",
        "lang": "en",
        "official": False,
        "offline": False,
        "turns": ["How much did I sell yesterday?"],
        "expect": {
            "agents": ["SupportAgent"],
            "tools_all": ["get_settlement_status"],
            "tools_none": [],
            "escalate": False,
            "priority": None,
            "blocked": False,
            "gold_urls": [],
            "facts_any": [],
            "facts_none": [],
            "abstain": None,
        },
    }

    chat = ScriptedChatModel(
        responses=[
            _tc("ask_support_agent", {"request": "vendas de ontem"}),
            _tc("get_settlement_status", {}),
            AIMessage(content="Vendas de ontem: R$ 3.367,20."),
            AIMessage(content="RASCUNHO-REPROVADO-1 com informação errada."),
            AIMessage(content="Suas vendas de ontem somaram R$ 3.367,20 com depósito previsto para hoje."),
        ]
    )
    rw = ScriptedChatModel(
        responses=[AIMessage(content="Yesterday's sales totaled R$ 3.367,20, scheduled for deposit today.")]
    )

    def _factory() -> OrchestrationGraph:
        return OrchestrationGraph(
            chat_model=chat,
            planner_model=ScriptedChatModel(responses=[_plan("en", code_source="terminal_screen")]),
            verifier_model=_ver_model(
                [
                    [{"step": 1, "verdict": "unsupported_claim", "note": "bad claim"}],
                    [{"step": 1, "verdict": "answered", "note": ""}],
                ]
            ),
            rewrite_model=rw,
            checkpointer=MemorySaver(),
        )

    out_file = tmp_path / "runs" / "layers.jsonl"
    summary = run_eval([case], out_file, "layers", orchestrator_factory=_factory, sleep_s=0)
    assert summary["ok"] == 1

    rec = json.loads(out_file.read_text(encoding="utf-8").splitlines()[0])
    t = rec["turns"][0]
    assert t["layers"] == {"planner": True, "verifier": True, "language": True, "plan_coverage": True}
    assert t["coverage"] == {"status": "complete", "missing": [], "retries": 0}
    assert t["tool_gate"] == {"code_source": "terminal_screen", "removed_tools": ["diagnose_declined_transaction"]}
    assert t["rejected_drafts"] == ["RASCUNHO-REPROVADO-1 com informação errada."]
    assert "RASCUNHO-REPROVADO-1" not in t["response"]
    assert isinstance(t["layer_latency_ms"]["verifier"], (int, float))
    assert isinstance(t["layer_latency_ms"]["language"], (int, float))
    assert "latency_ms" not in t["verification"]
    assert "latency_ms" not in t["language"]


def test_run_eval_sets_null_layer_latencies_when_disabled(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(settings, "PLANNER_ENABLED", True)
    monkeypatch.setattr(settings, "VERIFIER_ENABLED", False)
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)
    monkeypatch.setattr(settings, "PLAN_COVERAGE_ENABLED", False)

    case = {"id": "e_off", "category": "support", "lang": "pt", "official": False, "offline": False, "turns": ["Oi"], "expect": {}}
    chat = ScriptedChatModel(responses=[AIMessage(content="Olá!")])

    out_file = tmp_path / "runs" / "off.jsonl"
    run_eval(
        [case],
        out_file,
        "off",
        orchestrator_factory=lambda: OrchestrationGraph(
            chat_model=chat,
            planner_model=ScriptedChatModel(responses=[_plan("pt")]),
            checkpointer=MemorySaver(),
        ),
        sleep_s=0,
    )
    t = json.loads(out_file.read_text(encoding="utf-8").splitlines()[0])["turns"][0]
    assert t["layers"] == {"planner": True, "verifier": False, "language": False, "plan_coverage": False}
    assert t["layer_latency_ms"] == {"verifier": None, "language": None}
    assert "latency_ms" not in t["verification"]
    assert "latency_ms" not in t["language"]


def test_resume_with_different_layers_refused_and_cli_exits_nonzero(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setattr(settings, "PLANNER_ENABLED", True)
    monkeypatch.setattr(settings, "VERIFIER_ENABLED", True)
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", True)
    monkeypatch.setattr(settings, "PLAN_COVERAGE_ENABLED", True)

    cpath = tmp_path / "cases.jsonl"
    base_exp = {
        "agents": None,
        "tools_all": [],
        "tools_none": [],
        "escalate": False,
        "priority": None,
        "blocked": False,
        "gold_urls": [],
        "facts_any": [],
        "facts_none": [],
        "abstain": None,
    }
    cases = [
        {"id": "c1", "category": "support", "lang": "pt", "official": False, "offline": False, "turns": ["Oi"], "expect": dict(base_exp)},
        {"id": "c2", "category": "support", "lang": "pt", "official": False, "offline": False, "turns": ["Tchau"], "expect": dict(base_exp)},
    ]
    cpath.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    runs_dir = tmp_path / "runs"
    out_file = runs_dir / "mix.jsonl"

    run_eval(
        [cases[0]],
        out_file,
        "mix",
        orchestrator_factory=lambda: OrchestrationGraph(
            chat_model=ScriptedChatModel(responses=[AIMessage(content="Resposta em português.")]),
            planner_model=ScriptedChatModel(responses=[_plan("pt", delegate="none")]),
            verifier_model=_ver_model([[{"step": 1, "verdict": "answered", "note": ""}]]),
            checkpointer=MemorySaver(),
        ),
        sleep_s=0,
    )
    snapshot_text = out_file.read_text(encoding="utf-8")

    monkeypatch.setattr(settings, "VERIFIER_ENABLED", False)
    with pytest.raises(ValueError, match="layers"):
        run_eval(cases, out_file, "mix", sleep_s=0)
    assert out_file.read_text(encoding="utf-8") == snapshot_text

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "fake-key-for-cli-guard")
    monkeypatch.setattr(
        sys,
        "argv",
        ["eval", "run", "--run-id", "mix", "--runs-dir", str(runs_dir), "--cases", str(cpath)],
    )
    code = eval_cli_main()
    assert code != 0
    assert out_file.read_text(encoding="utf-8") == snapshot_text


def test_rejected_drafts_never_leak_to_chat_response_logs_or_spans(monkeypatch: Any) -> None:
    monkeypatch.setattr(settings, "LANGUAGE_ENFORCEMENT_ENABLED", False)
    exporter = InMemorySpanExporter()
    tracing.configure_tracing(exporter, simple=True)
    log_records: list[str] = []

    class _Cap(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            log_records.append(JsonFormatter().format(record))

    lg = logging.getLogger("multiagent")
    cap = _Cap()
    lg.addHandler(cap)

    draft_marker = "SECRET-DRAFT-ZQ-9988"

    class _RejectOnce(ScriptedChatModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            idx = len(self.received)
            self.received.append(list(messages))
            v = {"step": 1, "verdict": "unsupported_claim" if idx == 0 else "answered", "note": "reject" if idx == 0 else ""}
            return ChatResult(generations=[ChatGeneration(message=_tc("Verification", {"verdicts": [v]}))])

    chat = ScriptedChatModel(
        responses=[
            _tc("ask_support_agent", {"request": "vendas"}),
            _tc("get_settlement_status", {}),
            AIMessage(content="R$ 3.367,20."),
            AIMessage(content=f"Rascunho {draft_marker} sem apoio."),
            AIMessage(content="Suas vendas somam R$ 3.367,20."),
        ]
    )
    orch = OrchestrationGraph(
        chat_model=chat,
        planner_model=ScriptedChatModel(responses=[_plan("pt")]),
        verifier_model=_RejectOnce(),
        checkpointer=MemorySaver(),
    )
    old_get = app_main.get_orchestrator
    app_main.get_orchestrator = lambda: orch
    try:
        with TestClient(app_main.app) as client:
            resp = client.post(
                "/chat",
                json={"message": "Quanto vendi?", "session_id": "s-leak-check"},
                headers={"X-API-Key": "getnet-dev-key"},
            )
    finally:
        app_main.get_orchestrator = old_get
        lg.removeHandler(cap)
        spans = exporter.get_finished_spans()
        tracing.shutdown_tracing()

    assert resp.status_code == 200
    body = resp.json()
    meta = body["metadata"]
    assert "rejected_drafts" not in json.dumps(body)
    assert draft_marker not in resp.text
    assert meta["coverage"] == {"status": "complete", "missing": [], "retries": 0}
    assert meta["tool_gate"] == {"code_source": "none", "removed_tools": []}
    assert not any(draft_marker in line for line in log_records)
    assert not any(draft_marker in json.dumps(dict(s.attributes or {}), ensure_ascii=False) for s in spans)

    snap = orch.graph.get_state({"configurable": {"thread_id": "cliente1988:s-leak-check"}})
    assert (snap.values or {}).get("rejected_drafts") == [f"Rascunho {draft_marker} sem apoio."]
