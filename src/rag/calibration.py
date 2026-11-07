"""Retrieval evaluation and threshold calibration for RAG."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from src.config import settings

METRIC_KEYS = ("hit@1", "hit@3", "hit@5", "mrr@10", "answer_hit@3")
CURVE_KEYS = (
    "answer_rate",
    "off_topic_abstain_rate",
    "uncovered_abstain_rate",
    "balanced_accuracy",
    "abstain_precision",
    "abstain_recall",
)


def load_labeled(path: str | Path) -> list[dict[str, Any]]:
    """
    Read labeled JSONL dataset and return records in file order.

    Raises ValueError for:
    - category not in {"answerable", "uncovered", "off_topic"}
    - lang not in {"pt", "en"}
    - duplicate id
    - category == "answerable" with empty or missing gold_urls or gold_snippets
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for line_num, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception as exc:
            raise ValueError(f"Invalid JSON at line {line_num}: {exc}") from exc

        rec_id = rec.get("id")
        if not rec_id:
            raise ValueError(f"Missing 'id' at line {line_num}")
        if rec_id in seen_ids:
            raise ValueError(f"Duplicate id '{rec_id}' at line {line_num}")
        seen_ids.add(rec_id)

        category = rec.get("category")
        if category not in {"answerable", "uncovered", "off_topic"}:
            raise ValueError(f"Invalid category '{category}' at line {line_num}")

        lang = rec.get("lang")
        if lang not in {"pt", "en"}:
            raise ValueError(f"Invalid lang '{lang}' at line {line_num}")

        if category == "answerable":
            gold_urls = rec.get("gold_urls")
            if not isinstance(gold_urls, list) or len(gold_urls) == 0:
                raise ValueError(
                    f"Empty or missing 'gold_urls' for answerable query '{rec_id}' at line {line_num}"
                )
            gold_snippets = rec.get("gold_snippets")
            if not isinstance(gold_snippets, list) or len(gold_snippets) == 0:
                raise ValueError(
                    f"Empty or missing 'gold_snippets' for answerable query '{rec_id}' at line {line_num}"
                )

        records.append(rec)

    return records


def dataset_sha256(records: list[dict[str, Any]]) -> str:
    """Calculate canonical SHA-256 hash of dataset records."""
    canon = "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def normalize_text(s: str) -> str:
    """Normalize text without regex by splitting whitespace and lowercasing."""
    return " ".join(s.split()).lower()


def threshold_grid() -> list[float]:
    """Return threshold grid from 0.30 to 0.95 in steps of 0.01."""
    return [round(0.30 + 0.01 * i, 2) for i in range(66)]


def evaluate(
    records: list[dict[str, Any]],
    query_vectors: Any,
    chunks: list[dict[str, Any]],
    chunk_vectors: Any,
) -> dict[str, Any]:
    """
    Evaluate retrieval quality across labeled queries.

    Uses cosine similarity (float64 inner product with L2-normalized vectors)
    and stable sort. Computes hit@k, mrr@10, and answer_hit@3.
    """
    c_mat = np.asarray(chunk_vectors, dtype=np.float32).astype(np.float64)
    per_query: list[dict[str, Any]] = []

    for r, q in zip(records, query_vectors):
        q_arr = np.asarray(q, dtype=np.float32).astype(np.float64)
        n = np.linalg.norm(q_arr)
        q_norm = q_arr / n if n > 0 else q_arr
        scores = c_mat @ q_norm
        order = np.argsort(-scores, kind="stable")

        gold_urls = set(r.get("gold_urls", []))
        gold_rank = None
        for pos, idx in enumerate(order[:10], start=1):
            if chunks[idx]["doc_url"] in gold_urls:
                gold_rank = pos
                break

        snips = [normalize_text(x) for x in r.get("gold_snippets", [])]
        ah3 = any(
            chunks[i]["doc_url"] in gold_urls
            and any(x in normalize_text(chunks[i]["text"]) for x in snips)
            for i in order[:3]
        )

        top = int(order[0])
        per_query.append({
            "id": r["id"],
            "lang": r["lang"],
            "category": r["category"],
            "top1_score": float(scores[top]),
            "top1_chunk_id": chunks[top]["chunk_id"],
            "top1_url": chunks[top]["doc_url"],
            "gold_rank": gold_rank,
            "answer_hit@3": bool(ah3) if r["category"] == "answerable" else None,
        })

    def agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
        n = len(rows)
        if not n:
            return {k: None for k in METRIC_KEYS} | {"n": 0}
        return {
            "n": n,
            "hit@1": sum(1 for x in rows if x["gold_rank"] and x["gold_rank"] <= 1) / n,
            "hit@3": sum(1 for x in rows if x["gold_rank"] and x["gold_rank"] <= 3) / n,
            "hit@5": sum(1 for x in rows if x["gold_rank"] and x["gold_rank"] <= 5) / n,
            "mrr@10": sum(1.0 / x["gold_rank"] for x in rows if x["gold_rank"]) / n,
            "answer_hit@3": sum(1 for x in rows if x["answer_hit@3"]) / n,
        }

    ans = [x for x in per_query if x["category"] == "answerable"]
    retrieval = agg(ans)
    retrieval["by_lang"] = {lg: agg([x for x in ans if x["lang"] == lg]) for lg in ("pt", "en")}

    return {"per_query": per_query, "retrieval": retrieval}


