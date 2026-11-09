"""Tests for run context, account tier declarations, and model tracking."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.eval.compare import write_comparison
from src.eval.guardrail_eval import guardrail_summary, write_guardrail_summary
from src.eval.run_context import CONTEXT_NOTE, load_run_context, tier_label


def test_load_run_context_valid_and_missing(tmp_path: Path) -> None:
    valid_file = tmp_path / "context.json"
    valid_doc = {
        "runs": {
            "r1": {"date": "2026-11-09", "tier": "paid_tier_1"},
            "r2": {"date": "2026-11-07", "tier": "free"},
        }
    }
    valid_file.write_text(json.dumps(valid_doc), encoding="utf-8")

    loaded = load_run_context(valid_file)
    assert loaded == valid_doc["runs"]

    missing = load_run_context(tmp_path / "missing.json")
    assert missing == {}

    assert tier_label({"tier": "paid_tier_1"}) == "Tier 1 (pago)"
    assert tier_label({"tier": "free"}) == "nível gratuito"
    assert tier_label(None) == "não informado"
    assert tier_label({"tier": "unknown"}) == "não informado"


def test_load_run_context_rejects_bad_entries(tmp_path: Path) -> None:
    bad_runs = tmp_path / "bad_runs.json"
    bad_runs.write_text(json.dumps({"runs": [1, 2, 3]}), encoding="utf-8")
    with pytest.raises(TypeError, match="'runs' must be an object"):
        load_run_context(bad_runs)

    bad_keys = tmp_path / "bad_keys.json"
    bad_keys.write_text(
        json.dumps({"runs": {"r1": {"date": "2026-11-09", "tier": "paid_tier_1", "extra": "val"}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid entry"):
        load_run_context(bad_keys)

    missing_date = tmp_path / "missing_date.json"
    missing_date.write_text(json.dumps({"runs": {"r1": {"tier": "paid_tier_1"}}}), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid entry"):
        load_run_context(missing_date)

    invalid_tier = tmp_path / "invalid_tier.json"
    invalid_tier.write_text(
        json.dumps({"runs": {"r1": {"date": "2026-11-09", "tier": "invalid_tier"}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid entry"):
        load_run_context(invalid_tier)


def test_write_comparison_lists_runs_context(tmp_path: Path) -> None:
    cases = [
        {
            "id": "c1",
            "category": "knowledge",
            "lang": "pt",
            "official": True,
            "expect": {
                "agents": [],
                "tools_all": [],
                "tools_none": [],
                "escalate": None,
                "priority": None,
                "blocked": None,
                "gold_urls": [],
                "facts_any": [],
                "facts_none": [],
                "abstain": None,
            },
        }
    ]
    r1 = [{"id": "c1", "status": "ok", "turns": [{"llm_model": "model-a"}]}]
    j1 = [{"id": "c1", "status": "ok", "judge_model": "judge-a", "grounded": 5, "answers_question": 5, "abstained": False}]
    r2 = [{"id": "c1", "status": "ok", "turns": [{"llm_model": "model-b"}]}]
    groups = [("group1", [("run1", r1, j1), ("run2", r2, None)])]

    ctx = {
        "run1": {"date": "2026-11-08", "tier": "paid_tier_1"},
        "run2": {"date": "2026-11-07", "tier": "free"},
    }

    out_j = tmp_path / "comp.json"
    out_m = tmp_path / "comp.md"
    write_comparison(cases, groups, out_j, out_m, "test-comp", context=ctx)

    doc = json.loads(out_j.read_text(encoding="utf-8"))
    assert "runs_context" in doc
    assert doc["runs_context"] == [
        {
            "run_id": "run1",
            "group": "group1",
            "date": "2026-11-08",
            "tier": "paid_tier_1",
            "answer_models": ["model-a"],
            "judge_models": ["judge-a"],
        },
        {
            "run_id": "run2",
            "group": "group1",
            "date": "2026-11-07",
            "tier": "free",
            "answer_models": ["model-b"],
            "judge_models": [],
        },
    ]

    md = out_m.read_text(encoding="utf-8")
    assert "## Execuções" in md
    assert "- `run1` (group1): 2026-11-08, conta Tier 1 (pago); respostas: model-a; juiz: judge-a" in md
    assert "- `run2` (group1): 2026-11-07, conta nível gratuito; respostas: model-b; juiz: sem juiz" in md
    assert CONTEXT_NOTE in md


def test_guardrail_summary_has_tier_and_date(tmp_path: Path) -> None:
    rep1 = {
        "run_id": "gr1",
        "models": ["flash-lite"],
        "complete": True,
        "targets_met": True,
        "layers": {},
        "latency_ms": {},
        "cost_usd_mean_per_message": None,
    }
    rep2 = {
        "run_id": "gr2",
        "models": ["flash-lite"],
        "complete": True,
        "targets_met": False,
        "layers": {},
        "latency_ms": {},
        "cost_usd_mean_per_message": None,
    }

    ctx = {"gr1": {"date": "2026-11-09", "tier": "paid_tier_1"}}
    s = guardrail_summary([rep1, rep2], context=ctx)
    assert s["runs"][0]["date"] == "2026-11-09"
    assert s["runs"][0]["tier"] == "paid_tier_1"
    assert s["runs"][1]["date"] is None
    assert s["runs"][1]["tier"] is None

    out_j = tmp_path / "gr.json"
    out_m = tmp_path / "gr.md"
    write_guardrail_summary([rep1, rep2], out_j, out_m, context=ctx)

    md = out_m.read_text(encoding="utf-8")
    assert "conta Tier 1 (pago)" in md
    assert "conta não informado" in md
    assert md.rstrip().endswith("Metas atingidas em todas as execuções: não")
    assert CONTEXT_NOTE in md
