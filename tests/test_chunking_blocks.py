"""Offline tests for block-based boilerplate removal in chunking and index metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.rag.chunking import build_chunks
from src.rag.index import build_index


def _synthetic_page(idx: int, lines: list[str]) -> dict[str, Any]:
    text = "\n".join(lines)
    return {
        "url": f"https://example.invalid/doc-{idx}",
        "title": f"Documento {idx}",
        "market": "BR",
        "status": "ok",
        "fetched_at": "2026-11-19T00:00:00+00:00",
        "text": text,
        "chars": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def test_isolated_repeated_line_between_content_stays_in_chunks() -> None:
    pages = [
        _synthetic_page(
            i,
            [
                f"Cabeçalho exclusivo da página {i}",
                "Modelo Alfa",
                f"Mensalidade R$ {i}9,90 por mês",
                f"Condição específica número {i}",
            ],
        )
        for i in range(5)
    ]

    chunks = build_chunks(pages, max_chars=900, boilerplate_min_pages=4, boilerplate_min_run=2)
    assert len(chunks) == 5
    for chunk in chunks:
        assert "Modelo Alfa" in chunk["text"]


def test_repeated_block_removed_while_isolated_member_survives_elsewhere() -> None:
    shared_block = ["Rodapé Institucional Um", "Rodapé Institucional Dois", "Central Fictícia 0800"]
    pages = [
        _synthetic_page(i, [f"Conteúdo exclusivo {i}"] + shared_block)
        for i in range(4)
    ]
    pages.append(
        _synthetic_page(
            9,
            [
                "Texto inicial único",
                "Rodapé Institucional Um",
                "Parágrafo exclusivo separador",
                "Rodapé Institucional Dois",
                "Texto final único",
            ],
        )
    )

    chunks = build_chunks(pages, max_chars=900, boilerplate_min_pages=4, boilerplate_min_run=2)
    by_url = {c["doc_url"]: c["text"] for c in chunks}

    for i in range(4):
        txt = by_url[f"https://example.invalid/doc-{i}"]
        for line in shared_block:
            assert line not in txt

    isolated_txt = by_url["https://example.invalid/doc-9"]
    assert "Rodapé Institucional Um" in isolated_txt
    assert "Rodapé Institucional Dois" in isolated_txt


def test_min_run_one_matches_legacy_filter_and_build_index_writes_chunking_meta(tmp_path: Path) -> None:
    pages = [
        _synthetic_page(i, [f"Corpo exclusivo {i}", "Etiqueta Repetida", f"Valor {i}00"])
        for i in range(4)
    ]

    legacy_chunks = build_chunks(pages, max_chars=900, boilerplate_min_pages=4, boilerplate_min_run=1)
    assert all("Etiqueta Repetida" not in c["text"] for c in legacy_chunks)

    class _FakeEmbedder:
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0, 0.0] for _ in texts]

    cfg = {"max_chars": 900, "boilerplate_min_pages": 4, "boilerplate_min_run": 2, "min_chars": 0}
    with_cfg_dir = tmp_path / "with_cfg"
    build_index(
        chunks=legacy_chunks,
        embedder=_FakeEmbedder(),
        out_dir=with_cfg_dir,
        embedding_model="fake-emb",
        dim=3,
        chunking=cfg,
    )
    meta_with = json.loads((with_cfg_dir / "index_meta.json").read_text(encoding="utf-8"))
    assert meta_with["chunking"] == cfg

    no_cfg_dir = tmp_path / "no_cfg"
    build_index(
        chunks=legacy_chunks,
        embedder=_FakeEmbedder(),
        out_dir=no_cfg_dir,
        embedding_model="fake-emb",
        dim=3,
    )
    meta_without = json.loads((no_cfg_dir / "index_meta.json").read_text(encoding="utf-8"))
    assert "chunking" not in meta_without
