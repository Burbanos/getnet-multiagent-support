"""Offline unit tests for Phase 12B hybrid retrieval (BM25 + embeddings + LLM reranker)."""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from langchain_core.exceptions import ModelAuthenticationError
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage

from src.agents.specialists import SpecialistAgent
from src.config import settings
from src.core import graph as graph_mod
from src.core.llm import LLMConfigurationError
from src.rag import calibration, hybrid_eval
from src.rag import index as rag_index
from src.rag import retriever as rag_retriever
from src.rag.lexical import BM25Index, fold, tokenize
from src.rag.reranker import LLMReranker, format_rerank_input
from src.rag.retriever import Retriever
from tests.fakes import KeywordFakeEmbedder, ScriptedChatModel


class _RaisingModel(BaseChatModel):
    """Test double whose _generate always raises the configured exception."""

    exc: Exception

    def bind_tools(self, tools: Any, **kwargs: Any) -> _RaisingModel:
        return self

    def _generate(self, messages: Any, stop: Any = None, run_manager: Any = None, **kwargs: Any) -> Any:
        raise self.exc

    @property
    def _llm_type(self) -> str:
        return "raising-fake"


def _make_chunks() -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": "c0",
            "doc_url": "https://site.getnet.com.br/pix/",
            "title": "Pix na maquininha",
            "market": "BR",
            "fetched_at": "2026-11-06T12:00:00+00:00",
            "doc_sha256": "sha-0",
            "text": "Receba vendas por Pix diretamente na maquininha Getnet com liquidação imediata.",
        },
        {
            "chunk_id": "c1",
            "doc_url": "https://site.getnet.com.br/crediario/",
            "title": "Crediário Getnet",
            "market": "BR",
            "fetched_at": "2026-11-06T12:00:00+00:00",
            "doc_sha256": "sha-1",
            "text": "Parcele compras no crediário em até 48x sem comprometer o limite do cartão.",
        },
        {
            "chunk_id": "c2",
            "doc_url": "https://site.getnet.com.br/antecipacao/",
            "title": "Antecipação de recebíveis",
            "market": "BR",
            "fetched_at": "2026-11-06T12:00:00+00:00",
            "doc_sha256": "sha-2",
            "text": "Antecipe seus recebíveis de cartão de crédito pelo aplicativo ou portal Getnet.",
        },
        {
            "chunk_id": "c3",
            "doc_url": "https://site.getnet.com.br/taxas/",
            "title": "Taxas e prazos",
            "market": "BR",
            "fetched_at": "2026-11-06T12:00:00+00:00",
            "doc_sha256": "sha-3",
            "text": "Consulte taxas vigentes de débito, crédito à vista e parcelado.",
        },
    ]


class _ListEmbedder:
    def __init__(self, vectors: list[list[float]]) -> None:
        self._vectors = vectors

    def embed_documents(self, _texts: list[str]) -> list[list[float]]:
        return self._vectors

    def embed_query(self, _query: str) -> list[float]:
        return self._vectors[0]


def _make_index(tmp_path: Path, chunks: list[dict[str, Any]], vectors: list[list[float]]) -> rag_index.VectorIndex:
    out_dir = tmp_path / "idx"
    rag_index.build_index(
        chunks,
        _ListEmbedder(vectors),
        out_dir,
        embedding_model=settings.EMBEDDING_MODEL,
        dim=len(vectors[0]),
    )
    return rag_index.VectorIndex.load(out_dir)


class _FixedEmbedder:
    def __init__(self, vec: list[float]) -> None:
        self._vec = vec

    def embed_query(self, _query: str) -> list[float]:
        return self._vec


def test_fold_and_tokenize_accents() -> None:
    assert fold("Cartão Débito — Pré-Autorização 3D²!") == "cartao debito   pre autorizacao 3d2 "
    assert tokenize("Cartão Débito — Pré-Autorização 3D²!") == [
        "cartao",
        "debito",
        "pre",
        "autorizacao",
        "3d2",
    ]
    assert tokenize("a b c") == ["a", "b", "c"]


