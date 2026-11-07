"""Unit tests for retrieval evaluation and threshold calibration (offline, synthetic data)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from src.config import settings
from src.rag import calibration as cal
from src.rag import index as index_mod


def test_load_labeled_validations(tmp_path: Path) -> None:
    # 1. Unknown category
    p1 = tmp_path / "bad_cat.jsonl"
    p1.write_text(
        json.dumps({"id": "q1", "lang": "pt", "category": "invalid_cat", "query": "q", "gold_urls": [], "gold_snippets": []}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid category"):
        cal.load_labeled(p1)

    # 2. Bad language
    p2 = tmp_path / "bad_lang.jsonl"
    p2.write_text(
        json.dumps({"id": "q2", "lang": "es", "category": "off_topic", "query": "q", "gold_urls": [], "gold_snippets": []}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid lang"):
        cal.load_labeled(p2)

    # 3. Duplicate ID
    p3 = tmp_path / "dup_id.jsonl"
    line = json.dumps({"id": "dup", "lang": "pt", "category": "off_topic", "query": "q", "gold_urls": [], "gold_snippets": []})
    p3.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate id"):
        cal.load_labeled(p3)

    # 4. Answerable without gold_urls
    p4 = tmp_path / "no_urls.jsonl"
    p4.write_text(
        json.dumps({"id": "q4", "lang": "pt", "category": "answerable", "query": "q", "gold_urls": [], "gold_snippets": ["s"]}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="gold_urls"):
        cal.load_labeled(p4)

    # 5. Answerable without gold_snippets
    p5 = tmp_path / "no_snips.jsonl"
    p5.write_text(
        json.dumps({"id": "q5", "lang": "pt", "category": "answerable", "query": "q", "gold_urls": ["https://site.com/"], "gold_snippets": []}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="gold_snippets"):
        cal.load_labeled(p5)

    # 6. Valid records
    p_ok = tmp_path / "valid.jsonl"
    p_ok.write_text(
        json.dumps({"id": "ok1", "lang": "pt", "category": "answerable", "query": "q", "gold_urls": ["https://a.com/"], "gold_snippets": ["s1"]}) + "\n"
        + json.dumps({"id": "ok2", "lang": "en", "category": "off_topic", "query": "q2", "gold_urls": [], "gold_snippets": []}) + "\n",
        encoding="utf-8",
    )
    loaded = cal.load_labeled(p_ok)
    assert len(loaded) == 2
    assert loaded[0]["id"] == "ok1"
    assert loaded[1]["id"] == "ok2"


def test_evaluate_hit_and_mrr_ranks() -> None:
    # 3 chunks: c0 (url0), c1 (url1), c2 (url2)
    chunks = [
        {"chunk_id": f"c{i}", "doc_url": f"https://example.com/p{i}", "text": f"text {i}"}
        for i in range(3)
    ]
    # Chunk vectors orthogonal in 3D
    cvecs = np.eye(3, dtype=np.float32)

    # Query 1 matches c0 top-1 (rank 1)
    # Query 2 matches c1 top-1, but gold is c2 (rank 2, since score to c2 > score to c0)
    records = [
        {"id": "r1", "lang": "pt", "category": "answerable", "gold_urls": ["https://example.com/p0"], "gold_snippets": ["text 0"]},
        {"id": "r2", "lang": "en", "category": "answerable", "gold_urls": ["https://example.com/p2"], "gold_snippets": ["text 2"]},
    ]
    # q1 = [1, 0, 0] -> ranks c0 at pos 1
    # q2 = [0, 0.8, 0.6] -> inner products: c1=0.8, c2=0.6, c0=0.0 -> order: c1 (pos 1), c2 (pos 2)
    qvecs = np.array([[1.0, 0.0, 0.0], [0.0, 0.8, 0.6]], dtype=np.float32)

    res = cal.evaluate(records, qvecs, chunks, cvecs)
    pq = res["per_query"]
    assert pq[0]["gold_rank"] == 1
    assert pq[1]["gold_rank"] == 2

    ret = res["retrieval"]
    assert ret["n"] == 2
    assert ret["hit@1"] == 0.5  # 1 out of 2
    assert ret["hit@3"] == 1.0  # 2 out of 2
    # mrr@10 = (1/1 + 1/2) / 2 = 1.5 / 2 = 0.75
    assert ret["mrr@10"] == pytest.approx(0.75)


def test_evaluate_answer_hit3_multiline() -> None:
    chunks = [
        {
            "chunk_id": "c0",
            "doc_url": "https://site.getnet.com.br/crediario/",
            "text": "Parcelamento em\n  até 48x   com taxas especiais.",
        }
    ]
    cvecs = np.array([[1.0]], dtype=np.float32)
    qvecs = np.array([[1.0]], dtype=np.float32)

    # Snippet with different spacing and case
    records = [
        {
            "id": "a01",
            "lang": "pt",
            "category": "answerable",
            "gold_urls": ["https://site.getnet.com.br/crediario/"],
            "gold_snippets": ["Até  48X"],
        }
    ]
    res = cal.evaluate(records, qvecs, chunks, cvecs)
    assert res["per_query"][0]["answer_hit@3"] is True
    assert res["retrieval"]["answer_hit@3"] == 1.0


def test_abstention_curve_and_choose_threshold_tie() -> None:
    # Synthetic per-query with answerable, off_topic, and uncovered
    per_query = [
        {"category": "answerable", "top1_score": 0.80},
        {"category": "answerable", "top1_score": 0.60},
        {"category": "off_topic", "top1_score": 0.40},
        {"category": "off_topic", "top1_score": 0.20},
        {"category": "uncovered", "top1_score": 0.50},
    ]
    thresholds = [0.30, 0.50, 0.70]
    curve = cal.abstention_curve(per_query, thresholds)
    assert len(curve) == 3

    # At t=0.50:
    # answer_rate: scores >= 0.50 are 0.80, 0.60 (2/2 = 1.0)
    # off_topic_abstain_rate: scores < 0.50 are 0.40, 0.20 (2/2 = 1.0)
    # uncovered_abstain_rate: scores < 0.50 is none (0/1 = 0.0)
    # balanced_accuracy: (1.0 + 1.0) / 2 = 1.0
    # abstained among answerable+off_topic: 2 off_topic (0.40, 0.20), 0 answerable -> precision = 2/2 = 1.0
    at_50 = next(r for r in curve if r["threshold"] == 0.50)
    assert at_50["answer_rate"] == 1.0
    assert at_50["off_topic_abstain_rate"] == 1.0
    assert at_50["uncovered_abstain_rate"] == 0.0
    assert at_50["balanced_accuracy"] == 1.0
    assert at_50["abstain_precision"] == 1.0
    assert at_50["abstain_recall"] == 1.0

    # Plateau tie test: 4 tied values [0.41, 0.42, 0.43, 0.44] -> lower median is index (4-1)//2 = 1 -> 0.42
    plateau = [
        {"threshold": 0.40, "balanced_accuracy": 0.80},
        {"threshold": 0.41, "balanced_accuracy": 0.95},
        {"threshold": 0.42, "balanced_accuracy": 0.95},
        {"threshold": 0.43, "balanced_accuracy": 0.95},
        {"threshold": 0.44, "balanced_accuracy": 0.95},
        {"threshold": 0.45, "balanced_accuracy": 0.70},
    ]
    chosen = cal.choose_threshold(plateau)
    assert chosen == 0.42


def test_run_embed_with_fake_embedder(tmp_path: Path) -> None:
    ds_file = tmp_path / "ds.jsonl"
    ds_file.write_text(
        json.dumps({"id": "q1", "lang": "pt", "category": "off_topic", "query": "hello", "gold_urls": [], "gold_snippets": []}) + "\n",
        encoding="utf-8",
    )
    npy_file = tmp_path / "emb.npy"
    meta_file = tmp_path / "meta.json"

    class FakeEmbedder:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def embed_query(self, text: str) -> list[float]:
            self.calls.append(text)
            return [0.5] * settings.EMBEDDING_DIM

        def embed_documents(self, texts: Any) -> Any:
            raise AssertionError("embed_documents must not be called by run_embed")

    embedder = FakeEmbedder()
    cal.run_embed(ds_file, npy_file, meta_file, embedder=embedder, sleep_s=0.0)

    assert embedder.calls == ["hello"]
    arr = np.load(npy_file)
    assert arr.shape == (1, settings.EMBEDDING_DIM)
    assert arr.dtype == np.float32

    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    assert meta["embedding_model"] == settings.EMBEDDING_MODEL
    assert meta["dim"] == settings.EMBEDDING_DIM
    assert meta["task_type"] == "RETRIEVAL_QUERY"
    assert meta["query_ids"] == ["q1"]
    assert "dataset_sha256" in meta


def test_run_report_refuses_mismatches(tmp_path: Path) -> None:
    ds_file = tmp_path / "ds.jsonl"
    rec = {"id": "q1", "lang": "pt", "category": "off_topic", "query": "q", "gold_urls": [], "gold_snippets": []}
    ds_file.write_text(json.dumps(rec) + "\n", encoding="utf-8")

    npy_file = tmp_path / "emb.npy"
    np.save(npy_file, np.zeros((1, settings.EMBEDDING_DIM), dtype=np.float32))

    meta_file = tmp_path / "meta.json"
    meta = {
        "embedding_model": settings.EMBEDDING_MODEL,
        "dim": settings.EMBEDDING_DIM,
        "task_type": "RETRIEVAL_QUERY",
        "query_ids": ["q1"],
        "dataset_sha256": cal.dataset_sha256([rec]),
        "created_at": "2026-11-07T00:00:00Z",
    }
    meta_file.write_text(json.dumps(meta), encoding="utf-8")

    # Build dummy index
    class DocEmb:
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * settings.EMBEDDING_DIM for _ in texts]

    idx_dir = tmp_path / "idx"
    chunks = [{"chunk_id": "c1", "doc_url": "https://a.com/", "title": "t", "market": "BR", "fetched_at": "x", "doc_sha256": "y", "text": "text"}]
    index_mod.build_index(chunks, DocEmb(), idx_dir, settings.EMBEDDING_MODEL, settings.EMBEDDING_DIM, "sha")

    # 1. query_ids mismatch
    bad_meta = dict(meta, query_ids=["other_id"])
    meta_file.write_text(json.dumps(bad_meta), encoding="utf-8")
    with pytest.raises(ValueError, match="query_ids"):
        cal.run_report(ds_file, npy_file, meta_file, idx_dir, tmp_path / "out.json", tmp_path / "out.md")

    # 2. dataset_sha256 mismatch
    bad_meta = dict(meta, dataset_sha256="0" * 64)
    meta_file.write_text(json.dumps(bad_meta), encoding="utf-8")
    with pytest.raises(ValueError, match="dataset_sha256"):
        cal.run_report(ds_file, npy_file, meta_file, idx_dir, tmp_path / "out.json", tmp_path / "out.md")

    # 3. embedding_model mismatch
    bad_meta = dict(meta, embedding_model="unexpected-model")
    meta_file.write_text(json.dumps(bad_meta), encoding="utf-8")
    with pytest.raises(ValueError, match="embedding_model"):
        cal.run_report(ds_file, npy_file, meta_file, idx_dir, tmp_path / "out.json", tmp_path / "out.md")


def test_run_report_outputs(tmp_path: Path) -> None:
    ds_file = tmp_path / "ds.jsonl"
    recs = [
        {"id": "a01", "lang": "pt", "category": "answerable", "query": "q1", "gold_urls": ["https://site.com/p1"], "gold_snippets": ["trecho 1"]},
        {"id": "o01", "lang": "pt", "category": "off_topic", "query": "q2", "gold_urls": [], "gold_snippets": []},
    ]
    ds_file.write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")

    class FakeEmbedder:
        def embed_query(self, text: str) -> list[float]:
            v = [0.0] * settings.EMBEDDING_DIM
            v[0] = 1.0 if "q1" in text else 0.1
            return v

    npy_file = tmp_path / "emb.npy"
    meta_file = tmp_path / "meta.json"
    cal.run_embed(ds_file, npy_file, meta_file, embedder=FakeEmbedder(), sleep_s=0.0)

    class DocEmb:
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            res = []
            for t in texts:
                v = [0.0] * settings.EMBEDDING_DIM
                v[0] = 1.0 if "trecho 1" in t else 0.05
                res.append(v)
            return res

    idx_dir = tmp_path / "idx"
    chunks = [
        {"chunk_id": "c1", "doc_url": "https://site.com/p1", "title": "t1", "market": "BR", "fetched_at": "x", "doc_sha256": "y", "text": "trecho 1 com valor"},
        {"chunk_id": "c2", "doc_url": "https://site.com/p2", "title": "t2", "market": "BR", "fetched_at": "x", "doc_sha256": "z", "text": "outro texto"},
    ]
    index_mod.build_index(chunks, DocEmb(), idx_dir, settings.EMBEDDING_MODEL, settings.EMBEDDING_DIM, "sha_test")

    out_json = tmp_path / "report.json"
    out_md = tmp_path / "report.md"
    rep = cal.run_report(ds_file, npy_file, meta_file, idx_dir, out_json, out_md)

    assert out_json.exists()
    assert out_md.exists()
    assert "abstention" in rep
    assert "retrieval" in rep
    assert rep["dataset"]["n_queries"] == 2

    md_text = out_md.read_text(encoding="utf-8")
    assert "hit@3" in md_text
    assert "uncovered" in md_text
    assert f"{rep['abstention']['chosen_threshold']:.2f}" in md_text
