"""Evaluation CLI entry point for offline regression, model execution, judge, and reports."""
import argparse
import json
import sys
from pathlib import Path

from src.config import settings
from src.core.llm import LLMConfigurationError, LLMNotConfiguredError
from src.eval.ablation import write_ablation
from src.eval.annotator import compare_raters, import_annotator_xlsx
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
from src.eval.human_validation import (
    CASES_FILE as HV_CASES_FILE,
)
from src.eval.human_validation import (
    SAMPLE_DIR as HV_SAMPLE_DIR,
)
from src.eval.human_validation import (
    SOURCE_RUN as HV_SOURCE_RUN,
)
from src.eval.human_validation import (
    agreement,
    file_sha256,
    parse_answers,
    write_agreement_report,
    write_human_sample2,
    write_sample,
)
from src.eval.judge import load_judgments, run_judge
from src.eval.judge_calibration import (
    DEFAULT_ANNOTATOR_ANSWERS,
    DEFAULT_AUTHOR_ANSWERS,
    DEFAULT_OUT_DIR,
    DEFAULT_SAMPLE_PATH,
    run_judge_calibration,
    write_judge_calibration_report,
)
from src.eval.offline import run_offline
from src.eval.report import write_report
from src.eval.run_context import DEFAULT_RUN_CONTEXT_PATH, TIER_LABELS, update_run_context
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


def _cmd_human_sample(args: argparse.Namespace) -> int:
    try:
        sample = write_sample(
            out_dir=args.out_dir,
            cases_path=args.cases,
            run_id=args.run_id,
            runs_dir=args.runs_dir,
        )
        print(f"human-sample: {len(sample['items'])} items written to {args.out_dir}")
        return 0
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Error creating human validation sample: {exc}", file=sys.stderr)
        return 1


def _cmd_human_sample2(args: argparse.Namespace) -> int:
    try:
        sample = write_human_sample2(
            out_dir=args.out_dir,
            size=args.size,
            runs_dir=args.runs_dir,
        )
        print(f"human-sample2: {len(sample['items'])} items written to {args.out_dir}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error creating second human validation sample: {exc}", file=sys.stderr)
        return 1


def _cmd_human_agreement(args: argparse.Namespace) -> int:
    try:
        sample_path = Path(args.sample_dir) / "sample.json"
        if not sample_path.exists():
            print(f"Error: sample file not found at {sample_path}", file=sys.stderr)
            return 1

        answers_path = Path(args.answers)
        if not answers_path.exists():
            print(f"Error: answers file not found at {answers_path}", file=sys.stderr)
            return 1

        cases_path = Path(args.cases)
        if not cases_path.exists():
            print(f"Error: cases file not found at {cases_path}", file=sys.stderr)
            return 1

        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        run_id = sample["source_run"]
        runs_dir = Path(args.runs_dir)
        results_path = runs_dir / f"{run_id}.jsonl"
        judgments_path = runs_dir / f"{run_id}.judge.jsonl"

        if not results_path.exists():
            print(f"Error: results file not found at {results_path}", file=sys.stderr)
            return 1
        if not judgments_path.exists():
            print(f"Error: judgments file not found at {judgments_path}", file=sys.stderr)
            return 1

        if file_sha256(results_path) != sample["records_sha256"]:
            print(f"Error: records file changed since sample ({results_path})", file=sys.stderr)
            return 1
        if file_sha256(judgments_path) != sample["judgments_sha256"]:
            print(f"Error: judgments file changed since sample ({judgments_path})", file=sys.stderr)
            return 1

        cases_list = load_cases(cases_path)
        cases_by_id = {c["id"]: c for c in cases_list}
        hids = [it["hid"] for it in sample["items"]]
        answers = parse_answers(answers_path, hids)
        results = load_results(results_path)
        judgments = load_judgments(judgments_path)

        rep = agreement(
            sample=sample,
            answers=answers,
            cases_by_id=cases_by_id,
            results=results,
            judgments=judgments,
            sample_sha256=file_sha256(sample_path),
            answers_sha256=file_sha256(answers_path),
        )

        out_dir = Path(args.out_dir)
        out_json = out_dir / "human_validation.json"
        out_md = out_dir / "human_validation.md"
        write_agreement_report(rep, out_json, out_md)
        print(
            f"human-agreement: pass_rate_checks {rep['pass_rate_checks']:.4f}, "
            f"acceptable_rate_human {rep['acceptable_rate_human']:.4f}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error computing human agreement: {exc}", file=sys.stderr)
        return 1


