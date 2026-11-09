"""Unit tests for evaluation set v2, api_status check, observe_turn, judge passages, and CLI --cases."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.eval.__main__ import main as cli_main
from src.eval.cases import cases_sha256, load_cases
from src.eval.checks import evaluate_case
from src.eval.judge import build_judge_input
from src.eval.runner import observe_turn


def test_cases_v2_loads_and_v1_is_frozen() -> None:
    v2 = load_cases("data/eval/cases_v2.jsonl")
    v1 = load_cases("data/eval/cases.jsonl")
    assert len(v2) == 78
    assert sum(c["category"] == "public_data" for c in v2) == 11
    assert cases_sha256(v1) == "2d7d8e746a2322c2e61306f837b8176eabba838810b5a4f160584c433754ad07"
    assert cases_sha256(v2) == "e32b61a20c57fd3fb6c919b848339b56c6c57a7f7cf9b74959cb617f3b28bb10"


def test_api_status_validation(tmp_path: Path) -> None:
    v2 = load_cases("data/eval/cases_v2.jsonl")
    d02 = next(c for c in v2 if c["id"] == "d02")

    def make_case(expect_updates: dict[str, Any]) -> dict[str, Any]:
        c = json.loads(json.dumps(d02))
        for k, v in expect_updates.items():
            if v is None:
                c["expect"].pop(k, None)
            else:
                c["expect"][k] = v
        return c

    def assert_invalid(case_dict: dict[str, Any]) -> None:
        p = tmp_path / "case.jsonl"
        p.write_text(json.dumps(case_dict, ensure_ascii=False) + "\n", encoding="utf-8")
        with pytest.raises(ValueError):
            load_cases(p)

    # 1. unknown status in api_status
    assert_invalid(make_case({"api_status": {"get_weather_forecast": "maybe"}}))
    # 2. tool not in tools_all
    assert_invalid(make_case({"api_status": {"get_exchange_rate": "success"}}))
    # 3. tool is not an API tool
    assert_invalid(
        make_case({
            "tools_all": ["get_weather_forecast", "search_web"],
            "api_status": {"search_web": "success"},
        })
    )
    # 4. empty api_status dict
    assert_invalid(make_case({"api_status": {}}))
    # 5. api_status not a dict
    assert_invalid(make_case({"api_status": ["get_weather_forecast"]}))
    # 6. unknown key in expect
    assert_invalid(make_case({"extra_unknown_key": 123}))


def test_tools_ok_checks_api_status() -> None:
    v2 = load_cases("data/eval/cases_v2.jsonl")
    d02 = next(c for c in v2 if c["id"] == "d02")
    assert d02["expect"].get("api_status") == {"get_weather_forecast": "not_found"}

    def make_res(api_results: list[dict[str, Any]] | None) -> dict[str, Any]:
        turn = {
            "message": "Clima na cidade inexistente",
            "response": "Cidade não encontrada.",
            "agents_used": ["SupervisorAgent", "KnowledgeAgent"],
            "tools_used": ["get_weather_forecast"],
            "sources": [],
            "retrieved_docs": [],
            "web_results": [],
            "tool_results": [],
            "ticket_id": None,
            "ticket_priority": None,
            "is_safe": True,
            "handoff": None,
            "llm_model": "test-model",
            "tokens": None,
            "latency_ms": 1.0,
        }
        if api_results is not None:
            turn["api_results"] = api_results
        return {"id": "d02", "status": "ok", "turns": [turn]}

    # not_found -> True
    r_not_found = make_res([{"tool": "get_weather_forecast", "status": "not_found"}])
    assert evaluate_case(d02, r_not_found)["checks"]["tools_ok"] is True

    # success -> False
    r_success = make_res([{"tool": "get_weather_forecast", "status": "success"}])
    assert evaluate_case(d02, r_success)["checks"]["tools_ok"] is False

    # without api_results -> False
    r_empty = make_res([])
    assert evaluate_case(d02, r_empty)["checks"]["tools_ok"] is False
    r_none = make_res(None)
    assert evaluate_case(d02, r_none)["checks"]["tools_ok"] is False

    # A v1 case without api_status behaves identically with and without api_results
    v1 = load_cases("data/eval/cases.jsonl")
    k01 = next(c for c in v1 if c["id"] == "k01")
    r_k01_with = {
        "id": "k01",
        "status": "ok",
        "turns": [{
            "message": "Qual o prazo?",
            "response": "2 dias úteis.",
            "agents_used": ["SupervisorAgent", "KnowledgeAgent"],
            "tools_used": ["search_knowledge_base"],
            "sources": ["https://site.getnet.com.br/crediario/"],
            "retrieved_docs": [],
            "web_results": [],
            "api_results": [{"tool": "get_weather_forecast", "status": "success"}],
            "tool_results": [],
            "ticket_id": None,
            "ticket_priority": None,
            "is_safe": True,
            "handoff": None,
            "llm_model": "test-model",
            "tokens": None,
            "latency_ms": 1.0,
        }],
    }
    r_k01_without = json.loads(json.dumps(r_k01_with))
    del r_k01_without["turns"][0]["api_results"]
    assert evaluate_case(k01, r_k01_with)["checks"] == evaluate_case(k01, r_k01_without)["checks"]


def test_observe_turn_records_api_results() -> None:
    api = [
        {"tool": "get_exchange_rate", "status": "success", "source_url": "https://olinda/x", "buy": {"value": 5.5}},
        {"tool": "get_weather_forecast", "status": "unavailable", "source_url": None, "error": "timeout"},
    ]
    st = SimpleNamespace(
        agent_response="Resposta final",
        agents_used=["SupervisorAgent", "KnowledgeAgent"],
        tools_used=["get_exchange_rate"],
        sources=["https://olinda/x"],
        retrieved_docs=[],
        web_results=[],
        tool_results=[],
        ticket=None,
        escalation_ticket_id=None,
        is_safe=True,
        handoff=None,
        llm_model="test-model",
        tokens=None,
        api_results=api,
    )
    t = observe_turn(st, "Consulta", 12.5)
    assert "api_results" in t
    assert t["api_results"] == api
    assert t["api_results"][0] is not api[0]


def test_judge_sees_api_results() -> None:
    case = {
        "id": "d04",
        "category": "public_data",
        "turns": ["Qual o dólar?"],
        "expect": {
            "agents": ["KnowledgeAgent"],
            "tools_all": ["get_exchange_rate"],
            "tools_none": [],
            "escalate": False,
            "priority": None,
            "blocked": False,
            "gold_urls": [],
            "facts_any": [],
            "facts_none": [],
            "abstain": False,
            "api_status": {"get_exchange_rate": "success"},
        },
    }
    api = [
        {"tool": "get_exchange_rate", "status": "success", "source_url": "https://olinda/eur", "buy": {"value": 6.13}},
        {"tool": "get_weather_forecast", "status": "unavailable", "source_url": None, "error": "http_503"},
    ]
    turn = {
        "message": "Qual o dólar?",
        "response": "Cotação obtida: R$ 6,13.",
        "retrieved_docs": [],
        "web_results": [],
        "api_results": api,
        "tool_results": [],
    }
    result = {"id": "d04", "status": "ok", "turns": [turn]}
    payload = build_judge_input(case, result)
    data = json.loads(payload)

    passages = data.get("passages", [])
    assert len(passages) == 2
    assert passages[0]["url"] == "https://olinda/eur"
    assert json.loads(passages[0]["text"]) == api[0]
    assert passages[1]["url"] == ""
    assert json.loads(passages[1]["text"]) == api[1]

    assert "d04" not in payload
    assert "api_status" not in payload
    assert "public_data" not in payload


def test_cli_cases_option(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True)
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)

    v2_cases = load_cases("data/eval/cases_v2.jsonl")
    dummy_results = [{"id": c["id"], "status": "error", "error_type": "x", "turns": []} for c in v2_cases]
    (runs_dir / "test_run.jsonl").write_text(
        "\n".join(json.dumps(r) for r in dummy_results) + "\n",
        encoding="utf-8",
    )

    # 1. report with --cases data/eval/cases_v2.jsonl
    argv = [
        "python -m src.eval",
        "report",
        "--run-id",
        "test_run",
        "--runs-dir",
        str(runs_dir),
        "--out-dir",
        str(out_dir),
        "--cases",
        "data/eval/cases_v2.jsonl",
    ]
    monkeypatch.setattr(sys, "argv", argv)
    code = cli_main()
    assert code == 0

    report_json_path = out_dir / "eval_test_run.json"
    assert report_json_path.exists()
    report_data = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert report_data["cases_sha256"] == cases_sha256(v2_cases)
    assert report_data["cases_file"] == "data/eval/cases_v2.jsonl"
    assert report_data["n_cases"] == 78

    # 2. report with nonexistent --cases returns 1
    argv_bad = [
        "python -m src.eval",
        "report",
        "--run-id",
        "test_run",
        "--runs-dir",
        str(runs_dir),
        "--out-dir",
        str(out_dir),
        "--cases",
        str(tmp_path / "nonexistent.jsonl"),
    ]
    monkeypatch.setattr(sys, "argv", argv_bad)
    code_bad = cli_main()
    assert code_bad == 1
