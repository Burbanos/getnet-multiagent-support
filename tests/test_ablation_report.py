"""Offline tests for Phase 15 ablation analysis, paired comparisons, gate counts, and §3.4 decisions."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import pytest

from src.core.pricing import cost_usd
from src.eval.__main__ import main as eval_cli_main
from src.eval.ablation import build_ablation, write_ablation


def _write_ablation_fixture(
    tmp_path: Path,
    *,
    equal_quality: bool = False,
    extra_config: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    base_expect = {
        "agents": ["KnowledgeAgent"],
        "tools_all": ["search_knowledge_base"],
        "tools_none": [],
        "escalate": False,
        "priority": None,
        "blocked": False,
        "gold_urls": [],
        "facts_any": [],
        "facts_none": [],
        "abstain": None,
    }
    cases = [
        {"id": f"k{i}", "category": "knowledge", "lang": "pt", "official": i == 1, "offline": False, "turns": ["q"], "expect": dict(base_expect)}
        for i in range(1, 5)
    ]
    cases.append(
        {
            "id": "o1",
            "category": "off_topic",
            "lang": "pt",
            "official": False,
            "offline": False,
            "turns": ["o"],
            "expect": dict(base_expect, agents=None, tools_all=[], tools_none=[]),
        }
    )

    cpath = tmp_path / "cases.jsonl"
    cpath.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
    rdir = tmp_path / "runs"
    rdir.mkdir(parents=True, exist_ok=True)

    full_layers = {"planner": True, "verifier": True, "language": True, "plan_coverage": True}
    nv_layers = dict(full_layers, verifier=False)
    np_layers = dict(full_layers, planner=False)

    tba_full = {
        "SupervisorAgent": {"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100},
        "Verifier": {"input_tokens": 500, "output_tokens": 50, "total_tokens": 550},
    }
    tba_nv = {"SupervisorAgent": {"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100}}

    def _turn(ok: bool, *, layers: dict[str, bool], tba: dict[str, Any], ticket: bool = False, tools: list[str] | None = None, lang: str = "ok") -> dict[str, Any]:
        return {
            "message": "q",
            "response": "A taxa de débito é 1,09% segundo o portal oficial.",
            "agents_used": ["SupervisorAgent", "KnowledgeAgent"] if ok else ["SupervisorAgent"],
            "tools_used": list(tools) if tools is not None else (["search_knowledge_base"] if ok else []),
            "sources": [],
            "retrieved_docs": [],
            "web_results": [],
            "api_results": [],
            "tool_results": [],
            "ticket_id": "GET-TKT-1" if ticket else None,
            "ticket_priority": None,
            "is_safe": True,
            "handoff": None,
            "llm_model": "gemini-3.5-flash-lite",
            "tokens": {"input_tokens": sum(v["input_tokens"] for v in tba.values()), "output_tokens": sum(v["output_tokens"] for v in tba.values()), "total_tokens": sum(v["total_tokens"] for v in tba.values())},
            "tokens_by_agent": tba,
            "guardrail": None,
            "guardrail_layer": None,
            "answer_check": None,
            "web_guardrail": [],
            "plan": None,
            "verification": None,
            "language": {"status": lang},
            "escalation_gate": None,
            "action": None,
            "latency_ms": 1000.0,
            "layers": layers,
            "coverage": None,
            "tool_gate": None,
            "rejected_drafts": [],
        }

    for r in range(3):
        f_rows = [
            {"id": f"k{i}", "status": "ok", "error_type": None, "turns": [_turn(i != 4 if equal_quality else True, layers=full_layers, tba=tba_full, lang="rewritten" if (r == 0 and i == 1) else "ok")]}
            for i in range(1, 5)
        ]
        f_rows.append({"id": "o1", "status": "ok", "error_type": None, "turns": [_turn(True, layers=full_layers, tba=tba_full, tools=[])]})
        (rdir / f"f{r}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in f_rows), encoding="utf-8")

        n_rows = []
        for i in range(1, 5):
            if equal_quality:
                ok_flag = (r == 0) if i == 4 else True
                tkt = False
            else:
                ok_flag = not (i in (1, 2) or (i == 3 and r < 2))
                tkt = i == 4 and r == 0
            n_rows.append({"id": f"k{i}", "status": "ok", "error_type": None, "turns": [_turn(ok_flag, layers=nv_layers, tba=tba_nv, ticket=tkt)]})
        oot = ["search_web"] if (not equal_quality and r == 2) else []
        n_rows.append({"id": "o1", "status": "ok", "error_type": None, "turns": [_turn(True, layers=nv_layers, tba=tba_nv, tools=oot)]})
        (rdir / f"nv{r}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in n_rows), encoding="utf-8")

    if extra_config:
        np_rows = [
            {"id": f"k{i}", "status": "ok", "error_type": None, "turns": [_turn(True, layers=np_layers, tba=tba_nv)]}
            for i in range(1, 5)
        ]
        np_rows.append({"id": "o1", "status": "ok", "error_type": None, "turns": [_turn(True, layers=np_layers, tba=tba_nv, tools=[])]})
        (rdir / "np0.jsonl").write_text("".join(json.dumps(x) + "\n" for x in np_rows), encoding="utf-8")

    return cpath, rdir


def test_build_ablation_lossy_verifier_computes_paired_gates_costs_and_keep(tmp_path: Path) -> None:
    cpath, rdir = _write_ablation_fixture(tmp_path, equal_quality=False)
    rep = build_ablation(
        cpath,
        {"full": ["f0", "f1", "f2"], "no_verifier": ["nv0", "nv1", "nv2"]},
        baseline="full",
        runs_dir=rdir,
    )

    assert set(rep.keys()) == {"name", "cases_sha256", "baseline", "configs", "paired", "language_estimate", "decisions"}
    assert rep["configs"]["full"]["passed_per_run"] == [5, 5, 5]
    assert rep["configs"]["no_verifier"]["passed_per_run"] == [1, 2, 3]
    assert rep["configs"]["no_verifier"]["gates"] == {
        "unrequested_tickets": 1,
        "wrong_language": 0,
        "out_of_scope_tools": 1,
    }
    assert rep["paired"]["no_verifier"] == {"lost": ["k1", "k2", "k3"], "gained": []}

    ver_expected_cost = cost_usd("gemini-3.5-flash-lite", 500, 50) * 5
    assert math.isclose(rep["configs"]["full"]["cost_by_agent"]["Verifier"], ver_expected_cost, rel_tol=1e-6)

    dv = rep["decisions"]["verifier"]
    assert dv["config"] == "no_verifier"
    assert math.isclose(dv["delta_q"], 3.0, rel_tol=1e-6)
    assert dv["gates_baseline"] == 0
    assert dv["gates_ablated"] == 2
    assert dv["keep"] is True
    assert rep["decisions"]["language"] == {"rewritten_turns": 1, "cost_share": 0.0, "keep": True}
    assert rep["decisions"]["planner"] == {"config": None, "keep": True, "reason": "feature_dependency"}


def test_write_ablation_switches_off_equal_verifier_and_writes_pt_md(tmp_path: Path) -> None:
    cpath, rdir = _write_ablation_fixture(tmp_path, equal_quality=True, extra_config={"np": ["np0"]})
    out_dir = tmp_path / "out"
    rep = write_ablation(
        "abl_phase15",
        cpath,
        {"full": ["f0", "f1", "f2"], "no_verifier": ["nv0", "nv1", "nv2"], "no_planner": ["np0"]},
        baseline="full",
        runs_dir=rdir,
        out_dir=out_dir,
    )

    # Full failed k4 in 3/3 (passed=[4,4,4]); no_verifier passed k4 in 1/3 (failed majority 2/3, so not gained), delta_q = 4 - 4.333 < 0
    assert rep["decisions"]["verifier"]["keep"] is False
    assert rep["decisions"]["planner"] == {"config": "no_planner", "keep": True, "reason": "feature_dependency"}

    json_doc = json.loads((out_dir / "abl_phase15.json").read_text(encoding="utf-8"))
    assert set(json_doc.keys()) == {"name", "cases_sha256", "baseline", "configs", "paired", "language_estimate", "decisions"}
    md_text = (out_dir / "abl_phase15.md").read_text(encoding="utf-8")
    assert "seção 3.4 do `docs/SPEC.md`" in md_text
    assert "feature_dependency" in md_text
    assert "`no_verifier`" in md_text


def test_build_ablation_rejects_mixed_layers_multi_layer_diff_and_missing_baseline(tmp_path: Path) -> None:
    cpath, rdir = _write_ablation_fixture(tmp_path, equal_quality=False)

    with pytest.raises(ValueError, match="Baseline"):
        build_ablation(cpath, {"full": ["f0"]}, baseline="missing", runs_dir=rdir)

    # Mixed layers inside config
    nv2 = rdir / "nv2.jsonl"
    rows = [json.loads(ln) for ln in nv2.read_text(encoding="utf-8").splitlines()]
    rows[0]["turns"][0]["layers"]["verifier"] = True
    nv2.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="Mixed layers"):
        build_ablation(cpath, {"full": ["f0", "f1", "f2"], "no_verifier": ["nv0", "nv1", "nv2"]}, baseline="full", runs_dir=rdir)

    # Differs in more than one layer
    two_off = rdir / "two.jsonl"
    for row in rows:
        row["turns"][0]["layers"] = {"planner": False, "verifier": False, "language": True, "plan_coverage": True}
    two_off.write_text("".join(json.dumps(x) + "\n" for x in rows), encoding="utf-8")
    with pytest.raises(ValueError, match="more than one layer"):
        build_ablation(cpath, {"full": ["f0"], "two": ["two"]}, baseline="full", runs_dir=rdir)


def test_cli_ablation_subcommand_writes_reports(tmp_path: Path, monkeypatch: Any) -> None:
    cpath, rdir = _write_ablation_fixture(tmp_path, equal_quality=False)
    out_dir = tmp_path / "cli_out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "eval",
            "ablation",
            "--name",
            "cli_abl",
            "--cases",
            str(cpath),
            "--config",
            "full=f0,f1,f2",
            "--config",
            "no_verifier=nv0,nv1,nv2",
            "--baseline",
            "full",
            "--runs-dir",
            str(rdir),
            "--out-dir",
            str(out_dir),
        ],
    )
    assert eval_cli_main() == 0
    assert (out_dir / "cli_abl.json").exists()
    assert (out_dir / "cli_abl.md").exists()