def test_bm25_hand_computed_three_docs() -> None:
    docs = [
        "pix taxa zero",
        "taxa cartao debito",
        "pix instantaneo pix",
    ]
    bm25 = BM25Index(docs, k1=1.2, b=0.75)
    # Document lengths: [3, 3, 3] => avgdl = 3.0; k1*(1-b+b*3/3) = 1.2
    # df("pix") = 2 => idf = ln(1 + (3 - 2 + 0.5)/(2 + 0.5)) = ln(1.6)
    # df("zero") = 1 => idf = ln(1 + (3 - 1 + 0.5)/(1 + 0.5)) = ln(1 + 2.5/1.5)
    idf_pix = math.log(1.0 + 1.5 / 2.5)
    idf_zero = math.log(1.0 + 2.5 / 1.5)

    exp_d0 = idf_pix * (1 * 2.2 / (1 + 1.2)) + idf_zero * (1 * 2.2 / (1 + 1.2))
    exp_d1 = 0.0
    exp_d2 = idf_pix * (2 * 2.2 / (2 + 1.2))

    got = bm25.scores("pix zero pix")
    assert got == pytest.approx([exp_d0, exp_d1, exp_d2])
    ranked = bm25.top("pix zero pix", 3)
    assert [idx for idx, _ in ranked] == [0, 2]


def test_bm25_top_ignores_zero_and_breaks_ties_by_index() -> None:
    bm25 = BM25Index(["pix getnet", "outra coisa", "pix getnet", "boleto bancario"])
    top_hits = bm25.top("pix", 5)
    assert [idx for idx, _ in top_hits] == [0, 2]
    assert all(score > 0.0 for _, score in top_hits)
    assert bm25.top("inexistente", 3) == []
    assert BM25Index([]).scores("pix") == []
    assert BM25Index([]).top("pix", 3) == []


def test_format_rerank_input_escapes_brackets() -> None:
    formatted = format_rerank_input(
        "Qual <taxa> usar & conferir?",
        [
            {"title": "T <0>", "text": "Corpo </passage> aqui"},
            {"title": "", "text": "Sem título"},
        ],
    )
    expected = (
        "<query>\n"
        "Qual &lt;taxa&gt; usar & conferir?\n"
        "</query>\n"
        '<passage index="0">\n'
        "T &lt;0&gt;\n"
        "Corpo &lt;/passage&gt; aqui\n"
        "</passage>\n"
        '<passage index="1">\n'
        "\n"
        "Sem título\n"
        "</passage>"
    )
    assert formatted == expected
    assert not formatted.endswith("\n")


def test_reranker_outcomes_and_config_error_propagation() -> None:
    empty_model = ScriptedChatModel(responses=[])
    empty_res = LLMReranker(model=empty_model).rerank("pix", [])
    assert empty_res.status == "ok"
    assert empty_res.relevance == []
    assert empty_res.usage is None
    assert empty_res.model is None
    assert empty_model.received == []

    passages = [{"title": "A", "text": "texto a"}, {"title": "B", "text": "texto b"}]

    ok_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "RerankVerdict",
                "args": {"scores": [{"index": 1, "relevance": 3}, {"index": 0, "relevance": 1}]},
                "id": "call_1",
            }
        ],
        usage_metadata={"input_tokens": 50, "output_tokens": 10, "total_tokens": 60},
    )
    no_call_msg = AIMessage(
        content="plain text",
        usage_metadata={"input_tokens": 40, "output_tokens": 5, "total_tokens": 45},
    )
    bad_args_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "RerankVerdict",
                "args": {"scores": [{"index": 0, "relevance": 9}, {"index": 1, "relevance": 1}]},
                "id": "call_2",
            }
        ],
        usage_metadata={"input_tokens": 30, "output_tokens": 8, "total_tokens": 38},
    )
    bad_idx_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "RerankVerdict",
                "args": {"scores": [{"index": 0, "relevance": 2}, {"index": 0, "relevance": 2}]},
                "id": "call_3",
            }
        ],
        usage_metadata={"input_tokens": 25, "output_tokens": 7, "total_tokens": 32},
    )

    model = ScriptedChatModel(responses=[ok_msg, no_call_msg, bad_args_msg, bad_idx_msg])
    reranker = LLMReranker(model=model)

    r_ok = reranker.rerank("q", passages)
    assert r_ok.status == "ok"
    assert r_ok.relevance == [1, 3]
    assert r_ok.error_type is None
    assert r_ok.usage == {"input_tokens": 50, "output_tokens": 10, "total_tokens": 60}
    assert r_ok.model == "scripted-fake"

    r_nocall = reranker.rerank("q", passages)
    assert r_nocall.status == "invalid"
    assert r_nocall.error_type == "no_verdict_call"
    assert r_nocall.relevance is None
    assert r_nocall.usage == {"input_tokens": 40, "output_tokens": 5, "total_tokens": 45}

    r_badargs = reranker.rerank("q", passages)
    assert r_badargs.status == "invalid"
    assert r_badargs.error_type == "invalid_arguments"
    assert r_badargs.usage == {"input_tokens": 30, "output_tokens": 8, "total_tokens": 38}

    r_badidx = reranker.rerank("q", passages)
    assert r_badidx.status == "invalid"
    assert r_badidx.error_type == "bad_indexes"
    assert r_badidx.relevance is None

    r_err = LLMReranker(model=_RaisingModel(exc=RuntimeError("boom"))).rerank("q", passages)
    assert r_err.status == "error"
    assert r_err.error_type == "RuntimeError"
    assert r_err.relevance is None
    assert r_err.usage is None

    with pytest.raises(LLMConfigurationError):
        LLMReranker(model=_RaisingModel(exc=LLMConfigurationError("bad cfg"))).rerank("q", passages)

    with pytest.raises(LLMConfigurationError):
        LLMReranker(model=_RaisingModel(exc=ModelAuthenticationError("bad key"))).rerank("q", passages)


