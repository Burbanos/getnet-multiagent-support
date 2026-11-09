"""External web search tool using ddgs / DuckDuckGo."""
import logging
from typing import Any

from src.config import settings
from src.core.log_context import exc_brief

logger = logging.getLogger("multiagent.search")


def web_search_tool(query: str, max_results: int = 3) -> dict[str, Any]:
    """Execute external search for real-time information with graceful fallback on failure."""
    logger.info(f"Executing web search (query_chars={len(query)})")
    results_list: list[dict[str, str]] = []

    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        timeout = getattr(settings, "DDGS_TIMEOUT", 8)
        with DDGS(timeout=timeout) as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for item in raw_results:
                title = item.get("title", "").strip()
                snippet = item.get("body", item.get("snippet", "")).strip()
                url = item.get("href", item.get("url", "")).strip()
                if title or snippet:
                    results_list.append({
                        "title": title,
                        "snippet": snippet,
                        "url": url
                    })

        if not results_list:
            logger.warning("DuckDuckGo returned no results")
            return {
                "status": "unavailable",
                "query": query,
                "count": 0,
                "results": [],
                "message": "Nenhum resultado recente encontrado na busca pública para esta consulta."
            }

        return {
            "status": "success",
            "query": query,
            "count": len(results_list),
            "results": results_list
        }

    except Exception as exc:  # noqa: BLE001 - Web search must catch all network/service exceptions
        logger.warning(f"DuckDuckGo search error: {exc_brief(exc)}. Returning unavailable status.")
        return {
            "status": "unavailable",
            "query": query,
            "count": 0,
            "results": [],
            "message": "O serviço de busca na web está temporariamente indisponível no momento. Por favor, tente novamente mais tarde."
        }
