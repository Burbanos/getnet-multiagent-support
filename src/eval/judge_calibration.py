"""LLM judge calibration runner and human-agreement report generator (§3.5)."""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import settings
from src.core.llm import get_chat_model
from src.eval.cases import load_cases
from src.eval.human_validation import judge_acceptable, parse_answers
from src.eval.judge import build_judge_input, error_code, parse_judgment, response_text
from src.eval.runner import load_results

DEFAULT_OUT_DIR = Path("reports/judge_calibration")
DEFAULT_SAMPLE_PATH = Path("reports/human_validation/sample.json")
DEFAULT_AUTHOR_ANSWERS = Path("reports/human_validation/answers.csv")
DEFAULT_ANNOTATOR_ANSWERS = Path("reports/human_validation_annotator/answers.csv")


def _prompt_text_and_sha(prompt_path: str | Path) -> tuple[str, str]:
    text = Path(prompt_path).read_bytes().decode("utf-8").replace("\r\n", "\n")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, digest


def _load_calibration_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            rows.append(json.loads(raw_line))
        except json.JSONDecodeError:
            continue
    return rows


def run_judge_calibration(
    run_id: str,
    judge_model: str,
    prompt_path: str | Path,
    model: Any | None = None,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    sample_path: str | Path = DEFAULT_SAMPLE_PATH,
    runs_dir: str | Path = Path("reports/eval_runs"),
    sleep_s: float | None = None,
) -> dict[str, Any]:
    """Run candidate judge over all 30 items of human_validation sample with resumption."""
    prompt_text, prompt_sha = _prompt_text_and_sha(prompt_path)
    out_path = Path(out_dir) / f"{run_id}.jsonl"

    existing_rows = _load_calibration_rows(out_path)
    done_hids: set[str] = set()
    for row in existing_rows:
        if row.get("judge_model") != judge_model or row.get("prompt_sha256") != prompt_sha:
            raise ValueError(
                f"Cannot resume calibration run '{run_id}': existing records use "
                f"model={row.get('judge_model')}, prompt_sha256={row.get('prompt_sha256')}"
            )
        if row.get("status") == "ok" and row.get("hid"):
            done_hids.add(str(row["hid"]))

    sample = json.loads(Path(sample_path).read_text(encoding="utf-8"))
    default_source_run = sample.get("source_run")
    default_cases_file = sample.get("cases_file")
    runs_base = Path(runs_dir)

    cases_cache: dict[str, dict[str, dict[str, Any]]] = {}
    results_cache: dict[str, dict[str, dict[str, Any]]] = {}

    judge = model if model is not None else get_chat_model(judge_model)
    delay = sleep_s if sleep_s is not None else (0.0 if model is not None else settings.EVAL_SLEEP_S)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    attempted = 0
    ok = 0
    errors = 0
    skipped = 0

    with open(out_path, "a", encoding="utf-8", newline="\n") as f:
        for item in sample["items"]:
            hid = str(item["hid"])
            cid = str(item["case_id"])
            if hid in done_hids:
                skipped += 1
                continue

            item_cases_file = str(item.get("cases_file") or default_cases_file)
            item_run_id = str(item.get("run_id") or default_source_run)
            if item_cases_file not in cases_cache:
                cases_cache[item_cases_file] = {c["id"]: c for c in load_cases(item_cases_file)}
            if item_run_id not in results_cache:
                results_cache[item_run_id] = load_results(runs_base / f"{item_run_id}.jsonl")

            user_input = build_judge_input(
                cases_cache[item_cases_file][cid],
                results_cache[item_run_id][cid],
            )
            messages = [
                SystemMessage(content=prompt_text),
                HumanMessage(content=user_input),
            ]

            row: dict[str, Any]
            try:
                resp = judge.invoke(messages)
                raw_out = response_text(resp)
            except Exception as exc:  # noqa: BLE001
                row = {
                    "hid": hid,
                    "case_id": cid,
                    "judge_model": judge_model,
                    "prompt_sha256": prompt_sha,
                    "grounded": None,
                    "answers_question": None,
                    "abstained": None,
                    "acceptable": None,
                    "acceptable_source": None,
                    "rationale": "",
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error_code": error_code(exc),
                }
                errors += 1
            else:
                try:
                    parsed = parse_judgment(raw_out)
                except ValueError:
                    row = {
                        "hid": hid,
                        "case_id": cid,
                        "judge_model": judge_model,
                        "prompt_sha256": prompt_sha,
                        "grounded": None,
                        "answers_question": None,
                        "abstained": None,
                        "acceptable": None,
                        "acceptable_source": None,
                        "rationale": "",
                        "status": "error",
                        "error_type": "unparseable",
                        "error_code": None,
                    }
                    errors += 1
                else:
                    if "acceptable" in parsed:
                        acceptable = parsed["acceptable"]
                        acc_source = "model"
                    else:
                        acceptable = judge_acceptable(parsed)
                        acc_source = "derived"
                    row = {
                        "hid": hid,
                        "case_id": cid,
                        "judge_model": judge_model,
                        "prompt_sha256": prompt_sha,
                        "grounded": parsed["grounded"],
                        "answers_question": parsed["answers_question"],
                        "abstained": parsed["abstained"],
                        "acceptable": acceptable,
                        "acceptable_source": acc_source,
                        "rationale": parsed["rationale"],
                        "status": "ok",
                    }
                    ok += 1

            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            attempted += 1

            if delay and delay > 0:
                time.sleep(delay)

    return {
        "run_id": run_id,
        "judge_model": judge_model,
        "prompt_sha256": prompt_sha,
        "attempted": attempted,
        "ok": ok,
        "errors": errors,
        "skipped": skipped,
    }


