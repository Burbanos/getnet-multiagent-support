"""Pytest fixtures and configuration."""
import os
import sys
import tempfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure test environment variables are set before importing app
_test_tmp_dir = tempfile.mkdtemp(prefix="getnet_test_tickets_")
os.environ["TICKETS_DB_PATH"] = str(Path(_test_tmp_dir) / "tickets.db")
os.environ["GEMINI_API_KEY"] = ""
os.environ["APP_ENV"] = "testing"
os.environ["ENABLE_GUARDRAILS"] = "true"

from src.core.graph import get_orchestrator
from src.core.mock_db import get_mock_db
from src.main import app

_SAMPLE_CHUNKS = [
    {
        "chunk_id": "c001",
        "doc_url": "https://site.getnet.com.br/crediario/",
        "title": "Crediário Getnet",
        "market": "BR",
        "fetched_at": "2026-11-06T12:00:00+00:00",
        "doc_sha256": "sha-crediario",
        "text": "O crediário Getnet permite parcelamento e crediario em até 48x com recebimento rápido das vendas.",
    },
    {
        "chunk_id": "c002",
        "doc_url": "https://site.getnet.com.br/pix/",
        "title": "Pix na Maquininha",
        "market": "BR",
        "fetched_at": "2026-11-06T12:00:00+00:00",
        "doc_sha256": "sha-pix",
        "text": "Venda com Pix diretamente na maquininha Getnet via QR Code dinâmico sem necessidade de conta bancária exclusiva.",
    },
    {
        "chunk_id": "c003",
        "doc_url": "https://site.getnet.com.br/todas-as-maquininhas/",
        "title": "Maquininhas Getnet",
        "market": "BR",
        "fetched_at": "2026-11-06T12:00:00+00:00",
        "doc_sha256": "sha-maquininhas",
        "text": "Conheça os modelos Get Clássica (Get Classica) e Get Smart, com tela touch e tecnologia moderna.",
    },
    {
        "chunk_id": "c004",
        "doc_url": "https://site.getnet.com.br/get-ajuda-antecipacao-de-venda/",
        "title": "Antecipação de Vendas",
        "market": "BR",
        "fetched_at": "2026-11-06T12:00:00+00:00",
        "doc_sha256": "sha-antecipacao",
        "text": "Antecipação de recebíveis e vendas automática ou avulsa pelo aplicativo Getnet Brasil.",
    },
    {
        "chunk_id": "c005",
        "doc_url": "https://site.getnet.com.br/link-de-pagamento/",
        "title": "Link de Pagamento",
        "market": "BR",
        "fetched_at": "2026-11-06T12:00:00+00:00",
        "doc_sha256": "sha-link",
        "text": "Venda online com Link de Pagamento pelo WhatsApp e redes sociais com segurança.",
    },
    {
        "chunk_id": "c006",
        "doc_url": "https://site.getnet.com.br/get-ajuda-configuracoes/como-configurar-o-wi-fi-na-sua-maquininha-getnet/",
        "title": "Configuração Wi-Fi",
        "market": "BR",
        "fetched_at": "2026-11-06T12:00:00+00:00",
        "doc_sha256": "sha-wifi",
        "text": "Para configurar a rede Wi-Fi na maquininha Getnet acesse o menu de configurações e selecione a rede sem fio Wi-Fi.",
    },
]


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient session fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def orchestrator():
    """Singleton multi-agent orchestrator fixture."""
    return get_orchestrator()


@pytest.fixture(scope="session")
def mock_db():
    """Database fixture."""
    return get_mock_db()


@pytest.fixture(autouse=True)
def mock_knowledge_retriever(monkeypatch, tmp_path_factory):
    """Autouse fixture mounting a lightweight sample RAG index for tests."""
    from src.rag.index import VectorIndex, build_index
    from src.rag.retriever import Retriever
    from tests.fakes import KeywordFakeEmbedder

    idx_dir = tmp_path_factory.mktemp("test_knowledge_index")
    keywords = [
        "crediário", "crediario", "pix", "wi-fi", "wifi",
        "antecipação", "antecipacao", "smart", "clássica", "classica", "link", "whatsapp",
    ]
    embedder = KeywordFakeEmbedder(keywords)
    build_index(
        chunks=_SAMPLE_CHUNKS,
        embedder=embedder,
        out_dir=idx_dir,
        embedding_model="fake-kw",
        dim=len(keywords) + 1,
        corpus_sha256="sample-sha",
    )
    vindex = VectorIndex.load(idx_dir, expected_model="fake-kw", expected_dim=len(keywords) + 1)
    test_retriever = Retriever(index=vindex, embedder=embedder, min_score=0.6, top_k=2)

    monkeypatch.setattr("src.rag.retriever.get_knowledge_retriever", lambda: test_retriever)
    return test_retriever


@pytest.fixture(autouse=True)
def mock_web_search(monkeypatch):
    """Mock web search tool across all tests so no tests perform network I/O."""
    from src.tools import agent_tools, web_search

    def fake_web_search(query: str, max_results: int = 3):
        lower = query.lower()
        if "porto alegre" in lower:
            results = [{
                "title": "Previsão do Tempo em Porto Alegre",
                "snippet": "A previsão do tempo em Porto Alegre para amanhã indica sol com algumas nuvens e máxima de 28°C.",
                "url": "https://weather.example.com/porto-alegre"
            }]
        elif "euro" in lower:
            results = [{
                "title": "Cotação do Euro Hoje",
                "snippet": "O Euro comercial está cotado a R$ 6,10 para compra e R$ 6,12 para venda.",
                "url": "https://finance.example.com/euro"
            }]
        else:
            results = [{
                "title": f"Resultado de busca: {query}",
                "snippet": f"Informações atualizadas sobre {query}.",
                "url": "https://search.example.com"
            }]
        return {
            "status": "success",
            "query": query,
            "count": len(results),
            "results": results
        }

    monkeypatch.setattr(web_search, "web_search_tool", fake_web_search)
    monkeypatch.setattr(agent_tools, "web_search_tool", fake_web_search)
