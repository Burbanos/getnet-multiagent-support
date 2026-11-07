"""Evaluation CLI entry point."""
import sys
from pathlib import Path

from src.eval.cases import load_cases
from src.eval.checks import evaluate_case
from src.eval.offline import run_offline


def main() -> int:
    """Execute evaluation CLI command."""
    if len(sys.argv) < 2 or sys.argv[1] != "offline":
        print("Usage: python -m src.eval offline")
        return 2

    cases_path = Path("data/eval/cases.jsonl")
    if not cases_path.exists():
        print(f"Error: dataset file not found at {cases_path}")
        return 1

    cases = load_cases(cases_path)
    offline_cases = [c for c in cases if c.get("offline")]
    if not offline_cases:
        print("No offline cases found in dataset.")
        return 1

    results = run_offline(offline_cases)
    passed_count = 0
    zero_calls = True

    for c, r in zip(offline_cases, results):
        ev = evaluate_case(c, r)
        if ev.get("passed"):
            passed_count += 1
        if r.get("model_calls", 0) != 0:
            zero_calls = False

    total = len(offline_cases)
    print(f"offline: {passed_count}/{total} passed")

    if passed_count == total and zero_calls:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
