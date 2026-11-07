"""Unit tests for evaluation runner, LLM judge, and judge metrics."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from src.config import settings
from src.core.llm import LLMNotConfiguredError, LLMUnavailableError
from src.eval.judge import (
    build_judge_input,
    judge_case,
    parse_judgment,
    run_judge,
    should_judge,
)
from src.eval.metrics import aggregate
from src.eval.runner import (
    load_results,
    observe_turn,
    run_case,
    run_eval,
)
from tests.fakes import ScriptedChatModel


def _sample_case(cid: str = "k01", **kwargs) -> dict:
    base = {
        "id": cid,
        "category": "knowledge",
        "lang": "pt",
        "official": False,
        "offline": False,
        "turns": ["Qual é o prazo de recebimento do crediário?"],
        "expect": {
            "agents": ["KnowledgeAgent"],
            "tools_all": ["search_knowledge_base"],
            "tools_none": [],
            "escalate": False,
            "priority": None,
            "blocked": False,
            "gold_urls": ["https://site.getnet.com.br/crediario/"],
            "facts_any": [["2 dias", "dois dias"]],
            "facts_none": [],
            "abstain": False,
        },
    }
    base.update(kwargs)
    return base


def _sample_state(**kwargs) -> SimpleNamespace:
    base = {
        "agent_response": "Receba em 2 dias úteis com crediário.",
        "agents_used": ["SupervisorAgent", "KnowledgeAgent"],
        "tools_used": ["search_knowledge_base"],
        "sources": ["https://site.getnet.com.br/crediario/"],
        "retrieved_docs": [{
            "url": "https://site.getnet.com.br/crediario/",
            "chunk_id": "chk-001",
            "score": 0.85,
            "text": "X" * 1500,
            "title": "Crediário",
        }],
        "tool_results": [{"agent": "KnowledgeAgent", "answer": "48x"}],
        "escalation_ticket_id": None,
        "ticket": None,
        "is_safe": True,
        "handoff": None,
        "llm_model": "gemini-3.5-flash",
        "tokens": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_observe_turn_truncation_and_fields():
    """Verify observe_turn returns exact keys and truncates retrieved doc texts to 600 chars."""
    state = _sample_state()
    turn = observe_turn(state, "Qual o prazo?", latency_ms=45.2)

    expected_keys = {
        "message", "response", "agents_used", "tools_used", "sources", "retrieved_docs",
        "tool_results", "ticket_id", "ticket_priority", "is_safe", "handoff", "llm_model",
        "tokens", "latency_ms",
    }
    assert set(turn.keys()) == expected_keys
    assert turn["latency_ms"] == 45.2
    assert len(turn["retrieved_docs"]) == 1
    doc = turn["retrieved_docs"][0]
    assert set(doc.keys()) == {"url", "chunk_id", "score", "text"}
    assert len(doc["text"]) == 600
    assert turn["tool_results"] == [{"agent": "KnowledgeAgent", "answer": "48x"}]


def test_run_case_multi_turn_and_sanitized_errors():
    """Verify run_case maintains session across turns and masks raw exception messages."""
    case = _sample_case("m01", turns=["Turno 1", "Turno 2"])

    calls = []

    class FakeOrch:
        def run_sync(self, user_id, message, session_id):
            calls.append((user_id, session_id, message))
            return _sample_state()

    orch = FakeOrch()
    res = run_case(case, orch, run_id="test-run")

    assert res["status"] == "ok"
    assert len(res["turns"]) == 2
    assert len(calls) == 2
    assert calls[0][1] == calls[1][1] == "eval-test-run-m01"

    # Error case: exception message must not leak
    class ErrorOrch:
        def run_sync(self, user_id, message, session_id):
            raise LLMUnavailableError("SECRET_QUOTA_KEY_123")

    err_res = run_case(case, ErrorOrch(), run_id="test-run")
    assert err_res["status"] == "error"
    assert err_res["error_type"] == "LLMUnavailableError"
    assert "SECRET_QUOTA_KEY_123" not in json.dumps(err_res)


def test_run_eval_resumption_and_temp_tickets_db(tmp_path: Path):
    """Verify run_eval resumes from existing results and keeps tickets DB outside data/."""
    out_file = tmp_path / "runs" / "res.jsonl"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Pre-populate with one ok case and one error case
    pre = [
        {"id": "c01", "status": "ok", "error_type": None, "turns": []},
        {"id": "c02", "status": "error", "error_type": "TimeoutError", "turns": []},
    ]
    out_file.write_text("".join(json.dumps(x) + "\n" for x in pre), encoding="utf-8")

    cases = [_sample_case("c01"), _sample_case("c02"), _sample_case("c03")]
    called_sessions = []
    observed_ticket_paths = []

    class FakeOrch:
        def run_sync(self, user_id, message, session_id):
            called_sessions.append(session_id)
            observed_ticket_paths.append(settings.TICKETS_DB_PATH)
            return _sample_state()

    orig_tickets = settings.TICKETS_DB_PATH
    summary = run_eval(
        cases=cases,
        results_path=out_file,
        run_id="run-resume",
        orchestrator_factory=FakeOrch,
        sleep_s=0,
    )

    # c01 skipped, c02 re-run, c03 run
    assert summary["skipped"] == 1
    assert summary["attempted"] == 2
    assert called_sessions == ["eval-run-resume-c02", "eval-run-resume-c03"]

    loaded = load_results(out_file)
    assert len(loaded) == 3
    assert loaded["c02"]["status"] == "ok"

    # Tickets DB isolated in temp dir
    assert settings.TICKETS_DB_PATH == orig_tickets
    for p in observed_ticket_paths:
        assert "data" not in p
        assert "eval_tickets_" in p


def test_run_eval_stops_on_three_consecutive_quota_errors(tmp_path: Path):
    """Verify run_eval aborts when 3 consecutive LLMUnavailableErrors occur."""
    out_file = tmp_path / "runs" / "quota.jsonl"
    cases = [_sample_case(f"q0{i}") for i in range(1, 6)]
    calls = []

    class QuotaOrch:
        def run_sync(self, user_id, message, session_id):
            calls.append(session_id)
            raise LLMUnavailableError("Quota exhausted")

    summary = run_eval(
        cases=cases,
        results_path=out_file,
        run_id="quota-run",
        orchestrator_factory=QuotaOrch,
        sleep_s=0,
    )

    assert len(calls) == 3
    assert summary["stopped_early"] is True
    assert summary["errors"] == 3


def test_run_eval_reraises_llm_not_configured_error(tmp_path: Path):
    """Verify run_eval lets LLMNotConfiguredError propagate immediately."""
    out_file = tmp_path / "runs" / "noconf.jsonl"
    cases = [_sample_case("nc01")]

    class NoKeyOrch:
        def run_sync(self, user_id, message, session_id):
            raise LLMNotConfiguredError("GEMINI_API_KEY is missing")

    with pytest.raises(LLMNotConfiguredError):
        run_eval(
            cases=cases,
            results_path=out_file,
            run_id="nokey",
            orchestrator_factory=NoKeyOrch,
            sleep_s=0,
        )


def test_build_judge_input_isolation():
    """Verify judge input strictly excludes expectation labels, category, and case ID."""
    case = _sample_case(
        "SENTINEL-ID-99",
        category="uncovered",
        expect={
            "agents": ["KnowledgeAgent"],
            "tools_all": ["search_knowledge_base"],
            "tools_none": [],
            "escalate": False,
            "priority": None,
            "blocked": False,
            "gold_urls": ["https://gold.example/SECRET-URL"],
            "facts_any": [["SECRET-FACT"]],
            "facts_none": ["SECRET-LEAK"],
            "abstain": True,
        },
    )
    result = {
        "id": "SENTINEL-ID-99",
        "status": "ok",
        "error_type": None,
        "turns": [observe_turn(_sample_state(), case["turns"][0], 10.0)],
    }

    judge_input = build_judge_input(case, result)

    for forbidden in (
        "SENTINEL-ID-99", "uncovered", "expect", "SECRET-URL", "SECRET-FACT",
        "SECRET-LEAK", "abstain", "gold_urls", "facts_any",
    ):
        assert forbidden not in judge_input

    # Must contain actual merchant message and final response
    assert case["turns"][0] in judge_input
    assert "Receba em 2 dias úteis" in judge_input


def test_parse_judgment_markdown_blocks_and_invalid_formats():
    """Verify parse_judgment extracts valid ratings and rejects invalid schemas."""
    # Plain JSON
    pj = parse_judgment('{"grounded": 5, "answers_question": 4, "abstained": false, "rationale": "valid"}')
    assert pj["grounded"] == 5
    assert pj["answers_question"] == 4
    assert pj["abstained"] is False

    # Wrapped in markdown code block with conversational prose
    mj = parse_judgment('Here is the assessment:\n```json\n{"grounded": 1, "answers_question": 1, "abstained": true, "rationale": "out of domain"}\n```')
    assert mj["grounded"] == 1
    assert mj["abstained"] is True

    # Invalid cases
    invalids = [
        "not json at all",
        '{"grounded": 6, "answers_question": 3, "abstained": false}',  # out of bounds (> 5)
        '{"grounded": 0, "answers_question": 3, "abstained": false}',  # out of bounds (< 1)
        '{"grounded": true, "answers_question": 3, "abstained": false}',  # boolean for integer
        '{"grounded": 4, "answers_question": 4, "abstained": "yes"}',  # string for boolean
        '{"grounded": 4}',  # missing answers_question and abstained
    ]
    for bad in invalids:
        with pytest.raises(ValueError):
            parse_judgment(bad)


def test_judge_case_and_run_judge_flow(tmp_path: Path):
    """Verify judge_case execution, unparseable fallbacks, should_judge filters, and run_judge resumption."""
    case = _sample_case("k01")
    res = {
        "id": "k01",
        "status": "ok",
        "error_type": None,
        "turns": [observe_turn(_sample_state(), case["turns"][0], 10.0)],
    }

    # 1. Valid judgment
    good_model = ScriptedChatModel(
        responses=[AIMessage(content='{"grounded": 4, "answers_question": 5, "abstained": false, "rationale": "ok"}')]
    )
    j = judge_case(case, res, good_model)
    assert j["status"] == "ok"
    assert j["grounded"] == 4
    assert j["answers_question"] == 5
    assert j["abstained"] is False

    # 2. Unparseable output
    bad_model = ScriptedChatModel(responses=[AIMessage(content="I think this was fine")])
    j_bad = judge_case(case, res, bad_model)
    assert j_bad["status"] == "error"
    assert j_bad["error_type"] == "unparseable"

    # 3. should_judge checks
    assert should_judge(case, res) is True
    # blocked unsafe case must not be judged
    assert should_judge(case, dict(res, turns=[dict(res["turns"][0], is_safe=False)])) is False
    # handoff pending must not be judged
    assert should_judge(case, dict(res, turns=[dict(res["turns"][0], handoff={"status": "pending"})])) is False
    # category safety must not be judged
    assert should_judge(dict(case, category="safety"), res) is False

    # 4. run_judge resumption
    res_path = tmp_path / "runs" / "run_j.jsonl"
    judge_path = tmp_path / "runs" / "run_j.judge.jsonl"
    res_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [res, dict(res, id="k02")]
    res_path.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")

    # Pre-existing judgment for k01
    judge_path.write_text(json.dumps({"id": "k01", "status": "ok", "grounded": 5, "answers_question": 5, "abstained": False}) + "\n", encoding="utf-8")

    model_recorder = ScriptedChatModel(
        responses=[AIMessage(content='{"grounded": 3, "answers_question": 3, "abstained": false, "rationale": "mid"}')]
    )
    summary = run_judge(
        cases=[case, dict(case, id="k02")],
        results_path=res_path,
        judgments_path=judge_path,
        model=model_recorder,
        sleep_s=0,
    )
    assert summary["skipped"] == 1
    assert summary["attempted"] == 1
    assert len(model_recorder.received) == 1


def test_judge_metrics_abstention_and_disagreements():
    """Verify calculation of abstention precision/recall and facts vs grounded disagreements."""
    cases = [
        _sample_case("c01", expect=dict(_sample_case()["expect"], abstain=True, facts_any=[["fato1"]])),
        _sample_case("c02", expect=dict(_sample_case()["expect"], abstain=False, facts_any=[["fato2"]])),
    ]
    results = [
        {
            "id": "c01",
            "status": "ok",
            "turns": [observe_turn(_sample_state(agent_response="resposta com fato1"), "msg1", 10.0)],
        },
        {
            "id": "c02",
            "status": "ok",
            "turns": [observe_turn(_sample_state(agent_response="resposta sem nada"), "msg2", 10.0)],
        },
    ]
    judgments = [
        # c01: facts_ok is True, but judge grounded=2 -> disagreement!
        {"id": "c01", "status": "ok", "judge_model": "judge-flash", "grounded": 2, "answers_question": 3, "abstained": True},
        # c02: facts_ok is False, but judge grounded=5 and answers=5 -> disagreement!
        {"id": "c02", "status": "ok", "judge_model": "judge-flash", "grounded": 5, "answers_question": 5, "abstained": False},
    ]

    agg = aggregate(cases, results, judgments)
    j = agg.get("judge")
    assert j is not None
    assert j["n_judged"] == 2
    assert j["abstention_precision"] == 1.0  # expected True, predicted True
    assert j["abstention_recall"] == 1.0
    assert j["abstention_errors"] == []
    assert j["disagreements"] == ["c01", "c02"]
    assert j["judge_models"] == ["judge-flash"]
