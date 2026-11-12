"""Offline-capable evaluation runner and reporter for hybrid retrieval (dense + BM25 + LLM rerank)."""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from weakref import WeakKeyDictionary

import numpy as np

from src.config import settings
from src.core.llm import LLMConfigurationError, LLMNotConfiguredError
from src.core.pricing import cost_usd
from src.eval.metrics import pct
from src.rag.calibration import dataset_sha256, load_labeled, normalize_text
from src.rag.index import VectorIndex
from src.rag.lexical import BM25Index
from src.rag.reranker import LLMReranker
from src.rag.retriever import Retriever

DATASET = "data/eval/retrieval_labeled.jsonl"
EMB_NPY = "data/eval/retrieval_query_embeddings.npy"
EMB_META = "data/eval/retrieval_query_embeddings.json"
RUNS_DIR = "reports/retrieval_runs"

METRIC_KEYS = (
    "answer_rate",
    "hit@1",
    "hit@3",
    "mrr",
    "answer_hit@3",
    "off_topic_abstain_rate",
    "uncovered_abstain_rate",
)

_BM25_CACHE: WeakKeyDictionary[Any, tuple[int, int, BM25Index]] = WeakKeyDictionary()


class _StaticVectorEmbedder:
    """Stub embedder returning a precomputed query vector without calling external APIs."""

    def __init__(self, vector: Any) -> None:
        self._vector = vector

    def embed_query(self, _query: str) -> Any:
        return self._vector


def _get_or_build_bm25(index: VectorIndex) -> BM25Index:
    chunks_id = id(index.chunks)
    chunks_len = len(index.chunks)
    try:
        cached = _BM25_CACHE.get(index)
        if cached is not None and cached[0] == chunks_id and cached[1] == chunks_len:
            return cached[2]
    except TypeError:
        cached = None

    bm25 = BM25Index([f"{c.get('title', '')}\n{c.get('text', '')}" for c in index.chunks])
    try:
        _BM25_CACHE[index] = (chunks_id, chunks_len, bm25)
    except TypeError:
        pass
    return bm25


def load_inputs() -> tuple[list[dict[str, Any]], np.ndarray, VectorIndex]:
    """Load labeled retrieval queries, precomputed query embeddings, and VectorIndex."""
    records = load_labeled(Path(DATASET))
    qvecs = np.load(EMB_NPY)
    meta = json.loads(Path(EMB_META).read_text(encoding="utf-8"))

    if meta.get("query_ids") != [r["id"] for r in records]:
        raise ValueError("retrieval_query_embeddings.json query_ids do not match retrieval_labeled.jsonl")
    if meta.get("dataset_sha256") != dataset_sha256(records):
        raise ValueError("retrieval_query_embeddings.json dataset_sha256 mismatch")
    if meta.get("embedding_model") != settings.EMBEDDING_MODEL:
        raise ValueError(
            f"Embedding model mismatch: expected '{settings.EMBEDDING_MODEL}', "
            f"got '{meta.get('embedding_model')}'"
        )
    if qvecs.ndim != 2 or qvecs.shape[0] != len(records) or qvecs.shape[1] != settings.EMBEDDING_DIM:
        raise ValueError(
            f"Query embeddings shape mismatch: expected ({len(records)}, {settings.EMBEDDING_DIM}), "
            f"got {tuple(qvecs.shape)}"
        )

    index = VectorIndex.load(
        settings.INDEX_DIR,
        expected_model=settings.EMBEDDING_MODEL,
        expected_dim=settings.EMBEDDING_DIM,
    )
    return records, qvecs, index


def build_retriever(
    index: VectorIndex,
    vector: Any,
    reranker: Any,
) -> Retriever:
    """Construct production-configured hybrid Retriever over a precomputed query vector."""
    return Retriever(
        index=index,
        embedder=_StaticVectorEmbedder(vector),
        min_score=settings.RAG_MIN_SCORE,
        top_k=settings.RAG_TOP_K,
        lexical=_get_or_build_bm25(index),
        reranker=reranker,
        dense_candidates=settings.RAG_DENSE_CANDIDATES,
        lexical_candidates=settings.RAG_LEXICAL_CANDIDATES,
        min_relevance=settings.RAG_RERANK_MIN_RELEVANCE,
        rrf_k=settings.RAG_RRF_K,
    )


