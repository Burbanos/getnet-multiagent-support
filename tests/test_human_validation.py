"""Offline unit tests for human validation sampling, form rendering, answer parsing, and agreement."""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from src.eval.cases import cases_sha256, load_cases
from src.eval.human_validation import (
    CASES_FILE,
    FIELDS,
    SOURCE_RUN,
    agreement,
    allocate,
    file_sha256,
    label_route,
    parse_answers,
    select_sample,
    write_agreement_report,
    write_sample,
)
from src.eval.judge import load_judgments
from src.eval.runner import load_results


def _make_case(cid: str, category: str, agents: list[str] | None, escalate: bool = False, abstain: bool = False) -> dict[str, Any]:
    return {
        "id": cid,
        "category": category,
        "lang": "pt",
        "official": False,
        "offline": False,
        "turns": [f"Pergunta {cid}"],
        "expect": {
            "agents": agents,
            "tools_all": [],
            "tools_none": [],
            "escalate": escalate,
            "priority": None,
            "blocked": False,
            "gold_urls": [],
            "facts_any": [],
            "facts_none": [],
            "abstain": abstain,
        },
    }


def _make_ok_result(cid: str, agents: list[str] | None = None, ticket_id: str | None = None) -> dict[str, Any]:
    return {
        "id": cid,
        "status": "ok",
        "error_type": None,
        "turns": [
            {
                "message": f"Pergunta {cid}",
                "response": "Esta é uma resposta com os dados para você.",
                "agents_used": agents or [],
                "tools_used": [],
                "sources": [],
                "retrieved_docs": [],
                "web_results": [],
                "api_results": [],
                "tool_results": [],
                "ticket_id": ticket_id,
                "ticket_priority": None,
                "is_safe": True,
                "handoff": None,
            }
        ],
    }


def _make_judgment(cid: str, grounded: int = 5, answers_question: int = 5, abstained: bool = False) -> dict[str, Any]:
    return {
        "id": cid,
        "status": "ok",
        "judge_model": "fake-judge",
        "grounded": grounded,
        "answers_question": answers_question,
        "abstained": abstained,
        "rationale": "Ok",
    }


def test_allocate_largest_remainder_and_tiebreak():
    """Verify proportional allocation sums to size, applies largest remainder, and breaks ties alphabetically."""
    alloc = allocate({"b": 1, "a": 1}, 1)
    assert alloc == {"a": 1, "b": 0}
    assert sum(alloc.values()) == 1

    alloc2 = allocate({"c": 1, "a": 3, "b": 3}, 4)
    assert list(alloc2.keys()) == ["a", "b", "c"]
    assert sum(alloc2.values()) == 4
    assert alloc2 == {"a": 2, "b": 2, "c": 0}


def test_select_sample_deterministic_and_proportional():
    """Verify select_sample is deterministic and stratified proportionally by category."""
    cases = load_cases(CASES_FILE)
    results = load_results(f"reports/eval_runs/{SOURCE_RUN}.jsonl")
    judgments = load_judgments(f"reports/eval_runs/{SOURCE_RUN}.judge.jsonl")

    s1 = select_sample(cases, results, judgments, size=30)
    s2 = select_sample(cases, results, judgments, size=30)
    assert s1 == s2
    assert len(s1) == 30
    assert [it["hid"] for it in s1] == [f"h{i:02d}" for i in range(1, 31)]

    by_id = {c["id"]: c for c in cases}
    cats = {}
    for it in s1:
        cat = by_id[it["case_id"]]["category"]
        cats[cat] = cats.get(cat, 0) + 1
    assert cats["knowledge"] > cats["support"] > cats["multi_intent"]


