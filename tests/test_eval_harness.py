"""Unit tests for evaluation harness, deterministic checks, metrics, and report generation."""
import json
from pathlib import Path

import pytest

from src.eval.cases import cases_sha256, load_cases
from src.eval.checks import detect_language, evaluate_case
from src.eval.metrics import COST_NOTE, aggregate
from src.eval.report import write_report


def _base_case() -> dict:
    return {
        "id": "c01",
        "category": "knowledge",
        "lang": "pt",
        "official": False,
        "offline": False,
        "turns": ["Qual é o prazo de recebimento do crediário?"],
        "expect": {
            "agents": ["KnowledgeAgent"],
            "tools_all": ["search_knowledge_base"],
            "tools_none": ["search_web"],
            "escalate": False,
            "priority": None,
            "blocked": False,
            "gold_urls": ["https://site.getnet.com.br/crediario/"],
            "facts_any": [["2 dias", "dois dias"]],
            "facts_none": ["taxa zero", "gratuito"],
            "abstain": None,
        },
    }


def test_load_cases_validation_rejections(tmp_path: Path):
    """Test that load_cases strictly rejects invalid case schemas and semantics."""
    base = _base_case()

    bad_variants = {
        "dup_id": [base, dict(base, id="c01")],
        "bad_category": [dict(base, category="chitchat")],
        "bad_lang": [dict(base, lang="fr")],
        "empty_turns": [dict(base, turns=[])],
        "blank_turn": [dict(base, turns=["   "])],
        "unknown_agent": [dict(base, expect=dict(base["expect"], agents=["UnknownAgent"]))],
        "unknown_tool": [dict(base, expect=dict(base["expect"], tools_all=["fake_tool"]))],
        "offline_not_safety": [dict(base, offline=True)],
        "missing_expect_key": [
            dict(base, expect={k: v for k, v in base["expect"].items() if k != "abstain"})
        ],
    }

    for name, rows in bad_variants.items():
        file_path = tmp_path / f"bad_{name}.jsonl"
        file_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match=r"(Line|expect|offline|invalid|duplicate)"):
            load_cases(file_path)

    # Valid file load
    good_path = tmp_path / "valid.jsonl"
    good_path.write_text(json.dumps(base, ensure_ascii=False) + "\n", encoding="utf-8")
    loaded = load_cases(good_path)
    assert len(loaded) == 1
    assert loaded[0]["id"] == "c01"


def test_detect_language():
    """Test language detection for Portuguese, English, and unknown/draw."""
    assert detect_language("O crediário permite parcelar com a sua conta no portal.") == "pt"
    assert detect_language("You can check this in the app with your account.") == "en"
    assert detect_language("123 456 789") == "unknown"
    assert detect_language("") == "unknown"


def test_evaluate_case_individual_checks():
    """Verify each deterministic check computes True, False, and None accurately."""
    case = _base_case()

    ok_turn = {
        "message": "Qual é o prazo?",
        "response": "Você recebe em 2 dias úteis com o crediário Getnet.",
        "agents_used": ["SupervisorAgent", "KnowledgeAgent"],
        "tools_used": ["search_knowledge_base"],
        "sources": ["https://site.getnet.com.br/crediario/"],
        "ticket_id": None,
        "ticket_priority": None,
        "is_safe": True,
        "handoff": None,
    }
    result_ok = {"id": "c01", "status": "ok", "error_type": None, "turns": [ok_turn]}

    ev_ok = evaluate_case(case, result_ok)
    assert ev_ok["passed"] is True
    checks = ev_ok["checks"]
    assert checks["routing_ok"] is True
    assert checks["tools_ok"] is True
    assert checks["escalation_ok"] is True
    assert checks["priority_ok"] is None
    assert checks["blocked_ok"] is True
    assert checks["sources_ok"] is True
    assert checks["facts_ok"] is True
    assert checks["facts_none_ok"] is True
    assert checks["language_ok"] is True

    # Failing tools check (forbidden tool present)
    bad_tools_turn = dict(ok_turn, tools_used=["search_knowledge_base", "search_web"])
    ev_bad_tools = evaluate_case(case, {"id": "c01", "status": "ok", "turns": [bad_tools_turn]})
    assert ev_bad_tools["passed"] is False
    assert ev_bad_tools["checks"]["tools_ok"] is False

    # Failing facts_none check (leaked term)
    bad_leak_turn = dict(ok_turn, response="O serviço tem taxa zero e entrega em 2 dias.")
    ev_leak = evaluate_case(case, {"id": "c01", "status": "ok", "turns": [bad_leak_turn]})
    assert ev_leak["passed"] is False
    assert ev_leak["checks"]["facts_none_ok"] is False


