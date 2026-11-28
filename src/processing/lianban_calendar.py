"""连板网交易日历里的三星事件，转成 Google News 检索 query。

早报要回答的是「昨天盘后到今早，哪些数据与政策落了地」。连板网日历页按
星级标注事件的必看程度，三星是它自己认定「必看」的那一档。这里只取前一日
09:00 之后的三星：09:00 之前的事件，前一日早报已经覆盖过，再报一次是重复。

为什么转成 query 而不是在板块里印一行事件名：读者要的是「这个数据出来后市场
怎么解读」，不是「昨天有个数据」。事件名本身不是新闻，检索回来的报道才是。

解析按 class 定位，不按序号——站点改版时 class 比位置稳定。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
# 日历页只保留「今天及以后」：次日再抓，前一天那一整块已经不在了。所以当天跑的
# 时候先把今天的三星落盘，次日读这份存档。runner 每次都是全新的，靠 workflow 里
# 的 actions/cache 把它带过 run。
CALENDAR_DIR = Path("data/calendar")


def save_events(events: List[Dict[str, Any]], day: str, root: Path = CALENDAR_DIR) -> bool:
    """把某天的三星落盘，供次日早报读。写不进去只丢一天，不抛。"""
    if not events:
        return False
    try:
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        (root / f"{day}.json").write_text(
            json.dumps({"date": day, "events": events}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        return True
    except Exception as exc:  # noqa: BLE001 - 落盘失败只影响明天
        logger.warning("日历落盘失败（%s）：%s", day, exc)
        return False


def load_events(day: str, root: Path = CALENDAR_DIR) -> List[Dict[str, Any]]:
    """读某天的三星存档。没有就是没有，不猜、不拿别的日子顶。"""
    path = Path(root) / f"{day}.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - 坏档按没有处理
        logger.warning("日历存档读不出（%s）：%s", day, exc)
        return []
    events = payload.get("events") if isinstance(payload, dict) else None
    return [
        event
        for event in events or []
        if isinstance(event, dict) and event.get("name")
    ]


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


async def fetch_page(client) -> str:
    """抓一次日历页。当天落盘和昨日兜底共用同一份，不重复请求。"""
    resp = await client.get(CALENDAR_URL, headers={"User-Agent": UA})
    resp.raise_for_status()
    return resp.text


async def fetch_calendar(client) -> Optional[str]:
    """抓一次日历页；取不到返回 ``None``。

    ``None`` 与「页面取到、但没有三星事件」是两件事：前者不知道那天有没有事件，
    后者是确定的「没有」。以前两者都返回空串，早报日志就把「没取到」讲成「没有」。
    """
    try:
        return await fetch_page(client)
    except Exception as exc:  # noqa: BLE001 - 少一份日历，不能拖垮早报
        logger.warning("连板网日历取不到：%s", exc)
        return None


def archive_exists(day: str, root: Path = CALENDAR_DIR) -> bool:
    """那天有没有留过存档。

    没有存档时，「无事件」只说明第二天没东西可读，不说明那天真的没有三星事件。
    """
    try:
        return (Path(root) / f"{day}.json").is_file()
    except OSError:
        return False


def calendar_note(
    day: str, count: int, page_ok: bool, archived: bool
) -> Tuple[str, str]:
    """日志该写哪一种「没有」——三种情形不许共用一句话。

    * ``count`` 有数：正常注入；
    * 页面取到了、或存档在：这时说「无事件」是确定的结论；
    * 页面取不到、也没有存档：这次只是没取到，不能据此判断那天没有事件。
    """
    if count:
        return "dim", f"日历事件进检索：{day} {count} 条"
    if page_ok or archived:
        return "dim", f"日历无 {day} 三星事件，跳过注入"
    return (
        "yellow",
        f"日历页取不到、{day} 也没有存档：本次未注入，不能据此判断昨日无事件",
    )


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
