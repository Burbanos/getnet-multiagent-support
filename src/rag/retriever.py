"""Retriever module performing vector or hybrid search with threshold filtering and explicit abstention."""
from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from src.rag.lexical import BM25Index

logger = logging.getLogger("multiagent.rag.retriever")


def _legacy_doc(chunk: dict[str, Any], score: float) -> dict[str, Any]:
    return {
        "url": chunk.get("doc_url", ""),
        "title": chunk.get("title", ""),
        "fetched_at": chunk.get("fetched_at", ""),
        "market": chunk.get("market", ""),
        "chunk_id": chunk.get("chunk_id", ""),
        "score": float(score),
        "text": chunk.get("text", ""),
    }


def _hybrid_doc(
    chunk: dict[str, Any],
    score: float,
    dense_rank: int,
    lexical_rank: int | None,
    relevance: int | None,
) -> dict[str, Any]:
    doc = _legacy_doc(chunk, score)
    doc["dense_rank"] = dense_rank
    doc["lexical_rank"] = lexical_rank
    doc["relevance"] = relevance
    return doc


def _build_corpus_texts(chunks: list[dict[str, Any]]) -> list[str]:
    return [f"{c.get('title', '')}\n{c.get('text', '')}" for c in chunks]


class Retriever:
    """Vector or hybrid (dense + BM25 + LLM reranker) retriever over VectorIndex."""

    def __init__(
        self,
        index: Any,
        embedder: Any,
        min_score: float,
        top_k: int,
        lexical: Any | None = None,
        reranker: Any | None = None,
        dense_candidates: int = 6,
        lexical_candidates: int = 6,
        min_relevance: int = 2,
        rrf_k: int = 60,
    ) -> None:
        self.index = index
        self.embedder = embedder
        self.min_score = min_score
        self.top_k = top_k
        self.lexical = lexical
        self.reranker = reranker
        self.dense_candidates = dense_candidates
        self.lexical_candidates = lexical_candidates
        self.min_relevance = min_relevance
        self.rrf_k = rrf_k

    def _search_dense_only(self, query: str) -> dict[str, Any]:
        query_vec = self.embedder.embed_query(query)
        hits = self.index.search(query_vec, k=self.top_k)

        if not hits or hits[0][1] < self.min_score:
            return {
                "status": "abstain",
                "query": query,
                "documents": [],
                "min_score": self.min_score,
            }

        documents = [
            _legacy_doc(chunk, score)
            for chunk, score in hits
            if score >= self.min_score
        ]

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

    def search(self, query: str, include_candidates: bool = False) -> dict[str, Any]:
        """
        Perform retrieval for a query.
        When reranker is None, executes the legacy dense-only rule and ignores include_candidates.
        When reranker is set, applies semantic threshold gate, dense + BM25 RRF fusion, and LLM reranking.
        """
        if self.reranker is None:
            return self._search_dense_only(query)

        query_vec = self.embedder.embed_query(query)
        dense_scores = self.index.scores(query_vec)
        if len(dense_scores) == 0:
            dense_order: list[int] = []
        else:
            dense_order = [int(i) for i in np.argsort(-dense_scores, kind="stable")]

        if not dense_order or float(dense_scores[dense_order[0]]) < self.min_score:
            retrieval_meta: dict[str, Any] = {
                "mode": "hybrid",
                "candidates": 0,
                "rerank": None,
                "usage": None,
            }
            if include_candidates:
                retrieval_meta["candidate_list"] = []
                retrieval_meta["relevance"] = None
            return {
                "status": "abstain",
                "query": query,
                "documents": [],
                "min_score": self.min_score,
                "reason": "below_threshold",
                "retrieval": retrieval_meta,
            }

        dense_rank = {idx: rank for rank, idx in enumerate(dense_order, 1)}
        top_dense = dense_order[: self.dense_candidates]
        dense_pos = {idx: rank for rank, idx in enumerate(top_dense, 1)}

        if self.lexical is None:
            self.lexical = BM25Index(_build_corpus_texts(self.index.chunks))

        top_lexical = [idx for idx, _ in self.lexical.top(query, self.lexical_candidates)]
        lex_rank = {idx: rank for rank, idx in enumerate(top_lexical, 1)}

        unique_cands = list(dict.fromkeys(top_dense + top_lexical))
        fused_scores: dict[int, float] = {}
        for idx in unique_cands:
            terms: list[float] = []
            if idx in dense_pos:
                terms.append(1.0 / (self.rrf_k + dense_pos[idx]))
            if idx in lex_rank:
                terms.append(1.0 / (self.rrf_k + lex_rank[idx]))
            fused_scores[idx] = math.fsum(terms)

        cands = sorted(unique_cands, key=lambda idx: (-fused_scores[idx], dense_rank[idx], idx))
        passages = [
            {
                "title": self.index.chunks[idx].get("title", ""),
                "text": self.index.chunks[idx].get("text", ""),
            }
            for idx in cands
        ]

        res = self.reranker.rerank(query, passages)
        logger.info(
            "rerank finished",
            extra={"status": res.status, "latency_ms": res.latency_ms},
        )

        candidate_list = (
            [
                {
                    "chunk_id": self.index.chunks[idx].get("chunk_id", ""),
                    "dense_score": float(dense_scores[idx]),
                    "dense_rank": dense_rank[idx],
                    "lexical_rank": lex_rank.get(idx),
                }
                for idx in cands
            ]
            if include_candidates
            else None
        )

        if res.status == "ok":
            rel_scores = res.relevance or []
            kept_pos = [
                pos for pos in range(len(cands)) if rel_scores[pos] >= self.min_relevance
            ]
            kept_pos.sort(key=lambda pos: (-rel_scores[pos], pos))
            kept_pos = kept_pos[: self.top_k]

            documents = [
                _hybrid_doc(
                    self.index.chunks[cands[pos]],
                    float(dense_scores[cands[pos]]),
                    dense_rank[cands[pos]],
                    lex_rank.get(cands[pos]),
                    int(rel_scores[pos]),
                )
                for pos in kept_pos
            ]
            retrieval_meta = {
                "mode": "hybrid",
                "candidates": len(cands),
                "rerank": {**res.as_metadata(), "kept": len(documents)},
                "usage": res.usage,
            }
            if include_candidates:
                retrieval_meta["candidate_list"] = candidate_list
                retrieval_meta["relevance"] = list(rel_scores)

            if not documents:
                return {
                    "status": "abstain",
                    "query": query,
                    "documents": [],
                    "min_score": self.min_score,
                    "reason": "no_passage_answers",
                    "retrieval": retrieval_meta,
                }

            return {
                "status": "success",
                "query": query,
                "documents": documents,
                "min_score": self.min_score,
                "retrieval": retrieval_meta,
            }

        fallback_indices = [
            idx for idx in dense_order[: self.top_k] if float(dense_scores[idx]) >= self.min_score
        ]
        documents = [
            _hybrid_doc(
                self.index.chunks[idx],
                float(dense_scores[idx]),
                dense_rank[idx],
                lex_rank.get(idx),
                None,
            )
            for idx in fallback_indices
        ]
        retrieval_meta = {
            "mode": "hybrid",
            "candidates": len(cands),
            "rerank": {**res.as_metadata(), "kept": None},
            "usage": res.usage,
        }
        if include_candidates:
            retrieval_meta["candidate_list"] = candidate_list
            retrieval_meta["relevance"] = None

        return {
            "status": "success",
            "query": query,
            "documents": documents,
            "min_score": self.min_score,
            "retrieval": retrieval_meta,
        }


