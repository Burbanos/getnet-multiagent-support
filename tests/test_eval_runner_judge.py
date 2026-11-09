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
    error_code,
    judge_case,
    load_chunk_texts,
    parse_judgment,
    response_text,
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
            "text": "X" * 3000,
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
    """Verify observe_turn returns exact keys and truncates retrieved doc texts to 2000 chars."""
    state = _sample_state()
    turn = observe_turn(state, "Qual o prazo?", latency_ms=45.2)

    expected_keys = {
        "message", "response", "agents_used", "tools_used", "sources", "retrieved_docs",
        "web_results", "api_results", "tool_results", "ticket_id", "ticket_priority", "is_safe", "handoff", "llm_model",
        "tokens", "tokens_by_agent", "guardrail", "guardrail_layer", "latency_ms",
    }
    assert set(turn.keys()) == expected_keys
    assert turn["latency_ms"] == 45.2
    assert len(turn["retrieved_docs"]) == 1
    doc = turn["retrieved_docs"][0]
    assert set(doc.keys()) == {"url", "chunk_id", "score", "text"}
    assert len(doc["text"]) == 2000
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


def test_judge_case_list_blocks():
    """Verify judge_case handles list-of-blocks responses, ignoring thinking and non-text blocks."""
    case = _sample_case("k01")
    res = {
        "id": "k01",
        "status": "ok",
        "error_type": None,
        "turns": [observe_turn(_sample_state(), case["turns"][0], 10.0)],
    }
    blocks = [
        {"type": "thinking", "thinking": '{"grounded": 1}'},
        {"type": "text", "text": "Assessment:\n"},
        {"type": "image_url", "image_url": "https://example.com/img.png"},
        {"type": "text", "text": '{"grounded": 4, "answers_question": 5, "abstained": false, "rationale": "ok"}'},
    ]
    model = ScriptedChatModel(responses=[AIMessage(content=blocks)])
    j = judge_case(case, res, model)
    assert j["status"] == "ok"
    assert j["grounded"] == 4
    assert j["answers_question"] == 5
    assert j["abstained"] is False

    # Directly check response_text behavior
    msg = AIMessage(content=["str1", {"type": "text", "text": "str2"}, {"type": "thinking", "thinking": "skip"}])
    assert response_text(msg) == "str1str2"
    assert response_text(AIMessage(content="plain")) == "plain"


def test_error_code_extraction_and_no_leak():
    """Verify error_code extraction across cause chains and ensure exception messages never leak."""
    case = _sample_case("k01")
    res = {
        "id": "k01",
        "status": "ok",
        "error_type": None,
        "turns": [observe_turn(_sample_state(), case["turns"][0], 10.0)],
    }

    class DummyProviderError(Exception):
        def __init__(self, code: int, msg: str):
            super().__init__(f"{code} {msg}")
            self.code = code

    class DummyWrapperError(Exception):
        pass

    class RaisingModel(ScriptedChatModel):
        exc_factory: object = None

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self.received.append(list(messages))
            raise self.exc_factory()

    def wrapped_exc(code: int, msg: str) -> Exception:
        try:
            try:
                raise DummyProviderError(code, msg)
            except DummyProviderError as inner:
                raise DummyWrapperError(f"{code} UNAVAILABLE. {msg}") from inner
        except DummyWrapperError as outer:
            return outer

    # Directly check error_code function
    assert error_code(DummyProviderError(503, "msg")) == 503
    assert error_code(RuntimeError("429 RESOURCE_EXHAUSTED")) == 429
    assert error_code(ValueError("generic error")) is None

    # 1. Chained exception with code=503
    j1 = judge_case(case, res, RaisingModel(responses=[], exc_factory=lambda: wrapped_exc(503, "LEAK_SECRET_KEY")))
    assert j1["status"] == "error"
    assert j1["error_type"] == "DummyWrapperError"
    assert j1["error_code"] == 503
    assert "LEAK_SECRET_KEY" not in json.dumps(j1)

    # 2. String beginning with 429
    j2 = judge_case(case, res, RaisingModel(responses=[], exc_factory=lambda: RuntimeError("429 RESOURCE_EXHAUSTED details")))
    assert j2["status"] == "error"
    assert j2["error_code"] == 429
    assert "RESOURCE_EXHAUSTED" not in json.dumps(j2)

    # 3. Generic error without code
    j3 = judge_case(case, res, RaisingModel(responses=[], exc_factory=lambda: RuntimeError("internal secret failure")))
    assert j3["status"] == "error"
    assert j3["error_code"] is None
    assert "internal secret failure" not in json.dumps(j3)

    # 4. Unparseable output
    j4 = judge_case(case, res, ScriptedChatModel(responses=[AIMessage(content="no json anywhere")]))
    assert j4["status"] == "error"
    assert j4["error_type"] == "unparseable"
    assert j4["error_code"] is None


