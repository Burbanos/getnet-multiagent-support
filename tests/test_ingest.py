"""Tests for web ingestion module respecting robots.txt and rate limits (Phase 3A)."""
from __future__ import annotations

import hashlib
import json
import tempfile
import time
from pathlib import Path

import httpx

from src.rag import ingest
from src.rag.ingest import Ingestor, extract_text


def _make_client(routes: dict[str, tuple[int, str, dict | None]], log: list) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        log.append((request.method, str(request.url), request.headers.get("user-agent")))
        key = str(request.url)
        if key in routes:
            status, body, headers = routes[key]
            return httpx.Response(status, text=body, headers=headers or {})
        return httpx.Response(404, text="not found")

    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


LONG_TEXT = "Getnet oferece maquininhas seguras e soluções completas de pagamento. " * 15
HTML_PAGE = (
    "<html>"
    "<head><title>Título da Página de Teste</title><script>alert('x');</script><style>body {color: red;}</style></head>"
    "<body>"
    "<header>Cabeçalho institucional</header>"
    "<nav>Menu principal</nav>"
    "<main><h1>Pagamentos Getnet</h1><p>" + LONG_TEXT + "</p></main>"
    "<footer>Rodapé e copyright</footer>"
    "</body>"
    "</html>"
)


def test_extraction_clean_content_and_title():
    title, text = extract_text(HTML_PAGE)
    assert title == "Título da Página de Teste"
    assert "Pagamentos Getnet" in text
    assert "soluções completas de pagamento" in text
    for tag_content in ("alert('x')", "color: red", "Cabeçalho institucional", "Menu principal", "Rodapé e copyright"):
        assert tag_content not in text


def test_robots_txt_disallow_skips_page_request():
    log: list = []
    base = "https://site.getnet.com.br"
    routes = {
        f"{base}/robots.txt": (200, "User-agent: *\nDisallow: /", None),
        f"{base}/artigo": (200, HTML_PAGE, None),
    }
    client = _make_client(routes, log)
    ing = Ingestor(client=client, min_delay_s=0.0)

    rec = ing.fetch(f"{base}/artigo", "BR")
    assert rec["status"] == "robots_disallowed"
    assert rec["text"] == ""
    assert rec["sha256"] is None
    assert rec["chars"] == 0
    # Assert page was never requested
    assert not any(u.endswith("/artigo") for _, u, _ in log)


def test_robots_txt_404_allows_page_request():
    log: list = []
    base = "https://site.getnet.com.br"
    routes = {
        f"{base}/artigo": (200, HTML_PAGE, None),
    }
    client = _make_client(routes, log)
    ing = Ingestor(client=client, min_delay_s=0.0)

    rec = ing.fetch(f"{base}/artigo", "BR")
    assert rec["status"] == "ok"
    assert rec["http_status"] == 200
    assert len(rec["text"]) >= 300
    assert rec["sha256"] == hashlib.sha256(rec["text"].encode("utf-8")).hexdigest()
    assert rec["chars"] == len(rec["text"])


def test_robots_txt_500_disallows_page_request():
    log: list = []
    base = "https://site.getnet.com.br"
    routes = {
        f"{base}/robots.txt": (500, "Internal error", None),
        f"{base}/artigo": (200, HTML_PAGE, None),
    }
    client = _make_client(routes, log)
    ing = Ingestor(client=client, min_delay_s=0.0)

    rec = ing.fetch(f"{base}/artigo", "BR")
    assert rec["status"] == "robots_disallowed"
    assert not any(u.endswith("/artigo") for _, u, _ in log)


def test_user_agent_header_sent_on_all_requests():
    log: list = []
    base = "https://site.getnet.com.br"
    routes = {
        f"{base}/robots.txt": (200, "User-agent: *\nAllow: /", None),
        f"{base}/pagina": (200, HTML_PAGE, None),
    }
    client = _make_client(routes, log)
    ing = Ingestor(client=client, min_delay_s=0.0)
    ing.fetch(f"{base}/pagina", "BR")

    assert len(log) >= 2
    for _, _, ua in log:
        assert ua == ingest.USER_AGENT
        assert "getnet-multiagent-support-ingest" in ua


def test_http_error_handling():
    log: list = []
    base = "https://site.getnet.com.br"
    routes = {
        f"{base}/robots.txt": (200, "User-agent: *\nAllow: /", None),
        f"{base}/erro": (500, "Server Error", None),
    }
    client = _make_client(routes, log)
    ing = Ingestor(client=client, min_delay_s=0.0)

    rec = ing.fetch(f"{base}/erro", "BR")
    assert rec["status"] == "http_error"
    assert rec["http_status"] == 500
    assert rec["text"] == ""
    assert rec["sha256"] is None