def abstention_curve(per_query: list[dict[str, Any]], thresholds: list[float]) -> list[dict[str, Any]]:
    """
    Compute abstention curve metrics over a list of candidate score thresholds.
    """
    a = [x["top1_score"] for x in per_query if x["category"] == "answerable"]
    o = [x["top1_score"] for x in per_query if x["category"] == "off_topic"]
    u = [x["top1_score"] for x in per_query if x["category"] == "uncovered"]

    rows: list[dict[str, Any]] = []
    for t in thresholds:
        ar = sum(1 for s in a if s >= t) / len(a) if a else None
        orr = sum(1 for s in o if s < t) / len(o) if o else None
        ur = sum(1 for s in u if s < t) / len(u) if u else None
        abst = sum(1 for s in a if s < t) + sum(1 for s in o if s < t)
        prec = (sum(1 for s in o if s < t) / abst) if abst else None
        ba = (ar + orr) / 2 if ar is not None and orr is not None else None
        rows.append({
            "threshold": t,
            "answer_rate": ar,
            "off_topic_abstain_rate": orr,
            "uncovered_abstain_rate": ur,
            "balanced_accuracy": ba,
            "abstain_precision": prec,
            "abstain_recall": orr,
        })
    return rows


def choose_threshold(curve: list[dict[str, Any]]) -> float:
    """
    Choose optimal threshold maximizing balanced_accuracy.
    On ties, pick the lower median of tied candidate thresholds.
    """
    best = max(round(r["balanced_accuracy"], 9) for r in curve)
    cands = sorted(r["threshold"] for r in curve if round(r["balanced_accuracy"], 9) == best)
    return cands[(len(cands) - 1) // 2]


def run_embed(
    dataset_path: str | Path,
    out_npy: str | Path,
    out_meta: str | Path,
    embedder: Any = None,
    sleep_s: float = 0.5,
) -> None:
    """
    Embed all queries in dataset with embed_query (RETRIEVAL_QUERY).
    Saves unnormalized float32 embeddings array and metadata JSON.
    """
    records = load_labeled(dataset_path)
    if embedder is None:
        from src.core.llm import get_embedder

        embedder = get_embedder("RETRIEVAL_QUERY")

    vectors: list[list[float]] = []
    for idx, r in enumerate(records):
        vec = embedder.embed_query(r["query"])
        if len(vec) != settings.EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension mismatch: expected {settings.EMBEDDING_DIM}, got {len(vec)}"
            )
        vectors.append(vec)
        if sleep_s > 0 and idx < len(records) - 1:
            time.sleep(sleep_s)

    arr = np.array(vectors, dtype=np.float32)
    out_npy_path = Path(out_npy)
    out_npy_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(out_npy_path, arr)

    out_meta_path = Path(out_meta)
    out_meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "embedding_model": settings.EMBEDDING_MODEL,
        "dim": settings.EMBEDDING_DIM,
        "task_type": "RETRIEVAL_QUERY",
        "query_ids": [r["id"] for r in records],
        "dataset_sha256": dataset_sha256(records),
        "created_at": datetime.now(UTC).isoformat(),
    }
    out_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def _fmt_float(val: float | None, fmt: str = ".3f", default: str = "-") -> str:
    """Format float or return default placeholder if None."""
    if val is None:
        return default
    return f"{val:{fmt}}"


