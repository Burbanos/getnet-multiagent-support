"""Offline tests for selected-judge CLI flags, prompt_sha256 guards, and compare acceptable row."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

import src.eval.__main__ as eval_main
import src.eval.judge as judge_mod
from src.config import settings
from src.eval.compare import build_markdown_table, compare_runs
from tests.fakes import ScriptedChatModel

ROOT = Path(__file__).resolve().parent.parent


def _run_cli(monkeypatch: pytest.MonkeyPatch, argv_tail: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["src.eval", *argv_tail])
    return int(eval_main.main() or 0)


def _mk_case(cid: str, official: bool = True) -> dict:
    return {
        "id": cid,
        "category": "knowledge",
        "lang": "pt",
        "official": official,
        "offline": False,
        "turns": ["Qual o prazo?"],
        "expect": {
            "agents": [],
            "tools_all": [],
            "tools_none": [],
            "escalate": False,
            "priority": None,
            "blocked": False,
            "gold_urls": [],
            "facts_any": [],
            "facts_none": [],
            "abstain": False,
        },
    }


def _fake_result(cid: str, response_txt: str = "Resposta ok.") -> dict:
    return {
        "id": cid,
        "status": "ok",
        "turns": [
            {
                "response": response_txt,
                "retrieved_docs": [{"url": "https://site.getnet.com.br/", "text": "evidencia"}],
                "web_results": [],
                "api_results": [],
                "tool_results": [],
                "agents_used": [],
                "tools_used": [],
                "ticket_id": None,
                "handoff": None,
                "is_safe": True,
                "guardrail_blocked": False,
                "latency_ms": 10.0,
                "tokens": None,
                "llm_model": "fake-model",
            }
        ],
    }


def test_judge_cli_model_prompt_and_dir_writes_sha_and_acceptable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(json.dumps(_mk_case("jcase1")) + "\n", encoding="utf-8")

    runs_dir = tmp_path / "runs"
    judge_dir = tmp_path / "judge_sel"
    runs_dir.mkdir(parents=True)
    (runs_dir / "sel-1.jsonl").write_text(json.dumps(_fake_result("jcase1")) + "\n", encoding="utf-8")

    prompt_path = ROOT / "src" / "prompts" / "judge_acceptable.md"
    expected_sha = hashlib.sha256(
        prompt_path.read_bytes().decode("utf-8").replace("\r\n", "\n").encode("utf-8")
    ).hexdigest()
    reply = '{"acceptable": true, "grounded": 5, "answers_question": 5, "abstained": false, "rationale": "ok"}'
    fake_model = ScriptedChatModel(responses=[AIMessage(content=reply)])
    seen_models: list[str | None] = []

    monkeypatch.setattr(judge_mod, "get_judge_model", lambda name=None: (seen_models.append(name), fake_model)[1])
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-fake-key")
    monkeypatch.setattr(settings, "EVAL_SLEEP_S", 0.0)

    rc = _run_cli(
        monkeypatch,
        [
            "judge",
            "--run-id",
            "sel-1",
            "--runs-dir",
            str(runs_dir),
            "--cases",
            str(cases_path),
            "--judge-model",
            "gemini-3.8-flash",
            "--judge-prompt",
            str(prompt_path),
            "--judge-dir",
            str(judge_dir),
            "--sleep",
            "0",
        ],
    )
    assert rc == 0
    assert seen_models == ["gemini-3.8-flash"]
    assert not (runs_dir / "sel-1.judge.jsonl").exists()

    written = judge_dir / "sel-1.judge.jsonl"
    assert written.exists()
    row = json.loads(written.read_text(encoding="utf-8").strip())
    assert row["judge_model"] == "gemini-3.8-flash"
    assert row["prompt_sha256"] == expected_sha
    assert row["acceptable"] is True


def test_judge_cli_and_run_judge_refuse_mixed_prompt_or_model_without_writing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cases_path = tmp_path / "cases.jsonl"
    case = _mk_case("jcase2", official=False)
    cases_path.write_text(json.dumps(case) + "\n", encoding="utf-8")
    runs_dir = tmp_path / "runs"
    judge_dir = tmp_path / "jdir"
    runs_dir.mkdir(parents=True)
    judge_dir.mkdir(parents=True)
    (runs_dir / "mix-1.jsonl").write_text(json.dumps(_fake_result("jcase2")) + "\n", encoding="utf-8")

    jfile = judge_dir / "mix-1.judge.jsonl"
    initial_row = {
        "id": "other_done",
        "status": "ok",
        "judge_model": "gemini-3.8-flash",
        "prompt_sha256": "0" * 64,
        "grounded": 5,
        "answers_question": 5,
        "abstained": False,
        "acceptable": True,
    }
    jfile.write_text(json.dumps(initial_row) + "\n", encoding="utf-8")
    before = jfile.read_bytes()

    with pytest.raises(ValueError, match="Cannot resume judgments"):
        judge_mod.run_judge(
            cases=[case],
            results_path=runs_dir / "mix-1.jsonl",
            judgments_path=jfile,
            model=ScriptedChatModel(responses=[]),
            sleep_s=0.0,
            prompt_path=ROOT / "src" / "prompts" / "judge_acceptable.md",
            judge_model_name="gemini-3.8-flash",
        )
    assert jfile.read_bytes() == before

    monkeypatch.setattr(judge_mod, "get_judge_model", lambda name=None: ScriptedChatModel(responses=[]))
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-fake-key")
    rc = _run_cli(
        monkeypatch,
        [
            "judge",
            "--run-id",
            "mix-1",
            "--runs-dir",
            str(runs_dir),
            "--cases",
            str(cases_path),
            "--judge-dir",
            str(judge_dir),
            "--judge-model",
            "gemini-3.8-flash",
            "--sleep",
            "0",
        ],
    )
    assert rc == 2
    assert "Cannot resume judgments" in capsys.readouterr().err
    assert jfile.read_bytes() == before


def test_compare_acceptable_row_presence_and_judge_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    case = _mk_case("c_cmp_1")
    res_rec = _fake_result("c_cmp_1", "Olá!")
    jud_no_acc = [
        {"id": "c_cmp_1", "status": "ok", "judge_model": "m1", "grounded": 5, "answers_question": 5, "abstained": False}
    ]
    jud_with_acc = [
        {
            "id": "c_cmp_1",
            "status": "ok",
            "judge_model": "m2",
            "grounded": 5,
            "answers_question": 5,
            "abstained": False,
            "acceptable": True,
        }
    ]

    comp_plain = compare_runs([case], [("plain", [("r1", [res_rec], jud_no_acc)])])
    assert "judge_acceptable_rate" not in comp_plain["groups"][0]["metrics"]
    md_plain = "\n".join(build_markdown_table(comp_plain["groups"]))
    assert "Juiz: aceitável sem correção" not in md_plain

    comp_mixed = compare_runs(
        [case],
        [
            ("legacy", [("r1", [res_rec], jud_no_acc)]),
            ("selected", [("r2", [res_rec], jud_with_acc)]),
        ],
    )
    assert "judge_acceptable_rate" not in comp_mixed["groups"][0]["metrics"]
    assert comp_mixed["groups"][1]["metrics"]["judge_acceptable_rate"]["mean"] == 1.0
    md_mixed = "\n".join(build_markdown_table(comp_mixed["groups"]))
    assert "Juiz: aceitável sem correção" in md_mixed

    cases_path = tmp_path / "cases.jsonl"
    cases_path.write_text(json.dumps(case) + "\n", encoding="utf-8")
    runs_dir = tmp_path / "runs"
    judge_dir = tmp_path / "jdir"
    out_dir = tmp_path / "out"
    runs_dir.mkdir()
    judge_dir.mkdir()
    (runs_dir / "rx-1.jsonl").write_text(json.dumps(res_rec) + "\n", encoding="utf-8")
    (judge_dir / "rx-1.judge.jsonl").write_text(json.dumps(jud_with_acc[0]) + "\n", encoding="utf-8")

    rc = _run_cli(
        monkeypatch,
        [
            "compare",
            "--name",
            "sel_cmp",
            "--cases",
            str(cases_path),
            "--runs-dir",
            str(runs_dir),
            "--judge-dir",
            str(judge_dir),
            "--out-dir",
            str(out_dir),
            "--group",
            "sel=rx-1",
        ],
    )
    assert rc == 0
    assert "Juiz: aceitável sem correção" in (out_dir / "eval_sel_cmp.md").read_text(encoding="utf-8")