def test_hybrid_gate_does_not_call_reranker(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    chunks = _make_chunks()[:2]
    idx = _make_index(tmp_path, chunks, [[1.0, 0.0], [0.8, 0.2]])
    fake_model = ScriptedChatModel(responses=[])
    retriever = Retriever(
        index=idx,
        embedder=_FixedEmbedder([0.0, 1.0]),
        min_score=0.61,
        top_k=2,
        reranker=LLMReranker(model=fake_model),
    )

    with caplog.at_level(logging.INFO, logger="multiagent.rag.retriever"):
        out = retriever.search("pergunta fora do dominio", include_candidates=True)

    assert out["status"] == "abstain"
    assert out["reason"] == "below_threshold"
    assert out["documents"] == []
    assert out["retrieval"]["candidates"] == 0
    assert out["retrieval"]["rerank"] is None
    assert out["retrieval"]["usage"] is None
    assert out["retrieval"]["candidate_list"] == []
    assert out["retrieval"]["relevance"] is None
    assert fake_model.received == []
    assert not any(rec.message == "rerank finished" for rec in caplog.records)


def test_hybrid_rrf_order_and_min_relevance_filter(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    chunks = _make_chunks()
    # Query vec [1, 0, 0]: dense similarities c0=1.0, c1=0.9, c2=0.7, c3=0.5
    idx = _make_index(
        tmp_path,
        chunks,
        [[1.0, 0.0, 0.0], [0.9, 0.43, 0.0], [0.7, 0.71, 0.0], [0.5, 0.86, 0.0]],
    )
    # Lexical query "recebiveis" matches only c2; dense_candidates=2 gives D=[0, 1], L=[2].
    # With rrf_k=60: c0=1/61, c2=1/61 (tie broken by dense_rank -> c0 before c2), c1=1/62.
    # Fused candidate order passed to reranker: [c0, c2, c1].
    verdict = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "RerankVerdict",
                "args": {
                    "scores": [
                        {"index": 0, "relevance": 1},  # below min_relevance=2 -> filtered
                        {"index": 1, "relevance": 3},  # c2 kept first (rel=3)
                        {"index": 2, "relevance": 2},  # c1 kept second (rel=2)
                    ]
                },
                "id": "c_rrf",
            }
        ],
        usage_metadata={"input_tokens": 80, "output_tokens": 12, "total_tokens": 92},
    )
    retriever = Retriever(
        index=idx,
        embedder=_FixedEmbedder([1.0, 0.0, 0.0]),
        min_score=0.61,
        top_k=2,
        reranker=LLMReranker(model=ScriptedChatModel(responses=[verdict])),
        dense_candidates=2,
        lexical_candidates=2,
        min_relevance=2,
        rrf_k=60,
    )

    with caplog.at_level(logging.INFO, logger="multiagent.rag.retriever"):
        out = retriever.search("recebiveis", include_candidates=True)

    assert out["status"] == "success"
    assert "reason" not in out
    assert [d["chunk_id"] for d in out["documents"]] == ["c2", "c1"]
    assert out["documents"][0]["relevance"] == 3
    assert out["documents"][0]["lexical_rank"] == 1
    assert out["documents"][0]["dense_rank"] == 3
    assert out["documents"][1]["relevance"] == 2
    assert out["documents"][1]["lexical_rank"] is None
    assert [c["chunk_id"] for c in out["retrieval"]["candidate_list"]] == ["c0", "c2", "c1"]
    assert out["retrieval"]["relevance"] == [1, 3, 2]
    assert out["retrieval"]["rerank"]["kept"] == 2
    assert out["retrieval"]["usage"] == {"input_tokens": 80, "output_tokens": 12, "total_tokens": 92}
    assert any(rec.message == "rerank finished" and rec.status == "ok" for rec in caplog.records)