def test_label_route_all_six_cases():
    """Verify label_route handles escalate, None agents, empty, KnowledgeAgent, SupportAgent, and both."""
    assert label_route(_make_case("c1", "escalation", None, escalate=True)) == "humano"
    assert label_route(_make_case("c2", "safety", None, escalate=False)) is None
    assert label_route(_make_case("c3", "off_topic", [], escalate=False)) == "nenhum"
    assert label_route(_make_case("c4", "knowledge", ["KnowledgeAgent"], escalate=False)) == "conhecimento"
    assert label_route(_make_case("c5", "support", ["SupportAgent"], escalate=False)) == "conta"
    assert label_route(_make_case("c6", "multi_intent", ["KnowledgeAgent", "SupportAgent"], escalate=False)) == "ambos"


def test_write_sample_refuses_to_overwrite(tmp_path: Path):
    """Verify write_sample creates artifacts on first call and raises FileExistsError on second."""
    out_dir = tmp_path / "hv"
    sample = write_sample(out_dir=out_dir)
    assert len(sample["items"]) == 30
    assert (out_dir / "sample.json").exists()
    assert (out_dir / "form.md").exists()
    assert (out_dir / "answers_template.csv").exists()

    before = (out_dir / "sample.json").read_bytes()
    with pytest.raises(FileExistsError):
        write_sample(out_dir=out_dir)
    assert (out_dir / "sample.json").read_bytes() == before


def test_parse_answers_formats_cp1252_and_lowercase(tmp_path: Path):
    """Verify parse_answers supports ';' and ',', cp1252 encoding, and lowercase s/n."""
    hids = ["h01", "h02"]

    csv_semi = tmp_path / "semi.csv"
    csv_semi.write_text(
        "id;rota;deveria_abster;aceitavel;absteve;fundamentacao\n"
        "h01;conhecimento;N;S;n;5\n"
        "h02;conta;s;n;S;2\n",
        encoding="utf-8",
    )
    parsed_semi = parse_answers(csv_semi, hids)
    assert parsed_semi["h01"] == {
        "rota": "conhecimento",
        "deveria_abster": False,
        "aceitavel": True,
        "absteve": False,
        "fundamentacao": 5,
    }
    assert parsed_semi["h02"] == {
        "rota": "conta",
        "deveria_abster": True,
        "aceitavel": False,
        "absteve": True,
        "fundamentacao": 2,
    }

    csv_comma_cp1252 = tmp_path / "comma_cp1252.csv"
    # Include a cp1252-valid non-ASCII char in whitespace-padded header check? Actually header is exact ASCII;
    # write bytes encoded in cp1252 with CRLF and a cp1252 byte sequence test via invalid UTF-8 fallback.
    content = (
        "ID,ROTA,DEVERIA_ABSTER,ACEITAVEL,ABSTEVE,FUNDAMENTACAO\r\n"
        "h01,Conhecimento,n,s,n,5\r\n"
        "h02,Conta,s,n,s,2\r\n"
    )
    csv_comma_cp1252.write_bytes(content.encode("cp1252"))
    assert parse_answers(csv_comma_cp1252, hids) == parsed_semi

    # Test real cp1252 fallback by writing an invalid UTF-8 byte sequence inside an error-raising scenario vs valid cp1252
    # Wait: all valid routes are ASCII, so cp1252 fallback can also be tested with a non-UTF8 byte in trailing comment/invalid value raising ValueError instead of UnicodeDecodeError:
    bad_cp1252 = tmp_path / "bad_cp1252.csv"
    bad_cp1252.write_bytes(("id;rota;deveria_abster;aceitavel;absteve;fundamentacao\nh01;não;N;S;N;5\nh02;conta;N;S;N;5\n").encode("cp1252"))
    with pytest.raises(ValueError):
        parse_answers(bad_cp1252, hids)


