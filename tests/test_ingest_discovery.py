"""Offline tests for help-center discovery, PDF ingestion, safety filters, and hybrid_eval --dataset."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import httpx

from src.rag import hybrid_eval
from src.rag.ingest import Ingestor, extract_pdf_text

SITE = "https://site.getnet.com.br"
BODY_PAD = (
    "Para configurar a maquininha siga as etapas da central de ajuda da Getnet com atenção, "
    "conferindo a conexão de rede e os comprovantes emitidos após cada transação no estabelecimento. "
) * 3


def _build_pdf(pages: list[list[str]]) -> bytes:
    """Construct a minimal uncompressed multi-page WinAnsi PDF readable by pypdf."""
    def esc(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{4 + 2 * i} 0 R' for i in range(len(pages)))}] /Count {len(pages)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    for i, lines in enumerate(pages):
        content = "\n".join(["BT", "/F1 11 Tf", "14 TL", "50 780 Td", *[f"({esc(ln)}) Tj T*" for ln in lines], "ET"])
        stream = content.encode("cp1252")
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>".encode()
        )
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for num, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{num} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    return bytes(out)


def _html_page(title: str, body: str, links: list[str]) -> str:
    anchors = "".join(f'<p><a href="{url}">link</a></p>' for url in links)
    return f"<html><head><title>{title}</title></head><body><main><h1>{title}</h1><p>{body}</p>{anchors}</main></body></html>"


def _seed_corpus(tmp_path: Path, name: str) -> tuple[Path, Path, str]:
    out_dir = tmp_path / name
    out_dir.mkdir(parents=True, exist_ok=True)
    seeds = [f"{SITE}/get-ajuda-erros-maquininha/", f"{SITE}/todas-as-maquininhas/"]
    initial = [
        {
            "url": url,
            "final_url": url,
            "market": "BR",
            "status": "ok",
            "http_status": 200,
            "fetched_at": "2026-11-07T00:00:00+00:00",
            "title": "Seed",
            "text": "ajuda " * 80,
            "sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
            "chars": 480,
        }
        for url in seeds
    ]
    raw_lines = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in initial)
    (out_dir / "pages.jsonl").write_text(raw_lines, encoding="utf-8", newline="\n")
    (out_dir / "manifest.json").write_text(json.dumps({"counts": {"ok": 2}, "records": []}), encoding="utf-8")
    sources = tmp_path / f"{name}_sources.yaml"
    sources.write_text(
        "sources:\n" + "".join(f"  - url: {u}\n    market: BR\n" for u in seeds),
        encoding="utf-8",
    )
    return out_dir, sources, raw_lines


def _mock_site() -> tuple[callable, list[str]]:
    manual_pdf = _build_pdf(
        [
            [
                "Cabecalho Getnet PDF",
                "Primeira parte do manual operacional BODY-PDF-1 com detalhes suficientes para ultrapassar o minimo.",
                "Confira o carregamento e aguarde a inicializacao do terminal antes da primeira transacao.",
                "Rodape Pagina",
            ],
            [
                "Cabecalho Getnet PDF",
                "Segunda parte do manual operacional BODY-PDF-2 explicando a troca da bobina de papel termico.",
                "Feche a tampa firmemente e imprima o comprovante de teste para validar o funcionamento.",
                "Rodape Pagina",
            ],
        ]
    )
    internal_pdf = _build_pdf(
        [
            [
                "Classificacao da informacao: Uso Interno",
                "Documento interno BODY-INTERNO com orientacoes restritas que nunca devem entrar no corpus.",
                BODY_PAD,
            ]
        ]
    )
    oversized_pdf = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 50)

    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{SITE}/get-ajuda-x/artigo-a/</loc></url>"
        f"<url><loc>{SITE}/get-ajuda-bloqueado/segredo/</loc></url>"
        f"<url><loc>{SITE}/blog/novidade/</loc></url>"
        f"<url><loc>{SITE}/get-ajuda-erros-maquininha/</loc></url>"
        "</urlset>"
    )
    routes = {
        "/robots.txt": ("text/plain", "User-agent: *\nDisallow: /get-ajuda-bloqueado/\n"),
        "/sitemap_index.xml": ("application/xml", sitemap_xml),
        "/get-ajuda-erros-maquininha/": (
            "text/html",
            _html_page("Erros", BODY_PAD, [f"{SITE}/wp-content/uploads/2025/01/manual.pdf"]),
        ),
        "/todas-as-maquininhas/": (
            "text/html",
            _html_page(
                "Modelos",
                BODY_PAD,
                [
                    f"{SITE}/get-ajuda-x/artigo-b/",
                    f"{SITE}/outra-secao/",
                    f"{SITE}/wp-content/uploads/2025/01/interno.pdf",
                    "https://externo.example.com/guia.pdf",
                ],
            ),
        ),
        "/get-ajuda-x/artigo-a/": (
            "text/html",
            _html_page("Artigo A", BODY_PAD, [f"{SITE}/wp-content/uploads/2025/02/grande.pdf"]),
        ),
        "/get-ajuda-x/artigo-b/": ("text/html", _html_page("Artigo B", BODY_PAD, [])),
        "/wp-content/uploads/2025/01/manual.pdf": ("application/pdf", manual_pdf),
        "/wp-content/uploads/2025/01/interno.pdf": ("application/pdf", internal_pdf),
        "/wp-content/uploads/2025/02/grande.pdf": ("application/pdf", oversized_pdf),
    }
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if request.url.host != "site.getnet.com.br":
            return httpx.Response(404)
        item = routes.get(request.url.path)
        if item is None:
            return httpx.Response(404, text="not found")
        ctype, payload = item
        content = payload if isinstance(payload, bytes) else payload.encode("utf-8")
        return httpx.Response(200, content=content, headers={"content-type": ctype})

    return handler, requested


def test_extract_pdf_text_strips_repeated_headers_and_footers() -> None:
    pdf_bytes = _build_pdf(
        [
            ["Cabecalho Repetido", "Linha unica pagina 1", "Rodape Repetido"],
            ["Cabecalho Repetido", "Linha unica pagina 2", "Rodape Repetido"],
            ["Cabecalho Repetido", "Linha unica pagina 3", "Rodape Repetido"],
        ]
    )
    text, page_count, is_internal = extract_pdf_text(pdf_bytes)
    assert is_internal is False
    assert page_count == 3
    assert "Cabecalho Repetido" not in text
    assert "Rodape Repetido" not in text
    assert "Linha unica pagina 1" in text
    assert "Linha unica pagina 3" in text


def test_discover_collects_help_html_and_pdf_with_filters_and_preserves_existing(tmp_path: Path) -> None:
    handler, requested = _mock_site()
    out_dir, sources_path, before_lines = _seed_corpus(tmp_path, "disc_ok")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    with Ingestor(client=client, min_delay_s=0) as ing:
        summary = ing.discover(sources_path, out_dir, max_pages=10, max_pdfs=10)

    pages_text = (out_dir / "pages.jsonl").read_text(encoding="utf-8")
    assert pages_text.startswith(before_lines)
    records = [json.loads(line) for line in pages_text.splitlines() if line.strip()]
    new_by_url = {r["url"]: r for r in records[2:]}

    assert new_by_url[f"{SITE}/get-ajuda-x/artigo-a/"]["status"] == "ok"
    assert new_by_url[f"{SITE}/get-ajuda-x/artigo-a/"]["pdf_pages"] is None
    assert new_by_url[f"{SITE}/get-ajuda-x/artigo-b/"]["status"] == "ok"
    assert new_by_url[f"{SITE}/get-ajuda-bloqueado/segredo/"]["status"] == "robots_disallowed"
    assert f"{SITE}/get-ajuda-bloqueado/segredo/" not in [u for u in requested if not u.endswith("robots.txt")]

    manual = new_by_url[f"{SITE}/wp-content/uploads/2025/01/manual.pdf"]
    assert manual["status"] == "ok"
    assert manual["content_type"] == "application/pdf"
    assert manual["pdf_pages"] == 2
    assert "BODY-PDF-1" in manual["text"]
    assert "BODY-PDF-2" in manual["text"]
    assert "Cabecalho Getnet PDF" not in manual["text"]
    assert "Rodape Pagina" not in manual["text"]

    interno = new_by_url[f"{SITE}/wp-content/uploads/2025/01/interno.pdf"]
    assert interno["status"] == "internal_document"
    assert interno["text"] == ""
    assert "BODY-INTERNO" not in pages_text

    grande = new_by_url[f"{SITE}/wp-content/uploads/2025/02/grande.pdf"]
    assert grande["status"] == "too_large"
    assert summary["new_records_by_status"]["ok"] == 3


def test_discover_report_decisions_and_manifest_recount(tmp_path: Path) -> None:
    handler, _ = _mock_site()
    out_dir, sources_path, _ = _seed_corpus(tmp_path, "disc_rep")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    with Ingestor(client=client, min_delay_s=0) as ing:
        ing.discover(sources_path, out_dir, max_pages=10, max_pdfs=10)

    disc = json.loads((out_dir / "discovery.json").read_text(encoding="utf-8"))
    dec = {c["url"]: c["decision"] for c in disc["candidates"]}
    assert dec[f"{SITE}/blog/novidade/"] == "out_of_scope"
    assert dec[f"{SITE}/outra-secao/"] == "out_of_scope"
    assert dec["https://externo.example.com/guia.pdf"] == "off_allowlist"
    assert dec[f"{SITE}/get-ajuda-erros-maquininha/"] == "already_in_corpus"
    assert dec[f"{SITE}/get-ajuda-x/artigo-a/"] == "collected"
    assert dec[f"{SITE}/wp-content/uploads/2025/01/manual.pdf"] == "collected"

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    recs = [json.loads(line) for line in (out_dir / "pages.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    expected_counts: dict[str, int] = {}
    for rec in recs:
        expected_counts[rec["status"]] = expected_counts.get(rec["status"], 0) + 1
    assert all(manifest["counts"].get(k) == v for k, v in expected_counts.items())


def test_discover_enforces_max_pages_and_max_pdfs_caps(tmp_path: Path) -> None:
    handler, _ = _mock_site()
    out_dir, sources_path, _ = _seed_corpus(tmp_path, "disc_caps")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    with Ingestor(client=client, min_delay_s=0) as ing:
        ing.discover(sources_path, out_dir, max_pages=1, max_pdfs=1)

    new_recs = [
        json.loads(line) for line in (out_dir / "pages.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()
    ][2:]
    assert len([r for r in new_recs if r.get("content_type") == "text/html"]) == 1
    assert len([r for r in new_recs if r.get("content_type") == "application/pdf"]) <= 1

    disc = json.loads((out_dir / "discovery.json").read_text(encoding="utf-8"))
    capped = [c for c in disc["candidates"] if c.get("decision") == "cap_reached"]
    assert len(capped) >= 2


def test_hybrid_eval_dataset_option_and_embedding_paths(tmp_path: Path) -> None:
    ds_path = tmp_path / "custom_queries.jsonl"
    npy_path, meta_path = hybrid_eval.embedding_paths_for(ds_path)
    assert npy_path == tmp_path / "custom_queries_query_embeddings.npy"
    assert meta_path == tmp_path / "custom_queries_query_embeddings.json"

    shutil.copy("data/eval/retrieval_labeled.jsonl", ds_path)
    shutil.copy("data/eval/retrieval_query_embeddings.npy", npy_path)
    shutil.copy("data/eval/retrieval_query_embeddings.json", meta_path)

    recs_default, q_default, _ = hybrid_eval.load_inputs()
    recs_custom, q_custom, _ = hybrid_eval.load_inputs(dataset=ds_path)
    assert len(recs_custom) == len(recs_default) == 48
    assert q_custom.shape == q_default.shape

    proc = subprocess.run(
        [sys.executable, "-m", "src.rag.hybrid_eval", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--dataset" in proc.stdout
    assert "embed" in proc.stdout
