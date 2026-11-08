"""Tests for evaluation comparison utilities and multi-run report generation."""
import json
from pathlib import Path

from src.eval.compare import (
    build_markdown_table,
    compare_runs,
    format_cell,
    format_metric,
    write_comparison,
)


def _base_case(cid: str, abstain: bool | None = None) -> dict:
    return {
        "id": cid,
        "category": "knowledge",
        "lang": "pt",
        "official": False,
        "offline": False,
        "turns": ["Como funciona?"],
        "expect": {
            "agents": ["KnowledgeAgent"],
            "tools_all": ["search_knowledge_base"],
            "tools_none": [],
            "escalate": False,
            "priority": None,
            "blocked": False,
            "gold_urls": ["https://site.getnet.com.br/"],
            "facts_any": [["taxa"]],
            "facts_none": [],
            "abstain": abstain,
        },
    }


def _make_result(cid: str, ok: bool, passes: bool, model: str = "gemini-3.5-flash-lite", tokens: int = 100) -> dict:
    if not ok:
        return {"id": cid, "status": "error", "error": "fatal error"}
    return {
        "id": cid,
        "status": "ok",
        "turns": [{
            "response": "A taxa é de 2% ao mês." if passes else "Sem resposta.",
            "agents_used": ["KnowledgeAgent"] if passes else ["GeneralistAgent"],
            "tools_used": ["search_knowledge_base"] if passes else [],
            "sources": ["https://site.getnet.com.br/"] if passes else [],
            "is_safe": True,
            "latency_ms": 100.0,
            "llm_model": model,
            "tokens": {"input_tokens": tokens, "output_tokens": tokens, "total_tokens": tokens * 2},
        }],
    }


def test_compare_runs_mean_min_max():
    """Verify mean, min, and max calculations across multiple runs."""
    cases = [_base_case("c01"), _base_case("c02")]

    run1 = [
        _make_result("c01", ok=True, passes=True, tokens=100),
        _make_result("c02", ok=True, passes=True, tokens=100),
    ]
    run2 = [
        _make_result("c01", ok=True, passes=True, tokens=200),
        _make_result("c02", ok=True, passes=False, tokens=200),
    ]

    groups = [("model_a", [("r1", run1, None), ("r2", run2, None)])]
    comp = compare_runs(cases, groups)

    assert "cases_sha256" in comp
    assert len(comp["groups"]) == 1
    g = comp["groups"][0]
    assert g["label"] == "model_a"
    assert g["runs"] == ["r1", "r2"]
    assert g["answer_models"] == ["gemini-3.5-flash-lite"]
    assert g["complete"] is True

    # pass_rate: run1 is 1.0 (2/2), run2 is 0.5 (1/2) -> mean 0.75, min 0.5, max 1.0
    pr = g["metrics"]["pass_rate"]
    assert pr["values"] == [1.0, 0.5]
    assert pr["mean"] == 0.75
    assert pr["min"] == 0.5
    assert pr["max"] == 1.0

    # tokens_total: run1 is 400, run2 is 800 -> mean 600, min 400, max 800
    tt = g["metrics"]["tokens_total"]
    assert tt["values"] == [400, 800]
    assert tt["mean"] == 600.0
    assert tt["min"] == 400
    assert tt["max"] == 800


def test_compare_runs_none_handling():
    """Verify that any None value across runs propagates to None for mean, min, and max."""
    cases = [_base_case("c01")]

    # Run 1 has known model with price; Run 2 has unpriced model
    run1 = [_make_result("c01", ok=True, passes=True, model="gemini-3.5-flash-lite")]
    run2 = [_make_result("c01", ok=True, passes=True, model="unpriced-model")]

    groups = [("mix", [("r1", run1, None), ("r2", run2, None)])]
    comp = compare_runs(cases, groups)
    g = comp["groups"][0]

    cost_m = g["metrics"]["estimated_cost_usd"]
    assert cost_m["values"][0] is not None
    assert cost_m["values"][1] is None
    assert cost_m["mean"] is None
    assert cost_m["min"] is None
    assert cost_m["max"] is None

    # Judge metrics when no judge is provided should also be None
    judge_m = g["metrics"]["judge_grounded_mean"]
    assert judge_m["values"] == [None, None]
    assert judge_m["mean"] is None
    assert judge_m["min"] is None
    assert judge_m["max"] is None


