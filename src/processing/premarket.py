"""Pre-market brief: the morning page's tape and headlines, the calendar's day.

Two pages, two jobs. ``zaopan.html`` is the 09:25 snapshot — the overnight US
tape, the ticker → A-share theme map and the morning headlines. The map is
lianban's own and is ordered by that day's heat, which is why it is read here
instead of rebuilt from a fixed ticker list: the themes are the ones the site
itself put behind each move, and the heat rank says whether the theme actually
showed up on the board that day.

``calendar.html`` is the only source for today's calendar — new listings,
ex-rights dates and unlocks with the amount or the plan attached, plus the
three-star macro prints. The morning page carries a calendar of its own, but
only unlocks and without the amounts, so it is not read for that any more.

Timing matters more than parsing here. The morning page starts refreshing at
06:00 Beijing and is not finalised until 09:25, while the digest runs at 09:30
and also runs on weekends. The calendar page is published days ahead and keeps
today's group through the session, so a 09:30 run sees the whole day. The
morning snapshot is checked against its own date instead: on a Saturday it
still carries Friday's, and a stale tape or headline list is worse than none.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

PREMARKET_URL = "https://lianban.net/zaopan.html"
TIMEOUT_SECONDS = 20.0
SITE_ROOT = "https://lianban.net"
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
# 映射里的题材是带热度排名的：<a href="/ticai/ccxp-99bb.html">存储芯片 <i class="pmrk">当日热度第85</i></a>
_THEME_LINK_RE = re.compile(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.S)
_THEME_RANK_RE = re.compile(r'<i class="pmrk">([^<]*)</i>', re.S)
_RANK_NUM_RE = re.compile(r"第\s*(\d+)")
# 早间要闻：<div class="pmr"><span class="tm mono">09:09</span><i class="g">利好</i><a class="nlk" href="/haochu.html#h1">标题</a></div>
_NEWS_RE = re.compile(
    r'<div class="pmr"><span class="tm mono">([^<]*)</span><i class="([a-z]+)">([^<]*)</i>'
    r'<a class="nlk" href="([^"]*)">(.*?)</a></div>',
    re.S,
)

# 日历页按 <div class="cald" data-d="YYYY-MM-DD"> 分组，可以按日期精确取当天那一组，
# 不必把未来三周都读进来。当天的组带 today 类：<div class="cald today" data-d="...">。
CALENDAR_URL = "https://lianban.net/calendar.html"
_CAL_DAY_SPLIT = re.compile(r'<div class="cald[^"]*" data-d="(\d{4}-\d{2}-\d{2})">')
# g3 = 三星（必看），g2 = 二星。只要 g3：二星几乎全是央行官员讲话。
_CAL_MACRO_RE = re.compile(
    r'<div class="cmr g3">\s*<span class="ct mono">([^<]*)</span>\s*'
    r'<span class="cg">[^<]*</span>\s*<b>(.*?)</b>',
    re.S,
)
_CAL_GROUP_RE = re.compile(
    r'<div class="csgl">\s*([^<]*)<b>\d+</b>\s*</div>\s*<div class="csgc">(.*?)</div>',
    re.S,
)
# 条目：<span class="cse" data-stk="603192" data-nm="汇得科技">汇得科技<em>0.1亿元</em><u>今年4板</u></span>
# <em> 才是这三类日历的用处所在：解禁规模与占流通比、每10股派X元、新股发行价。
_CAL_ITEM_RE = re.compile(
    r'<span class="cse" data-stk="(\d{6})" data-nm="([^"]+)">(.*?)</span>', re.S
)
_CAL_NOTE_RE = re.compile(r"<em>(.*?)</em>", re.S)
_CATEGORY_EMOJI_RE = re.compile(r"^[^\w\u4e00-\u9fff]+")
_LEAD_SYMBOL_RE = re.compile(r"^[^\w\u4e00-\u9fff]+")


def _plain(raw: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()


def _meaningful_event(text: str) -> bool:
    """False for a macro line that names no event.

    The upstream feed sometimes ships only the region twice — 「中国台湾 台湾」,
    「中国澳门 澳门」, 「中国香港 香港」 — which reads as a duplicate and tells the
    reader nothing. A two-part line whose second half just repeats the tail of
    the first is dropped; 「美国 M2」 and 「美国 PCE物价指数」 survive.
    """
    text = _LEAD_SYMBOL_RE.sub("", str(text or "")).strip()
    if not text:
        return False
    parts = text.split()
    if len(parts) == 2:
        region, event = parts
        if event == region or (len(event) <= 2 and region.endswith(event)):
            return False
    return True


def _theme(raw: str) -> Optional[Dict[str, Any]]:
    """One theme link → name plus the heat rank lianban printed beside it."""
    match = _THEME_RANK_RE.search(raw)
    name = _plain(_THEME_RANK_RE.sub("", raw))
    if not name:
        return None
    rank = 0
    if match:
        number = _RANK_NUM_RE.search(match.group(1))
        if number:
            rank = int(number.group(1))
    return {"name": name, "rank": rank}


def parse_calendar(page: str, today: str) -> Optional[Dict[str, Any]]:
    """The calendar page's block for one date, or ``None`` when it has none.

    The site drops a day from that page once it is over, so a run after the
    close gets nothing here — and nothing is what the block then prints, since
    the morning page's own list is not a substitute for it.
    """
    parts = _CAL_DAY_SPLIT.split(page)
    for index in range(1, len(parts) - 1, 2):
        if parts[index] != today:
            continue
        body = parts[index + 1]
        events = []
        for clock, name in _CAL_MACRO_RE.findall(body):
            label = _plain(name)
            if not _meaningful_event(label):
                continue
            clock = clock.strip()
            events.append(f"{clock} {label}" if clock else label)
        calendar = []
        for raw_tag, inner in _CAL_GROUP_RE.findall(body):
            tag = _CATEGORY_EMOJI_RE.sub("", _plain(raw_tag)).strip()
            if not tag:
                continue
            for code, name, cell in _CAL_ITEM_RE.findall(inner):
                note = _CAL_NOTE_RE.search(cell)
                calendar.append(
                    {
                        "code": code,
                        "name": _plain(name),
                        "tag": tag,
                        "note": _plain(note.group(1)) if note else "",
                    }
                )
        return {"events": " ｜ ".join(events), "calendar": calendar}
    return None


def parse(page: str) -> Dict[str, Any]:
    """Split the morning page into the blocks the digest may print."""
    brief: Dict[str, Any] = {
        "snapshot": "",
        "indices": [],
        "mapping": [],
        "news": [],
    }
    stamp = _SNAPSHOT_RE.search(page)
    if stamp:
        brief["snapshot"] = stamp.group(1)
    for name, pct in _INDEX_RE.findall(page):
        brief["indices"].append({"name": name.strip(), "pct": pct})
    for _tone, pct, ticker, rest in _MAP_RE.findall(page):
        themes = [row for row in (_theme(raw) for _href, raw in _THEME_LINK_RE.findall(rest)) if row]
        brief["mapping"].append(
            {"us": ticker.strip(), "pct": pct, "themes": themes}
        )
    for clock, tone_class, tone, href, title in _NEWS_RE.findall(page):
        title = _plain(title)
        if not title:
            continue
        url = href if href.startswith("http") else SITE_ROOT + href
        brief["news"].append(
            {
                "time": clock.strip(),
                "tone": _plain(tone) or ("利空" if tone_class == "b" else "利好"),
                "url": url,
                "title": title,
            }
        )
    return brief


async def fetch_premarket(
    url: str = PREMARKET_URL, expect_date: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Two GETs per run; any failure drops only the block that source fed.

    A retry spends another request against an endpoint that already answers 429
    when asked too often, and a missing block is not worth a blocked digest.
    """
    today = expect_date or datetime.now(CST).strftime("%Y-%m-%d")
    brief: Optional[Dict[str, Any]] = None
    day: Optional[Dict[str, Any]] = None
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=HEADERS)
            response.raise_for_status()
            brief = parse(response.text)
        except Exception as exc:  # noqa: BLE001 - the block is optional
            logger.warning("Pre-market brief unavailable: %s", exc)
        # 日历只认日历页：早盘页那份只有限售解禁、没有金额，不再当兜底。
        try:
            calendar_response = await client.get(CALENDAR_URL, headers=HEADERS)
            calendar_response.raise_for_status()
            day = parse_calendar(calendar_response.text, today)
        except Exception as exc:  # noqa: BLE001 - 少一个源不该让别的块消失
            logger.warning("Calendar page unavailable: %s", exc)
            day = None

    if brief is None:
        brief = {"snapshot": "", "indices": [], "mapping": [], "news": []}
    brief["events"] = (day or {}).get("events", "")
    brief["calendar"] = (day or {}).get("calendar", [])

    # 早盘页挂着前一天的快照时，它那份盘面、映射和要闻一起作废；日历页是按
    # data-d 精确取的当天组，与快照无关，可以留下。
    if brief["snapshot"] and brief["snapshot"] != today:
        logger.warning(
            "Pre-market brief is dated %s, expected %s; dropping the morning page",
            brief["snapshot"],
            today,
        )
        brief["snapshot"] = ""
        brief["indices"], brief["mapping"], brief["news"] = [], [], []

    if not any(
        (brief["indices"], brief["mapping"], brief["news"], brief["events"], brief["calendar"])
    ):
        logger.warning("Pre-market brief parsed empty; block skipped")
        return None
    logger.warning(
        "Pre-market brief %s: %d indices, %d mappings, %d news, %d calendar",
        brief["snapshot"] or "(calendar only)",
        len(brief["indices"]),
        len(brief["mapping"]),
        len(brief["news"]),
        len(brief["calendar"]),
    )
    return brief