def test_no_content_for_short_pages():
    log: list = []
    base = "https://site.getnet.com.br"
    routes = {
        f"{base}/robots.txt": (200, "User-agent: *\nAllow: /", None),
        f"{base}/curto": (200, "<html><body><main>Pouco conteúdo</main></body></html>", None),
    }
    client = _make_client(routes, log)
    ing = Ingestor(client=client, min_delay_s=0.0)

    rec = ing.fetch(f"{base}/curto", "BR")
    assert rec["status"] == "no_content"
    assert rec["text"] == ""
    assert rec["chars"] == 0


def test_redirect_off_allowlist():
    log: list = []
    base = "https://site.getnet.com.br"
    routes = {
        f"{base}/robots.txt": (200, "User-agent: *\nAllow: /", None),
        f"{base}/externo": (302, "", {"location": "https://nao-autorizado.com/pagina"}),
        "https://nao-autorizado.com/pagina": (200, HTML_PAGE, None),
    }
    client = _make_client(routes, log)
    ing = Ingestor(client=client, min_delay_s=0.0)

    rec = ing.fetch(f"{base}/externo", "BR")
    assert rec["status"] == "off_allowlist"
    assert rec["text"] == ""
    assert rec["sha256"] is None


def test_unknown_host_off_allowlist_without_network_request():
    log: list = []
    client = _make_client({}, log)
    ing = Ingestor(client=client, min_delay_s=0.0)

    rec = ing.fetch("https://google.com/search", "BR")
    assert rec["status"] == "off_allowlist"
    assert log == []


def test_robots_txt_cached_single_request_per_host():
    log: list = []
    base = "https://www.getnet.net"
    routes = {
        f"{base}/robots.txt": (200, "User-agent: *\nAllow: /", None),
        f"{base}/en/p1": (200, HTML_PAGE, None),
        f"{base}/en/p2": (200, HTML_PAGE, None),
    }
    client = _make_client(routes, log)
    ing = Ingestor(client=client, min_delay_s=0.0)

    ing.fetch(f"{base}/en/p1", "global")
    ing.fetch(f"{base}/en/p2", "global")

    robots_requests = [u for _, u, _ in log if u.endswith("/robots.txt")]
    assert len(robots_requests) == 1


def test_rate_limiting_enforced_per_host():
    log: list = []
    base = "https://www.getnet.net"
    routes = {
        f"{base}/robots.txt": (200, "User-agent: *\nAllow: /", None),
        f"{base}/en/1": (200, HTML_PAGE, None),
        f"{base}/en/2": (200, HTML_PAGE, None),
    }
    client = _make_client(routes, log)
    delay = 0.25
    ing = Ingestor(client=client, min_delay_s=delay)

    t0 = time.perf_counter()
    ing.fetch(f"{base}/en/1", "global")
    ing.fetch(f"{base}/en/2", "global")
    elapsed = time.perf_counter() - t0

    assert elapsed >= delay * 0.95


def test_ingestor_run_generates_pages_jsonl_and_manifest():
    base = "https://site.getnet.com.br"
    log: list = []
    routes = {
        f"{base}/robots.txt": (200, "User-agent: *\nDisallow: /bloqueado", None),
        f"{base}/ok1": (200, HTML_PAGE, None),
        f"{base}/bloqueado": (200, HTML_PAGE, None),
    }
    client = _make_client(routes, log)
    ing = Ingestor(client=client, min_delay_s=0.0)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        sources_yaml = tmp / "sources.yaml"
        sources_yaml.write_text(
            "sources:\n"
            f"  - url: {base}/ok1\n    market: BR\n"
            f"  - url: {base}/bloqueado\n    market: BR\n",
            encoding="utf-8",
        )
        out_dir = tmp / "corpus"
        counts = ing.run(sources_path=sources_yaml, out_dir=out_dir)

        assert counts["ok"] == 1
        assert counts["robots_disallowed"] == 1

        pages_file = out_dir / "pages.jsonl"
        assert pages_file.exists()
        recs = [json.loads(ln) for ln in pages_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(recs) == 2
        assert recs[0]["status"] == "ok"
        assert recs[1]["status"] == "robots_disallowed"

        manifest_file = out_dir / "manifest.json"
        assert manifest_file.exists()
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        assert manifest["counts"]["ok"] == 1
        assert manifest["counts"]["robots_disallowed"] == 1
        assert manifest["user_agent"] == ingest.USER_AGENT
        assert len(manifest["records"]) == 2
