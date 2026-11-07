"""Retriever module performing vector search with threshold filtering and explicit abstention."""
from __future__ import annotations

from typing import Any


class Retriever:
    """Cosine similarity retriever over VectorIndex with strict score threshold."""

    def __init__(
        self,
        index: Any,
        embedder: Any,
        min_score: float,
        top_k: int,
    ) -> None:
        self.index = index
        self.embedder = embedder
        self.min_score = min_score
        self.top_k = top_k

    def search(self, query: str) -> dict[str, Any]:
        """
        Embed query, perform top-k vector search, filter by min_score, and return formatted response.
        If no results or best score < min_score, returns status 'abstain'.
        """
        query_vec = self.embedder.embed_query(query)
        hits = self.index.search(query_vec, k=self.top_k)

        if not hits or hits[0][1] < self.min_score:
            return {
                "status": "abstain",
                "query": query,
                "documents": [],
                "min_score": self.min_score,
            }

        documents: list[dict[str, Any]] = []
        for chunk, score in hits:
            if score >= self.min_score:
                documents.append(
                    {
                        "url": chunk.get("doc_url", ""),
                        "title": chunk.get("title", ""),
                        "fetched_at": chunk.get("fetched_at", ""),
                        "chunk_id": chunk.get("chunk_id", ""),
                        "score": float(score),
                        "text": chunk.get("text", ""),
                    }
                )

        if not documents:
            return {
                "status": "abstain",
                "query": query,
                "documents": [],
                "min_score": self.min_score,
            }

        return {
            "status": "success",
            "query": query,
            "documents": documents,
            "min_score": self.min_score,
        }
