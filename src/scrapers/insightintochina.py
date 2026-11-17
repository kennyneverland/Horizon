"""Scrape InsightIntoChina's public A-share research summaries.

The site publishes English write-ups of Chinese brokerage research (CITIC,
Tianfeng, Guosheng, Shenwan Hongyuan and others) but exposes no RSS endpoint.
The homepage lists the latest ``/publish/<slug>`` links; each article page
carries schema.org WebPage JSON-LD with ``datePublished`` and a short preview
body split into "What Happened" and "Bottom Line", with the covered ticker in
the byline.

The scraper reads the homepage list, fetches each article page concurrently,
and emits one ContentItem per article. Articles older than the collection
window are dropped before any AI work happens. One failed article is skipped
without aborting the batch; a failed homepage request is reported as a source
failure so the rest of the run continues.
"""

from __future__ import annotations

import asyncio
import hashlib
import html as html_lib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import urljoin

import httpx

from .base import BaseScraper, FetchResult
from ..models import ContentItem, InsightIntoChinaConfig, SourceType

logger = logging.getLogger(__name__)

BASE_URL = "https://www.insightintochina.com"
USER_AGENT = (
    "Mozilla/5.0 (compatible; HorizonDigest/1.0; "
    "+https://github.com/kennyneverland/Horizon)"
)
MAX_CONCURRENT_ARTICLES = 4
MAX_BODY_CHARS = 3000

# Accept both the relative form the site serves today (``href="/publish/x"``)
# and an absolute or single-quoted variant, so a markup tweak cannot silently
# reduce the list to zero.
_ARTICLE_LINK_RE = re.compile(
    r"""href=["'](?:https?://(?:www\.)?insightintochina\.com)?(/publish/[A-Za-z0-9_\-]+)["']"""
)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
_SECTION_RE = re.compile(r"<h2[^>]*>(.*?)</h2>\s*<p[^>]*>(.*?)</p>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_LDJSON_RE = re.compile(
    r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S
)
_TICKER_RE = re.compile(r"\$(\d{6}\.(?:SZ|SH|BJ)|\d{4,5}\.HK)")
_BYLINE_RE = re.compile(
    r'class="iic-ssr-meta"[^>]*>\s*(Bullish|Bearish|Neutral)\b', re.I
)
_BYLINE_FALLBACK_RE = re.compile(r"\b(Bullish|Bearish|Neutral)\s*·", re.I)


def _text(fragment: str) -> str:
    """Strip tags, decode entities, and collapse whitespace in one fragment."""
    plain = html_lib.unescape(_TAG_RE.sub(" ", fragment))
    return re.sub(r"\s+", " ", plain).strip()


