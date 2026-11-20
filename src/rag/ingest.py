"""Ingestion module for official Getnet knowledge sources respecting robots.txt."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import math
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx
import yaml
from bs4 import BeautifulSoup

logger = logging.getLogger("multiagent.rag.ingest")

USER_AGENT = "getnet-multiagent-support-ingest/1.0 (+https://github.com/Burbanos/getnet-multiagent-support)"
ALLOWED_DOMAINS = {"www.getnet.net", "site.getnet.com.br", "www.getnet.com.br"}
SITE_HOST = "site.getnet.com.br"
SITE_BASE = f"https://{SITE_HOST}"
HELP_PREFIX = "/get-ajuda-"
PDF_PREFIX = f"{SITE_BASE}/wp-content/uploads/"
MIN_CHARS = 300
MAX_PDF_BYTES = 5 * 1024 * 1024
_INTERNAL_DOC_RE = re.compile(r"classifica[cç][aã]o da informa[cç][aã]o:\s*interno|uso interno", re.IGNORECASE)
_ASSET_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".css", ".js", ".woff", ".woff2", ".ttf", ".zip")
STATUSES = {
    "ok",
    "robots_disallowed",
    "http_error",
    "fetch_error",
    "no_content",
    "off_allowlist",
    "redirect_duplicate",
    "internal_document",
    "too_large",
}


def _extract_lines(node: Any) -> str:
    raw_text = node.get_text("\n")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    return "\n".join(lines)


def extract_text(html: str) -> tuple[str, str]:
    """
    Extract title and cleaned text from HTML page using BeautifulSoup.
    Strips scripts, styles, navigation, headers, footers, forms and other clutter.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.title:
        title = soup.title.get_text().strip()

    for tag in soup.find_all(
        ["script", "style", "noscript", "nav", "header", "footer", "form", "svg", "iframe", "aside"]
    ):
        tag.decompose()

    body = soup.find("body") or soup
    body_text = _extract_lines(body)
    text = body_text

    main_tag = soup.find("main")
    if main_tag is not None:
        main_text = _extract_lines(main_tag)
        if len(main_text) >= MIN_CHARS:
            text = main_text
    else:
        articles = soup.find_all("article")
        if len(articles) == 1:
            article_text = _extract_lines(articles[0])
            if len(article_text) >= MIN_CHARS and len(article_text) * 2 >= len(body_text):
                text = article_text

    return title, text


def extract_pdf_text(data: bytes) -> tuple[str, int, bool]:
    """
    Extract text and page count from PDF bytes using pypdf.
    Removes running headers/footers present on >= max(2, ceil(pages/2)) pages.
    Returns (text, page_count, is_internal_document).
    """
    import pypdf

    reader = pypdf.PdfReader(io.BytesIO(data))
    pages_lines: list[list[str]] = []
    raw_chunks: list[str] = []
    for page in reader.pages:
        raw = page.extract_text() or ""
        raw_chunks.append(raw)
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        pages_lines.append(lines)

    page_count = len(pages_lines)
    full_raw = "\n".join(raw_chunks)
    if _INTERNAL_DOC_RE.search(full_raw):
        return "", page_count, True

    repeated: set[str] = set()
    if page_count >= 2:
        freq: dict[str, int] = {}
        for plines in pages_lines:
            for ln in set(plines):
                freq[ln] = freq.get(ln, 0) + 1
        threshold = max(2, math.ceil(page_count / 2))
        repeated = {ln for ln, count in freq.items() if count >= threshold}

    kept_lines: list[str] = []
    for plines in pages_lines:
        for ln in plines:
            if ln not in repeated:
                kept_lines.append(ln)

    return "\n".join(kept_lines), page_count, False


def _extract_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for tag in soup.find_all("a", href=True):
        href = str(tag["href"]).strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        resolved = urljoin(base_url, href)
        parsed = urlparse(resolved)
        if parsed.scheme not in ("http", "https"):
            continue
        clean = urlunparse(parsed._replace(fragment=""))
        if clean not in seen:
            seen.add(clean)
            links.append(clean)
    return links