def run_hybrid(
    run_id: str,
    runs_dir: str | Path = RUNS_DIR,
    reranker: Any | None = None,
    sleep_s: float = 0.0,
    max_consecutive_errors: int = 3,
) -> dict[str, Any]:
    """Execute resumable hybrid retrieval run over the labeled 3D dataset."""
    records, qvecs, index = load_inputs()
    active_reranker = reranker if reranker is not None else LLMReranker()

    out_path = Path(runs_dir) / f"{run_id}.jsonl"
    last_by_id: dict[str, dict[str, Any]] = {}
    if out_path.exists():
        for raw_line in out_path.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            row = json.loads(raw_line)
            last_by_id[row["id"]] = row

    attempted = 0
    ok = 0
    invalid = 0
    errors = 0
    gated = 0
    skipped = 0
    consecutive_errors = 0
    stopped_early = False

    for rec, qvec in zip(records, qvecs, strict=True):
        cid = rec["id"]
        prev = last_by_id.get(cid)
        if prev is not None and prev.get("rerank_status") in ("ok", "invalid", "gated"):
            skipped += 1
            continue

        retriever = build_retriever(index, qvec, active_reranker)
        result = retriever.search(rec["query"], include_candidates=True)
        retrieval_info = result["retrieval"]
        rerank_info = retrieval_info["rerank"]

        if rerank_info is None:
            rerank_status = "gated"
            error_type = None
            latency_ms = None
            model_name = None
            usage = None
        else:
            rerank_status = rerank_info["status"]
            error_type = rerank_info["error_type"]
            latency_ms = rerank_info["latency_ms"]
            model_name = rerank_info["model"]
            usage = retrieval_info["usage"]

        row = {
            "id": cid,
            "run_id": run_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": result["status"],
            "reason": result.get("reason"),
            "documents": [d["chunk_id"] for d in result["documents"]],
            "candidates": retrieval_info["candidate_list"],
            "relevance": retrieval_info["relevance"],
            "rerank_status": rerank_status,
            "error_type": error_type,
            "latency_ms": latency_ms,
            "model": model_name,
            "usage": usage,
        }

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()

        attempted += 1
        if rerank_status == "gated":
            gated += 1
            consecutive_errors = 0
        elif rerank_status == "ok":
            ok += 1
            consecutive_errors = 0
        elif rerank_status == "invalid":
            invalid += 1
            consecutive_errors = 0
        else:
            errors += 1
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                stopped_early = True
                break

        if rerank_status != "gated" and sleep_s > 0.0:
            time.sleep(sleep_s)

    return {
        "attempted": attempted,
        "ok": ok,
        "invalid": invalid,
        "errors": errors,
        "gated": gated,
        "skipped": skipped,
        "stopped_early": stopped_early,
    }


def dense_baseline(
    records: list[dict[str, Any]],
    qvecs: np.ndarray,
    index: VectorIndex,
) -> dict[str, list[str]]:
    """Compute dense-only baseline document chunk_ids per query under current threshold rules."""
    out: dict[str, list[str]] = {}
    for rec, qvec in zip(records, qvecs, strict=True):
        s = index.scores(qvec)
        if len(s) == 0:
            out[rec["id"]] = []
            continue
        order = [int(i) for i in np.argsort(-s, kind="stable")]
        if float(s[order[0]]) < settings.RAG_MIN_SCORE:
            out[rec["id"]] = []
            continue
        out[rec["id"]] = [
            index.chunks[idx]["chunk_id"]
            for idx in order[: settings.RAG_TOP_K]
            if float(s[idx]) >= settings.RAG_MIN_SCORE
        ]
    return out