def test_hybrid_no_passage_answers(tmp_path: Path) -> None:
    chunks = _make_chunks()[:2]
    idx = _make_index(tmp_path, chunks, [[1.0, 0.0], [0.8, 0.2]])
    verdict = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "RerankVerdict",
                "args": {"scores": [{"index": 0, "relevance": 1}, {"index": 1, "relevance": 0}]},
                "id": "c_none",
            }
        ],
    )
    retriever = Retriever(
        index=idx,
        embedder=_FixedEmbedder([1.0, 0.0]),
        min_score=0.61,
        top_k=2,
        reranker=LLMReranker(model=ScriptedChatModel(responses=[verdict])),
        dense_candidates=2,
        lexical_candidates=2,
        min_relevance=2,
    )
    out = retriever.search("pix")
    assert out["status"] == "abstain"
    assert out["reason"] == "no_passage_answers"
    assert out["documents"] == []
    assert out["retrieval"]["rerank"]["kept"] == 0


def test_hybrid_fallbacks_to_dense_on_error_and_invalid(tmp_path: Path) -> None:
    chunks = _make_chunks()[:2]
    idx = _make_index(tmp_path, chunks, [[1.0, 0.0], [0.8, 0.6]])

    invalid_msg = AIMessage(content="no tool call here")
    for rerank_model, expected_status in [
        (_RaisingModel(exc=TimeoutError("timeout")), "error"),
        (ScriptedChatModel(responses=[invalid_msg]), "invalid"),
    ]:
        retriever = Retriever(
            index=idx,
            embedder=_FixedEmbedder([1.0, 0.0]),
            min_score=0.61,
            top_k=2,
            reranker=LLMReranker(model=rerank_model),
            dense_candidates=2,
            lexical_candidates=2,
        )
        out = retriever.search("pix", include_candidates=True)
        assert out["status"] == "success"
        assert "reason" not in out
        assert [d["chunk_id"] for d in out["documents"]] == ["c0", "c1"]
        assert all(d["relevance"] is None for d in out["documents"])
        assert out["retrieval"]["rerank"]["status"] == expected_status
        assert out["retrieval"]["rerank"]["kept"] is None
        assert out["retrieval"]["relevance"] is None


def test_retriever_without_reranker_unchanged(tmp_path: Path) -> None:
    chunks = _make_chunks()[:2]
    emb = KeywordFakeEmbedder(["pix", "crediário"])
    rag_index.build_index(chunks, emb, tmp_path, embedding_model="fake", dim=3)
    idx = rag_index.VectorIndex.load(tmp_path)
    retriever = Retriever(index=idx, embedder=emb, min_score=0.5, top_k=2, reranker=None)
    res_plain = retriever.search("pix")
    res_flag = retriever.search("pix", include_candidates=True)
    assert res_plain == res_flag
    assert list(res_plain.keys()) == ["status", "query", "documents", "min_score"]
    assert list(res_plain["documents"][0].keys()) == [
        "url",
        "title",
        "fetched_at",
        "market",
        "chunk_id",
        "score",
        "text",
    ]