def test_compare_runs_failed_intersection():
    """Verify that failed_in_all_runs is the strict intersection of failed case IDs."""
    cases = [_base_case(f"c0{i}", abstain=True) for i in range(1, 6)]

    # Run 1 fails c01, c02, c03
    run1 = [
        _make_result("c01", ok=True, passes=False),
        _make_result("c02", ok=True, passes=False),
        _make_result("c03", ok=True, passes=False),
        _make_result("c04", ok=True, passes=True),
        _make_result("c05", ok=True, passes=True),
    ]
    # Run 2 fails c02, c03, c04
    run2 = [
        _make_result("c01", ok=True, passes=True),
        _make_result("c02", ok=True, passes=False),
        _make_result("c03", ok=True, passes=False),
        _make_result("c04", ok=True, passes=False),
        _make_result("c05", ok=True, passes=True),
    ]
    # Run 3 fails c02, c05
    run3 = [
        _make_result("c01", ok=True, passes=True),
        _make_result("c02", ok=True, passes=False),
        _make_result("c03", ok=True, passes=True),
        _make_result("c04", ok=True, passes=True),
        _make_result("c05", ok=True, passes=False),
    ]

    def _jud(cid: str, abstained: bool) -> dict:
        return {"id": cid, "status": "ok", "grounded": 5, "answers_question": 5, "abstained": abstained}

    # Add judge data with abstention errors: cases expect abstain=True, so abstained=False is an error
    j1 = [_jud("c01", False), _jud("c02", False), _jud("c03", True), _jud("c04", True), _jud("c05", True)]
    j2 = [_jud("c01", True), _jud("c02", False), _jud("c03", False), _jud("c04", True), _jud("c05", True)]
    j3 = [_jud("c01", True), _jud("c02", False), _jud("c03", True), _jud("c04", False), _jud("c05", True)]

    groups = [("group_fail", [("r1", run1, j1), ("r2", run2, j2), ("r3", run3, j3)])]
    comp = compare_runs(cases, groups)
    g = comp["groups"][0]

    assert g["failed_in_all_runs"] == ["c02"]
    assert g["judge_abstention_errors_in_all_runs"] == ["c02"]


def test_markdown_table_formatting_pct_and_usd():
    """Verify Markdown cell formatting for pct and usd categories, including en-dash and locale comma."""
    # pct
    pct_cell = format_cell("pct", {"mean": 0.86, "min": 0.841, "max": 0.899})
    assert pct_cell == "86,0% (84,1–89,9)"

    # usd
    usd_cell = format_cell("usd", {"mean": 0.167, "min": 0.163, "max": 0.170})
    assert usd_cell == "US$ 0,167 (0,163–0,170)"

    # None value produces n/d
    assert format_cell("pct", {"mean": None, "min": None, "max": None}) == "n/d"
    assert format_metric("pct", None) == "n/d"

    # dec2, sec, int
    assert format_cell("dec2", {"mean": 4.98, "min": 4.95, "max": 5.0}) == "4,98 (4,95–5,00)"
    assert format_cell("sec", {"mean": 4300, "min": 4200, "max": 4300}) == "4,3 s (4,2–4,3)"
    assert format_cell("int", {"mean": 421140, "min": 413563, "max": 426999}) == "421.140 (413.563–426.999)"

    # build_markdown_table structure
    sample_group = {
        "label": "test_label",
        "runs": ["r1"],
        "answer_models": ["model_a"],
        "metrics": {m[0]: {"mean": None, "min": None, "max": None} for m in [
            ("pass_rate",), ("official_pass_rate",), ("routing_rate",), ("tools_rate",),
            ("escalation_rate",), ("facts_rate",), ("sources_rate",), ("language_rate",),
            ("judge_grounded_mean",), ("judge_answers_mean",), ("judge_abstention_precision",),
            ("judge_abstention_recall",), ("latency_ms_p50",), ("latency_ms_p95",),
            ("tokens_total",), ("estimated_cost_usd",),
        ]},
    }
    table_lines = build_markdown_table([sample_group])
    assert len(table_lines) == 20
    assert table_lines[0] == "| Métrica | test_label |"


def test_write_comparison_artifacts(tmp_path: Path):
    """Verify write_comparison creates valid JSON and Markdown output."""
    cases = [_base_case("c01")]
    run1 = [_make_result("c01", ok=True, passes=True)]
    groups = [("test_group", [("r1", run1, None)])]

    out_json = tmp_path / "eval_test.json"
    out_md = tmp_path / "eval_test.md"

    write_comparison(cases, groups, out_json, out_md, name="test")

    assert out_json.exists()
    assert out_md.exists()

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["name"] == "test"
    assert "generated_at" in data
    assert len(data["groups"]) == 1

    md_content = out_md.read_text(encoding="utf-8")
    assert md_content.startswith("# Comparação de execuções: test\n\n| Métrica | test_group |")
