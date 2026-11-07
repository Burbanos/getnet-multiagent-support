"""Offline evaluation regression tests for CI."""
from pathlib import Path

from src.eval.cases import load_cases
from src.eval.checks import evaluate_case
from src.eval.offline import run_offline


def test_eval_offline_regression_subset():
    """Verify that all offline safety cases pass deterministically without model calls."""
    cases_path = Path("data/eval/cases.jsonl")
    cases = load_cases(cases_path)
    offline_cases = [c for c in cases if c.get("offline")]

    assert len(offline_cases) == 6, f"Expected 6 offline cases, found {len(offline_cases)}"

    results = run_offline(offline_cases)
    assert len(results) == len(offline_cases)

    for case, result in zip(offline_cases, results):
        assert result["status"] == "ok", f"Case {case['id']} failed with error {result.get('error_type')}"
        assert result["model_calls"] == 0, f"Case {case['id']} triggered {result['model_calls']} LLM calls"

        evaluation = evaluate_case(case, result)
        assert evaluation["passed"] is True, f"Case {case['id']} checks failed: {evaluation['checks']}"
