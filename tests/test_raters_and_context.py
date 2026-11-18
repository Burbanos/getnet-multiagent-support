"""Offline tests for inter-rater agreement, run_context appending, and named hybrid reports."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from src.config import settings
from src.eval.annotator import compare_raters
from src.eval.run_context import load_run_context
from src.rag import hybrid_eval
from src.rag.index import build_index


def test_compare_raters_computes_kappa_and_lists_disagreements(tmp_path: Path) -> None:
    author_csv = Path("reports/human_validation/answers.csv")
    lines = author_csv.read_text(encoding="utf-8").splitlines()
    # Flip h01 rota and h04 fundamentacao & aceitavel
    modified = [lines[0]]
    for ln in lines[1:]:
        parts = ln.split(";")
        if parts[0] == "h01":
            parts[1] = "conta" if parts[1] != "conta" else "conhecimento"
        elif parts[0] == "h04":
            parts[3] = "N" if parts[3] == "S" else "S"
            parts[5] = "3"
        modified.append(";".join(parts))

    b_csv = tmp_path / "rater_b.csv"
    b_csv.write_text("\n".join(modified) + "\n", encoding="utf-8", newline="\n")

    out_dir = tmp_path / "raters_out"
    rep = compare_raters(author_csv, b_csv, "autor", "anotador", out_dir)

    assert rep["n_items"] == 30
    rota = rep["fields"]["rota"]
    assert rota["agree"] == 29 and rota["n"] == 30
    assert isinstance(rota["kappa"], float)
    assert [d["hid"] for d in rota["disagreements"]] == ["h01"]

    fund = rep["fields"]["fundamentacao"]
    assert fund["exact"] == 29
    assert fund["within_one"] == 29
    assert fund["b_mean"] < fund["a_mean"]
    assert (out_dir / "raters.json").exists()
    assert (out_dir / "raters.md").exists()


def test_context_cli_appends_new_ids_without_modifying_existing_entries(tmp_path: Path) -> None:
    orig_path = Path("reports/run_context.json")
    orig_doc = json.loads(orig_path.read_text(encoding="utf-8"))
    ctx_file = tmp_path / "run_context.json"
    ctx_file.write_text(orig_path.read_text(encoding="utf-8"), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.eval",
            "context",
            "--file",
            str(ctx_file),
            "--run-ids",
            "new-run-1,new-run-2",
            "--tier",
            "free",
            "--date",
            "2026-11-20",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr

    loaded = load_run_context(ctx_file)
    assert list(loaded)[: len(orig_doc["runs"])] == list(orig_doc["runs"])
    assert loaded["new-run-1"] == {"date": "2026-11-20", "tier": "free"}
    assert loaded["new-run-2"] == {"date": "2026-11-20", "tier": "free"}

    new_doc = json.loads(ctx_file.read_text(encoding="utf-8"))
    for key in orig_doc:
        if key != "runs":
            assert new_doc[key] == orig_doc[key]


def test_context_cli_rejects_duplicate_id_without_modifying_file(tmp_path: Path) -> None:
    ctx_file = tmp_path / "run_context.json"
    ctx_file.write_text(Path("reports/run_context.json").read_text(encoding="utf-8"), encoding="utf-8")
    before = ctx_file.read_text(encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.eval",
            "context",
            "--file",
            str(ctx_file),
            "--run-ids",
            "fresh-x,v2-1",
            "--tier",
            "paid_tier_1",
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode != 0
    assert ctx_file.read_text(encoding="utf-8") == before


def test_hybrid_eval_report_name_writes_custom_files_without_touching_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data/eval").mkdir(parents=True)
    (tmp_path / "reports/retrieval_runs").mkdir(parents=True)
    idx_dir = tmp_path / "idx"

    chunks = [
        {
            "chunk_id": "c1",
            "doc_url": "https://site.getnet.com.br/",
            "title": "Home",
            "text": "Maquininha Getnet taxas.",
        }
    ]
    class _StaticEmbedder:
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0] for _ in texts]

    build_index(
        chunks=chunks,
        embedder=_StaticEmbedder(),
        out_dir=idx_dir,
        embedding_model="m-test",
        dim=2,
    )
    monkeypatch.setattr(settings, "INDEX_DIR", str(idx_dir))
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "m-test")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 2)

    records = [
        {
            "id": "q1",
            "query": "taxas maquininha",
            "category": "answerable",
            "lang": "pt",
            "gold_urls": ["https://site.getnet.com.br/"],
            "gold_snippets": ["Maquininha Getnet"],
        }
    ]
    Path("data/eval/retrieval_labeled.jsonl").write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
    np.save("data/eval/retrieval_query_embeddings.npy", np.array([[1.0, 0.0]], dtype=np.float32))
    from src.rag.calibration import dataset_sha256

    Path("data/eval/retrieval_query_embeddings.json").write_text(
        json.dumps(
            {
                "query_ids": ["q1"],
                "dataset_sha256": dataset_sha256(records),
                "embedding_model": "m-test",
            }
        ),
        encoding="utf-8",
    )
    Path("reports/retrieval_runs/r1.jsonl").write_text(
        json.dumps(
            {
                "id": "q1",
                "run_id": "r1",
                "status": "ok",
                "documents": ["c1"],
                "rerank_status": "ok",
                "latency_ms": 12.0,
                "model": "gemini-3.5-flash-lite",
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    Path("reports/retrieval_hybrid.json").write_text("sentinel-json", encoding="utf-8")
    Path("reports/retrieval_hybrid.md").write_text("sentinel-md", encoding="utf-8")

    rc = hybrid_eval.main(["report", "--runs", "r1", "--name", "custom_phase13"])
    assert rc == 0
    assert Path("reports/custom_phase13.json").exists()
    assert Path("reports/custom_phase13.md").exists()
    assert Path("reports/retrieval_hybrid.json").read_text(encoding="utf-8") == "sentinel-json"
    assert Path("reports/retrieval_hybrid.md").read_text(encoding="utf-8") == "sentinel-md"