_cached_retriever: Retriever | None = None


def get_knowledge_retriever() -> Retriever:
    """Return cached singleton Retriever instance, initialized lazily."""
    global _cached_retriever
    if _cached_retriever is None:
        from src.config import settings
        from src.core.llm import get_embedder
        from src.rag.index import VectorIndex

        embedder = get_embedder("RETRIEVAL_QUERY")
        index = VectorIndex.load(
            settings.INDEX_DIR,
            expected_model=settings.EMBEDDING_MODEL,
            expected_dim=settings.EMBEDDING_DIM,
        )
        if settings.RAG_RERANK_ENABLED:
            from src.rag.reranker import LLMReranker

            _cached_retriever = Retriever(
                index=index,
                embedder=embedder,
                min_score=settings.RAG_MIN_SCORE,
                top_k=settings.RAG_TOP_K,
                lexical=BM25Index(_build_corpus_texts(index.chunks)),
                reranker=LLMReranker(),
                dense_candidates=settings.RAG_DENSE_CANDIDATES,
                lexical_candidates=settings.RAG_LEXICAL_CANDIDATES,
                min_relevance=settings.RAG_RERANK_MIN_RELEVANCE,
                rrf_k=settings.RAG_RRF_K,
            )
        else:
            _cached_retriever = Retriever(
                index=index,
                embedder=embedder,
                min_score=settings.RAG_MIN_SCORE,
                top_k=settings.RAG_TOP_K,
            )
    return _cached_retriever


def reset_knowledge_retriever() -> None:
    """Reset the cached singleton Retriever instance (primarily for tests)."""
    global _cached_retriever
    _cached_retriever = None