def test_run_judge_stops_on_three_consecutive_errors_resets_on_ok(tmp_path: Path):
    """Verify run_judge halts after 3 consecutive errors of any kind, and resets on status ok."""
    good_json = '{"grounded": 4, "answers_question": 4, "abstained": false, "rationale": "good"}'
    cases = [_sample_case(f"k0{i}") for i in range(1, 8)]
    res = {
        "id": "k01",
        "status": "ok",
        "error_type": None,
        "turns": [observe_turn(_sample_state(), "msg", 10.0)],
    }
    rp = tmp_path / "runs.jsonl"
    rp.write_text("".join(json.dumps(dict(res, id=c["id"])) + "\n" for c in cases), encoding="utf-8")

    # Sequence 1: 3 unparseable in a row -> stops after 3
    model_unparseable = ScriptedChatModel(responses=[AIMessage(content="not json")] * 7)
    s1 = run_judge(cases, rp, tmp_path / "j1.jsonl", model=model_unparseable, sleep_s=0)
    assert s1["stopped_early"] is True
    assert len(model_unparseable.received) == 3
    assert s1["errors"] == 3

    # Sequence 2: 2 unparseable, 1 good (resets count), 3 unparseable -> stops after 6
    seq = [
        AIMessage(content="bad1"),
        AIMessage(content="bad2"),
        AIMessage(content=good_json),
        AIMessage(content="bad3"),
        AIMessage(content="bad4"),
        AIMessage(content="bad5"),
        AIMessage(content=good_json),
    ]
    model_mixed = ScriptedChatModel(responses=seq)
    s2 = run_judge(cases, rp, tmp_path / "j2.jsonl", model=model_mixed, sleep_s=0)
    assert s2["stopped_early"] is True
    assert len(model_mixed.received) == 6
    assert s2["ok"] == 1
    assert s2["errors"] == 5


def test_run_eval_deletes_temp_tickets_dir(tmp_path: Path):
    """Verify run_eval deletes the temporary tickets directory on completion and exception."""
    cases = [_sample_case("k01"), _sample_case("k02")]
    observed_dirs = []

    class FakeOrch:
        def run_sync(self, user_id, message, session_id):
            observed_dirs.append(Path(settings.TICKETS_DB_PATH).parent)
            return _sample_state()

    orig_path = settings.TICKETS_DB_PATH
    out_file = tmp_path / "eval_clean.jsonl"

    run_eval(
        cases=cases,
        results_path=out_file,
        run_id="run-clean",
        orchestrator_factory=FakeOrch,
        sleep_s=0,
    )

    assert settings.TICKETS_DB_PATH == orig_path
    assert len(observed_dirs) > 0
    for d in observed_dirs:
        assert not d.exists()


def test_build_judge_input_full_passages_from_index():
    """Verify build_judge_input uses full text from index when chunk_id exists, falling back to stored text."""
    all_chunks = load_chunk_texts()
    assert len(all_chunks) > 0
    first_cid, first_text = next(iter(all_chunks.items()))

    case = _sample_case("k01")
    docs = [
        {"url": "https://site.getnet.com.br/gold", "chunk_id": first_cid, "score": 0.9, "text": "SHORT_TRUNCATED"},
        {"url": "https://example.org/missing", "chunk_id": "not-in-index-999", "score": 0.6, "text": "STORED_FALLBACK"},
        {"url": "https://example.org/nochunck", "chunk_id": None, "score": None, "text": "STORED_NO_CHUNK_ID"},
    ]
    res = {
        "id": "k01",
        "status": "ok",
        "error_type": None,
        "turns": [observe_turn(_sample_state(retrieved_docs=docs), case["turns"][0], 1.0)],
    }

    judge_json = build_judge_input(case, res)
    payload = json.loads(judge_json)
    passages = payload.get("passages", [])
    assert len(passages) == 3

    # Passage 1: resolved from index to full text
    assert passages[0]["url"] == "https://site.getnet.com.br/gold"
    assert passages[0]["text"] == first_text
    assert set(passages[0].keys()) == {"url", "text"}

    # Passages 2 & 3: fallback to stored text
    assert passages[1]["text"] == "STORED_FALLBACK"
    assert passages[2]["text"] == "STORED_NO_CHUNK_ID"

    # Strictly blind
    for forbidden in ("k01", "expect", "category", "facts_any"):
        assert forbidden not in judge_json


def test_load_chunk_texts_caching_and_custom_path(tmp_path: Path):
    """Verify load_chunk_texts caches default index and loads custom paths independently."""
    custom_file = tmp_path / "custom_chunks.jsonl"
    custom_file.write_text(json.dumps({"chunk_id": "custom-01", "text": "CUSTOM_TEXT"}) + "\n", encoding="utf-8")

    # Custom path loads correctly without being cached as default
    custom_mapping = load_chunk_texts(custom_file)
    assert custom_mapping == {"custom-01": "CUSTOM_TEXT"}

    # Default path loads and caches
    default_mapping = load_chunk_texts()
    assert isinstance(default_mapping, dict)
    assert len(default_mapping) > 0

    # Repeated default call uses cache
    default_again = load_chunk_texts()
    assert default_again is default_mapping

    # Calling custom path again still works independently
    assert load_chunk_texts(custom_file) == {"custom-01": "CUSTOM_TEXT"}
