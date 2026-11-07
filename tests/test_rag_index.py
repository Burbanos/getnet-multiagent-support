"""Tests for chunking, embedding index, and retriever (Phase 3B)."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import numpy as np
import pytest

from src.config import settings
from src.core import llm as llm_mod
from src.rag import chunking, index, retriever


class FakeKeywordEmbedder:
    """Deterministic offline embedder for tests: counts keywords + constant bias."""

    def __init__(self, keywords: list[str]) -> None:
        self.keywords = keywords

    def _vec(self, text: str) -> list[float]:
        t = text.lower()
        return [float(t.count(k)) for k in self.keywords] + [0.01]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vec(text)


def _make_page(i: int, body: list[str], status: str = "ok", footer: list[str] | None = None) -> dict:
    foot = footer or []
    text = "\n".join(body + foot)
    return {
        "url": f"https://site.getnet.com.br/pagina-{i}",
        "title": f"Página {i}",
        "market": "BR",
        "status": status,
        "fetched_at": "2026-11-06T12:00:00+00:00",
        "text": text,
        "chars": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def test_boilerplate_removal_and_dash_lines():
    common_footer = ["Getnet Brasil 2026", "Central de Atendimento 4002-4000", "Fale com o suporte"]
    records = [
        _make_page(0, ["Conteúdo da página zero sobre taxas"], footer=common_footer),
        _make_page(1, ["Conteúdo da página um sobre maquininhas", "—", "- - -", "Parágrafo dois"], footer=common_footer),
        _make_page(2, ["Conteúdo da página dois sobre Pix"], footer=common_footer),
        _make_page(3, ["Conteúdo da página três sobre antecipação"], footer=common_footer),
    ]

    chunks = chunking.build_chunks(records, max_chars=900, boilerplate_min_pages=4)
    all_chunk_text = "\n".join(c["text"] for c in chunks)

    # Boilerplate appearing in all 4 pages must be omitted
    for foot in common_footer:
        assert foot not in all_chunk_text

    # Lines without alphanumeric characters must be dropped
    assert "—" not in all_chunk_text
    assert "- - -" not in all_chunk_text


def test_non_ok_records_ignored():
    records = [
        _make_page(0, ["Página válida"]),
        _make_page(1, ["Página com erro HTTP"], status="http_error"),
        _make_page(2, ["Página bloqueada por robots"], status="robots_disallowed"),
        _make_page(3, ["Página curta sem conteúdo"], status="no_content"),
    ]

    chunks = chunking.build_chunks(records)
    urls = {c["doc_url"] for c in chunks}
    assert "https://site.getnet.com.br/pagina-0" in urls
    assert "https://site.getnet.com.br/pagina-1" not in urls
    assert "https://site.getnet.com.br/pagina-2" not in urls
    assert "https://site.getnet.com.br/pagina-3" not in urls


def test_chunk_size_capped_at_max_chars():
    long_body = [f"Linha de detalhe de transação número {i} com informações completas e seguras." for i in range(40)]
    records = [_make_page(0, long_body)]

    chunks = chunking.build_chunks(records, max_chars=600)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c["text"]) <= 600
        assert len(c["text"].strip()) > 0


def test_chunk_lines_are_verbatim():
    records = [
        _make_page(0, ["Primeira linha de texto", "Segunda linha com pontuação!", "Terceira linha final."]),
    ]
    chunks = chunking.build_chunks(records, max_chars=900)
    source_lines = set(records[0]["text"].split("\n"))

    for c in chunks:
        for chunk_line in c["text"].split("\n"):
            assert chunk_line in source_lines


def test_chunk_id_deterministic_and_unique():
    records = [
        _make_page(0, [f"Linha {i} do documento para teste de consistência determinística." for i in range(25)]),
        _make_page(1, ["Outro documento com informações sobre antecipação de recebíveis."]),
    ]

    chunks_run_1 = chunking.build_chunks(records, max_chars=500)
    chunks_run_2 = chunking.build_chunks(records, max_chars=500)

    ids_1 = [c["chunk_id"] for c in chunks_run_1]
    ids_2 = [c["chunk_id"] for c in chunks_run_2]

    assert ids_1 == ids_2
    assert len(set(ids_1)) == len(ids_1)
    for cid in ids_1:
        assert len(cid.split("-")) == 2
        prefix, seq = cid.split("-")
        assert len(prefix) == 12
        assert len(seq) == 3


def test_chunk_fields_completeness():
    records = [_make_page(0, ["Texto explicativo"])]
    chunks = chunking.build_chunks(records)
    assert len(chunks) == 1
    c = chunks[0]
    expected_fields = {"chunk_id", "doc_url", "title", "market", "fetched_at", "doc_sha256", "text"}
    assert expected_fields <= set(c.keys())
    assert c["doc_sha256"] == records[0]["sha256"]
    assert c["doc_url"] == records[0]["url"]
    assert c["title"] == records[0]["title"]
    assert c["market"] == records[0]["market"]


def test_build_index_artifacts_and_normalization():
    records = [
        _make_page(0, ["Maquininha Getnet aceita Pix e cartões."]),
        _make_page(1, ["Configuração de Wi-Fi e conexão 3G/4G."]),
    ]
    chunks = chunking.build_chunks(records)
    embedder = FakeKeywordEmbedder(["pix", "wi-fi", "cartões"])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        meta = index.build_index(
            chunks=chunks,
            embedder=embedder,
            out_dir=tmp_path,
            embedding_model="fake-model",
            dim=4,
            corpus_sha256="test-sha",
        )

        assert meta["embedding_model"] == "fake-model"
        assert meta["dim"] == 4
        assert meta["n_chunks"] == len(chunks)
        assert meta["corpus_sha256"] == "test-sha"

        # Check persisted files
        assert (tmp_path / "index_meta.json").exists()
        assert (tmp_path / "chunks.jsonl").exists()
        assert (tmp_path / "embeddings.npy").exists()

        loaded_embs = np.load(tmp_path / "embeddings.npy")
        assert loaded_embs.shape == (len(chunks), 4)
        assert loaded_embs.dtype == np.float32

        # Verify unit norm
        norms = np.linalg.norm(loaded_embs, axis=1)
        assert np.all(np.abs(norms - 1.0) < 1e-4)


def test_vector_index_load_valid_and_mismatches():
    records = [_make_page(0, ["Texto básico para teste de carregamento do índice."])]
    chunks = chunking.build_chunks(records)
    embedder = FakeKeywordEmbedder(["básico"])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        index.build_index(
            chunks=chunks,
            embedder=embedder,
            out_dir=tmp_path,
            embedding_model="model-v1",
            dim=2,
        )

        # Successful load
        vi = index.VectorIndex.load(tmp_path, expected_model="model-v1", expected_dim=2)
        assert len(vi.chunks) == 1

        # Mismatched model
        with pytest.raises(ValueError, match="Embedding model mismatch"):
            index.VectorIndex.load(tmp_path, expected_model="other-model", expected_dim=2)

        # Mismatched dim
        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            index.VectorIndex.load(tmp_path, expected_model="model-v1", expected_dim=512)


def test_vector_index_search_cosine_ordering():
    records = [
        _make_page(0, ["Solução de crediário em até 36 vezes no cartão de crédito."]),
        _make_page(1, ["Configuração avançada de rede Wi-Fi na maquininha."]),
    ]
    chunks = chunking.build_chunks(records)
    embedder = FakeKeywordEmbedder(["crediário", "wi-fi"])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        index.build_index(
            chunks=chunks,
            embedder=embedder,
            out_dir=tmp_path,
            embedding_model="fake-kw",
            dim=3,
        )
        vi = index.VectorIndex.load(tmp_path)

        query_vec = embedder.embed_query("Quero saber sobre crediário parcelado")
        hits = vi.search(query_vec, k=2)

        assert len(hits) == 2
        assert hits[0][0]["doc_url"].endswith("/pagina-0")
        assert hits[0][1] >= hits[1][1]

        # Edge cases
        assert vi.search(query_vec, k=0) == []


def test_retriever_success_abstain_and_top_k():
    records = [
        _make_page(0, ["Como configurar a conexão Wi-Fi na maquininha Getnet."]),
        _make_page(1, ["Taxas e prazos de antecipação de recebíveis."]),
    ]
    chunks = chunking.build_chunks(records)
    embedder = FakeKeywordEmbedder(["wi-fi", "antecipação", "taxas"])

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        index.build_index(
            chunks=chunks,
            embedder=embedder,
            out_dir=tmp_path,
            embedding_model="fake-kw",
            dim=4,
        )
        vi = index.VectorIndex.load(tmp_path)

        # Success case
        ret = retriever.Retriever(vi, embedder, min_score=0.5, top_k=2)
        res_ok = ret.search("Configuração de Wi-Fi")
        assert res_ok["status"] == "success"
        assert len(res_ok["documents"]) >= 1
        top_doc = res_ok["documents"][0]
        assert top_doc["url"].endswith("/pagina-0")
        assert top_doc["score"] >= 0.5
        assert set(top_doc.keys()) >= {"url", "title", "fetched_at", "chunk_id", "score", "text"}

        # Abstain case
        res_abs = ret.search("Receita culinária de sobremesa de morango")
        assert res_abs["status"] == "abstain"
        assert res_abs["documents"] == []

        # Top k limit
        ret_top1 = retriever.Retriever(vi, embedder, min_score=0.0, top_k=1)
        res_top1 = ret_top1.search("taxas e antecipação")
        assert len(res_top1["documents"]) == 1


def test_get_embedder_configuration():
    old_key = settings.GEMINI_API_KEY
    try:
        # Missing key raises LLMNotConfiguredError
        settings.GEMINI_API_KEY = ""
        with pytest.raises(llm_mod.LLMNotConfiguredError):
            llm_mod.get_embedder("RETRIEVAL_DOCUMENT")

        # Configured key builds embedder with correct properties
        settings.GEMINI_API_KEY = "test-fake-key"
        emb = llm_mod.get_embedder("RETRIEVAL_QUERY")
        assert emb.task_type == "RETRIEVAL_QUERY"
        assert emb.model == settings.EMBEDDING_MODEL
        assert emb.output_dimensionality == settings.EMBEDDING_DIM
    finally:
        settings.GEMINI_API_KEY = old_key