def test_evaluate_case_facts_any_groups():
    """Verify facts_any requires all alternative groups to be present with normalization."""
    case = _base_case()
    case["expect"]["facts_any"] = [
        ["48x", "48 vezes", "quarenta e oito"],
        ["2 dias", "dois dias"],
    ]

    # Both groups matched
    turn_both = {
        "response": "Parcele em até 48x e receba em 2 dias.",
        "agents_used": ["KnowledgeAgent"],
        "tools_used": ["search_knowledge_base"],
        "sources": ["https://site.getnet.com.br/crediario/"],
        "is_safe": True,
    }
    ev = evaluate_case(case, {"id": "c01", "status": "ok", "turns": [turn_both]})
    assert ev["checks"]["facts_ok"] is True

    # One group missing
    turn_one = dict(turn_both, response="Parcele em até 48x sem prazo definido.")
    ev_missing = evaluate_case(case, {"id": "c01", "status": "ok", "turns": [turn_one]})
    assert ev_missing["checks"]["facts_ok"] is False

    # Normalization with multiple spaces and mixed case
    turn_norm = dict(turn_both, response="PARCELE  EM  ATÉ   48 VEZES  E  RECEBA   EM  DOIS DIAS.")
    ev_norm = evaluate_case(case, {"id": "c01", "status": "ok", "turns": [turn_norm]})
    assert ev_norm["checks"]["facts_ok"] is True


def test_evaluate_case_error_and_empty_turns():
    """Verify results with errors or empty turns produce all None checks and passed=False."""
    case = _base_case()

    res_err = {"id": "c01", "status": "error", "error_type": "LLMUnavailableError", "turns": []}
    ev_err = evaluate_case(case, res_err)
    assert ev_err["passed"] is False
    assert all(v is None for v in ev_err["checks"].values())

    res_empty = {"id": "c01", "status": "ok", "turns": []}
    ev_empty = evaluate_case(case, res_empty)
    assert ev_empty["passed"] is False
    assert all(v is None for v in ev_empty["checks"].values())


def test_aggregate_metrics_excludes_errors():
    """Verify aggregate excludes execution errors from metric rate denominators."""
    c1 = dict(_base_case(), id="c01")
    c2 = dict(_base_case(), id="c02")

    r1 = {
        "id": "c01",
        "status": "ok",
        "turns": [{
            "response": "Receba em 2 dias úteis com crediário.",
            "agents_used": ["KnowledgeAgent"],
            "tools_used": ["search_knowledge_base"],
            "sources": ["https://site.getnet.com.br/crediario/"],
            "is_safe": True,
            "latency_ms": 120.0,
        }],
    }
    r2 = {"id": "c02", "status": "error", "error_type": "TimeoutError", "turns": []}

    agg = aggregate([c1, c2], [r1, r2])
    assert agg["n_cases"] == 2
    assert agg["n_evaluated"] == 1
    assert agg["n_errors"] == 1
    assert agg["error_ids"] == ["c02"]
    assert agg["metrics"]["pass_rate"] == 1.0