def test_knowledge_agent_accumulates_reranker_usage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    chunks = _make_chunks()[:2]
    idx = _make_index(tmp_path, chunks, [[1.0, 0.0], [0.1, 0.9]])
    rerank_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "RerankVerdict",
                "args": {"scores": [{"index": 0, "relevance": 3}]},
                "id": "rk1",
            }
        ],
        usage_metadata={"input_tokens": 110, "output_tokens": 15, "total_tokens": 125},
    )
    fake_retriever = Retriever(
        index=idx,
        embedder=_FixedEmbedder([1.0, 0.0]),
        min_score=0.61,
        top_k=2,
        reranker=LLMReranker(model=ScriptedChatModel(responses=[rerank_msg])),
        dense_candidates=1,
        lexical_candidates=1,
    )
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: fake_retriever)

    specialist_model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "search_knowledge_base", "args": {"query": "pix"}, "id": "t1"}],
                usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
            ),
            AIMessage(
                content="Você pode receber vendas por Pix na maquininha.",
                usage_metadata={"input_tokens": 200, "output_tokens": 30, "total_tokens": 230},
            ),
        ]
    )
    agent = SpecialistAgent(
        name="KnowledgeAgent",
        prompt_file="knowledge_agent.md",
        tools=graph_mod.KNOWLEDGE_TOOLS,
        chat_model=specialist_model,
    )
    res = agent.run("Como funciona Pix na maquininha?", user_id="u1", trace_id="trc-1")
    assert res["status"] == "ok"
    assert res["usage"] == {"input_tokens": 410, "output_tokens": 65, "total_tokens": 475}


