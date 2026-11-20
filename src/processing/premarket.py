"""Pre-market brief from lianban's morning page.

The page is server-rendered, so one GET carries every block: overseas
indices, the overnight US → A-share theme map, exchange alerts and today's
calendar. It is printed as backdrop and never as a pick. Across the five
sessions to 2026-11-20, none of the thirty mapped themes reached the top 100
of lianban's own heat board (median rank 575), so a reader who traded the map
would have been wrong every day. The digest therefore shows the tape and the
map, and says so in one line.
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

PREMARKET_URL = "https://lianban.net/zaopan.html"
TIMEOUT_SECONDS = 20.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}

_INDEX_RE = re.compile(
    r'<span class="pmi"><b>([^<]+)</b><em class="[a-z ]*mono">([+-]?[\d.]+%)</em></span>'
)
_MAP_RE = re.compile(
    r'<div class="pmr"><b class="mono ([a-z]+)">([+-]?[\d.]+%)</b>\s*([^<]+?)\s*'
    r'<span class="arr">→</span>\s*(.*?)</div>',
    re.S,
)
_THEME_RE = re.compile(r"<a[^>]*>([^<]+)</a>")
_ALERT_RE = re.compile(
    r'<span class="pmk warn" data-stk="(\d{6})" data-nm="([^"]+)">[^<]*<i>([^<]+)</i></span>'
)
_CALENDAR_RE = re.compile(
    r'<span class="pmk" data-stk="(\d{6})" data-nm="([^"]+)"><i>([^<]+)</i>[^<]*<i>([^<]+)</i></span>'
)


def _plain(raw: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()


def parse(page: str) -> Dict[str, Any]:
    """Split the rendered page into the four blocks the digest may print."""
    brief: Dict[str, Any] = {
        "indices": [],
        "mapping": [],
        "alerts": [],
        "calendar": [],
    }
    for name, pct in _INDEX_RE.findall(page):
        brief["indices"].append({"name": name.strip(), "pct": pct})
    for _tone, pct, ticker, rest in _MAP_RE.findall(page):
        brief["mapping"].append(
            {
                "us": ticker.strip(),
                "pct": pct,
                "themes": [name.strip() for name in _THEME_RE.findall(rest)],
            }
        )
    for code, name, note in _ALERT_RE.findall(page):
        brief["alerts"].append(
            {"code": code, "name": _plain(name), "note": _plain(note)}
        )
    for code, name, tag, note in _CALENDAR_RE.findall(page):
        brief["calendar"].append(
            {"code": code, "name": _plain(name), "tag": _plain(tag), "note": _plain(note)}
        )
    return brief


async def fetch_premarket(url: str = PREMARKET_URL) -> Optional[Dict[str, Any]]:
    """One GET per run; any failure returns None and the digest drops the block.

    A retry spends another request against an endpoint that already answers 429
    when asked too often, and a missing backdrop is not worth a blocked digest.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            brief = parse(response.text)
    except Exception as exc:  # noqa: BLE001 - the block is optional
        logger.warning("Pre-market brief unavailable: %s", exc)
        return None
    if not brief["indices"] and not brief["mapping"]:
        logger.warning("Pre-market brief parsed empty; block skipped")
        return None
    logger.warning(
        "Pre-market brief: %d indices, %d mappings, %d alerts, %d calendar",
        len(brief["indices"]),
        len(brief["mapping"]),
        len(brief["alerts"]),
        len(brief["calendar"]),
    )
    return brief
