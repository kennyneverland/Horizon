"""Pre-market brief from lianban's morning page.

The page is server-rendered, so one GET carries every block: overseas
indices, the overnight US → A-share theme map, exchange alerts and today's
calendar. Only the calendar is printed by the digest now — the tape moved to
Sina, which answers on weekends and carries no browse quota.

Timing matters more than parsing here. The page starts refreshing at 06:00
Beijing and is not finalised until 09:25, while the digest runs at 08:00 and
also runs on weekends. Unlocks, ex-rights dates and macro prints are published
days ahead, so they are whole at 08:00; the morning headlines and the exchange
alerts keep changing until 09:25, and neither is printed. Every fetch is still
checked against the snapshot date on the page: on a Saturday the page still
carries Friday's snapshot, and a stale calendar is worse than none.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

PREMARKET_URL = "https://lianban.net/zaopan.html"
TIMEOUT_SECONDS = 20.0
# The page stamps its snapshot in Beijing time; the digest's own date is UTC.
CST = timezone(timedelta(hours=8))
_SNAPSHOT_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*早盘情报快照")
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
# The macro line sits ahead of the ticker chips: 「🌍 中国 贷款市场报价利率(LPR)、…」
_EVENTS_RE = re.compile(r"今日日历</b>\s*<i>[^<]*</i>\s*<div class=\"pmc\">(.*?)</div>", re.S)


def _plain(raw: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()


def parse(page: str) -> Dict[str, Any]:
    """Split the rendered page into the blocks the digest may print."""
    brief: Dict[str, Any] = {
        "snapshot": "",
        "events": "",
        "indices": [],
        "mapping": [],
        "alerts": [],
        "calendar": [],
    }
    stamp = _SNAPSHOT_RE.search(page)
    if stamp:
        brief["snapshot"] = stamp.group(1)
    events = _EVENTS_RE.search(page)
    if events:
        brief["events"] = _plain(events.group(1))
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


async def fetch_premarket(
    url: str = PREMARKET_URL, expect_date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """One GET per run; any failure returns None and the digest drops the block.

    A retry spends another request against an endpoint that already answers 429
    when asked too often, and a missing calendar is not worth a blocked digest.
    A snapshot dated for another day is dropped as well: the cron runs every
    day, so a Saturday run would otherwise print Friday's calendar as today's.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            brief = parse(response.text)
    except Exception as exc:  # noqa: BLE001 - the block is optional
        logger.warning("Pre-market brief unavailable: %s", exc)
        return None
    if not brief["indices"] and not brief["mapping"] and not brief["calendar"]:
        logger.warning("Pre-market brief parsed empty; block skipped")
        return None
    expected = expect_date or datetime.now(CST).strftime("%Y-%m-%d")
    if brief["snapshot"] != expected:
        logger.warning(
            "Pre-market brief is dated %s, expected %s; block skipped",
            brief["snapshot"] or "(no date on page)",
            expected,
        )
        return None
    logger.warning(
        "Pre-market brief %s: %d indices, %d mappings, %d alerts, %d calendar",
        brief["snapshot"],
        len(brief["indices"]),
        len(brief["mapping"]),
        len(brief["alerts"]),
        len(brief["calendar"]),
    )
    return brief
