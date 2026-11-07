"""Tests for real RAG wired into Knowledge Agent and search_knowledge_base tool (Phase 3C)."""
from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage

from src.config import settings
from src.core import llm as llm_mod
from src.core.graph import OrchestrationGraph
from src.rag import chunking, index
from src.rag import retriever as rag_retriever
from src.tools.agent_tools import TOOLS_BY_NAME
from tests.fakes import KeywordFakeEmbedder, ScriptedChatModel


def test_search_knowledge_base_success(monkeypatch, tmp_path):
    emb = KeywordFakeEmbedder(["crediário", "pix"])
    chunks = [
        {
            "chunk_id": "chk001",
            "doc_url": "https://site.getnet.com.br/crediario/",
            "title": "Crediário Getnet",
            "market": "BR",
            "fetched_at": "2026-11-06T12:00:00+00:00",
            "doc_sha256": "sha-cred",
            "text": "Crediário Getnet permite parcelamento em até 48 vezes.",
        }
    ]
    index.build_index(chunks, emb, tmp_path, embedding_model="fake-m", dim=3)
    fake_retriever = rag_retriever.Retriever(
        index.VectorIndex.load(tmp_path),
        emb,
        min_score=0.6,
        top_k=2,
    )
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: fake_retriever)

    tool = TOOLS_BY_NAME["search_knowledge_base"]
    raw = tool.invoke({"query": "Dúvida sobre crediário"})
    result = json.loads(raw)

    assert result["status"] == "success"
    assert len(result["documents"]) == 1
    doc = result["documents"][0]
    expected_fields = {"url", "title", "fetched_at", "market", "chunk_id", "score", "text"}
    assert expected_fields <= set(doc.keys())
    assert doc["url"] == "https://site.getnet.com.br/crediario/"
    assert doc["market"] == "BR"
    assert doc["score"] >= 0.6


def test_search_knowledge_base_abstain(monkeypatch, tmp_path):
    emb = KeywordFakeEmbedder(["crediário"])
    chunks = [
        {
            "chunk_id": "chk001",
            "doc_url": "https://site.getnet.com.br/crediario/",
            "title": "Crediário",
            "market": "BR",
            "fetched_at": "2026-11-06T12:00:00+00:00",
            "doc_sha256": "sha-cred",
            "text": "Conteúdo exclusivo sobre crediário.",
        }
    ]
    index.build_index(chunks, emb, tmp_path, embedding_model="fake-m", dim=2)
    fake_retriever = rag_retriever.Retriever(
        index.VectorIndex.load(tmp_path),
        emb,
        min_score=0.6,
        top_k=2,
    )
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: fake_retriever)

    tool = TOOLS_BY_NAME["search_knowledge_base"]
    raw = tool.invoke({"query": "receita de bolo de chocolate"})
    result = json.loads(raw)

    assert result["status"] == "abstain"
    assert result["documents"] == []
    assert result["query"] == "receita de bolo de chocolate"


def test_search_knowledge_base_unavailable_on_retriever_exception(monkeypatch):
    def broken_retriever():
        raise llm_mod.LLMNotConfiguredError("GEMINI_API_KEY is not configured.")

    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", broken_retriever)

    tool = TOOLS_BY_NAME["search_knowledge_base"]
    raw = tool.invoke({"query": "pix"})
    result = json.loads(raw)

    assert result["status"] == "unavailable"
    assert result["documents"] == []
    assert result["error"] == "LLMNotConfiguredError"