def metrics(
    records_labeled: list[dict[str, Any]],
    documents_by_id: dict[str, list[str]],
    chunks_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compute retrieval quality metrics across answerable, off_topic, and uncovered categories."""
    answerable = [r for r in records_labeled if r["category"] == "answerable"]
    off_topic = [r for r in records_labeled if r["category"] == "off_topic"]
    uncovered = [r for r in records_labeled if r["category"] == "uncovered"]

    answered = 0
    hit1 = 0
    hit3 = 0
    rr_list: list[float] = []
    answer_hit3 = 0
    answer_chunk_rank: dict[str, int | None] = {}

    for rec in answerable:
        cid = rec["id"]
        doc_ids = documents_by_id.get(cid, [])
        if doc_ids:
            answered += 1

        gold_urls = set(rec.get("gold_urls") or [])
        norm_snippets = [
            sn for sn in (normalize_text(s) for s in (rec.get("gold_snippets") or [])) if sn
        ]

        url_rank: int | None = None
        ans_rank: int | None = None
        for pos, chunk_id in enumerate(doc_ids, 1):
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None or chunk.get("doc_url") not in gold_urls:
                continue
            if url_rank is None:
                url_rank = pos
            if ans_rank is None and norm_snippets:
                norm_text = normalize_text(chunk.get("text", ""))
                if any(sn in norm_text for sn in norm_snippets):
                    ans_rank = pos

        if url_rank is not None:
            if url_rank <= 1:
                hit1 += 1
            if url_rank <= 3:
                hit3 += 1
            rr_list.append(1.0 / url_rank)
        else:
            rr_list.append(0.0)

        answer_chunk_rank[cid] = ans_rank
        if ans_rank is not None and ans_rank <= 3:
            answer_hit3 += 1

    n_ans = len(answerable)
    off_abstain = sum(1 for r in off_topic if not documents_by_id.get(r["id"], []))
    unc_abstain = sum(1 for r in uncovered if not documents_by_id.get(r["id"], []))

    return {
        "answer_rate": answered / n_ans if n_ans else 0.0,
        "hit@1": hit1 / n_ans if n_ans else 0.0,
        "hit@3": hit3 / n_ans if n_ans else 0.0,
        "mrr": math.fsum(rr_list) / n_ans if n_ans else 0.0,
        "answer_hit@3": answer_hit3 / n_ans if n_ans else 0.0,
        "off_topic_abstain_rate": off_abstain / len(off_topic) if off_topic else 0.0,
        "uncovered_abstain_rate": unc_abstain / len(uncovered) if uncovered else 0.0,
        "answer_chunk_rank": answer_chunk_rank,
    }


def _summarize_run(
    run_id: str,
    run_path: Path,
    records: list[dict[str, Any]],
    chunks_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Load and aggregate metrics, counts, latency, and cost for a single hybrid run."""
    last_by_id: dict[str, dict[str, Any]] = {}
    for raw_line in run_path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        row = json.loads(raw_line)
        last_by_id[row["id"]] = row

    counts = {"ok": 0, "invalid": 0, "errors": 0, "gated": 0}
    model_name: str | None = None
    latencies: list[float] = []
    usage_rows: list[dict[str, Any]] = []

    for row in last_by_id.values():
        rstatus = row.get("rerank_status")
        if rstatus == "ok":
            counts["ok"] += 1
        elif rstatus == "invalid":
            counts["invalid"] += 1
        elif rstatus == "error":
            counts["errors"] += 1
        elif rstatus == "gated":
            counts["gated"] += 1

        if model_name is None and row.get("model") is not None:
            model_name = row["model"]

        if rstatus in ("ok", "invalid") and row.get("latency_ms") is not None:
            latencies.append(float(row["latency_ms"]))

        if isinstance(row.get("usage"), dict):
            usage_rows.append(row["usage"])

    complete = len(last_by_id) == len(records) and counts["errors"] == 0
    docs_by_id = {
        rec["id"]: list(last_by_id[rec["id"]].get("documents") or [])
        if rec["id"] in last_by_id
        else []
        for rec in records
    }
    run_metrics = metrics(records, docs_by_id, chunks_by_id)

    p50 = pct(latencies, 0.50) if latencies else None
    p95 = pct(latencies, 0.95) if latencies else None

    if usage_rows:
        mean_in = math.fsum(float(u.get("input_tokens") or 0) for u in usage_rows) / len(usage_rows)
        mean_out = math.fsum(float(u.get("output_tokens") or 0) for u in usage_rows) / len(usage_rows)
        tokens_mean_per_call: dict[str, float] | None = {
            "input_tokens": mean_in,
            "output_tokens": mean_out,
        }
        cost_per_call = cost_usd(model_name, mean_in, mean_out)
    else:
        tokens_mean_per_call = None
        cost_per_call = None

    summary_entry = {
        "complete": complete,
        "counts": counts,
        "model": model_name,
        "metrics": run_metrics,
        "rerank_latency_p50_ms": p50,
        "rerank_latency_p95_ms": p95,
        "tokens_mean_per_call": tokens_mean_per_call,
        "cost_usd_per_call": cost_per_call,
    }
    return summary_entry, last_by_id


def _decision_label(row: dict[str, Any] | None) -> str:
    if row is None:
        return "ausente"
    docs = row.get("documents") or []
    rstatus = row.get("rerank_status", "-")
    if docs:
        return f"responde ({len(docs)}) [{rstatus}]"
    reason = row.get("reason") or "abstain"
    return f"abstém ({reason}) [{rstatus}]"


def _render_markdown(
    report: dict[str, Any],
    records: list[dict[str, Any]],
    dense_docs: dict[str, list[str]],
    rows_by_run: dict[str, dict[str, dict[str, Any]]],
) -> str:
    """Render pt-BR comparison report covering metrics, per-query decisions, and rank shifts."""
    run_ids = list(report["runs"].keys())
    lines: list[str] = [
        "# Relatório de Busca Híbrida (Denso + BM25 + Reranker LLM)",
        "",
        f"- Conjunto: `{report['dataset']}` (`{report['dataset_sha256'][:12]}`)",
        f"- Trechos no índice: {report['index_chunks']}",
        f"- Execuções avaliadas: {', '.join(f'`{rid}`' for rid in run_ids)}",
        "",
        "## Comparação de métricas",
        "",
    ]

    header = ["Métrica", "Denso (regra atual)", *run_ids, "Média"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    dense_m = report["dense"]["metrics"]
    for key in METRIC_KEYS:
        row_cells = [f"`{key}`", f"{dense_m[key]:.4f}"]
        for rid in run_ids:
            row_cells.append(f"{report['runs'][rid]['metrics'][key]:.4f}")
        row_cells.append(f"{report['summary'][key]['mean']:.4f}")
        lines.append("| " + " | ".join(row_cells) + " |")

    lines.extend(["", "## Decisão por consulta", ""])
    q_header = ["ID", "Categoria", "Denso (regra atual)", *run_ids]
    lines.append("| " + " | ".join(q_header) + " |")
    lines.append("| " + " | ".join(["---"] * len(q_header)) + " |")

    for rec in records:
        cid = rec["id"]
        ddocs = dense_docs.get(cid, [])
        dense_dec = f"responde ({len(ddocs)})" if ddocs else "abstém"
        cells = [f"`{cid}`", rec["category"], dense_dec]
        for rid in run_ids:
            cells.append(_decision_label(rows_by_run[rid].get(cid)))
        lines.append("| " + " | ".join(cells) + " |")

    lines.extend(["", "## Mudanças de posição do trecho com a resposta (`answerable`)", ""])
    dense_ranks = dense_m["answer_chunk_rank"]
    changes: list[str] = []
    for rec in records:
        if rec["category"] != "answerable":
            continue
        cid = rec["id"]
        d_rank = dense_ranks.get(cid)
        run_ranks = [report["runs"][rid]["metrics"]["answer_chunk_rank"].get(cid) for rid in run_ids]
        numeric_ranks = [float(r) for r in run_ranks if r is not None]
        mean_rank_str = f"{math.fsum(numeric_ranks) / len(numeric_ranks):.2f}" if numeric_ranks else "None"
        mean_cmp = math.fsum(numeric_ranks) / len(numeric_ranks) if len(numeric_ranks) == len(run_ids) else None
        changed = any(r != d_rank for r in run_ranks) or (mean_cmp != d_rank)
        if changed:
            per_run_fmt = ", ".join(f"{rid}={r}" for rid, r in zip(run_ids, run_ranks, strict=True))
            changes.append(
                f"| `{cid}` | {d_rank} | {per_run_fmt} | {mean_rank_str} |"
            )

    if changes:
        lines.append("| ID | Posição denso | Posições por execução | Média híbrida |")
        lines.append("| --- | --- | --- | --- |")
        lines.extend(changes)
    else:
        lines.append("Nenhuma consulta `answerable` mudou de posição entre o denso e as execuções.")

    lines.append("")
    return "\n".join(lines)


def hybrid_report(
    run_ids: list[str],
    runs_dir: str | Path = RUNS_DIR,
    out_json: str | Path = "reports/retrieval_hybrid.json",
    out_md: str | Path = "reports/retrieval_hybrid.md",
) -> dict[str, Any]:
    """Generate JSON and pt-BR Markdown comparison reports for one or more hybrid runs."""
    runs_base = Path(runs_dir)
    run_paths = {rid: runs_base / f"{rid}.jsonl" for rid in run_ids}
    missing = [str(p) for p in run_paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing run file(s): {', '.join(missing)}")

    records, qvecs, index = load_inputs()
    chunks_by_id = {c["chunk_id"]: c for c in index.chunks}
    dense_docs = dense_baseline(records, qvecs, index)
    dense_metrics = metrics(records, dense_docs, chunks_by_id)

    runs_summary: dict[str, dict[str, Any]] = {}
    rows_by_run: dict[str, dict[str, dict[str, Any]]] = {}
    for rid in run_ids:
        entry, last_rows = _summarize_run(rid, run_paths[rid], records, chunks_by_id)
        runs_summary[rid] = entry
        rows_by_run[rid] = last_rows

    summary: dict[str, dict[str, float]] = {}
    for key in METRIC_KEYS:
        vals = [float(runs_summary[rid]["metrics"][key]) for rid in run_ids]
        summary[key] = {
            "mean": math.fsum(vals) / len(vals),
            "min": min(vals),
            "max": max(vals),
        }

    report: dict[str, Any] = {
        "dataset": DATASET,
        "dataset_sha256": dataset_sha256(records),
        "index_chunks": len(index.chunks),
        "settings": {
            "min_score": settings.RAG_MIN_SCORE,
            "top_k": settings.RAG_TOP_K,
            "dense_candidates": settings.RAG_DENSE_CANDIDATES,
            "lexical_candidates": settings.RAG_LEXICAL_CANDIDATES,
            "min_relevance": settings.RAG_RERANK_MIN_RELEVANCE,
            "rrf_k": settings.RAG_RRF_K,
        },
        "dense": {"metrics": dense_metrics},
        "runs": runs_summary,
        "summary": summary,
    }

    out_json_path = Path(out_json)
    out_md_path = Path(out_md)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_md_path.parent.mkdir(parents=True, exist_ok=True)

    out_json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    out_md_path.write_text(
        _render_markdown(report, records, dense_docs, rows_by_run),
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for hybrid retrieval evaluation."""
    parser = argparse.ArgumentParser(description="Hybrid retrieval evaluation runner and reporter.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Execute a hybrid retrieval run over the labeled queries.")
    run_p.add_argument("--run-id", required=True, help="Run identifier (writes <run_id>.jsonl).")
    run_p.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep after each rerank call.")

    rep_p = sub.add_parser("report", help="Generate comparison report from recorded hybrid runs.")
    rep_p.add_argument("--runs", required=True, help="Comma-separated run IDs (e.g. rerank-1,rerank-2,rerank-3).")

    args = parser.parse_args(argv)

    if args.command == "run":
        if not settings.GEMINI_API_KEY:
            print(
                "Error: GEMINI_API_KEY is required to run hybrid retrieval with the LLM reranker.",
                file=sys.stderr,
            )
            return 2
        try:
            summary = run_hybrid(run_id=args.run_id, sleep_s=args.sleep)
        except (LLMNotConfiguredError, LLMConfigurationError) as exc:
            print(f"Configuration error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    if args.command == "report":
        run_ids = [item.strip() for item in args.runs.split(",") if item.strip()]
        if not run_ids:
            print("Error: --runs must include at least one run ID.", file=sys.stderr)
            return 1
        try:
            report = hybrid_report(run_ids)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
