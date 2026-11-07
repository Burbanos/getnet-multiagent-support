"""Evaluation CLI entry point for offline regression, model execution, judge, and reports."""
import argparse
import sys
from pathlib import Path

from src.config import settings
from src.eval.cases import load_cases
from src.eval.checks import evaluate_case
from src.eval.judge import load_judgments, run_judge
from src.eval.offline import run_offline
from src.eval.report import write_report
from src.eval.runner import load_results, run_eval

DEFAULT_CASES_PATH = Path("data/eval/cases.jsonl")


def _cmd_offline(cases_path: Path) -> int:
    if not cases_path.exists():
        print(f"Error: dataset file not found at {cases_path}", file=sys.stderr)
        return 1

    cases = load_cases(cases_path)
    offline_cases = [c for c in cases if c.get("offline")]
    if not offline_cases:
        print("No offline cases found in dataset.", file=sys.stderr)
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


def main() -> int:
    """Parse arguments and dispatch to evaluation subcommands."""
    parser = argparse.ArgumentParser(description="Evaluation harness and runner CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. offline
    subparsers.add_parser("offline", help="Run offline regression subset")

    # 2. run
    p_run = subparsers.add_parser("run", help="Run evaluation with live models")
    p_run.add_argument("--run-id", required=True, help="Evaluation run ID")
    p_run.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")
    p_run.add_argument("--sleep", type=float, default=None, help="Pause between cases in seconds")
    p_run.add_argument("--max-cases", type=int, default=None, help="Maximum cases to attempt")
    p_run.add_argument("--only", default=None, help="Comma-separated case IDs to evaluate")

    # 3. judge
    p_judge = subparsers.add_parser("judge", help="Run LLM judge evaluation")
    p_judge.add_argument("--run-id", required=True, help="Evaluation run ID")
    p_judge.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")
    p_judge.add_argument("--sleep", type=float, default=None, help="Pause between cases in seconds")

    # 4. report
    p_report = subparsers.add_parser("report", help="Generate evaluation JSON and Markdown report")
    p_report.add_argument("--run-id", required=True, help="Evaluation run ID")
    p_report.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")
    p_report.add_argument("--out-dir", default="reports", help="Output directory for reports")

    args = parser.parse_args()

    if args.subcommand == "offline":
        return _cmd_offline(DEFAULT_CASES_PATH)

    cases = load_cases(DEFAULT_CASES_PATH)

    if args.subcommand == "run":
        if not settings.GEMINI_API_KEY:
            print(
                "Error: GEMINI_API_KEY environment variable is required to run evaluation with live models.",
                file=sys.stderr,
            )
            return 2

        only_list = [x.strip() for x in args.only.split(",") if x.strip()] if args.only else None
        results_file = Path(args.runs_dir) / f"{args.run_id}.jsonl"

        summary = run_eval(
            cases=cases,
            results_path=results_file,
            run_id=args.run_id,
            sleep_s=args.sleep,
            max_cases=args.max_cases,
            only=only_list,
        )
        print(
            f"Run '{args.run_id}': attempted={summary['attempted']}, ok={summary['ok']}, "
            f"errors={summary['errors']}, skipped={summary['skipped']}, stopped_early={summary['stopped_early']}"
        )
        print("Resumption is supported: simply run the command again to continue from where it stopped.")
        return 0 if not summary["errors"] and not summary["stopped_early"] else 1

    if args.subcommand == "judge":
        if not settings.GEMINI_API_KEY:
            print(
                "Error: GEMINI_API_KEY environment variable is required to run judge evaluation.",
                file=sys.stderr,
            )
            return 2

        results_file = Path(args.runs_dir) / f"{args.run_id}.jsonl"
        judge_file = Path(args.runs_dir) / f"{args.run_id}.judge.jsonl"

        summary = run_judge(
            cases=cases,
            results_path=results_file,
            judgments_path=judge_file,
            sleep_s=args.sleep,
        )
        print(
            f"Judge '{args.run_id}': attempted={summary['attempted']}, ok={summary['ok']}, "
            f"errors={summary['errors']}, skipped={summary['skipped']}, stopped_early={summary['stopped_early']}"
        )
        print("Resumption is supported: simply run the command again to continue from where it stopped.")
        return 0 if not summary["errors"] and not summary["stopped_early"] else 1

    if args.subcommand == "report":
        runs_dir = Path(args.runs_dir)
        results_file = runs_dir / f"{args.run_id}.jsonl"
        judge_file = runs_dir / f"{args.run_id}.judge.jsonl"

        results_dict = load_results(results_file)
        results = list(results_dict.values())

        judgments = None
        if judge_file.exists():
            judgments_dict = load_judgments(judge_file)
            judgments = list(judgments_dict.values())

        out_dir = Path(args.out_dir)
        out_json = out_dir / f"eval_{args.run_id}.json"
        out_md = out_dir / f"eval_{args.run_id}.md"

        write_report(
            cases=cases,
            results=results,
            out_json=out_json,
            out_md=out_md,
            run_id=args.run_id,
            judgments=judgments,
        )
        print(f"Generated report at {out_json} and {out_md}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