def _parse_sitemap_locs(xml_text: str) -> tuple[bool, list[str]]:
    """Return (is_index, locs) parsed from an XML sitemap or sitemapindex."""
    root = ET.fromstring(xml_text)
    root_tag = root.tag.rsplit("}", 1)[-1].lower()
    locs: list[str] = []
    for elem in root.iter():
        if elem.tag.rsplit("}", 1)[-1].lower() == "loc" and elem.text:
            loc = elem.text.strip()
            if loc:
                locs.append(urlunparse(urlparse(loc)._replace(fragment="")))
    return root_tag == "sitemapindex", locs


class Ingestor:
    """Ingestor for official Getnet documentation sources respecting robots.txt and rate limits."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        user_agent: str = USER_AGENT,
        min_delay_s: float = 1.0,
    ) -> None:
        self.user_agent = user_agent
        self.min_delay_s = min_delay_s
        if client is not None:
            self.client = client
            self._owns_client = False
        else:
            self.client = httpx.Client(follow_redirects=True, timeout=15.0)
            self._owns_client = True

        self._robots_cache: dict[str, RobotFileParser | bool] = {}
        self._last_request_time: dict[str, float] = {}

    def _wait_rate_limit(self, host: str) -> None:
        """Enforce minimum delay between requests to the same host."""
        if self.min_delay_s > 0 and host in self._last_request_time:
            elapsed = time.perf_counter() - self._last_request_time[host]
            wait_time = self.min_delay_s - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
        self._last_request_time[host] = time.perf_counter()

    def _check_robots_allowed(self, url: str, host: str) -> bool:
        """Fetch and cache robots.txt for the host, checking if url can be crawled."""
        if host not in self._robots_cache:
            parsed = urlparse(url)
            scheme = parsed.scheme or "https"
            robots_url = f"{scheme}://{host}/robots.txt"
            self._wait_rate_limit(host)
            try:
                resp = self.client.get(robots_url, headers={"User-Agent": self.user_agent})
                if resp.status_code == 200:
                    rp = RobotFileParser()
                    rp.parse(resp.text.splitlines())
                    self._robots_cache[host] = rp
                elif resp.status_code in (404, 410):
                    self._robots_cache[host] = True
                else:
                    self._robots_cache[host] = False
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed to fetch robots.txt for {host}: {exc}")
                self._robots_cache[host] = False

        cached = self._robots_cache[host]
        if cached is True:
            return True
        if cached is False:
            return False
        return cached.can_fetch(self.user_agent, url)

    def _robots_sitemaps(self, host: str) -> list[str]:
        """Fetch/read cached robots.txt and return any declared Sitemap URLs for host."""
        sitemaps: list[str] = []
        robots_url = f"https://{host}/robots.txt"
        self._wait_rate_limit(host)
        try:
            resp = self.client.get(robots_url, headers={"User-Agent": self.user_agent})
            if resp.status_code == 200:
                rp = RobotFileParser()
                lines = resp.text.splitlines()
                rp.parse(lines)
                self._robots_cache[host] = rp
                for ln in lines:
                    if ln.lower().startswith("sitemap:"):
                        sm_url = ln.split(":", 1)[1].strip()
                        if sm_url and sm_url not in sitemaps:
                            sitemaps.append(sm_url)
            elif resp.status_code in (404, 410):
                self._robots_cache[host] = True
            else:
                self._robots_cache[host] = False
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed to read sitemaps from robots.txt for {host}: {exc}")
            self._robots_cache[host] = False
        return sitemaps

    def _fetch_with_links(
        self,
        url: str,
        market: str,
        known_urls: set[str] | None = None,
    ) -> tuple[dict[str, Any], list[str]]:
        """
        Fetch and parse a single document URL, also returning extracted links on HTTP 200 HTML responses.
        """
        now_iso = datetime.now(UTC).isoformat()
        parsed = urlparse(url)
        host = parsed.hostname or ""

        if host not in ALLOWED_DOMAINS:
            return {
                "url": url,
                "final_url": url,
                "market": market,
                "status": "off_allowlist",
                "http_status": None,
                "fetched_at": now_iso,
                "title": "",
                "text": "",
                "sha256": None,
                "chars": 0,
            }, []

        if not self._check_robots_allowed(url, host):
            return {
                "url": url,
                "final_url": url,
                "market": market,
                "status": "robots_disallowed",
                "http_status": None,
                "fetched_at": now_iso,
                "title": "",
                "text": "",
                "sha256": None,
                "chars": 0,
            }, []

        self._wait_rate_limit(host)
        try:
            response = self.client.get(url, headers={"User-Agent": self.user_agent})
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Network error fetching {url}: {exc}")
            return {
                "url": url,
                "final_url": url,
                "market": market,
                "status": "fetch_error",
                "http_status": None,
                "fetched_at": now_iso,
                "title": "",
                "text": "",
                "sha256": None,
                "chars": 0,
            }, []

        final_url = str(response.url)
        final_host = urlparse(final_url).hostname or ""

        if final_host not in ALLOWED_DOMAINS:
            return {
                "url": url,
                "final_url": final_url,
                "market": market,
                "status": "off_allowlist",
                "http_status": response.status_code,
                "fetched_at": now_iso,
                "title": "",
                "text": "",
                "sha256": None,
                "chars": 0,
            }, []

        if response.status_code != 200:
            return {
                "url": url,
                "final_url": final_url,
                "market": market,
                "status": "http_error",
                "http_status": response.status_code,
                "fetched_at": now_iso,
                "title": "",
                "text": "",
                "sha256": None,
                "chars": 0,
            }, []

        links = _extract_links(response.text, final_url)
        if final_url != url and known_urls and final_url in known_urls:
            title, _ = extract_text(response.text)
            return {
                "url": url,
                "final_url": final_url,
                "market": market,
                "status": "redirect_duplicate",
                "http_status": response.status_code,
                "fetched_at": now_iso,
                "title": title,
                "text": "",
                "sha256": None,
                "chars": 0,
            }, links

        title, text = extract_text(response.text)
        if len(text) < MIN_CHARS:
            return {
                "url": url,
                "final_url": final_url,
                "market": market,
                "status": "no_content",
                "http_status": 200,
                "fetched_at": now_iso,
                "title": title,
                "text": "",
                "sha256": None,
                "chars": 0,
            }, links

        sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()

        return {
            "url": url,
            "final_url": final_url,
            "market": market,
            "status": "ok",
            "http_status": 200,
            "fetched_at": now_iso,
            "title": title,
            "text": text,
            "sha256": sha256,
            "chars": len(text),
        }, links

    def fetch(self, url: str, market: str, known_urls: set[str] | None = None) -> dict[str, Any]:
        """
        Fetch and parse a single document URL.
        Validates host allowlist, robots.txt, HTTP status, duplicate redirects, and text content size.
        """
        rec, _ = self._fetch_with_links(url, market, known_urls=known_urls)
        return rec

    def run(
        self,
        sources_path: str | Path = "data/sources.yaml",
        out_dir: str | Path = "data/corpus",
        only_urls: list[str] | set[str] | None = None,
    ) -> dict[str, int]:
        """
        Process sources defined in sources.yaml (or only the given --only URLs) and update corpus records.
        Generates/updates pages.jsonl and manifest.json inside out_dir.
        """
        sources_path = Path(sources_path)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        sources_bytes = sources_path.read_bytes()
        raw_sources = yaml.safe_load(sources_bytes.decode("utf-8")) or {}
        sources_list = raw_sources.get("sources", []) if isinstance(raw_sources, dict) else []
        market_by_url = {item.get("url", ""): item.get("market", "BR") for item in sources_list if item.get("url")}
        known_urls = set(market_by_url)

        pages_path = out_dir / "pages.jsonl"
        manifest_path = out_dir / "manifest.json"
        now_iso = datetime.now(UTC).isoformat()

        if only_urls:
            target_list = list(dict.fromkeys(u.strip() for u in only_urls if str(u).strip()))
            target_set = set(target_list)
            existing_lines = pages_path.read_text(encoding="utf-8").splitlines() if pages_path.exists() else []
            for raw_ln in existing_lines:
                if raw_ln.strip():
                    known_urls.add(json.loads(raw_ln).get("url", ""))
            known_urls |= target_set

            final_lines: list[str] = []
            records: list[dict[str, Any]] = []
            replaced: set[str] = set()
            for raw_ln in existing_lines:
                if not raw_ln.strip():
                    continue
                parsed = json.loads(raw_ln)
                rec_url = parsed.get("url", "")
                if rec_url in target_set:
                    rec = self.fetch(rec_url, market_by_url.get(rec_url, parsed.get("market", "BR")), known_urls=known_urls)
                    final_lines.append(json.dumps(rec, ensure_ascii=False))
                    records.append(rec)
                    replaced.add(rec_url)
                else:
                    final_lines.append(raw_ln)
                    records.append(parsed)

            for rec_url in target_list:
                if rec_url not in replaced:
                    rec = self.fetch(rec_url, market_by_url.get(rec_url, "BR"), known_urls=known_urls)
                    final_lines.append(json.dumps(rec, ensure_ascii=False))
                    records.append(rec)

            pages_path.write_text("\n".join(final_lines) + "\n", encoding="utf-8")

            counts = {s: 0 for s in STATUSES}
            for rec in records:
                st = rec.get("status", "fetch_error")
                counts[st] = counts.get(st, 0) + 1

            prev_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
            generated_at = prev_manifest.get("generated_at", now_iso)
        else:
            counts = {s: 0 for s in STATUSES}
            records = []
            for item in sources_list:
                url = item.get("url", "")
                market = item.get("market", "BR")
                rec = self.fetch(url, market, known_urls=known_urls)
                records.append(rec)
                status = rec.get("status", "fetch_error")
                counts[status] = counts.get(status, 0) + 1

            with pages_path.open("w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            generated_at = now_iso

        manifest = {
            "user_agent": self.user_agent,
            "generated_at": generated_at,
            "updated_at": now_iso,
            "sources_file_sha256": hashlib.sha256(sources_bytes).hexdigest(),
            "counts": counts,
            "records": [
                {
                    "url": r["url"],
                    "status": r["status"],
                    "http_status": r["http_status"],
                    "fetched_at": r["fetched_at"],
                    "sha256": r["sha256"],
                    "chars": r["chars"],
                }
                for r in records
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return counts

    def _fetch_pdf(self, url: str, market: str, *, discovered_from: str) -> dict[str, Any]:
        """Fetch and extract a single PDF document respecting robots.txt, 5 MB limit, and internal markings."""
        now_iso = datetime.now(UTC).isoformat()
        parsed = urlparse(url)
        host = parsed.hostname or ""

        def _make_rec(
            status: str,
            *,
            final_url: str = url,
            http_status: int | None = None,
            title: str = "",
            text: str = "",
            pdf_pages: int | None = None,
        ) -> dict[str, Any]:
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest() if status == "ok" else None
            return {
                "url": url,
                "final_url": final_url,
                "market": market,
                "status": status,
                "http_status": http_status,
                "fetched_at": now_iso,
                "title": title,
                "text": text,
                "sha256": sha,
                "chars": len(text) if status == "ok" else 0,
                "content_type": "application/pdf",
                "discovered_from": discovered_from,
                "pdf_pages": pdf_pages,
            }

        if host not in ALLOWED_DOMAINS:
            return _make_rec("off_allowlist")
        if not self._check_robots_allowed(url, host):
            return _make_rec("robots_disallowed")

        self._wait_rate_limit(host)
        try:
            response = self.client.get(url, headers={"User-Agent": self.user_agent})
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Network error fetching PDF {url}: {exc}")
            return _make_rec("fetch_error")

        final_url = str(response.url)
        final_host = urlparse(final_url).hostname or ""
        if final_host not in ALLOWED_DOMAINS:
            return _make_rec("off_allowlist", final_url=final_url, http_status=response.status_code)
        if response.status_code != 200:
            return _make_rec("http_error", final_url=final_url, http_status=response.status_code)

        content = response.content or b""
        content_len_hdr = response.headers.get("content-length")
        if (content_len_hdr and content_len_hdr.isdigit() and int(content_len_hdr) > MAX_PDF_BYTES) or (
            len(content) > MAX_PDF_BYTES
        ):
            return _make_rec("too_large", final_url=final_url, http_status=200)

        try:
            text, page_count, is_internal = extract_pdf_text(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Failed parsing PDF {url}: {exc}")
            return _make_rec("no_content", final_url=final_url, http_status=200)

        if is_internal:
            return _make_rec("internal_document", final_url=final_url, http_status=200, pdf_pages=page_count)
        if len(text) < MIN_CHARS:
            return _make_rec("no_content", final_url=final_url, http_status=200, pdf_pages=page_count)

        title = Path(urlparse(final_url).path).name or "documento.pdf"
        return _make_rec("ok", final_url=final_url, http_status=200, title=title, text=text, pdf_pages=page_count)

    def _collect_sitemap_candidates(self) -> list[tuple[str, str]]:
        """Discover candidate URLs from sitemaps declared in robots.txt and default WordPress paths."""
        sitemap_queue = self._robots_sitemaps(SITE_HOST)
        for fallback_sm in (f"{SITE_BASE}/sitemap_index.xml", f"{SITE_BASE}/wp-sitemap.xml"):
            if fallback_sm not in sitemap_queue:
                sitemap_queue.append(fallback_sm)

        seen_sitemaps: set[str] = set()
        found: list[tuple[str, str]] = []
        while sitemap_queue:
            sm_url = sitemap_queue.pop(0)
            if sm_url in seen_sitemaps:
                continue
            seen_sitemaps.add(sm_url)
            host = urlparse(sm_url).hostname or ""
            if host not in ALLOWED_DOMAINS or not self._check_robots_allowed(sm_url, host):
                continue
            self._wait_rate_limit(host)
            try:
                resp = self.client.get(sm_url, headers={"User-Agent": self.user_agent})
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed fetching sitemap {sm_url}: {exc}")
                continue
            if resp.status_code != 200 or not resp.text.strip():
                continue
            try:
                is_index, locs = _parse_sitemap_locs(resp.text)
            except ET.ParseError:
                continue
            if is_index:
                for child_sm in locs:
                    if child_sm not in seen_sitemaps:
                        sitemap_queue.append(child_sm)
            else:
                for loc in locs:
                    found.append((loc, sm_url))
        return found

    def discover(
        self,
        sources_path: str | Path = "data/sources.yaml",
        out_dir: str | Path = "data/corpus",
        max_pages: int = 120,
        max_pdfs: int = 15,
    ) -> dict[str, Any]:
        """
        Discover help-center HTML pages (/get-ajuda-) and official PDFs (/wp-content/uploads/)
        from site.getnet.com.br sitemaps and seed links, appending new records to pages.jsonl
        while keeping existing lines byte-identical.
        """
        sources_path = Path(sources_path)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        pages_path = out_dir / "pages.jsonl"
        manifest_path = out_dir / "manifest.json"
        discovery_path = out_dir / "discovery.json"

        sources_bytes = sources_path.read_bytes()
        raw_sources = yaml.safe_load(sources_bytes.decode("utf-8")) or {}
        sources_list = raw_sources.get("sources", []) if isinstance(raw_sources, dict) else []

        existing_lines: list[str] = []
        existing_records: list[dict[str, Any]] = []
        known_urls: set[str] = set()
        if pages_path.exists():
            raw_text = pages_path.read_bytes().decode("utf-8")
            for ln in raw_text.splitlines():
                if not ln.strip():
                    continue
                existing_lines.append(ln)
                rec = json.loads(ln)
                existing_records.append(rec)
                if rec.get("url"):
                    known_urls.add(str(rec["url"]))
                if rec.get("final_url"):
                    known_urls.add(str(rec["final_url"]))

        # Gather candidates preserving first-seen discovered_from
        discovered_from_map: dict[str, str] = {}

        def _note_candidate(url: str, source_url: str) -> None:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return
            clean = urlunparse(parsed._replace(fragment=""))
            if clean.lower().endswith(_ASSET_EXTS):
                return
            if clean not in discovered_from_map:
                discovered_from_map[clean] = source_url

        for url, src_sm in self._collect_sitemap_candidates():
            _note_candidate(url, src_sm)

        site_seeds = [
            str(item.get("url"))
            for item in sources_list
            if isinstance(item, dict)
            and item.get("url")
            and (urlparse(str(item["url"])).hostname or "") == SITE_HOST
        ]
        for seed_url in site_seeds:
            if not self._check_robots_allowed(seed_url, SITE_HOST):
                continue
            self._wait_rate_limit(SITE_HOST)
            try:
                resp = self.client.get(seed_url, headers={"User-Agent": self.user_agent})
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Failed fetching seed links from {seed_url}: {exc}")
                continue
            if resp.status_code == 200 and "html" in (resp.headers.get("content-type", "text/html").lower()):
                for link in _extract_links(resp.text, str(resp.url)):
                    _note_candidate(link, seed_url)

        candidate_entries: dict[str, dict[str, Any]] = {}
        html_eligible: list[str] = []
        pdf_eligible: list[str] = []

        def _classify_url(url: str, discovered_from: str) -> None:
            if url in candidate_entries:
                return
            parsed = urlparse(url)
            host = parsed.hostname or ""
            is_pdf = parsed.path.lower().endswith(".pdf")
            kind = "pdf" if is_pdf else "html"
            if host not in ALLOWED_DOMAINS:
                candidate_entries[url] = {
                    "url": url,
                    "kind": kind,
                    "discovered_from": discovered_from,
                    "decision": "off_allowlist",
                    "status": None,
                }
                return
            if url in known_urls:
                candidate_entries[url] = {
                    "url": url,
                    "kind": kind,
                    "discovered_from": discovered_from,
                    "decision": "already_in_corpus",
                    "status": None,
                }
                return
            if is_pdf:
                if url.startswith(PDF_PREFIX):
                    candidate_entries[url] = {
                        "url": url,
                        "kind": "pdf",
                        "discovered_from": discovered_from,
                        "decision": None,
                        "status": None,
                    }
                    pdf_eligible.append(url)
                else:
                    candidate_entries[url] = {
                        "url": url,
                        "kind": "pdf",
                        "discovered_from": discovered_from,
                        "decision": "out_of_scope",
                        "status": None,
                    }
                return
            if host == SITE_HOST and parsed.path.startswith(HELP_PREFIX):
                candidate_entries[url] = {
                    "url": url,
                    "kind": "html",
                    "discovered_from": discovered_from,
                    "decision": None,
                    "status": None,
                }
                html_eligible.append(url)
            else:
                candidate_entries[url] = {
                    "url": url,
                    "kind": "other",
                    "discovered_from": discovered_from,
                    "decision": "out_of_scope",
                    "status": None,
                }

        for url in sorted(discovered_from_map):
            _classify_url(url, discovered_from_map[url])

        new_records: list[dict[str, Any]] = []
        html_processed = 0
        for url in sorted(html_eligible):
            if html_processed >= max_pages:
                candidate_entries[url]["decision"] = "cap_reached"
                continue
            html_processed += 1
            disc_from = str(candidate_entries[url]["discovered_from"])

            rec, page_links = self._fetch_with_links(url, "BR", known_urls=known_urls)
            rec["content_type"] = "text/html"
            rec["discovered_from"] = disc_from
            rec["pdf_pages"] = None
            new_records.append(rec)
            known_urls.add(url)
            if rec.get("final_url"):
                known_urls.add(str(rec["final_url"]))
            candidate_entries[url]["decision"] = "collected"
            candidate_entries[url]["status"] = rec["status"]

            for link in page_links:
                clean_link = urlunparse(urlparse(link)._replace(fragment=""))
                if urlparse(clean_link).path.lower().endswith(".pdf"):
                    _classify_url(clean_link, url)

        pdf_processed = 0
        for url in sorted(pdf_eligible):
            if pdf_processed >= max_pdfs:
                candidate_entries[url]["decision"] = "cap_reached"
                continue
            pdf_processed += 1
            disc_from = str(candidate_entries[url]["discovered_from"])
            rec = self._fetch_pdf(url, "BR", discovered_from=disc_from)
            new_records.append(rec)
            known_urls.add(url)
            if rec.get("final_url"):
                known_urls.add(str(rec["final_url"]))
            candidate_entries[url]["decision"] = "collected"
            candidate_entries[url]["status"] = rec["status"]

        final_lines = existing_lines + [json.dumps(r, ensure_ascii=False) for r in new_records]
        pages_path.write_text("\n".join(final_lines) + ("\n" if final_lines else ""), encoding="utf-8", newline="\n")

        all_records = existing_records + new_records
        counts = {s: 0 for s in STATUSES}
        for rec in all_records:
            st = rec.get("status", "fetch_error")
            counts[st] = counts.get(st, 0) + 1

        now_iso = datetime.now(UTC).isoformat()
        prev_manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        manifest = {
            "user_agent": self.user_agent,
            "generated_at": prev_manifest.get("generated_at", now_iso),
            "updated_at": now_iso,
            "sources_file_sha256": hashlib.sha256(sources_bytes).hexdigest(),
            "counts": counts,
            "records": [
                {
                    "url": r["url"],
                    "status": r["status"],
                    "http_status": r["http_status"],
                    "fetched_at": r["fetched_at"],
                    "sha256": r["sha256"],
                    "chars": r["chars"],
                    **(
                        {
                            "content_type": r["content_type"],
                            "discovered_from": r["discovered_from"],
                            "pdf_pages": r["pdf_pages"],
                        }
                        if "content_type" in r
                        else {}
                    ),
                }
                for r in all_records
            ],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        candidates_out = [candidate_entries[u] for u in sorted(candidate_entries)]
        dec_counts: dict[str, int] = {}
        new_status_counts: dict[str, int] = {}
        for c in candidates_out:
            d = str(c.get("decision") or "unknown")
            dec_counts[d] = dec_counts.get(d, 0) + 1
        for r in new_records:
            st = str(r.get("status") or "fetch_error")
            new_status_counts[st] = new_status_counts.get(st, 0) + 1

        discovery_report = {
            "generated_at": now_iso,
            "max_pages": max_pages,
            "max_pdfs": max_pdfs,
            "counts_by_decision": dec_counts,
            "new_records_by_status": new_status_counts,
            "candidates": candidates_out,
        }
        discovery_path.write_text(json.dumps(discovery_report, indent=2, ensure_ascii=False), encoding="utf-8")
        return discovery_report


    def close(self) -> None:
        """Close the underlying HTTP client if owned by this Ingestor."""
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Getnet official pages respecting robots.txt.")
    parser.add_argument("--sources", default="data/sources.yaml", help="Path to sources.yaml")
    parser.add_argument("--out-dir", default="data/corpus", help="Output corpus directory")
    parser.add_argument("--only", action="append", dest="only_urls", default=None, help="Recollect only specified URL(s)")
    parser.add_argument("--discover", action="store_true", help="Discover new /get-ajuda- HTML pages and PDFs")
    parser.add_argument("--max-pages", type=int, default=120, help="Max new HTML pages to collect in --discover")
    parser.add_argument("--max-pdfs", type=int, default=15, help="Max new PDFs to collect in --discover")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ing = Ingestor()
    try:
        if args.discover:
            report = ing.discover(
                sources_path=args.sources,
                out_dir=args.out_dir,
                max_pages=args.max_pages,
                max_pdfs=args.max_pdfs,
            )
            print("\n--- Discovery Summary ---")
            print(json.dumps(
                {
                    "counts_by_decision": report["counts_by_decision"],
                    "new_records_by_status": report["new_records_by_status"],
                },
                indent=2,
                ensure_ascii=False,
            ))
        else:
            summary = ing.run(sources_path=args.sources, out_dir=args.out_dir, only_urls=args.only_urls)
            print("\n--- Ingestion Summary ---")
            for k, v in summary.items():
                if v > 0:
                    print(f"  {k}: {v}")
    finally:
        ing.close()
    sys.exit(0)