def _cmd_human_import(args: argparse.Namespace) -> int:
    try:
        res = import_annotator_xlsx(
            xlsx_path=args.xlsx,
            out_dir=args.out_dir,
            sample_dir=args.sample_dir,
            omit_name=args.omit_name,
        )
        print(
            f"human-import: {res['n_items']} answers and {res['comments_count']} comments written to {res['out_dir']}"
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error importing annotator workbook:\n{exc}", file=sys.stderr)
        return 1


def _cmd_human_raters(args: argparse.Namespace) -> int:
    try:
        rep = compare_raters(
            a_path=args.a,
            b_path=args.b,
            a_name=args.a_name,
            b_name=args.b_name,
            out_dir=args.out_dir,
            sample_dir=args.sample_dir,
        )
        r = rep["fields"]["rota"]
        print(f"human-raters: {rep['a']} vs {rep['b']} ({rep['n_items']} items, rota agree={r['agree']}/{r['n']})")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error comparing rater answers: {exc}", file=sys.stderr)
        return 1


def _cmd_context(args: argparse.Namespace) -> int:
    try:
        run_ids = [r.strip() for r in args.run_ids.split(",") if r.strip()]
        updated = update_run_context(
            run_ids=run_ids,
            tier=args.tier,
            date_str=args.date,
            path=args.file,
        )
        print(f"context: added {len(run_ids)} run(s); total={len(updated)}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error updating run context: {exc}", file=sys.stderr)
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
    p_judge.add_argument("--judge-model", default=None, help="Judge model name (default: EVAL_JUDGE_MODEL)")
    p_judge.add_argument("--judge-prompt", default=None, help="Path to judge prompt Markdown (default: src/prompts/judge.md)")
    p_judge.add_argument("--judge-dir", default=None, help="Directory for judgment JSONL files (default: --runs-dir)")

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
    p_compare.add_argument("--judge-dir", default=None, help="Directory containing .judge.jsonl files (default: --runs-dir)")
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

    # 10. human-sample
    p_hs = subparsers.add_parser("human-sample", help="Generate stratified blind sample for human validation")
    p_hs.add_argument("--run-id", default=HV_SOURCE_RUN, help="Source run ID")
    p_hs.add_argument("--cases", default=HV_CASES_FILE, help="Path to evaluation cases JSONL")
    p_hs.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")
    p_hs.add_argument("--out-dir", default=HV_SAMPLE_DIR, help="Output directory for sample files")

    # 10b. human-sample2
    p_hs2 = subparsers.add_parser("human-sample2", help="Generate balanced blind second sample for judge calibration")
    p_hs2.add_argument("--out-dir", default="reports/human_validation_2", help="Output directory for sample files")
    p_hs2.add_argument("--size", type=int, default=40, help="Total sample size (half failing, half passing)")
    p_hs2.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")

    # 11. human-agreement
    p_ha = subparsers.add_parser("human-agreement", help="Compute human agreement metrics and report")
    p_ha.add_argument("--answers", default=f"{HV_SAMPLE_DIR}/answers.csv", help="Path to filled answers CSV")
    p_ha.add_argument("--sample-dir", default=HV_SAMPLE_DIR, help="Directory containing sample.json")
    p_ha.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")
    p_ha.add_argument("--cases", default=HV_CASES_FILE, help="Path to evaluation cases JSONL")
    p_ha.add_argument("--out-dir", default="reports", help="Output directory for agreement reports")

    # 12. human-import
    p_hi = subparsers.add_parser("human-import", help="Import external annotator .xlsx into CSV and declaration JSON")
    p_hi.add_argument("--xlsx", required=True, help="Path to annotator .xlsx file")
    p_hi.add_argument("--out-dir", required=True, help="Output directory for answers.csv, comments.csv, declaration.json")
    p_hi.add_argument("--sample-dir", default=HV_SAMPLE_DIR, help="Directory containing sample.json")
    p_hi.add_argument(
        "--omit-name",
        action="store_true",
        default=False,
        help="Omit annotator name from declaration.json even when authorized",
    )

    # 13. human-raters
    p_hr = subparsers.add_parser("human-raters", help="Compare two annotator answers CSV files on the same sample")
    p_hr.add_argument("--a", required=True, help="Path to first rater answers CSV")
    p_hr.add_argument("--b", required=True, help="Path to second rater answers CSV")
    p_hr.add_argument("--a-name", required=True, help="Label for first rater")
    p_hr.add_argument("--b-name", required=True, help="Label for second rater")
    p_hr.add_argument("--out-dir", required=True, help="Output directory for raters.json and raters.md")
    p_hr.add_argument("--sample-dir", default=HV_SAMPLE_DIR, help="Directory containing sample.json")

    # 14. context
    p_ctx = subparsers.add_parser("context", help="Declare account tier and date for new run IDs")
    p_ctx.add_argument("--run-ids", required=True, help="Comma-separated run IDs to append")
    p_ctx.add_argument("--tier", required=True, choices=list(TIER_LABELS), help="Gemini account tier")
    p_ctx.add_argument("--date", default=None, help="Run date YYYY-MM-DD (default: UTC today)")
    p_ctx.add_argument("--file", default=str(DEFAULT_RUN_CONTEXT_PATH), help="Path to run_context.json")

    # 15. ablation
    p_abl = subparsers.add_parser("ablation", help="Compare single-layer ablation configurations")
    p_abl.add_argument("--name", required=True, help="Ablation report name")
    p_abl.add_argument("--cases", required=True, help="Path to evaluation cases JSONL")
    p_abl.add_argument("--config", required=True, action="append", help="Config in format LABEL=run1,run2,...")
    p_abl.add_argument("--baseline", required=True, help="Baseline configuration label")
    p_abl.add_argument("--runs-dir", default="reports/eval_runs", help="Directory for raw run JSONL")
    p_abl.add_argument("--out-dir", default="reports", help="Output directory for ablation reports")

    # 16. judge-calibrate
    p_jc = subparsers.add_parser("judge-calibrate", help="Run candidate judge prompt/model over human validation sample")
    p_jc.add_argument("--run-id", required=True, help="Calibration run ID")
    p_jc.add_argument("--judge-model", required=True, help="Candidate judge model name")
    p_jc.add_argument("--judge-prompt", required=True, help="Path to candidate judge prompt file")
    p_jc.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for calibration run JSONL")
    p_jc.add_argument("--sample", default=str(DEFAULT_SAMPLE_PATH), help="Path to sample.json")
    p_jc.add_argument("--runs-dir", default="reports/eval_runs", help="Directory containing source eval run")
    p_jc.add_argument("--sleep", type=float, default=None, help="Pause between items in seconds")

    # 17. judge-calibration-report
    p_jcr = subparsers.add_parser("judge-calibration-report", help="Generate agreement report across calibration runs")
    p_jcr.add_argument("--name", required=True, help="Calibration report name")
    p_jcr.add_argument("--runs", required=True, help="Comma-separated calibration run IDs")
    p_jcr.add_argument("--runs-dir", default=str(DEFAULT_OUT_DIR), help="Directory containing calibration runs")
    p_jcr.add_argument("--author-answers", default=str(DEFAULT_AUTHOR_ANSWERS), help="Author answers CSV path")
    p_jcr.add_argument("--annotator-answers", default=str(DEFAULT_ANNOTATOR_ANSWERS), help="Annotator answers CSV path")
    p_jcr.add_argument("--sample", default=str(DEFAULT_SAMPLE_PATH), help="Path to sample.json")
    p_jcr.add_argument("--out-dir", default="reports", help="Output directory for calibration reports")

    args = parser.parse_args()

    if args.subcommand == "ablation":
        configs: dict[str, list[str]] = {}
        for cfg_str in args.config:
            if "=" not in cfg_str:
                print(f"Error: invalid config '{cfg_str}'. Expected LABEL=run1,run2,...", file=sys.stderr)
                return 1
            lbl, runs_csv = cfg_str.split("=", 1)
            lbl = lbl.strip()
            rids = [r.strip() for r in runs_csv.split(",") if r.strip()]
            configs[lbl] = rids
        try:
            rep = write_ablation(
                name=args.name,
                cases_path=args.cases,
                configs=configs,
                baseline=args.baseline,
                runs_dir=args.runs_dir,
                out_dir=args.out_dir,
            )
            print(f"Generated ablation report for {len(rep['configs'])} configs at {args.out_dir}/{args.name}.md")
            return 0
        except (ValueError, FileNotFoundError) as exc:
            print(f"Error generating ablation report: {exc}", file=sys.stderr)
            return 1

    if args.subcommand == "judge-calibrate":
        if not settings.GEMINI_API_KEY:
            print(
                "Error: GEMINI_API_KEY environment variable is required to run judge calibration.",
                file=sys.stderr,
            )
            return 2
        try:
            summary = run_judge_calibration(
                run_id=args.run_id,
                judge_model=args.judge_model,
                prompt_path=args.judge_prompt,
                out_dir=args.out_dir,
                sample_path=args.sample,
                runs_dir=args.runs_dir,
                sleep_s=args.sleep,
            )
            print(
                f"judge-calibrate '{args.run_id}': attempted={summary['attempted']}, "
                f"ok={summary['ok']}, errors={summary['errors']}, skipped={summary['skipped']}"
            )
            return 0 if not summary["errors"] else 1
        except (ValueError, FileNotFoundError, LLMConfigurationError, LLMNotConfiguredError) as exc:
            print(f"Error running judge calibration: {exc}", file=sys.stderr)
            return 1

    if args.subcommand == "judge-calibration-report":
        rids = [r.strip() for r in args.runs.split(",") if r.strip()]
        ann_arg = (args.annotator_answers or "").strip()
        annot_opt: str | None = None if ann_arg.lower() in ("", "none", "null") else ann_arg
        try:
            rep = write_judge_calibration_report(
                name=args.name,
                run_ids=rids,
                runs_dir=args.runs_dir,
                author_answers=args.author_answers,
                annotator_answers=annot_opt,
                sample_path=args.sample,
                out_dir=args.out_dir,
            )
            print(f"Generated calibration report ({len(rep['candidates'])} candidates) at {args.out_dir}/{args.name}.md")
            return 0
        except (ValueError, FileNotFoundError) as exc:
            print(f"Error generating calibration report: {exc}", file=sys.stderr)
            return 1

    if args.subcommand == "offline":
        return _cmd_offline(DEFAULT_CASES_PATH)

    if args.subcommand == "human-sample":
        return _cmd_human_sample(args)

    if args.subcommand == "human-sample2":
        return _cmd_human_sample2(args)

    if args.subcommand == "human-agreement":
        return _cmd_human_agreement(args)

    if args.subcommand == "human-import":
        return _cmd_human_import(args)

    if args.subcommand == "human-raters":
        return _cmd_human_raters(args)

    if args.subcommand == "context":
        return _cmd_context(args)

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

        try:
            summary = run_eval(
                cases=cases,
                results_path=results_file,
                run_id=args.run_id,
                sleep_s=args.sleep,
                max_cases=args.max_cases,
                only=only_list,
            )
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
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
        judge_dir = Path(args.judge_dir) if args.judge_dir else Path(args.runs_dir)
        judge_file = judge_dir / f"{args.run_id}.judge.jsonl"
        judge_model_name = args.judge_model or settings.EVAL_JUDGE_MODEL

        try:
            summary = run_judge(
                cases=cases,
                results_path=results_file,
                judgments_path=judge_file,
                sleep_s=args.sleep,
                prompt_path=args.judge_prompt,
                judge_model_name=judge_model_name,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
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
        judge_dir = Path(args.judge_dir) if args.judge_dir else runs_dir
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
                judge_file = judge_dir / f"{rid}.judge.jsonl"
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
