"""Evaluation CLI entry point for offline regression, model execution, judge, and reports."""
import argparse
import json
import sys
from pathlib import Path

from src.config import settings
from src.core.llm import LLMConfigurationError, LLMNotConfiguredError
from src.eval.cases import load_cases
from src.eval.checks import evaluate_case
from src.eval.compare import write_comparison
from src.eval.guardrail_eval import (
    load_guardrail_set,
    run_guardrail,
    write_guardrail_report,
    write_guardrail_summary,
    write_pattern_report,
)
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
    p_run.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to the evaluation cases JSONL")
    p_run.add_argument("--sleep", type=float, default=None, help="Pause between cases in seconds")
    p_run.add_argument("--max-cases", type=int, default=None, help="Maximum cases to attempt")
    p_run.add_argument("--only", default=None, help="Comma-separated case IDs to evaluate")

    # 3. judge
    p_judge = subparsers.add_parser("judge", help="Run LLM judge evaluation")
    p_judge.add_argument("--run-id", required=True, help="Evaluation run ID")
    p_judge.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")
    p_judge.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to the evaluation cases JSONL")
    p_judge.add_argument("--sleep", type=float, default=None, help="Pause between cases in seconds")

    # 4. report
    p_report = subparsers.add_parser("report", help="Generate evaluation JSON and Markdown report")
    p_report.add_argument("--run-id", required=True, help="Evaluation run ID")
    p_report.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")
    p_report.add_argument("--out-dir", default="reports", help="Output directory for reports")
    p_report.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to the evaluation cases JSONL")

    # 5. compare
    p_compare = subparsers.add_parser("compare", help="Compare multiple evaluation runs")
    p_compare.add_argument("--name", required=True, help="Comparison report name")
    p_compare.add_argument(
        "--group",
        required=True,
        action="append",
        help="Group definition in format LABEL=run1,run2,...",
    )
    p_compare.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")
    p_compare.add_argument("--out-dir", default="reports", help="Output directory for reports")
    p_compare.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to the evaluation cases JSONL")

    # 6. guardrail-patterns
    p_gp = subparsers.add_parser("guardrail-patterns", help="Evaluate and report guardrail pattern matching layer")
    p_gp.add_argument("--set", default="data/eval/guardrail_labeled.jsonl", help="Path to guardrail labeled JSONL dataset")
    p_gp.add_argument("--out-dir", default="reports", help="Output directory for reports")

    # 7. guardrail-run
    p_grun = subparsers.add_parser("guardrail-run", help="Run guardrail evaluation on live models")
    p_grun.add_argument("--run-id", required=True, help="Guardrail run ID")
    p_grun.add_argument("--set", default="data/eval/guardrail_labeled.jsonl", help="Path to guardrail labeled dataset")
    p_grun.add_argument("--runs-dir", default="reports/guardrail_runs", help="Directory for raw run JSONL")
    p_grun.add_argument("--sleep", type=float, default=None, help="Pause between cases in seconds")

    # 8. guardrail-report
    p_grep = subparsers.add_parser("guardrail-report", help="Generate guardrail JSON and Markdown report")
    p_grep.add_argument("--run-id", required=True, help="Guardrail run ID")
    p_grep.add_argument("--set", default="data/eval/guardrail_labeled.jsonl", help="Path to guardrail labeled dataset")
    p_grep.add_argument("--runs-dir", default="reports/guardrail_runs", help="Directory for raw run JSONL")
    p_grep.add_argument("--out-dir", default="reports", help="Output directory for reports")

    # 9. guardrail-summary
    p_gsum = subparsers.add_parser("guardrail-summary", help="Aggregate multiple guardrail run reports")
    p_gsum.add_argument("--run-ids", required=True, help="Comma-separated run IDs to summarize")
    p_gsum.add_argument("--out-dir", default="reports", help="Output directory for reports")

    args = parser.parse_args()

    if args.subcommand == "offline":
        return _cmd_offline(DEFAULT_CASES_PATH)

    if args.subcommand == "guardrail-patterns":
        try:
            set_path = Path(args.set)
            if not set_path.exists():
                print(f"Error: dataset file not found at {set_path}", file=sys.stderr)
                return 1
            g_cases = load_guardrail_set(set_path)
        except Exception as exc:  # noqa: BLE001
            print(f"Error loading guardrail set: {exc}", file=sys.stderr)
            return 1

        out_dir = Path(args.out_dir)
        out_json = out_dir / "guardrail_patterns.json"
        out_md = out_dir / "guardrail_patterns.md"

        report = write_pattern_report(g_cases, out_json, out_md, set_path=set_path)
        b_rate = report["metrics"]["all"]["block_rate"]
        fp_rate = report["metrics"]["all"]["false_positive_rate"]
        print(f"patterns: block_rate {b_rate}, false_positive_rate {fp_rate}")
        return 0

    if args.subcommand == "guardrail-run":
        try:
            set_path = Path(args.set)
            if not set_path.exists():
                print(f"Error: dataset file not found at {set_path}", file=sys.stderr)
                return 1
            cases = load_guardrail_set(set_path)
            results_file = Path(args.runs_dir) / f"{args.run_id}.jsonl"
            out = run_guardrail(cases, results_file, args.run_id, sleep_s=args.sleep)
            print(
                f"guardrail-run: attempted {out['attempted']}, ok {out['ok']}, errors {out['errors']}, "
                f"skipped {out['skipped']}, stopped_early {out['stopped_early']}"
            )
            return 0
        except LLMNotConfiguredError as exc:
            print(f"Error: GEMINI_API_KEY is required ({exc})", file=sys.stderr)
            return 2
        except LLMConfigurationError as exc:
            print(f"Error: LLMConfigurationError - {exc}", file=sys.stderr)
            return 2

    if args.subcommand == "guardrail-report":
        runs_dir = Path(args.runs_dir)
        results_file = runs_dir / f"{args.run_id}.jsonl"
        if not results_file.exists():
            print(f"Error: results file not found at {results_file}", file=sys.stderr)
            return 1
        try:
            set_path = Path(args.set)
            if not set_path.exists():
                print(f"Error: dataset file not found at {set_path}", file=sys.stderr)
                return 1
            cases = load_guardrail_set(set_path)
        except Exception as exc:  # noqa: BLE001
            print(f"Error loading dataset: {exc}", file=sys.stderr)
            return 1

        records = load_results(results_file)
        out_dir = Path(args.out_dir)
        out_json = out_dir / f"guardrail_{args.run_id}.json"
        out_md = out_dir / f"guardrail_{args.run_id}.md"

        rep = write_guardrail_report(cases, records, out_json, out_md, args.run_id, set_path=set_path)
        h = rep["layers"]["hybrid"]["all"]
        print(
            f"guardrail-report: hybrid block_rate {h['block_rate']}, "
            f"false_positive_rate {h['false_positive_rate']}, targets_met {rep['targets_met']}"
        )
        return 0

    if args.subcommand == "guardrail-summary":
        run_ids = [r.strip() for r in args.run_ids.split(",") if r.strip()]
        out_dir = Path(args.out_dir)
        reports = []
        for rid in run_ids:
            rep_file = out_dir / f"guardrail_{rid}.json"
            if not rep_file.exists():
                print(f"Error: report file not found at {rep_file}", file=sys.stderr)
                return 1
            try:
                reports.append(json.loads(rep_file.read_text(encoding="utf-8")))
            except Exception as exc:  # noqa: BLE001
                print(f"Error reading report {rep_file}: {exc}", file=sys.stderr)
                return 1

        out_json = out_dir / "guardrail_summary.json"
        out_md = out_dir / "guardrail_summary.md"
        s = write_guardrail_summary(reports, out_json, out_md)
        print(f"guardrail-summary: {s['n_runs']} runs, all_targets_met {s['all_targets_met']}")
        return 0

    cases_path = Path(args.cases)
    if not cases_path.exists():
        print(f"Error: dataset file not found at {cases_path}", file=sys.stderr)
        return 1
    cases = load_cases(cases_path)

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
        if not results_file.exists():
            print(f"Error: results file not found at {results_file}", file=sys.stderr)
            return 1
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
            cases_file=cases_path.as_posix(),
        )
        print(f"Generated report at {out_json} and {out_md}")
        return 0

    if args.subcommand == "compare":
        runs_dir = Path(args.runs_dir)
        groups = []
        for g_str in args.group:
            if "=" not in g_str:
                print(f"Error: invalid group format '{g_str}'. Expected LABEL=run1,run2,...", file=sys.stderr)
                return 1
            label, runs_str = g_str.split("=", 1)
            run_ids = [r.strip() for r in runs_str.split(",") if r.strip()]
            runs_data = []
            for rid in run_ids:
                res_file = runs_dir / f"{rid}.jsonl"
                if not res_file.exists():
                    print(f"Error: results file not found at {res_file}", file=sys.stderr)
                    return 1
                judge_file = runs_dir / f"{rid}.judge.jsonl"
                results = list(load_results(res_file).values())
                judgments = list(load_judgments(judge_file).values()) if judge_file.exists() else None
                runs_data.append((rid, results, judgments))
            groups.append((label, runs_data))

        out_dir = Path(args.out_dir)
        out_json = out_dir / f"eval_{args.name}.json"
        out_md = out_dir / f"eval_{args.name}.md"

        write_comparison(
            cases=cases,
            groups=groups,
            out_json=out_json,
            out_md=out_md,
            name=args.name,
        )
        print(f"Generated comparison report at {out_json} and {out_md}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