def test_parse_answers_validation_errors(tmp_path: Path):
    """Verify parse_answers rejects missing id, duplicate id, invalid values, and rating 6."""
    hids = ["h01", "h02"]
    header = ";".join(FIELDS)

    cases_bad = {
        "missing_id": f"{header}\nh01;conta;N;S;N;5\n",
        "duplicate_id": f"{header}\nh01;conta;N;S;N;5\nh01;conta;N;S;N;5\nh02;conta;N;S;N;5\n",
        "unknown_id": f"{header}\nh01;conta;N;S;N;5\nh99;conta;N;S;N;5\n",
        "bad_route": f"{header}\nh01;desconhecida;N;S;N;5\nh02;conta;N;S;N;5\n",
        "bad_bool": f"{header}\nh01;conta;X;S;N;5\nh02;conta;N;S;N;5\n",
        "grade_6": f"{header}\nh01;conta;N;S;N;6\nh02;conta;N;S;N;5\n",
        "grade_0": f"{header}\nh01;conta;N;S;N;0\nh02;conta;N;S;N;5\n",
    }

    for name, body in cases_bad.items():
        p = tmp_path / f"{name}.csv"
        p.write_text(body, encoding="utf-8")
        with pytest.raises(ValueError):
            parse_answers(p, hids)


def test_agreement_perfect_and_disagreements_math(tmp_path: Path):
    """Verify agreement calculation against hand-computed rates, kappa, and disagreements."""
    c1 = _make_case("c1", "knowledge", ["KnowledgeAgent"], escalate=False, abstain=False)
    c2 = _make_case("c2", "support", ["SupportAgent"], escalate=False, abstain=False)
    cases_list = [c1, c2]
    cases_by_id = {c["id"]: c for c in cases_list}
    results = {
        "c1": _make_ok_result("c1", ["KnowledgeAgent"]),
        "c2": _make_ok_result("c2", ["SupportAgent"]),
    }
    judgments = {
        "c1": _make_judgment("c1", grounded=5, answers_question=5, abstained=False),
        "c2": _make_judgment("c2", grounded=4, answers_question=4, abstained=False),
    }
    sample = {
        "seed": "test-seed",
        "source_run": "r-test",
        "cases_file": "synthetic.jsonl",
        "cases_sha256": cases_sha256(cases_list),
        "records_sha256": "r" * 64,
        "judgments_sha256": "j" * 64,
        "size": 2,
        "eligible": 2,
        "allocation": {"knowledge": 1, "support": 1},
        "items": [{"hid": "h01", "case_id": "c1"}, {"hid": "h02", "case_id": "c2"}],
    }

    # 1) All agree
    ans_ok = {
        "h01": {"rota": "conhecimento", "deveria_abster": False, "aceitavel": True, "absteve": False, "fundamentacao": 5},
        "h02": {"rota": "conta", "deveria_abster": False, "aceitavel": True, "absteve": False, "fundamentacao": 4},
    }
    rep_ok = agreement(sample, ans_ok, cases_by_id, results, judgments, "s" * 64, "a" * 64)
    assert rep_ok["n_items"] == 2
    assert rep_ok["pass_rate_checks"] == 1.0
    assert rep_ok["acceptable_rate_human"] == 1.0
    for comp in rep_ok["comparisons"].values():
        assert comp["agree"] == 2
        assert comp["rate"] == 1.0
        assert comp["disagreements"] == []
    assert rep_ok["grounded_vs_judge"]["exact_rate"] == 1.0
    assert rep_ok["grounded_vs_judge"]["within_one_rate"] == 1.0

    # 2) Partial disagreement: swap routes on h02 (h02 human says "conhecimento", label is "conta")
    # For route_vs_label: human=["conhecimento", "conhecimento"], other=["conhecimento", "conta"]
    # agree=1/2=0.5. po=0.5. pe = (1.0 * 0.5) + (0.0 * 0.5) = 0.5 -> kappa = (0.5 - 0.5)/(1 - 0.5) = 0.0
    ans_dis = {
        "h01": {"rota": "conhecimento", "deveria_abster": False, "aceitavel": True, "absteve": False, "fundamentacao": 3},
        "h02": {"rota": "conhecimento", "deveria_abster": True, "aceitavel": False, "absteve": True, "fundamentacao": 4},
    }
    rep_dis = agreement(sample, ans_dis, cases_by_id, results, judgments, "s" * 64, "a" * 64)
    assert rep_dis["acceptable_rate_human"] == 0.5
    route_comp = rep_dis["comparisons"]["route_vs_label"]
    assert route_comp["n"] == 2
    assert route_comp["agree"] == 1
    assert route_comp["rate"] == 0.5
    assert math.isclose(route_comp["kappa"], 0.0, abs_tol=1e-9)
    assert route_comp["disagreements"] == [{"hid": "h02", "case_id": "c2", "human": "conhecimento", "other": "conta"}]
    assert rep_dis["grounded_vs_judge"]["exact"] == 1
    assert rep_dis["grounded_vs_judge"]["within_one"] == 1
    assert rep_dis["grounded_vs_judge"]["human_lower"] == 1

    written = write_agreement_report(rep_dis, tmp_path / "out.json", tmp_path / "out.md")
    assert "generated_at" in written
    assert (tmp_path / "out.json").exists()
    assert (tmp_path / "out.md").exists()


