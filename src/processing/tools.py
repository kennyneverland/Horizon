"""Built-in tools available to enrichment blocks."""

import asyncio
from dataclasses import dataclass
from datetime import timezone
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from ddgs import DDGS

from ..models import ContentItem
from .history import HistorySearchTool

logger = logging.getLogger(__name__)

# Cap every lookup so a dead search backend cannot stall the enrichment stage.
_WEB_SEARCH_TIMEOUT_SEC = 12.0
_TAVILY_ENDPOINT = "https://api.tavily.com/search"


@dataclass(frozen=True)
class ToolResult:
    request_id: str
    block_id: str
    tool: str
    results: list[dict[str, str]]


class WebSearchTool:
    """Web search backed by Tavily, with DuckDuckGo as a fallback.

    DuckDuckGo aggressively rate-limits datacenter IP ranges such as GitHub
    Actions runners and returns empty results after long retries, so Tavily is
    used whenever ``TAVILY_API_KEY`` is present.
    """

    name = "web_search"

    async def execute(self, arguments: dict[str, Any]) -> list[dict[str, str]]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("web_search requires a non-empty query")

        query = query.strip()
        api_key = os.getenv("TAVILY_API_KEY")
        if api_key:
            return await self._tavily(query, api_key)
        return await self._duckduckgo(query)

    async def _tavily(self, query: str, api_key: str) -> list[dict[str, str]]:
        """Query the Tavily search API, which works from datacenter IPs."""
        try:
            async with httpx.AsyncClient(timeout=_WEB_SEARCH_TIMEOUT_SEC) as client:
                response = await client.post(
                    _TAVILY_ENDPOINT,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "query": query,
                        "max_results": 3,
                        "search_depth": "basic",
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            logger.warning("web_search (Tavily) failed for %r: %s", query, exc)
            return []

        return [
            {
                "title": str(result.get("title", "")),
                "url": str(result.get("url", "")),
                "text": str(result.get("content", "")),
            }
            for result in (payload.get("results") or [])
            if result.get("url")
        ]

    async def _duckduckgo(self, query: str) -> list[dict[str, str]]:
        """Fallback backend used when no Tavily key is configured."""
        try:
            raw = await asyncio.wait_for(
                asyncio.to_thread(DDGS().text, query, max_results=3),
                timeout=_WEB_SEARCH_TIMEOUT_SEC,
            )
        except Exception as exc:
            logger.warning("web_search (DuckDuckGo) failed for %r: %s", query, exc)
            return []
        return [
            {
                "title": str(result.get("title", "")),
                "url": str(result.get("href", "")),
                "text": str(result.get("body", "")),
            }
            for result in (raw or [])
            if result.get("href")
        ]


class ToolRegistry:
    """Small allowlisted registry for executable profile tools."""

    def __init__(self, summaries_dir: Path | None = None):
        self._tools = {
            WebSearchTool.name: WebSearchTool(),
            HistorySearchTool.name: HistorySearchTool(summaries_dir),
        }

    @property
    def names(self) -> set[str]:
        return set(self._tools)

    async def execute(
        self,
        request_id: str,
        block_id: str,
        tool: str,
        arguments: dict[str, Any],
        current_item: ContentItem | None = None,
    ) -> ToolResult:
        try:
            implementation = self._tools[tool]
        except KeyError as exc:
            raise ValueError(f"Unknown enrichment tool: {tool}") from exc
        if isinstance(implementation, HistorySearchTool) and current_item is not None:
            results = await implementation.execute(
                arguments,
                before=current_item.published_at.astimezone(timezone.utc).date(),
                exclude_url=str(current_item.url),
            )
        else:
            results = await implementation.execute(arguments)
        return ToolResult(
            request_id=request_id,
            block_id=block_id,
            tool=tool,
            results=results,
        )