class InsightIntoChinaScraper(BaseScraper):
    """Scraper for InsightIntoChina's public research list."""

    SOURCE_TYPE = SourceType.INSIGHT_INTO_CHINA

    def __init__(
        self,
        config: InsightIntoChinaConfig,
        http_client: httpx.AsyncClient,
    ):
        """Initialize the scraper.

        Args:
            config: InsightIntoChina source configuration.
            http_client: Shared async HTTP client.
        """
        super().__init__({"insightintochina": config}, http_client)
        self.cfg = config

    async def fetch(self, since: datetime) -> FetchResult:
        result = FetchResult()
        if self.cfg.enabled:
            await result.collect("latest", self._fetch_articles(since))
        return result

    async def _fetch_articles(self, since: datetime) -> List[ContentItem]:
        """Read the homepage list and fetch each listed article."""
        paths: List[str] = []
        last_size = 0
        for attempt in range(2):
            response = await self.client.get(
                BASE_URL + "/", follow_redirects=True, headers={"User-Agent": USER_AGENT}
            )
            response.raise_for_status()
            last_size = len(response.text)
            for match in _ARTICLE_LINK_RE.finditer(response.text):
                path = match.group(1)
                if path not in paths:
                    paths.append(path)
            if paths:
                break
            if attempt == 0:
                # The list page sometimes answers 200 with a shell while it
                # redeploys. On 2026-11-17 that cost the whole source for a run;
                # one retry recovers it instead of dropping to zero articles.
                logger.warning(
                    "InsightIntoChina homepage returned no article links "
                    "(%d bytes); retrying in 3s",
                    last_size,
                )
                await asyncio.sleep(3.0)

        paths = paths[: max(0, self.cfg.max_articles)]
        if not paths:
            raise ValueError(
                "InsightIntoChina homepage listed no articles "
                f"({last_size} bytes)"
            )

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_ARTICLES)

        async def fetch_one(path: str) -> Optional[ContentItem]:
            async with semaphore:
                try:
                    return await self._fetch_article(path, since)
                except Exception as exc:  # noqa: BLE001 - one bad article must not fail the batch
                    logger.warning(
                        "Skipping InsightIntoChina article %s: %s", path, exc
                    )
                    return None

        items = await asyncio.gather(*(fetch_one(path) for path in paths))
        return [item for item in items if item is not None]

    async def _fetch_article(
        self, path: str, since: datetime
    ) -> Optional[ContentItem]:
        """Map one article page into a ContentItem, or None when it is stale."""
        url = urljoin(BASE_URL, path)
        response = await self.client.get(
            url, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
        html = response.text

        published = self._published_at(html)
        if published is None or published < self._ensure_utc(since):
            return None

        title = self._title(html)
        if not title:
            return None

        metadata: dict[str, Any] = {
            "source_name": "InsightIntoChina",
            "feed_name": "InsightIntoChina",
            "category": self.cfg.category,
        }
        tickers = sorted(set(_TICKER_RE.findall(html)))
        if tickers:
            metadata["tickers"] = tickers
        direction = self._direction(html)
        if direction:
            metadata["broker_direction"] = direction

        slug = path.rstrip("/").rsplit("/", 1)[-1]
        entry_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

        return ContentItem(
            id=self._generate_id("insightintochina", slug, entry_hash),
            source_type=self.SOURCE_TYPE,
            title=title,
            url=url,
            content=self._body(html) or None,
            author="InsightIntoChina",
            published_at=published,
            profile=self.cfg.profile,
            metadata={key: value for key, value in metadata.items() if value is not None},
        )

    @staticmethod
    def _published_at(html: str) -> Optional[datetime]:
        """Read ``datePublished`` from the page's schema.org JSON-LD."""
        for match in _LDJSON_RE.finditer(html):
            try:
                payload = json.loads(match.group(1))
            except ValueError:
                continue
            if not isinstance(payload, dict):
                continue
            nodes = payload.get("@graph")
            if not isinstance(nodes, list):
                nodes = [payload]
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                raw = node.get("datePublished") or node.get("dateModified")
                if not raw:
                    continue
                try:
                    moment = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                except ValueError:
                    continue
                return moment.astimezone(timezone.utc)
        return None

    @staticmethod
    def _title(html: str) -> str:
        match = _H1_RE.search(html)
        if match:
            title = _text(match.group(1))
            if title:
                return title
        match = re.search(
            r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html
        )
        return _text(match.group(1)) if match else ""

    @staticmethod
    def _body(html: str) -> str:
        """Join the "What Happened" / "Bottom Line" sections into plain text."""
        sections: List[str] = []
        for match in _SECTION_RE.finditer(html):
            heading = _text(match.group(1))
            content = _text(match.group(2))
            if heading and content:
                sections.append(f"{heading}: {content}")
        return "\n".join(sections)[:MAX_BODY_CHARS]

    @staticmethod
    def _direction(html: str) -> Optional[str]:
        """Read the broker stance from the byline when it is stated."""
        match = _BYLINE_RE.search(html) or _BYLINE_FALLBACK_RE.search(html)
        return match.group(1).lower() if match else None

    @staticmethod
    def _ensure_utc(moment: datetime) -> datetime:
        if moment.tzinfo is None:
            return moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)
