"""Embedding index creation, persistence, and cosine vector search."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("multiagent.rag.index")


def build_index(
    chunks: list[dict[str, Any]],
    embedder: Any,
    out_dir: str | Path,
    embedding_model: str,
    dim: int,
    corpus_sha256: str | None = None,
) -> dict[str, Any]:
    """
    Generate embeddings for chunks, L2-normalize them, and persist the index artifacts.

    Persists:
    - out_dir/embeddings.npy: Float32 array of shape (n_chunks, dim) with unit L2 norm.
    - out_dir/chunks.jsonl: One chunk JSON record per line (UTF-8, ensure_ascii=False).
    - out_dir/index_meta.json: Metadata containing model, dimension, count, and corpus sha256.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if chunks:
        texts = [c["text"] for c in chunks]
        raw_embs = embedder.embed_documents(texts)
        arr = np.array(raw_embs, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        normed_arr = (arr / norms).astype(np.float32)
    else:
        normed_arr = np.empty((0, dim), dtype=np.float32)

    np.save(out_path / "embeddings.npy", normed_arr)

    chunks_lines = [json.dumps(c, ensure_ascii=False) for c in chunks]
    (out_path / "chunks.jsonl").write_text(
        "\n".join(chunks_lines) + ("\n" if chunks_lines else ""),
        encoding="utf-8",
    )

    meta: dict[str, Any] = {
        "embedding_model": embedding_model,
        "dim": dim,
        "n_chunks": len(chunks),
        "corpus_sha256": corpus_sha256,
        "created_at": datetime.now(UTC).isoformat(),
    }
    (out_path / "index_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return meta


class VectorIndex:
    """In-memory cosine vector index backed by persisted NumPy embeddings and chunks."""

    def __init__(
        self,
        chunks: list[dict[str, Any]],
        embeddings: np.ndarray,
        meta: dict[str, Any],
    ) -> None:
        self.chunks = chunks
        self.embeddings = embeddings
        self.meta = meta

    @classmethod
    def load(
        cls,
        index_dir: str | Path,
        expected_model: str | None = None,
        expected_dim: int | None = None,
    ) -> VectorIndex:
        """
        Load index artifacts from directory and validate model/dimension parameters.
        Raises ValueError if metadata does not match expectations.
        """
        p = Path(index_dir)
        meta_file = p / "index_meta.json"
        chunks_file = p / "chunks.jsonl"
        emb_file = p / "embeddings.npy"

        if not (meta_file.exists() and chunks_file.exists() and emb_file.exists()):
            raise FileNotFoundError(f"Missing index files in {index_dir}")

        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        if expected_model is not None and meta.get("embedding_model") != expected_model:
            raise ValueError(
                f"Embedding model mismatch: expected {expected_model!r}, got {meta.get('embedding_model')!r}"
            )
        if expected_dim is not None and meta.get("dim") != expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {expected_dim!r}, got {meta.get('dim')!r}"
            )

        chunks_raw = chunks_file.read_text(encoding="utf-8").splitlines()
        chunks = [json.loads(ln) for ln in chunks_raw if ln.strip()]
        embeddings = np.load(emb_file)

        return cls(chunks=chunks, embeddings=embeddings, meta=meta)

    def search(self, vector: list[float] | np.ndarray, k: int) -> list[tuple[dict[str, Any], float]]:
        """
        Query index with a vector and return top-k (chunk, cosine_similarity) in descending order.
        """
        if not self.chunks or self.embeddings.shape[0] == 0 or k <= 0:
            return []

        q = np.array(vector, dtype=np.float32).flatten()
        norm = np.linalg.norm(q)
        if norm > 0.0:
            q = q / norm

        scores = self.embeddings @ q
        limit = min(k, len(self.chunks))
        top_indices = np.argsort(-scores)[:limit]

        return [(self.chunks[i], float(scores[i])) for i in top_indices]


def main() -> None:
    """CLI to build embedding index from data/corpus/pages.jsonl."""
    from src.config import settings
    from src.core.llm import get_embedder
    from src.rag.chunking import build_chunks

    corpus_file = Path("data/corpus/pages.jsonl")
    if not corpus_file.exists():
        print(f"Error: {corpus_file} not found.")
        return

    pages = [json.loads(line) for line in corpus_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    ok_pages = [p for p in pages if p.get("status") == "ok"]

    corpus_sha = hashlib.sha256("".join(p["sha256"] for p in ok_pages).encode("utf-8")).hexdigest()
    chunks = build_chunks(ok_pages, max_chars=900, boilerplate_min_pages=4)

    embedder = get_embedder("RETRIEVAL_DOCUMENT")
    meta = build_index(
        chunks=chunks,
        embedder=embedder,
        out_dir=settings.INDEX_DIR,
        embedding_model=settings.EMBEDDING_MODEL,
        dim=settings.EMBEDDING_DIM,
        corpus_sha256=corpus_sha,
    )

    print(f"Built index with {meta['n_chunks']} chunks from {len(ok_pages)} ok pages (dim={meta['dim']}).")


if __name__ == "__main__":
    main()