def _write_synthetic_dataset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    n_answerable: int = 30,
    n_off: int = 9,
    n_uncovered: int = 9,
) -> tuple[Path, list[dict[str, Any]], np.ndarray]:
    chunks = _make_chunks()
    vecs = [[1.0, 0.0, 0.0], [0.9, 0.4, 0.0], [0.5, 0.8, 0.0], [0.0, 0.0, 1.0]]
    idx = _make_index(tmp_path, chunks, vecs)

    records: list[dict[str, Any]] = []
    qvecs_list: list[list[float]] = []

    for i in range(n_answerable):
        records.append(
            {
                "id": f"q{i+1:02d}",
                "query": f"pergunta segredo {i+1}",
                "category": "answerable",
                "lang": "pt",
                "gold_urls": ["https://site.getnet.com.br/pix/"],
                "gold_snippets": ["Pix diretamente na maquininha"],
            }
        )
        qvecs_list.append([1.0, 0.0, 0.0])

    for i in range(n_off):
        records.append(
            {
                "id": f"q{n_answerable + i + 1:02d}",
                "query": f"receita secreta {i+1}",
                "category": "off_topic",
                "lang": "pt",
                "gold_urls": [],
                "gold_snippets": [],
            }
        )
        qvecs_list.append([0.0, 1.0, 0.0])

    for i in range(n_uncovered):
        records.append(
            {
                "id": f"q{n_answerable + n_off + i + 1:02d}",
                "query": f"assunto desconhecido {i+1}",
                "category": "uncovered",
                "lang": "pt",
                "gold_urls": [],
                "gold_snippets": [],
            }
        )
        qvecs_list.append([0.0, 0.0, 0.0])

    ds_path = tmp_path / "retrieval_labeled.jsonl"
    ds_path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    qvecs = np.asarray(qvecs_list, dtype=np.float32)
    npy_path = tmp_path / "qvecs.npy"
    np.save(npy_path, qvecs)
    meta_path = tmp_path / "qvecs.json"
    meta_path.write_text(
        json.dumps(
            {
                "query_ids": [r["id"] for r in records],
                "dataset_sha256": calibration.dataset_sha256(records),
                "embedding_model": settings.EMBEDDING_MODEL,
                "embedding_dim": 3,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(hybrid_eval, "DATASET", str(ds_path))
    monkeypatch.setattr(hybrid_eval, "EMB_NPY", str(npy_path))
    monkeypatch.setattr(hybrid_eval, "EMB_META", str(meta_path))
    monkeypatch.setattr(settings, "INDEX_DIR", str(tmp_path / "idx"))
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 3)
    assert len(idx.chunks) == 4
    return tmp_path / "runs", records, qvecs


class _ScriptedEvalReranker:
    def __init__(self, statuses: list[str]) -> None:
        self._statuses = list(statuses)
        self.calls = 0

    def rerank(self, _query: str, passages: list[dict[str, Any]]) -> Any:
        from src.rag.reranker import RerankResult

        status = self._statuses[self.calls] if self.calls < len(self._statuses) else "ok"
        self.calls += 1
        if status == "error":
            return RerankResult("error", None, "TimeoutError", 12.0, None, "gemini-3.1-flash-lite")
        if status == "invalid":
            return RerankResult(
                "invalid",
                None,
                "no_verdict_call",
                9.0,
                {"input_tokens": 50, "output_tokens": 5, "total_tokens": 55},
                "gemini-3.1-flash-lite",
            )
        rel = [3 if i == 0 else 1 for i in range(len(passages))]
        return RerankResult(
            "ok",
            rel,
            None,
            10.0,
            {"input_tokens": 60, "output_tokens": 10, "total_tokens": 70},
            "gemini-3.1-flash-lite",
        )


def test_run_hybrid_writes_48_no_text_and_resumes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runs_dir, records, _ = _write_synthetic_dataset(tmp_path, monkeypatch)
    # 30 answerable non-gated + 9 off_topic non-gated (0.8>=0.61) + 9 uncovered gated (0.0<0.61).
    # First attempt: trigger 3 consecutive errors to stop early at q03.
    first_reranker = _ScriptedEvalReranker(["error", "error", "error"])
    s1 = hybrid_eval.run_hybrid("run-1", runs_dir=runs_dir, reranker=first_reranker, max_consecutive_errors=3)
    assert s1["attempted"] == 3
    assert s1["errors"] == 3
    assert s1["stopped_early"] is True

    # Resume with healthy reranker: retries all 3 error rows + runs remaining 45 rows.
    second_reranker = _ScriptedEvalReranker(["ok"] * 50)
    s2 = hybrid_eval.run_hybrid("run-1", runs_dir=runs_dir, reranker=second_reranker)
    assert s2["skipped"] == 0
    assert s2["attempted"] == len(records)
    assert s2["ok"] == 39
    assert s2["gated"] == 9
    assert s2["stopped_early"] is False

    # Re-running complete file skips all 48 lines without calling reranker.
    third_reranker = _ScriptedEvalReranker([])
    s3 = hybrid_eval.run_hybrid("run-1", runs_dir=runs_dir, reranker=third_reranker)
    assert s3["skipped"] == 48
    assert s3["attempted"] == 0
    assert third_reranker.calls == 0

    raw_text = (runs_dir / "run-1.jsonl").read_text(encoding="utf-8")
    assert "pergunta segredo" not in raw_text
    assert "Pix diretamente" not in raw_text


def test_hybrid_report_synthetic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    runs_dir, _, _ = _write_synthetic_dataset(tmp_path, monkeypatch)
    hybrid_eval.run_hybrid("r1", runs_dir=runs_dir, reranker=_ScriptedEvalReranker(["ok"] * 50))
    hybrid_eval.run_hybrid("r2", runs_dir=runs_dir, reranker=_ScriptedEvalReranker(["ok"] * 50))

    out_json = tmp_path / "reports" / "retrieval_hybrid.json"
    out_md = tmp_path / "reports" / "retrieval_hybrid.md"
    rep = hybrid_eval.hybrid_report(["r1", "r2"], runs_dir=runs_dir, out_json=out_json, out_md=out_md)

    assert list(rep.keys()) == [
        "dataset",
        "dataset_sha256",
        "index_chunks",
        "settings",
        "dense",
        "runs",
        "summary",
    ]
    assert rep["runs"]["r1"]["complete"] is True
    assert rep["runs"]["r1"]["counts"] == {"ok": 39, "invalid": 0, "errors": 0, "gated": 9}
    assert rep["runs"]["r1"]["rerank_latency_p50_ms"] == pytest.approx(10.0)
    assert rep["runs"]["r1"]["tokens_mean_per_call"] == {"input_tokens": 60.0, "output_tokens": 10.0}
    assert rep["runs"]["r1"]["cost_usd_per_call"] is not None
    assert out_json.exists()
    md_text = out_md.read_text(encoding="utf-8")
    assert "Denso (regra atual)" in md_text
    assert "r1" in md_text
    assert "Média" in md_text
