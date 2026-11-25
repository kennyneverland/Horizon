"""连板网交易日历里的三星事件，转成 Google News 检索 query。

早报要回答的是「昨天盘后到今早，哪些数据与政策落了地」。连板网日历页按
星级标注事件的必看程度，三星是它自己认定「必看」的那一档。这里只取前一日
09:00 之后的三星：09:00 之前的事件，前一日早报已经覆盖过，再报一次是重复。

为什么转成 query 而不是在板块里印一行事件名：读者要的是「这个数据出来后市场
怎么解读」，不是「昨天有个数据」。事件名本身不是新闻，检索回来的报道才是。

解析按 class 定位，不按序号——站点改版时 class 比位置稳定。
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from ..models import GoogleNewsConfig

logger = logging.getLogger(__name__)

CALENDAR_URL = "https://lianban.net/calendar.html"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
# 一天一块：<div class="cald today" data-d="2026-11-25">
_DAY_SPLIT = re.compile(r'<div class="cald[^"]*" data-d="')
# 三星一行：<div class="cmr g3"><span class="ct mono">21:30</span>
#          <span class="cg">⭐⭐⭐</span><b>美国 PCE物价指数</b><a>证券</a></div>
_STAR_RE = re.compile(
    r'<div class="cmr g3"><span class="ct mono">([^<]*)</span>'
    r'<span class="cg">[^<]*</span><b>([^<]+)</b>(.*?)</div>',
    re.S,
)
_LINK_RE = re.compile(r"<a[^>]*>([^<]+)</a>")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
# 同一份数据的另一个口径：核心 PCE 与 PCE 来自同一份报告，只是去不去食品能源。
# 判断「是不是同一份数据」时先抹掉这些修饰，检索时也只发一个更通用的 query。
_VARIANT_RE = re.compile(r"核心|初值|终值|修正值?|季调|年化|环比|同比")

# 09:00 是分界线：更早的事件在前一日早报里已经出现过。
CUTOFF = "09:00"
# 一天三星通常 2-3 条；上限设 4，避免某天异常多时把抓取时间拖长。
MAX_QUERIES = 4
RESULTS_PER_QUERY = 5


def _clean(raw: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw or "")).strip()


def _name_ok(name: str) -> bool:
    """站点部分条目名称残缺，如「中国台湾 台湾」——指标名丢了。

    判断方式：末段是地区名且已经出现在首段里，说明站点只给了地区没给指标。
    这类条目检索不出东西，印出来也只是一行没有信息量的字。
    """
    parts = name.split()
    if len(parts) >= 2 and parts[-1] and parts[-1] in parts[0]:
        return False
    return len(name) >= 4


def _canonical(name: str) -> str:
    """去掉「核心」「初值」这类口径修饰，用来判断两个事件是不是同一份数据。"""
    return _VARIANT_RE.sub("", name).replace(" ", "").strip()


def parse(page: str, day: str, cutoff: str = CUTOFF) -> List[Dict[str, Any]]:
    """某一天 ``cutoff`` 之后的三星事件。

    Args:
        page: 日历页 HTML。
        day: ``YYYY-MM-DD``。
        cutoff: 早于这个时刻的条目不要。

    Returns:
        ``[{"date", "time", "name", "themes"}]``，按页面顺序。
    """
    blocks = _DAY_SPLIT.split(page or "")
    out: List[Dict[str, Any]] = []
    for block in blocks[1:]:
        if block[:10] != day:
            continue
        body = block.split('<div class="cald', 1)[0]
        for time, name, rest in _STAR_RE.findall(body):
            time = time.strip()
            name = _clean(name)
            if not _TIME_RE.match(time) or time < cutoff:
                continue
            if not _name_ok(name):
                logger.info("日历事件名称残缺，跳过：%s", name)
                continue
            out.append(
                {
                    "date": day,
                    "time": time,
                    "name": name,
                    "themes": [_clean(x) for x in _LINK_RE.findall(rest)],
                }
            )
        break
    return out


async def fetch_events(client, day: str, cutoff: str = CUTOFF) -> List[Dict[str, Any]]:
    """抓日历页并解析。取不到就返回空，早报照常出。"""
    try:
        resp = await client.get(CALENDAR_URL, headers={"User-Agent": UA})
        resp.raise_for_status()
        return parse(resp.text, day, cutoff)
    except Exception as exc:  # noqa: BLE001 - 少一份日历，不能拖垮早报
        logger.warning("连板网日历取不到（%s）：%s", day, exc)
        return []


def to_queries(
    events: List[Dict[str, Any]], max_queries: int = MAX_QUERIES
) -> List[GoogleNewsConfig]:
    """事件 → Google News query，同一份数据的多个口径只发一个。

    核心 PCE 与 PCE 来自同一份报告，标题里都带「PCE」：分成两个 query 搜，
    召回的报道高度重叠，去重那一步要多处理一倍条目，边际收益很低。所以先按
    抹掉口径修饰后的名字归并，再用更通用的那个名字去搜——它同时能命中核心
    口径的报道，反过来则不行。
    """
    out: List[GoogleNewsConfig] = []
    seen: set[str] = set()
    for event in events:
        name = str(event.get("name") or "").strip()
        if not name:
            continue
        key = _canonical(name)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(
            GoogleNewsConfig(
                enabled=True,
                query=key,
                language="zh-CN",
                country="CN",
                ceid="CN:zh-Hans",
                max_results=RESULTS_PER_QUERY,
                category="finance",
                profile="finance-news",
            )
        )
        if len(out) >= max_queries:
            break
    return out
