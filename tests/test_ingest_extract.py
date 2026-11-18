"""Tests for general extract_text heuristics, --only URL updates, and redirect_duplicate (Phase 13C)."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

from src.rag.ingest import Ingestor, extract_text


def test_extract_text_handles_wordpress_landing_without_main_and_small_article_cards() -> None:
    card_block = "<article><h3>Passos rápidos</h3><p>Texto breve de cartão.</p></article>"
    body_copy = "Conheça o Link de Pagamento Getnet para vender pelas redes sociais com antifraude e Pix. " * 10
    html = (
        "<html><head><title>Link de Pagamento | Getnet</title></head><body>"
        "<header><nav>Menu topo</nav></header>"
        f"<section><h1>Link de Pagamento</h1><p>{body_copy}</p></section>"
        f"<section>{card_block * 4}</section>"
        "<footer>Rodapé institucional</footer>"
        "</body></html>"
    )
    title, text = extract_text(html)
    assert title == "Link de Pagamento | Getnet"
    assert "Link de Pagamento Getnet" in text
    assert "Menu topo" not in text
    assert "Rodapé institucional" not in text
    assert len(text) >= 600


def test_extract_text_uses_single_article_or_main_when_substantial() -> None:
    article_body = "Conteúdo completo do artigo de suporte Getnet sobre taxas e prazos de recebimento. " * 8
    html_article = (
        "<html><head><title>Artigo</title></head><body>"
        f"<article><h1>Taxas</h1><p>{article_body}</p></article>"
        "<div>Relacionado</div></body></html>"
    )
    _, extracted = extract_text(html_article)
    assert "Taxas" in extracted
    assert "Relacionado" not in extracted

    html_empty_main = (
        "<html><head><title>Vazio</title></head><body>"
        "<main><p>Curto</p></main>"
        f"<section>{'Conteúdo principal fora do main. ' * 15}</section></body></html>"
    )
    _, fallback_text = extract_text(html_empty_main)
    assert "Conteúdo principal fora do main." in fallback_text


def test_ingest_only_replaces_only_targeted_urls_byte_for_byte(tmp_path: Path) -> None:
    base = "https://site.getnet.com.br"
    unchanged_line = json.dumps(
        {
            "url": f"{base}/pix/",
            "final_url": f"{base}/pix/",
            "market": "BR",
            "status": "ok",
            "http_status": 200,
            "fetched_at": "2026-11-07T01:37:09+00:00",
            "title": "Pix",
            "text": "Texto original intacto.",
            "sha256": "abc123",
            "chars": 23,
        },
        ensure_ascii=False,
    )
    old_target = json.dumps(
        {
            "url": f"{base}/link/",
            "final_url": f"{base}/link/",
            "market": "BR",
            "status": "no_content",
            "http_status": 200,
            "fetched_at": "2026-11-07T01:37:10+00:00",
            "title": "Link",
            "text": "",
            "sha256": None,
            "chars": 0,
        },
        ensure_ascii=False,
    )
    sources_yaml = tmp_path / "sources.yaml"
    sources_yaml.write_text(
        f"sources:\n  - url: {base}/pix/\n    market: BR\n  - url: {base}/link/\n    market: BR\n",
        encoding="utf-8",
    )
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "pages.jsonl").write_text(f"{unchanged_line}\n{old_target}\n", encoding="utf-8")

    new_html = f"<html><head><title>Link</title></head><body><main>{'Link de Pagamento Getnet. ' * 25}</main></body></html>"

    def handler(req: httpx.Request) -> httpx.Response:
        if str(req.url).endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nAllow: /")
        if str(req.url) == f"{base}/link/":
            return httpx.Response(200, text=new_html)
        raise AssertionError(f"Unexpected URL requested: {req.url}")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    counts = Ingestor(client=client, min_delay_s=0.0).run(
        sources_path=sources_yaml, out_dir=corpus_dir, only_urls=[f"{base}/link/"]
    )

    lines = (corpus_dir / "pages.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines[0] == unchanged_line
    rec1 = json.loads(lines[1])
    assert rec1["status"] == "ok"
    assert rec1["chars"] >= 300
    assert counts["ok"] == 2
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    assert "updated_at" in manifest


def test_ingest_redirect_to_existing_url_marks_redirect_duplicate(tmp_path: Path) -> None:
    base = "https://site.getnet.com.br"
    sources_yaml = tmp_path / "sources.yaml"
    sources_yaml.write_text(
        f"sources:\n  - url: {base}/link/\n    market: BR\n  - url: {base}/wa/\n    market: BR\n",
        encoding="utf-8",
    )
    html_link = f"<html><head><title>Link</title></head><body><main>{'Link oficial Getnet. ' * 25}</main></body></html>"

    def handler(req: httpx.Request) -> httpx.Response:
        if str(req.url).endswith("/robots.txt"):
            return httpx.Response(404, text="")
        if str(req.url) == f"{base}/wa/":
            return httpx.Response(301, headers={"location": f"{base}/link/"})
        if str(req.url) == f"{base}/link/":
            return httpx.Response(200, text=html_link)
        return httpx.Response(404, text="not found")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    corpus_dir = tmp_path / "corpus"
    counts = Ingestor(client=client, min_delay_s=0.0).run(sources_path=sources_yaml, out_dir=corpus_dir)

    assert counts["ok"] == 1
    assert counts["redirect_duplicate"] == 1
    recs = {json.loads(ln)["url"]: json.loads(ln) for ln in (corpus_dir / "pages.jsonl").read_text(encoding="utf-8").splitlines()}
    wa = recs[f"{base}/wa/"]
    assert wa["status"] == "redirect_duplicate"
    assert wa["final_url"] == f"{base}/link/"
    assert wa["text"] == ""
    assert wa["chars"] == 0
    assert wa["sha256"] is None