def _generate_markdown_report(report: dict[str, Any]) -> str:
    """Format calibration metrics and curve as GitHub-flavored Markdown."""
    ret = report["retrieval"]
    by_lang = ret.get("by_lang", {})
    pt_met = by_lang.get("pt", {})
    en_met = by_lang.get("en", {})
    ab = report["abstention"]
    chosen = ab["chosen_threshold"]
    at_chosen = ab["at_chosen"]
    warnings = report.get("warnings", [])

    lines = [
        "# Relatório de Calibração e Avaliação de Retrieval (RAG)",
        "",
        f"- **Gerado em:** {report['generated_at']}",
        f"- **Dataset:** `{report['dataset']['path']}` ({report['dataset']['n_queries']} consultas, sha256 `{report['dataset']['sha256'][:12]}...`)",
        f"- **Índice:** `{report['index']['dir']}` ({report['index']['n_chunks']} chunks, modelo `{report['index']['embedding_model']}`, dim {report['index']['dim']})",
        "",
        "## 1. Métricas de Retrieval (Consultas Respondíveis)",
        "",
        "| Métrica | Geral (n=30) | Português (n=21) | Inglês (n=9) |",
        "| :--- | :---: | :---: | :---: |",
        f"| **hit@1** | {_fmt_float(ret.get('hit@1'))} | {_fmt_float(pt_met.get('hit@1'))} | {_fmt_float(en_met.get('hit@1'))} |",
        f"| **hit@3** | {_fmt_float(ret.get('hit@3'))} | {_fmt_float(pt_met.get('hit@3'))} | {_fmt_float(en_met.get('hit@3'))} |",
        f"| **hit@5** | {_fmt_float(ret.get('hit@5'))} | {_fmt_float(pt_met.get('hit@5'))} | {_fmt_float(en_met.get('hit@5'))} |",
        f"| **mrr@10** | {_fmt_float(ret.get('mrr@10'))} | {_fmt_float(pt_met.get('mrr@10'))} | {_fmt_float(en_met.get('mrr@10'))} |",
        f"| **answer_hit@3** | {_fmt_float(ret.get('answer_hit@3'))} | {_fmt_float(pt_met.get('answer_hit@3'))} | {_fmt_float(en_met.get('answer_hit@3'))} |",
        "",
        "## 2. Limiar Escolhido e Métricas de Abstenção",
        "",
        f"- **Limiar Calibrado (`RAG_MIN_SCORE`):** `{chosen:.2f}`",
        f"- **Regra de Seleção:** {ab['rule']}",
        f"- **Balanced Accuracy:** {_fmt_float(at_chosen.get('balanced_accuracy'))}",
        f"- **Taxa de Resposta (Answerable):** {_fmt_float(at_chosen.get('answer_rate'))}",
        f"- **Abstenção Off-Topic:** {_fmt_float(at_chosen.get('off_topic_abstain_rate'))}",
        f"- **Abstenção Uncovered (`uncovered`):** {_fmt_float(at_chosen.get('uncovered_abstain_rate'))} (consultas uncovered fora do corpus oficial da Getnet)",
        f"- **Precisão de Abstenção:** {_fmt_float(at_chosen.get('abstain_precision'), default='N/A')}",
        f"- **Recall de Abstenção:** {_fmt_float(at_chosen.get('abstain_recall'))}",
        "",
        "## 3. Curva de Abstenção",
        "",
        "| Limiar | Answer Rate | Off-Topic Abstain | Uncovered Abstain | Balanced Accuracy | Precisão | Recall |",
        "| :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    highlighted_thresholds = set()
    for row in ab["curve"]:
        t = round(row["threshold"], 2)
        if abs(t % 0.05) < 1e-6 or abs(t % 0.05 - 0.05) < 1e-6 or abs(t - chosen) < 1e-6:
            highlighted_thresholds.add(t)

    for row in sorted(ab["curve"], key=lambda x: x["threshold"]):
        t = round(row["threshold"], 2)
        if t in highlighted_thresholds:
            marker = " **(escolhido)**" if abs(t - chosen) < 1e-6 else ""
            lines.append(
                f"| {t:.2f}{marker} | {_fmt_float(row.get('answer_rate'))} | {_fmt_float(row.get('off_topic_abstain_rate'))} | "
                f"{_fmt_float(row.get('uncovered_abstain_rate'))} | {_fmt_float(row.get('balanced_accuracy'))} | "
                f"{_fmt_float(row.get('abstain_precision'), default='-')} | {_fmt_float(row.get('abstain_recall'))} |"
            )

    lines.extend([
        "",
        "## 4. Avisos",
        "",
    ])
    if warnings:
        for w in warnings:
            lines.append(f"- `[!WARNING]` `{w}`")
    else:
        lines.append("- Nenhum aviso reportado.")

    lines.extend([
        "",
        "## 5. Avaliação por Consulta",
        "",
        "| ID | Idioma | Categoria | Top-1 Score | Top-1 Chunk | Gold Rank | Answer Hit@3 | Decisão |",
        "| :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: |",
    ])
    for row in report["per_query"]:
        gr = str(row["gold_rank"]) if row["gold_rank"] is not None else "-"
        ah3 = "Sim" if row["answer_hit@3"] is True else ("Não" if row["answer_hit@3"] is False else "-")
        lines.append(
            f"| `{row['id']}` | {row['lang']} | {row['category']} | {row['top1_score']:.3f} | "
            f"`{row['top1_chunk_id']}` | {gr} | {ah3} | `{row['decision_at_chosen']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def run_report(
    dataset_path: str | Path,
    emb_npy: str | Path,
    emb_meta: str | Path,
    index_dir: str | Path,
    out_json: str | Path,
    out_md: str | Path,
) -> dict[str, Any]:
    """
    Run retrieval evaluation and abstention threshold calibration report.
    Validates metadata and index dimensions, computes metrics and curve, writes outputs.
    """
    records = load_labeled(dataset_path)

    emb_meta_path = Path(emb_meta)
    if not emb_meta_path.exists():
        raise FileNotFoundError(f"Embeddings meta file not found: {emb_meta}")
    meta = json.loads(emb_meta_path.read_text(encoding="utf-8"))

    if meta.get("query_ids") != [r["id"] for r in records]:
        raise ValueError("query_ids mismatch between dataset and embeddings metadata")
    if meta.get("dataset_sha256") != dataset_sha256(records):
        raise ValueError("dataset_sha256 mismatch between dataset and embeddings metadata")
    if meta.get("embedding_model") != settings.EMBEDDING_MODEL:
        raise ValueError(
            f"embedding_model mismatch: expected {settings.EMBEDDING_MODEL!r}, got {meta.get('embedding_model')!r}"
        )

    from src.rag.index import VectorIndex

    idx = VectorIndex.load(
        index_dir,
        expected_model=meta.get("embedding_model"),
        expected_dim=meta.get("dim"),
    )

    qvecs = np.load(emb_npy)
    if qvecs.shape[0] != len(records):
        raise ValueError(
            f"Embeddings count ({qvecs.shape[0]}) does not match records count ({len(records)})"
        )
    if qvecs.shape[1] != meta.get("dim"):
        raise ValueError(
            f"Embeddings dim ({qvecs.shape[1]}) does not match meta dim ({meta.get('dim')})"
        )

    eval_result = evaluate(records, qvecs, idx.chunks, idx.embeddings)
    grid = threshold_grid()
    curve = abstention_curve(eval_result["per_query"], grid)
    chosen = choose_threshold(curve)

    at_chosen = next(r for r in curve if abs(r["threshold"] - chosen) < 1e-6)

    warnings: list[str] = []
    if at_chosen["balanced_accuracy"] is not None and at_chosen["balanced_accuracy"] < 0.9:
        warnings.append("weak_separation")
    if at_chosen["uncovered_abstain_rate"] is not None and at_chosen["uncovered_abstain_rate"] < 0.5:
        warnings.append("uncovered_not_filtered")
    if eval_result["retrieval"]["answer_hit@3"] is not None and eval_result["retrieval"]["answer_hit@3"] < 0.7:
        warnings.append("low_answer_hit")
    if chosen in (0.30, 0.95):
        warnings.append("threshold_at_grid_edge")
    warnings.sort()

    per_query_annotated = []
    for row in eval_result["per_query"]:
        row_copy = dict(row)
        row_copy["decision_at_chosen"] = "answer" if row["top1_score"] >= chosen else "abstain"
        per_query_annotated.append(row_copy)

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "path": str(dataset_path),
            "sha256": dataset_sha256(records),
            "n_queries": len(records),
            "by_category": {
                cat: sum(1 for r in records if r["category"] == cat)
                for cat in ("answerable", "uncovered", "off_topic")
            },
            "by_lang": {
                lg: sum(1 for r in records if r["lang"] == lg)
                for lg in ("pt", "en")
            },
        },
        "index": {
            "dir": str(index_dir),
            "embedding_model": meta["embedding_model"],
            "dim": meta["dim"],
            "n_chunks": len(idx.chunks),
            "corpus_sha256": idx.meta.get("corpus_sha256"),
        },
        "query_embeddings": {
            "path": str(emb_npy),
            "created_at": meta.get("created_at"),
        },
        "retrieval": eval_result["retrieval"],
        "abstention": {
            "calibration_set": "answerable vs off_topic",
            "rule": "maximize balanced accuracy on answerable vs off_topic; ties pick lower median",
            "curve": curve,
            "chosen_threshold": chosen,
            "at_chosen": at_chosen,
        },
        "per_query": per_query_annotated,
        "warnings": warnings,
    }

    out_json_path = Path(out_json)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    out_md_path = Path(out_md)
    out_md_path.parent.mkdir(parents=True, exist_ok=True)
    md_content = _generate_markdown_report(report)
    out_md_path.write_text(md_content, encoding="utf-8")

    return report


