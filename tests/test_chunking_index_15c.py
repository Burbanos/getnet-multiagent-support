"""Tests for per-URL chunk IDs, section-aware boilerplate filtering, and index exclusions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import src.core.llm as llm_mod
import src.rag.index as index_mod
from src.config import settings
from src.rag.calibration import load_labeled, normalize_text
from src.rag.chunking import build_chunks

ROOT = Path(__file__).resolve().parent.parent


def _rec(url: str, lines: list[str]) -> dict:
    text = "\n".join(lines)
    return {
        "url": url,
        "status": "ok",
        "title": "Documento",
        "market": "BR",
        "fetched_at": "2026-11-20T00:00:00+00:00",
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text": text,
    }


class _StubEmbedder:
    def __init__(self, dim: int) -> None:
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for txt in texts:
            digest = hashlib.sha256(txt.encode("utf-8")).digest()
            out.append([(digest[i % 32] / 255.0) - 0.5 for i in range(self.dim)])
        return out


def test_chunk_ids_are_unique_per_url_and_deterministic() -> None:
    same_lines = [
        "Conteúdo idêntico publicado em duas páginas distintas da central de ajuda.",
        "Segunda linha do conteúdo compartilhado entre páginas.",
    ]
    rec_a = _rec("https://site.getnet.com.br/get-ajuda-cat/pagina-1/", same_lines)
    rec_b = _rec("https://site.getnet.com.br/get-ajuda-cat/pagina-2/", same_lines)

    run_1 = build_chunks([rec_a, rec_b])
    run_2 = build_chunks([rec_a, rec_b])

    ids_1 = [c["chunk_id"] for c in run_1]
    assert ids_1 == [c["chunk_id"] for c in run_2]
    assert len(set(ids_1)) == 2
    assert ids_1 == [
        f"{hashlib.sha256(rec_a['url'].encode('utf-8')).hexdigest()[:12]}-000",
        f"{hashlib.sha256(rec_b['url'].encode('utf-8')).hexdigest()[:12]}-000",
    ]


def test_section_aware_boilerplate_rule_scope_and_default() -> None:
    shared_steps = [
        "Passo comum A: reinicie o terminal segurando o botão.",
        "Passo comum B: confirme a conexão de rede.",
    ]
    shared_menu = [
        "Menu principal Getnet",
        "Atendimento ao lojista Getnet",
    ]

    same_section = [
        _rec(f"https://site.getnet.com.br/get-ajuda-erros/erro-{i}/", [f"Título erro {i}", *shared_steps])
        for i in range(5)
    ]
    different_sections = [
        _rec(f"https://site.getnet.com.br/get-ajuda-sec-{i}/artigo/", [f"Assunto {i}", *shared_menu])
        for i in range(5)
    ]
    root_pages = [
        _rec(f"https://site.getnet.com.br/pagina-raiz-{i}/", [f"Raiz {i}", *shared_steps])
        for i in range(5)
    ]

    kept_same = " ".join(c["text"] for c in build_chunks(same_section, boilerplate_section_exempt=True))
    dropped_default = " ".join(c["text"] for c in build_chunks(same_section))
    dropped_false = " ".join(c["text"] for c in build_chunks(same_section, boilerplate_section_exempt=False))
    dropped_cross = " ".join(c["text"] for c in build_chunks(different_sections, boilerplate_section_exempt=True))
    dropped_root = " ".join(c["text"] for c in build_chunks(root_pages, boilerplate_section_exempt=True))

    assert "Passo comum A" in kept_same and "Passo comum B" in kept_same
    assert "Passo comum A" not in dropped_default
    assert dropped_default == dropped_false
    assert "Menu principal Getnet" not in dropped_cross
    assert "Passo comum A" not in dropped_root


def test_index_main_excludes_corporate_pdfs_and_persists_meta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tmp_index = tmp_path / "index_out"
    monkeypatch.setattr(settings, "INDEX_DIR", str(tmp_index))
    monkeypatch.setattr(llm_mod, "get_embedder", lambda *a, **kw: _StubEmbedder(int(settings.EMBEDDING_DIM)))

    index_mod.main()

    meta = json.loads((tmp_index / "index_meta.json").read_text(encoding="utf-8"))
    chunks = [json.loads(line) for line in (tmp_index / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    chunk_ids = [c["chunk_id"] for c in chunks]
    indexed_urls = {c["doc_url"] for c in chunks}

    expected_excluded = {
        "https://site.getnet.com.br/wp-content/uploads/2026/10/Codigo_de_Conduta_Getnet_2026.pdf",
        "https://site.getnet.com.br/wp-content/uploads/2026/10/Regulamento-do-Canal-Aberto-2026.pdf",
    }
    assert set(index_mod.INDEX_EXCLUDED_URLS) == expected_excluded
    assert meta["excluded_urls"] == sorted(expected_excluded)
    assert meta["chunking"]["boilerplate_section_exempt"] is True
    assert indexed_urls.isdisjoint(expected_excluded)
    assert len(chunk_ids) == len(set(chunk_ids))

    corpus_pages = [
        json.loads(line)
        for line in (ROOT / "data" / "corpus" / "pages.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len([p for p in corpus_pages if p.get("url") in expected_excluded and p.get("status") == "ok"]) == 2


def test_chunking_on_committed_corpus_covers_both_retrieval_datasets() -> None:
    corpus_pages = [
        json.loads(line)
        for line in (ROOT / "data" / "corpus" / "pages.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    excluded = set(index_mod.INDEX_EXCLUDED_URLS)
    ok_pages = [p for p in corpus_pages if p.get("status") == "ok" and p.get("url") not in excluded]
    chunks = build_chunks(
        ok_pages,
        max_chars=900,
        boilerplate_min_pages=4,
        boilerplate_min_run=2,
        min_chars=settings.RAG_MIN_CHUNK_CHARS,
        boilerplate_section_exempt=True,
    )

    for rel in ("data/eval/retrieval_labeled.jsonl", "data/eval/retrieval_labeled2.jsonl"):
        for query in load_labeled(ROOT / rel):
            if query["category"] != "answerable":
                continue
            gold_urls = set(query["gold_urls"])
            gold_snips = [normalize_text(s) for s in query["gold_snippets"]]
            found = any(
                c["doc_url"] in gold_urls and any(snip in normalize_text(c["text"]) for snip in gold_snips)
                for c in chunks
            )
            assert found, f"Missing gold snippet chunk for query {query['id']} in {rel}"


def test_original_33_pages_match_committed_chunks_as_url_text_pairs() -> None:
    corpus_lines = (ROOT / "data" / "corpus" / "pages.jsonl").read_text(encoding="utf-8").splitlines()
    corpus_pages = [json.loads(line) for line in corpus_lines if line.strip()]
    orig_urls = {p["url"] for p in corpus_pages[:33]}

    excluded = set(index_mod.INDEX_EXCLUDED_URLS)
    ok_pages = [p for p in corpus_pages if p.get("status") == "ok" and p.get("url") not in excluded]
    rebuilt_chunks = build_chunks(
        ok_pages,
        max_chars=900,
        boilerplate_min_pages=4,
        boilerplate_min_run=2,
        min_chars=settings.RAG_MIN_CHUNK_CHARS,
        boilerplate_section_exempt=True,
    )
    rebuilt_pairs = {(c["doc_url"], c["text"]) for c in rebuilt_chunks if c["doc_url"] in orig_urls}

    committed_chunks = [
        json.loads(line)
        for line in (ROOT / "data" / "index" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    committed_pairs = {(c["doc_url"], c["text"]) for c in committed_chunks if c["doc_url"] in orig_urls}

    assert len(committed_pairs) == 103
    assert rebuilt_pairs == committed_pairs


def test_build_index_records_excluded_urls_only_when_provided(tmp_path: Path) -> None:
    chunks = [
        {
            "chunk_id": "0123456789ab-000",
            "doc_url": "https://site.getnet.com.br/get-ajuda-x/p/",
            "title": "T",
            "market": "BR",
            "fetched_at": "2026-11-20T00:00:00+00:00",
            "doc_sha256": "f" * 64,
            "text": "Texto de teste para indexação.",
        }
    ]
    embedder = _StubEmbedder(4)

    meta_without = index_mod.build_index(chunks, embedder, tmp_path / "m1", "fake-emb", 4)
    assert "excluded_urls" not in meta_without

    meta_with = index_mod.build_index(
        chunks,
        embedder,
        tmp_path / "m2",
        "fake-emb",
        4,
        excluded_urls=["https://b.example/z.pdf", "https://a.example/a.pdf"],
    )
    assert meta_with["excluded_urls"] == ["https://a.example/a.pdf", "https://b.example/z.pdf"]