def test_agreement_rejects_changed_cases():
    """Verify agreement raises ValueError if cases_sha256 does not match the sample."""
    c1 = _make_case("c1", "knowledge", ["KnowledgeAgent"])
    cases_by_id = {"c1": c1}
    sample = {
        "seed": "s",
        "source_run": "r",
        "cases_sha256": "0" * 64,
        "items": [{"hid": "h01", "case_id": "c1"}],
    }
    with pytest.raises(ValueError, match="cases changed since the sample"):
        agreement(sample, {}, cases_by_id, {}, {}, "s" * 64, "a" * 64)


def test_cli_human_agreement_rejects_tampered_records(tmp_path: Path):
    """Verify `human-agreement` exits 1 and writes nothing if run records were altered."""
    sample_dir = tmp_path / "hv"
    runs_dir = tmp_path / "runs"
    out_dir = tmp_path / "out"
    runs_dir.mkdir()
    out_dir.mkdir()

    # Copy v2-1 records
    src_runs = Path("reports/eval_runs")
    (runs_dir / f"{SOURCE_RUN}.jsonl").write_bytes((src_runs / f"{SOURCE_RUN}.jsonl").read_bytes())
    (runs_dir / f"{SOURCE_RUN}.judge.jsonl").write_bytes((src_runs / f"{SOURCE_RUN}.judge.jsonl").read_bytes())

    sample = write_sample(out_dir=sample_dir, runs_dir=runs_dir)
    answers_path = sample_dir / "answers.csv"
    rows = [";".join(FIELDS)] + [f"{it['hid']};conhecimento;N;S;N;5" for it in sample["items"]]
    answers_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    # Tamper records file
    with open(runs_dir / f"{SOURCE_RUN}.jsonl", "a", encoding="utf-8") as f:
        f.write("\n")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.eval",
            "human-agreement",
            "--answers",
            str(answers_path),
            "--sample-dir",
            str(sample_dir),
            "--runs-dir",
            str(runs_dir),
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert proc.returncode == 1
    assert not (out_dir / "human_validation.json").exists()
    assert not (out_dir / "human_validation.md").exists()
    assert "changed" in proc.stderr.lower() or "error" in proc.stderr.lower()


def test_committed_sample_files_sha_integrity():
    """Verify committed sample artifacts match file hashes of the source files."""
    sample_path = Path("reports/human_validation/sample.json")
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    assert sample["records_sha256"] == file_sha256(f"reports/eval_runs/{SOURCE_RUN}.jsonl")
    assert sample["judgments_sha256"] == file_sha256(f"reports/eval_runs/{SOURCE_RUN}.judge.jsonl")
    assert len(sample["items"]) == 30