def test_aggregate_percentiles_tokens_and_cost():
    """Verify calculation of latency percentiles, token usage, and cost placeholders."""
    cases = [dict(_base_case(), id=f"c{i:02d}") for i in range(1, 6)]
    results = [
        {
            "id": f"c{i:02d}",
            "status": "ok",
            "turns": [{
                "response": "Receba em 2 dias úteis.",
                "agents_used": ["KnowledgeAgent"],
                "tools_used": ["search_knowledge_base"],
                "sources": ["https://site.getnet.com.br/crediario/"],
                "is_safe": True,
                "latency_ms": float(i * 100),
                "tokens": {"total_tokens": i * 10},
            }],
        }
        for i in range(1, 6)
    ]

    agg = aggregate(cases, results)
    m = agg["metrics"]
    assert m["latency_ms_p50"] == 300.0
    assert m["latency_ms_p95"] == 500.0
    assert m["tokens_total"] == 150
    assert m["tokens_mean_per_case"] == 30.0
    assert m["estimated_cost_usd"] is None
    assert agg["cost_note"] == COST_NOTE


def test_write_report_json_and_markdown(tmp_path: Path):
    """Verify write_report outputs valid JSON and Markdown files with required sections."""
    case = _base_case()
    result = {
        "id": "c01",
        "status": "ok",
        "turns": [{
            "response": "Receba em 2 dias úteis.",
            "agents_used": ["KnowledgeAgent"],
            "tools_used": ["search_knowledge_base"],
            "sources": ["https://site.getnet.com.br/crediario/"],
            "is_safe": True,
            "latency_ms": 150.0,
        }],
    }

    out_json = tmp_path / "reports" / "summary.json"
    out_md = tmp_path / "reports" / "summary.md"

    rep = write_report([case], [result], out_json, out_md, run_id="unit-test-run")
    assert rep["run_id"] == "unit-test-run"

    assert out_json.exists()
    assert out_md.exists()

    disk_json = json.loads(out_json.read_text(encoding="utf-8"))
    assert disk_json["run_id"] == "unit-test-run"
    assert "cases_sha256" in disk_json
    assert disk_json["metrics"]["pass_rate"] == 1.0

    md_text = out_md.read_text(encoding="utf-8")
    assert "pass_rate" in md_text
    assert "routing_rate" in md_text
    assert "Performance por Categoria" in md_text
    assert "Performance por Idioma" in md_text
    assert "Cenários Oficiais" in md_text


def test_cases_sha256_stability():
    """Verify checksum determinism independent of dictionary key iteration order."""
    case_a = _base_case()
    case_b = {k: case_a[k] for k in sorted(case_a.keys())}
    assert cases_sha256([case_a]) == cases_sha256([case_b])


def test_aggregate_estimated_cost_usd():
    """Verify aggregate calculates estimated_cost_usd as sum of turn costs, or None if missing price."""
    case = _base_case()

    # Case 1: valid turns with pricing
    res_ok = [
        {
            "id": "c01",
            "status": "ok",
            "turns": [
                {
                    "llm_model": "gemini-3.5-flash-lite",
                    "tokens": {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
                },
                {
                    "llm_model": "gemini-3.8-flash",
                    "tokens": {"input_tokens": 2_000_000, "output_tokens": 1_000_000},
                },
            ],
        }
    ]
    # gemini-3.5-flash-lite: 1M in ($0.30) + 1M out ($2.50) = 2.80
    # gemini-3.8-flash: 2M in (2 * $0.75 = $1.50) + 1M out ($3.75) = 5.25
    # total = 8.05
    agg_ok = aggregate([case], res_ok)
    assert agg_ok["metrics"]["estimated_cost_usd"] == 8.05

    # Case 2: a turn has tokens but model has no price
    res_unpriced = [
        {
            "id": "c01",
            "status": "ok",
            "turns": [
                {
                    "llm_model": "gemini-3.5-flash-lite",
                    "tokens": {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
                },
                {
                    "llm_model": "unknown-model",
                    "tokens": {"input_tokens": 1_000, "output_tokens": 1_000},
                },
            ],
        }
    ]
    agg_unpriced = aggregate([case], res_unpriced)
    assert agg_unpriced["metrics"]["estimated_cost_usd"] is None