def main() -> None:
    """CLI for calibration: embed and report commands."""
    if len(sys.argv) < 2 or sys.argv[1] not in {"embed", "report"}:
        print("Usage: python -m src.rag.calibration [embed|report]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    dataset_path = Path("data/eval/retrieval_labeled.jsonl")
    emb_npy = Path("data/eval/retrieval_query_embeddings.npy")
    emb_meta = Path("data/eval/retrieval_query_embeddings.json")
    index_dir = settings.INDEX_DIR
    out_json = Path("reports/retrieval_calibration.json")
    out_md = Path("reports/retrieval_calibration.md")

    if cmd == "embed":
        if not settings.GEMINI_API_KEY:
            print(
                "Error: GEMINI_API_KEY is not configured. Please set the environment variable.",
                file=sys.stderr,
            )
            sys.exit(2)
        records = load_labeled(dataset_path)
        print(f"Embedding {len(records)} queries using model {settings.EMBEDDING_MODEL}...")
        run_embed(dataset_path, emb_npy, emb_meta, sleep_s=0.5)
        print(f"Saved query embeddings to {emb_npy} and {emb_meta}.")

    elif cmd == "report":
        if not emb_npy.exists() or not emb_meta.exists():
            print(
                f"Error: Query embeddings ({emb_npy} / {emb_meta}) not found. Run 'embed' first.",
                file=sys.stderr,
            )
            sys.exit(1)
        rep = run_report(dataset_path, emb_npy, emb_meta, index_dir, out_json, out_md)
        chosen = rep["abstention"]["chosen_threshold"]
        hit3 = rep["retrieval"]["hit@3"]
        print(f"Chosen threshold: {chosen:.2f}, hit@3: {hit3:.3f}")
        print(f"Reports written to {out_json} and {out_md}.")


if __name__ == "__main__":
    main()