def test_supervisor_knowledge_flow_extracts_source_url(monkeypatch, tmp_path):
    emb = KeywordFakeEmbedder(["pix"])
    chunks = [
        {
            "chunk_id": "c_pix",
            "doc_url": "https://site.getnet.com.br/pix/",
            "title": "Pix Getnet",
            "market": "BR",
            "fetched_at": "2026-11-06T12:00:00+00:00",
            "doc_sha256": "sha-pix",
            "text": "Receba pagamentos com Pix na sua maquininha Getnet via QR Code.",
        }
    ]
    index.build_index(chunks, emb, tmp_path, embedding_model="fake-m", dim=2)
    fake_retriever = rag_retriever.Retriever(
        index.VectorIndex.load(tmp_path),
        emb,
        min_score=0.6,
        top_k=2,
    )
    monkeypatch.setattr(rag_retriever, "get_knowledge_retriever", lambda: fake_retriever)

    fake_model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[{"name": "ask_knowledge_agent", "args": {"question": "Como usar o Pix?"}, "id": "call-sup"}],
            ),
            AIMessage(
                content="",
                tool_calls=[{"name": "search_knowledge_base", "args": {"query": "Pix"}, "id": "call-spec"}],
            ),
            AIMessage(content="Você pode receber Pix por QR Code na maquininha."),
            AIMessage(content="O Pix na maquininha funciona via QR Code direto na tela."),
        ]
    )
    graph = OrchestrationGraph(chat_model=fake_model)
    state = graph.run_sync(user_id="cliente1988", message="Como funciona o Pix?", session_id="test-p3c-flow")

    assert state.agent_response == "O Pix na maquininha funciona via QR Code direto na tela."
    assert "https://site.getnet.com.br/pix/" in state.sources
    assert state.agents_used == ["SupervisorAgent", "KnowledgeAgent"]


def test_build_chunks_with_min_chars():
    def make_rec(url: str, text: str) -> dict:
        import hashlib
        return {
            "url": url,
            "title": "Doc",
            "market": "BR",
            "status": "ok",
            "fetched_at": "2026-11-06T00:00:00+00:00",
            "text": text,
            "chars": len(text),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

    short_page = make_rec("https://site.getnet.com.br/curta", "Texto muito curto com poucas palavras.")
    long_page_text = (
        "Linha inicial longa com detalhes e procedimentos operacionais completos sobre a maquininha.\n" * 10
        + "Cauda curta final."
    )
    long_page = make_rec("https://site.getnet.com.br/longa", long_page_text)

    # With min_chars=120: short_page is discarded
    chunks = chunking.build_chunks([short_page, long_page], max_chars=500, min_chars=120)
    assert not any(c["doc_url"] == "https://site.getnet.com.br/curta" for c in chunks)

    # Every chunk has >= 120 chars, and trailing short tail was merged
    long_chunks = [c for c in chunks if c["doc_url"] == "https://site.getnet.com.br/longa"]
    assert len(long_chunks) >= 1
    for c in long_chunks:
        assert len(c["text"]) >= 120
    assert "Cauda curta final." in long_chunks[-1]["text"]


def test_get_knowledge_retriever_without_key_raises_error(monkeypatch):
    monkeypatch.undo()
    rag_retriever.reset_knowledge_retriever()
    old_key = settings.GEMINI_API_KEY
    try:
        settings.GEMINI_API_KEY = ""
        with pytest.raises(llm_mod.LLMNotConfiguredError):
            rag_retriever.get_knowledge_retriever()
    finally:
        settings.GEMINI_API_KEY = old_key
        rag_retriever.reset_knowledge_retriever()


def test_get_knowledge_retriever_loads_committed_index(monkeypatch):
    monkeypatch.undo()
    rag_retriever.reset_knowledge_retriever()
    old_key = settings.GEMINI_API_KEY
    try:
        settings.GEMINI_API_KEY = "test-fake-key-for-loading"
        retriever_inst = rag_retriever.get_knowledge_retriever()
        assert retriever_inst.min_score == settings.RAG_MIN_SCORE
        assert retriever_inst.top_k == settings.RAG_TOP_K
        assert retriever_inst.index is not None
        assert len(retriever_inst.index.chunks) > 0
        assert retriever_inst.embedder.task_type == "RETRIEVAL_QUERY"
        # Singleton cached identity check
        assert rag_retriever.get_knowledge_retriever() is retriever_inst
    finally:
        settings.GEMINI_API_KEY = old_key
        rag_retriever.reset_knowledge_retriever()