def _cohens_kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = sum(1 for x in a if x) / n
    pb = sum(1 for y in b if y) / n
    pe = pa * pb + (1.0 - pa) * (1.0 - pb)
    return None if pe == 1.0 else (po - pe) / (1.0 - pe)


def _gwets_ac1(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    q = (sum(1 for x in a if x) / n + sum(1 for y in b if y) / n) / 2.0
    pe = 2.0 * q * (1.0 - q)
    return None if pe == 1.0 else (po - pe) / (1.0 - pe)


def _majority_value(vals: list[Any]) -> Any:
    if not vals:
        return None
    counts: dict[Any, int] = {}
    first_idx: dict[Any, int] = {}
    for idx, v in enumerate(vals):
        counts[v] = counts.get(v, 0) + 1
        first_idx.setdefault(v, idx)
    return max(counts, key=lambda v: (counts[v], -first_idx[v]))


def build_judge_calibration_report(
    run_ids: list[str],
    runs_dir: str | Path = DEFAULT_OUT_DIR,
    author_answers: str | Path = DEFAULT_AUTHOR_ANSWERS,
    annotator_answers: str | Path | None = DEFAULT_ANNOTATOR_ANSWERS,
    sample_path: str | Path = DEFAULT_SAMPLE_PATH,
) -> dict[str, Any]:
    """Build agreement, κ, AC1, grounding and stability report across candidate judge runs."""
    if not run_ids:
        raise ValueError("At least one calibration run ID is required")

    sample = json.loads(Path(sample_path).read_text(encoding="utf-8"))
    hids = [str(it["hid"]) for it in sample["items"]]
    author = parse_answers(author_answers, hids)
    annotator = parse_answers(annotator_answers, hids) if annotator_answers is not None else None

    if annotator is not None:
        auth_acc = [bool(author[h]["aceitavel"]) for h in hids]
        anno_acc = [bool(annotator[h]["aceitavel"]) for h in hids]
        humans: dict[str, Any] | None = {
            "agreement": sum(1 for x, y in zip(auth_acc, anno_acc) if x == y),
            "kappa": _cohens_kappa(auth_acc, anno_acc),
            "ac1": _gwets_ac1(auth_acc, anno_acc),
        }
        raters_data: tuple[tuple[str, dict[str, dict[str, Any]]], ...] = (
            ("autor", author),
            ("anotador", annotator),
        )
    else:
        humans = None
        raters_data = (("autor", author),)

    r_dir = Path(runs_dir)
    grouped: dict[tuple[str, str], list[tuple[str, dict[str, dict[str, Any]]]]] = {}
    for rid in run_ids:
        r_path = r_dir / f"{rid}.jsonl"
        if not r_path.exists():
            raise ValueError(f"Calibration run file not found: {r_path}")
        raw_rows = _load_calibration_rows(r_path)
        by_hid: dict[str, dict[str, Any]] = {}
        pairs_seen: set[tuple[str, str]] = set()
        for row in raw_rows:
            if row.get("hid"):
                by_hid[str(row["hid"])] = row
            if row.get("judge_model") and row.get("prompt_sha256"):
                pairs_seen.add((str(row["judge_model"]), str(row["prompt_sha256"])))
        if len(pairs_seen) != 1:
            raise ValueError(f"Calibration run '{rid}' has missing or mixed (judge_model, prompt_sha256): {pairs_seen}")
        cand_key = next(iter(pairs_seen))
        grouped.setdefault(cand_key, []).append((rid, by_hid))

    candidates: list[dict[str, Any]] = []

    for (j_model, p_sha), cand_runs in grouped.items():
        maj_acc: dict[str, bool] = {}
        maj_abs: dict[str, bool] = {}
        maj_gnd: dict[str, int] = {}

        for h in hids:
            ok_rows = [
                by_hid[h]
                for _, by_hid in cand_runs
                if h in by_hid and by_hid[h].get("status") == "ok"
            ]
            if not ok_rows:
                continue
            acc_vals = [bool(r["acceptable"]) for r in ok_rows if isinstance(r.get("acceptable"), bool)]
            abs_vals = [bool(r["abstained"]) for r in ok_rows if isinstance(r.get("abstained"), bool)]
            gnd_vals = [int(r["grounded"]) for r in ok_rows if type(r.get("grounded")) is int]
            if acc_vals:
                maj_acc[h] = bool(_majority_value(acc_vals))
            if abs_vals:
                maj_abs[h] = bool(_majority_value(abs_vals))
            if gnd_vals:
                maj_gnd[h] = int(_majority_value(gnd_vals))

        raters_out: dict[str, dict[str, Any]] = {}
        abs_kappa_out: dict[str, float | None] = {}
        grounding_out: dict[str, dict[str, Any]] = {}

        acc_hids = [h for h in hids if h in maj_acc]
        abs_hids = [h for h in hids if h in maj_abs]
        gnd_hids = [h for h in hids if h in maj_gnd]

        for rname, ans_map in raters_data:
            h_vec = [bool(ans_map[h]["aceitavel"]) for h in acc_hids]
            j_vec = [maj_acc[h] for h in acc_hids]
            n_acc = len(acc_hids)
            agree_acc = sum(1 for x, y in zip(h_vec, j_vec) if x == y)
            neg_map = {h: maj_acc.get(h) for h in hids if not ans_map[h]["aceitavel"]}
            raters_out[rname] = {
                "agreement": agree_acc,
                "n": n_acc,
                "kappa": _cohens_kappa(h_vec, j_vec),
                "ac1": _gwets_ac1(h_vec, j_vec),
                "judge_on_rater_negatives": neg_map,
            }

            h_abs_vec = [bool(ans_map[h]["absteve"]) for h in abs_hids]
            j_abs_vec = [maj_abs[h] for h in abs_hids]
            abs_kappa_out[rname] = _cohens_kappa(h_abs_vec, j_abs_vec)

            exact_g = sum(1 for h in gnd_hids if maj_gnd[h] == ans_map[h]["fundamentacao"])
            mad_g = (
                math.fsum(abs(maj_gnd[h] - ans_map[h]["fundamentacao"]) for h in gnd_hids) / len(gnd_hids)
                if gnd_hids
                else None
            )
            grounding_out[rname] = {
                "exact": exact_g,
                "mean_abs_diff": mad_g,
            }

        stability: float | None = None
        if len(cand_runs) >= 2:
            pair_rates: list[float] = []
            for i in range(len(cand_runs)):
                for j in range(i + 1, len(cand_runs)):
                    rows_i = cand_runs[i][1]
                    rows_j = cand_runs[j][1]
                    common = [
                        h
                        for h in hids
                        if rows_i.get(h, {}).get("status") == "ok"
                        and rows_j.get(h, {}).get("status") == "ok"
                        and isinstance(rows_i[h].get("acceptable"), bool)
                        and isinstance(rows_j[h].get("acceptable"), bool)
                    ]
                    if common:
                        agree_p = sum(
                            1 for h in common if rows_i[h]["acceptable"] == rows_j[h]["acceptable"]
                        ) / len(common)
                        pair_rates.append(agree_p)
            stability = (math.fsum(pair_rates) / len(pair_rates)) if pair_rates else None

        candidates.append({
            "judge_model": j_model,
            "prompt_sha256": p_sha,
            "runs": [rid for rid, _ in cand_runs],
            "raters": raters_out,
            "abstention_kappa": abs_kappa_out,
            "grounding": grounding_out,
            "stability": stability,
        })

    return {
        "items": len(hids),
        "humans": humans,
        "candidates": candidates,
    }


def _fmt_num(val: float | None, nd: int = 3) -> str:
    return "n/d" if val is None else f"{val:.{nd}f}".replace(".", ",")


def _render_calibration_md(report: dict[str, Any], name: str) -> str:
    h = report["humans"]
    n_items = report["items"]
    lines: list[str] = [
        f"# Calibração do Juiz: {name}",
        "",
        f"Amostra de {n_items} itens.",
        "",
        "## Humanos vs Juízes Candidatos",
        "",
        "| Comparação | Concordância | κ de Cohen | AC1 de Gwet | Estabilidade |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    if h is not None:
        lines.append(
            f"| Humanos (`autor` × `anotador`) | {h['agreement']}/{n_items} | {_fmt_num(h['kappa'])} | {_fmt_num(h['ac1'])} | — |"
        )
    for idx, c in enumerate(report["candidates"], start=1):
        label = f"Candidato {idx} (`{c['judge_model']}`, `{c['prompt_sha256'][:8]}`)"
        stab = _fmt_num(c["stability"])
        for rname, r in c["raters"].items():
            lines.append(
                f"| {label} × `{rname}` | {r['agreement']}/{r['n']} | {_fmt_num(r['kappa'])} | {_fmt_num(r['ac1'])} | {stab} |"
            )

    lines.extend(["", "## Negativos humanos, abstenção e fundamentação", ""])
    for idx, c in enumerate(report["candidates"], start=1):
        lines.append(f"### Candidato {idx}: `{c['judge_model']}` (`{c['prompt_sha256'][:12]}`)")
        lines.append("")
        lines.append(f"- **Execuções:** {', '.join(f'`{r}`' for r in c['runs'])}")
        for rname, neg_source in c["raters"].items():
            g = c["grounding"][rname]
            ak = _fmt_num(c["abstention_kappa"][rname])
            neg = neg_source["judge_on_rater_negatives"]
            neg_str = ", ".join(f"`{k}`={v}" for k, v in sorted(neg.items())) or "nenhum"
            lines.append(
                f"- **Contra `{rname}`:** κ(abstenção)={ak}; fundamentação exata={g['exact']}/{n_items}, "
                f"MAE={_fmt_num(g['mean_abs_diff'])}; negativos={neg_str}"
            )
        lines.append("")

    return "\n".join(lines)


def write_judge_calibration_report(
    name: str,
    run_ids: list[str],
    runs_dir: str | Path = DEFAULT_OUT_DIR,
    author_answers: str | Path = DEFAULT_AUTHOR_ANSWERS,
    annotator_answers: str | Path | None = DEFAULT_ANNOTATOR_ANSWERS,
    sample_path: str | Path = DEFAULT_SAMPLE_PATH,
    out_dir: str | Path = Path("reports"),
) -> dict[str, Any]:
    """Build judge calibration report and write `<out_dir>/<name>.json` and `<out_dir>/<name>.md`."""
    report = build_judge_calibration_report(
        run_ids=run_ids,
        runs_dir=runs_dir,
        author_answers=author_answers,
        annotator_answers=annotator_answers,
        sample_path=sample_path,
    )
    out_base = Path(out_dir)
    out_base.mkdir(parents=True, exist_ok=True)
    json_path = out_base / f"{name}.json"
    md_path = out_base / f"{name}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    md_path.write_text(_render_calibration_md(report, name), encoding="utf-8", newline="\n")
    return report
