"""Offline tests for the second blind human validation sample and calibration updates."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from langchain_core.messages import AIMessage

from src.eval.cases import load_cases
from src.eval.checks import evaluate_case
from src.eval.human_validation import write_human_sample2
from src.eval.judge_calibration import build_judge_calibration_report, run_judge_calibration
from src.eval.runner import load_results
from tests.fakes import ScriptedChatModel

ROOT = Path(__file__).resolve().parent.parent


def test_write_human_sample2_is_deterministic_balanced_disjoint_and_blind(tmp_path: Path) -> None:
    dir_a = tmp_path / "sample2_a"
    dir_b = tmp_path / "sample2_b"
    write_human_sample2(dir_a, size=40)
    write_human_sample2(dir_b, size=40)

    sample_json_a = (dir_a / "sample.json").read_text(encoding="utf-8")
    assert sample_json_a == (dir_b / "sample.json").read_text(encoding="utf-8")
    assert (dir_a / "form.md").read_text(encoding="utf-8") == (dir_b / "form.md").read_text(encoding="utf-8")
    assert not (dir_a / "answers.csv").exists()

    sample2 = json.loads(sample_json_a)
    items = sample2["items"]
    assert len(items) == 40
    assert [it["hid"] for it in items] == [f"g{i:02d}" for i in range(1, 41)]

    case_ids = [it["case_id"] for it in items]
    assert len(set(case_ids)) == 40

    sample1 = json.loads((ROOT / "reports" / "human_validation" / "sample.json").read_text(encoding="utf-8"))
    src_run1 = str(sample1.get("source_run") or "")
    sample1_pairs = {(str(it.get("run_id") or src_run1), it["case_id"]) for it in sample1["items"]}
    sample2_pairs = {(it["run_id"], it["case_id"]) for it in items}
    assert sample1_pairs.isdisjoint(sample2_pairs)

    cases_cache: dict[str, dict] = {}
    results_cache: dict[str, dict] = {}
    passed = 0
    failed = 0
    for item in items:
        cfile = item["cases_file"]
        rid = item["run_id"]
        if cfile not in cases_cache:
            cases_cache[cfile] = {c["id"]: c for c in load_cases(ROOT / cfile)}
        if rid not in results_cache:
            results_cache[rid] = load_results(ROOT / "reports" / "eval_runs" / f"{rid}.jsonl")
        case = cases_cache[cfile][item["case_id"]]
        rec = results_cache[rid][item["case_id"]]
        assert rec["status"] == "ok"
        check_res = evaluate_case(case, rec)
        if check_res["passed"]:
            passed += 1
        else:
            failed += 1
    assert passed == 20 and failed == 20

    form_text = (dir_a / "form.md").read_text(encoding="utf-8")
    form_without_hids = re.sub(r"(?m)^### [a-z]\d{2}\s*$", "", form_text)
    form_without_hids = re.sub(r"Os ids `[a-z]\d{2}` a `[a-z]\d{2}`", "", form_without_hids)
    for cid in case_ids:
        assert not re.search(rf"\b{re.escape(cid)}\b", form_without_hids), f"Leaked case_id {cid}"
    assert "deterministic" not in form_text.lower()

    with open(dir_a / "answers_template.csv", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 40


def test_run_judge_calibration_reads_per_item_run_id_and_cases_file(tmp_path: Path) -> None:
    sample_dir = tmp_path / "sample2_sub"
    write_human_sample2(sample_dir, size=40)
    full = json.loads((sample_dir / "sample.json").read_text(encoding="utf-8"))
    subset_items = full["items"][:4]
    subset_path = tmp_path / "subset_sample.json"
    subset_path.write_text(
        json.dumps({"seed": full["seed"], "source_run": None, "cases_file": None, "items": subset_items}),
        encoding="utf-8",
    )

    judge_payload = json.dumps(
        {
            "grounded": 5,
            "answers_question": 5,
            "abstained": False,
            "abstained_cleanly": True,
            "reason": "Resposta fundamentada nas evidências.",
        }
    )
    fake_judge = ScriptedChatModel(responses=[AIMessage(content=judge_payload) for _ in subset_items])

    out_dir = tmp_path / "calib_runs"
    res = run_judge_calibration(
        run_id="mock-calib-2",
        judge_model="fake-judge",
        prompt_path="src/prompts/judge.md",
        model=fake_judge,
        out_dir=out_dir,
        sample_path=subset_path,
        runs_dir=ROOT / "reports" / "eval_runs",
        sleep_s=0.0,
    )
    assert res["ok"] == 4
    assert res["errors"] == 0
    assert (out_dir / "mock-calib-2.jsonl").exists()


def test_build_judge_calibration_report_supports_single_rater_mode(tmp_path: Path) -> None:
    sample_dir = tmp_path / "sample2_sr"
    write_human_sample2(sample_dir, size=40)
    full = json.loads((sample_dir / "sample.json").read_text(encoding="utf-8"))
    items = full["items"][:6]
    sample_path = tmp_path / "sr_sample.json"
    sample_path.write_text(json.dumps({"items": items}), encoding="utf-8")

    answers_path = tmp_path / "author_answers.csv"
    with open(answers_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["id", "rota", "deveria_abster", "aceitavel", "absteve", "fundamentacao"])
        for idx, it in enumerate(items):
            writer.writerow(
                [it["hid"], "conta", "N", "S" if idx % 2 == 0 else "N", "N", "5" if idx % 2 == 0 else "2"]
            )

    cal_dir = tmp_path / "cal"
    cal_dir.mkdir()
    prompt_sha = "deadbeef" * 8
    rows = [
        {
            "hid": it["hid"],
            "status": "ok",
            "judge_model": "fake-j",
            "prompt_sha256": prompt_sha,
            "acceptable": (idx % 2 == 0),
            "abstained": False,
            "grounded": 5 if idx % 2 == 0 else 2,
        }
        for idx, it in enumerate(items)
    ]
    (cal_dir / "r1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    report = build_judge_calibration_report(
        ["r1"],
        runs_dir=cal_dir,
        author_answers=answers_path,
        annotator_answers=None,
        sample_path=sample_path,
    )
    assert report["humans"] is None
    assert report["items"] == 6
    assert list(report["candidates"][0]["raters"].keys()) == ["autor"]
    assert report["candidates"][0]["raters"]["autor"]["agreement"] == 6
