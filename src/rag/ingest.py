"""Ingestion module for official Getnet knowledge sources respecting robots.txt."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import yaml
from bs4 import BeautifulSoup

logger = logging.getLogger("multiagent.rag.ingest")

USER_AGENT = "getnet-multiagent-support-ingest/1.0 (+https://github.com/Burbanos/getnet-multiagent-support)"
ALLOWED_DOMAINS = {"www.getnet.net", "site.getnet.com.br", "www.getnet.com.br"}
MIN_CHARS = 300
STATUSES = {"ok", "robots_disallowed", "http_error", "fetch_error", "no_content", "off_allowlist"}


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

    container = soup.find("main") or soup.find("article") or soup.find("body") or soup
    raw_text = container.get_text("\n")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    text = "\n".join(lines)
    return title, text


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

    def fetch(self, url: str, market: str) -> dict[str, Any]:
        """
        Fetch and parse a single document URL.
        Validates host allowlist, robots.txt, HTTP status, and text content size.
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
            }

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
            }

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
            }

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
            }

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
            }

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
            }

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
        }

    def run(
        self,
        sources_path: str | Path = "data/sources.yaml",
        out_dir: str | Path = "data/corpus",
    ) -> dict[str, int]:
        """
        Process all sources defined in sources.yaml and write corpus records.
        Generates pages.jsonl and manifest.json inside out_dir.
        """
        sources_path = Path(sources_path)
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        sources_bytes = sources_path.read_bytes()
        raw_sources = yaml.safe_load(sources_bytes.decode("utf-8")) or {}
        sources_list = raw_sources.get("sources", []) if isinstance(raw_sources, dict) else []

        counts = {s: 0 for s in STATUSES}
        records = []

        for item in sources_list:
            url = item.get("url", "")
            market = item.get("market", "BR")
            rec = self.fetch(url, market)
            records.append(rec)
            status = rec.get("status", "fetch_error")
            counts[status] = counts.get(status, 0) + 1

        pages_path = out_dir / "pages.jsonl"
        with pages_path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        manifest = {
            "user_agent": self.user_agent,
            "generated_at": datetime.now(UTC).isoformat(),
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

        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        return counts

    def close(self) -> None:
        """Close the underlying HTTP client if owned by this Ingestor."""
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ing = Ingestor()
    try:
        summary = ing.run()
        print("\n--- Ingestion Summary ---")
        for k, v in summary.items():
            if v > 0:
                print(f"  {k}: {v}")
    finally:
        ing.close()
    sys.exit(0)
