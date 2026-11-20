"""Offline tests for judge_calibration runner, parse_judgment acceptable key, and calibration reports."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage

from src.eval.__main__ import main as eval_cli_main
from src.eval.human_validation import parse_answers
from src.eval.judge import parse_judgment
from src.eval.judge_calibration import (
    build_judge_calibration_report,
    run_judge_calibration,
    write_judge_calibration_report,
)
from tests.fakes import ScriptedChatModel


def _load_sample_and_humans() -> tuple[list[str], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    sample = json.loads(Path("reports/human_validation/sample.json").read_text(encoding="utf-8"))
    hids = [it["hid"] for it in sample["items"]]
    author = parse_answers("reports/human_validation/answers.csv", hids)
    annotator = parse_answers("reports/human_validation_annotator/answers.csv", hids)
    return hids, author, annotator


def _cohens_kappa(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa = sum(a) / n
    pb = sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else (po - pe) / (1 - pe)


def _gwets_ac1(a: list[bool], b: list[bool]) -> float | None:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    q = (sum(a) / n + sum(b) / n) / 2
    pe = 2 * q * (1 - q)
    return None if pe == 1 else (po - pe) / (1 - pe)


def test_parse_judgment_accepts_optional_boolean_acceptable_and_rejects_non_bool() -> None:
    plain = parse_judgment('{"grounded": 5, "answers_question": 5, "abstained": false, "rationale": "ok"}')
    assert "acceptable" not in plain

    with_true = parse_judgment('{"grounded": 4, "answers_question": 5, "abstained": false, "acceptable": true}')
    assert with_true["acceptable"] is True

    with_false = parse_judgment('{"grounded": 5, "answers_question": 5, "abstained": false, "acceptable": false}')
    assert with_false["acceptable"] is False

    for bad in (
        '{"grounded": 5, "answers_question": 5, "abstained": false, "acceptable": "yes"}',
        '{"grounded": 5, "answers_question": 5, "abstained": false, "acceptable": 1}',
        '{"grounded": 5, "answers_question": 5, "abstained": false, "acceptable": null}',
    ):
        with pytest.raises(ValueError):
            parse_judgment(bad)


def test_run_judge_calibration_model_vs_derived_and_resume_guards(tmp_path: Path) -> None:
    hids, author, _ = _load_sample_and_humans()
    p1 = tmp_path / "cand1.md"
    p1.write_bytes(b"# Judge A\r\nReturn JSON.\r\n")
    p2 = tmp_path / "cand2.md"
    p2.write_text("# Judge B\nReturn JSON.\n", encoding="utf-8")
    expected_sha = hashlib.sha256(b"# Judge A\nReturn JSON.\n").hexdigest()

    out_dir = tmp_path / "jc"
    resps_partial = [
        AIMessage(
            content=json.dumps(
                {
                    "grounded": 5,
                    "answers_question": 5,
                    "abstained": author[h]["absteve"],
                    "acceptable": bool(author[h]["aceitavel"]),
                    "rationale": "ok",
                }
            )
        )
        for h in hids[:10]
    ] + [AIMessage(content="not json")] * 20

    s1 = run_judge_calibration("run-a", "gemini-3.6-flash", p1, model=ScriptedChatModel(responses=resps_partial), out_dir=out_dir)
    assert s1["ok"] == 10 and s1["errors"] == 20 and s1["prompt_sha256"] == expected_sha

    resps_rest = [
        AIMessage(
            content=json.dumps(
                {
                    "grounded": 5 if author[h]["aceitavel"] else 2,
                    "answers_question": 5 if author[h]["aceitavel"] else 2,
                    "abstained": author[h]["absteve"],
                    "rationale": "derived",
                }
            )
        )
        for h in hids[10:]
    ]
    s2 = run_judge_calibration("run-a", "gemini-3.6-flash", p1, model=ScriptedChatModel(responses=resps_rest), out_dir=out_dir)
    assert s2["skipped"] == 10 and s2["attempted"] == 20 and s2["ok"] == 20

    rows = [json.loads(ln) for ln in (out_dir / "run-a.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    by_hid = {r["hid"]: r for r in rows}
    assert len(by_hid) == 30
    assert sum(1 for r in by_hid.values() if r["acceptable_source"] == "model") == 10
    assert sum(1 for r in by_hid.values() if r["acceptable_source"] == "derived") == 20

    with pytest.raises(ValueError, match="Cannot resume"):
        run_judge_calibration("run-a", "gemini-3.6-flash", p2, model=ScriptedChatModel(responses=[]), out_dir=out_dir)
    with pytest.raises(ValueError, match="Cannot resume"):
        run_judge_calibration("run-a", "other-model", p1, model=ScriptedChatModel(responses=[]), out_dir=out_dir)


def test_build_and_write_judge_calibration_report_metrics_and_stability(tmp_path: Path) -> None:
    hids, author, annot = _load_sample_and_humans()
    p1 = tmp_path / "p1.md"
    p1.write_text("# Cand 1\n", encoding="utf-8")
    p2 = tmp_path / "p2.md"
    p2.write_text("# Cand 2\n", encoding="utf-8")
    jc_dir = tmp_path / "jc"

    # Candidate 1 run 1 & run 2: differ only on h01 to test stability < 1.0 and tie-breaking -> first run (True)
    msgs_c1_r1 = [
        AIMessage(
            content=json.dumps(
                {
                    "grounded": 5,
                    "answers_question": 5,
                    "abstained": author[h]["absteve"],
                    "acceptable": bool(author[h]["aceitavel"]),
                    "rationale": "r1",
                }
            )
        )
        for h in hids
    ]
    msgs_c1_r2 = [
        AIMessage(
            content=json.dumps(
                {
                    "grounded": 4,
                    "answers_question": 5,
                    "abstained": author[h]["absteve"],
                    "acceptable": (not author[h]["aceitavel"]) if h == "h01" else bool(author[h]["aceitavel"]),
                    "rationale": "r2",
                }
            )
        )
        for h in hids
    ]
    msgs_c2 = [
        AIMessage(
            content=json.dumps(
                {
                    "grounded": 5,
                    "answers_question": 5,
                    "abstained": annot[h]["absteve"],
                    "acceptable": bool(annot[h]["aceitavel"]),
                    "rationale": "c2",
                }
            )
        )
        for h in hids
    ]

    run_judge_calibration("c1-1", "gemini-3.6-flash", p1, model=ScriptedChatModel(responses=msgs_c1_r1), out_dir=jc_dir)
    run_judge_calibration("c1-2", "gemini-3.6-flash", p1, model=ScriptedChatModel(responses=msgs_c1_r2), out_dir=jc_dir)
    run_judge_calibration("c2-1", "gemini-3.8-flash", p2, model=ScriptedChatModel(responses=msgs_c2), out_dir=jc_dir)

    rep = build_judge_calibration_report(["c1-1", "c1-2", "c2-1"], runs_dir=jc_dir)
    assert rep["items"] == 30
    assert math.isclose(rep["humans"]["kappa"], _cohens_kappa([author[h]["aceitavel"] for h in hids], [annot[h]["aceitavel"] for h in hids]), abs_tol=1e-6)
    assert len(rep["candidates"]) == 2

    c1, c2 = rep["candidates"]
    assert c1["runs"] == ["c1-1", "c1-2"]
    assert math.isclose(c1["stability"], 29 / 30, abs_tol=1e-6)
    # Tie on h01 broken by first run -> matches author 30/30
    assert c1["raters"]["autor"]["agreement"] == 30
    assert c1["raters"]["autor"]["judge_on_rater_negatives"] == {"h02": False}
    assert math.isclose(
        c1["raters"]["anotador"]["ac1"],
        _gwets_ac1([annot[h]["aceitavel"] for h in hids], [author[h]["aceitavel"] for h in hids]),
        abs_tol=1e-6,
    )

    assert c2["runs"] == ["c2-1"]
    assert c2["stability"] is None
    assert c2["raters"]["anotador"]["agreement"] == 30

    out_dir = tmp_path / "rep_out"
    written = write_judge_calibration_report("cal_rep", ["c1-1", "c1-2", "c2-1"], runs_dir=jc_dir, out_dir=out_dir)
    assert written == rep
    assert (out_dir / "cal_rep.json").exists()
    md = (out_dir / "cal_rep.md").read_text(encoding="utf-8")
    assert "Calibração do Juiz" in md
    assert "AC1 de Gwet" in md


def test_cli_judge_calibration_report_subcommand(tmp_path: Path, monkeypatch: Any) -> None:
    hids, author, _ = _load_sample_and_humans()
    p = tmp_path / "p.md"
    p.write_text("# Prompt\n", encoding="utf-8")
    jc_dir = tmp_path / "jc"
    msgs = [
        AIMessage(
            content=json.dumps(
                {
                    "grounded": 5,
                    "answers_question": 5,
                    "abstained": author[h]["absteve"],
                    "acceptable": bool(author[h]["aceitavel"]),
                    "rationale": "ok",
                }
            )
        )
        for h in hids
    ]
    run_judge_calibration("cli-jc-1", "gemini-3.6-flash", p, model=ScriptedChatModel(responses=msgs), out_dir=jc_dir)

    out_dir = tmp_path / "cli_rep"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eval",
            "judge-calibration-report",
            "--name",
            "cli_cal",
            "--runs",
            "cli-jc-1",
            "--runs-dir",
            str(jc_dir),
            "--out-dir",
            str(out_dir),
        ],
    )
    assert eval_cli_main() == 0
    assert (out_dir / "cli_cal.json").exists()
    assert (out_dir / "cli_cal.md").exists()
