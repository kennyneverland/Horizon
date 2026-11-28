"""The evening brief's three buckets, read back by the next morning's digest.

The evening brief answers "where is the money going tomorrow" with three named
buckets — 主线 (running, with continuity), 活跃 (moved today, unproven) and
蓄势 (not moved yet, structure ready). The morning digest answers "what
happened", and it answers it from headline wording alone. The two never met:
on 2026-11-19 the brief named six themes and the 11-20 digest touched one of
them, because a theme the brief called a 主线 only reaches the digest when that
morning happens to carry a matching story.

So the brief is read back here. The page the brief already publishes carries a
``next-day-brief`` JSON block; this module fetches the most recent one before
today and hands the three buckets to the digest, which crosses them with the
day's stories. Nothing here decides anything: it is the same lookup discipline
as the theme index, and a missing page simply means the digest runs as before.

Two things the block is *not* used for. It does not replace the digest's theme
match — a name list from yesterday is not a match for today's headline. And it
does not turn 蓄势 into recommendations: those are stocks that have not moved,
and presenting them as tomorrow's buys is the one reading the brief itself
refuses to make.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from datetime import date as _date
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional

try:  # 包内导入
    from . import session as _session
except ImportError:  # 以单文件方式导入（脚本、独立用例）
    import session as _session  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

BRIEF_URL = "https://kennyneverland.github.io/Horizon/post-market/{date}.html"
BLOCK_RE = re.compile(
    r'<script[^>]*id="next-day-brief"[^>]*>(.*?)</script>', re.S
)
# A long weekend is the widest gap the digest should still look back across;
# beyond that the brief is describing a different week.
LOOKBACK_DAYS = 5
BUCKET_ORDER = ("主线", "活跃", "蓄势")
# 晚报「蓄势」用的是板块名，早报用的是连板网题材库的名字，两套口径字面不通。
# 这张表只收两类对应：晚报自己写明了的（「轻工制造（对应当日题材 家电）」），
# 和一边确实包含另一边的（光刻机 ⊂ 半导体设备）。联想性的对应一律不收——
# 把「通用设备」认成「机器人」会把「无新消息」误报成「有覆盖」，那是假证据。
_BUCKET_BRIDGE = {
    "轻工制造": ("家电", "家用电器"),
    "光刻机（胶）": ("半导体设备", "光刻机"),
    # 下面四条是产业链的上下位，不是联想：晚报点的是产业线（芯片、算力），
    # 早报的题材标签是这条线上的具体环节（设备、封测、液冷、光模块）。不收
    # 它们，「新苗头」会把晚报已经点过的线全部重报一遍——2026-11-20 那行 19
    # 个里有 15 个是这么来的。宽泛且跨行业的标签（阿里概念、蚂蚁金服概念）
    # 仍然不收：它们不对应某一条线，硬归就是造假证据。
    "芯片": ("半导体", "半导体设备", "集成电路", "集成电路制造", "先进封装", "封测"),
    "算力": (
        "数据中心", "AIDC", "云计算", "液冷服务器", "CPO", "光模块",
        "英伟达", "算力租赁",
    ),
    "多元金融": ("证券", "银行", "保险"),
    "AI应用(AI视频)": ("AI智能体", "智能体", "垂直应用软件", "AI视频"),
}
_NOISE_RE = re.compile(r"[（(][^）)]*[）)]|\s+")


def _fold(text: Any) -> str:
    """Drop brackets, spaces and the 概念/板块 suffix so two names can be compared."""
    out = _NOISE_RE.sub("", str(text or ""))
    for suffix in ("概念", "板块", "指数", "行业"):
        if out.endswith(suffix) and len(out) > len(suffix) + 1:
            out = out[: -len(suffix)]
    return out.strip()


def _shift(day: str, back: int) -> str:
    try:
        base = _date.fromisoformat(day)
    except ValueError:
        return ""
    return (base - timedelta(days=back)).isoformat()


def _get(url: str, timeout: float = 20.0) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; HorizonDigest/1.0; "
                "+https://github.com/kennyneverland/Horizon)"
            ),
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            import gzip

            raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def load(
    day: str,
    base: str = BRIEF_URL,
    lookback: int = LOOKBACK_DAYS,
    trading_day: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """The most recent brief published before ``day``, or None.

    ``day`` is the digest's own date. The brief for the previous session is what
    the reader saw last night, so the walk starts one day back and stops at the
    first page that carries the block — a Monday digest reaches back to Friday.

    ``trading_day`` says whether ``day`` itself is a session. On a day the market
    is closed there is no 「今天要关注什么」 to answer: the block would just read
    last night's brief back under a date that never opened (2026-11-28, a
    Saturday, did exactly that). Not passed, the calendar decides: weekends from
    the weekday, weekday holidays from ``session.opened`` — only the limit-up
    pool knows those, and the morning's opening block has already asked it.
    """
    if trading_day is None:
        try:
            trading_day = _date.fromisoformat(day).weekday() < 5
        except (TypeError, ValueError):
            trading_day = True
        # 星期几认不出工作日休市（元旦、国庆）。开盘块当天落了快照就是开市，
        # 没落才问一次东财——问不到（None）时维持星期几的判断，不替它下结论。
        if trading_day and _session.opened(day) is False:
            trading_day = False
    if not trading_day:
        logger.info("next-day brief skipped: %s is not a trading day", day)
        return None
    for back in range(1, lookback + 1):
        target = _shift(day, back)
        if not target:
            return None
        try:
            page = _get(base.format(date=target))
        except Exception as exc:  # noqa: BLE001 - a missing brief is not an error
            logger.info("next-day brief %s unavailable (%s)", target, exc)
            continue
        doc: Optional[Dict[str, Any]] = None
        match = BLOCK_RE.search(page)
        if match:
            try:
                parsed = json.loads(match.group(1))
            except ValueError as exc:
                logger.warning("next-day brief %s is not valid JSON: %s", target, exc)
                parsed = None
            if isinstance(parsed, dict):
                doc = parsed
        if doc is None:
            # 老页面没有 JSON 块。同一份内容就在页面上，按标题结构读一遍，
            # 这样新块上线之前发布的晚报也能用——回验不用等一天。
            doc = _parse_page(page)
        if doc is None:
            continue
        doc["_source_date"] = target
        doc["_gap_days"] = back
        return doc
    logger.info("no next-day brief found within %d days of %s", lookback, day)
    return None


def _related(late_theme: str, morning_theme: str) -> bool:
    """Whether a brief theme and a digest theme are the same line.

    Only two things count: the folded names match, or one contains the other.
    A bridge entry widens that for the buckets the brief labels with a sector
    name, and nothing else does — a wrong join here would credit the digest with
    covering a line it never touched.
    """
    a, b = _fold(late_theme), _fold(morning_theme)
    if not a or not b:
        return False
    if a == b:
        return True
    if a in b or b in a:
        return True
    for alias in _BUCKET_BRIDGE.get(late_theme, ()):  # exact key, not folded
        folded = _fold(alias)
        if folded and (folded == b or folded in b or b in folded):
            return True
    return False


_SECTION_RE = re.compile(
    r"<h2>\s*明日关注\s*·\s*(蓄势|主线|活跃)\s*</h2>(.*?)(?=<h2>|<footer|</main>)",
    re.S,
)
_ITEM_RE = re.compile(r"<div class='wl'>(.*?)</div>\s*(?=<div class='wl'>|</div>|$)", re.S)
_H3_RE = re.compile(r"<h3>(.*?)</h3>", re.S)
_TAG_RE = re.compile(r"<span class='tag'>([^<]*)</span>")
_NAME_RE = re.compile(r"<span class='nm'>([^<]*)</span>")
_BADGE_RE = re.compile(r"^\s*(\d+)\s*家涨停\s*$")


def _parse_page(page: str) -> Optional[Dict[str, Any]]:
    """Read the three buckets out of a page that predates the JSON block.

    Same content, different carrier. The block is preferred because it carries
    the signal line and the stock tags verbatim; this reader exists so a brief
    published before the block shipped is still usable, and so a template change
    that breaks the block degrades to parsing rather than to nothing.
    """
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for bucket, body in _SECTION_RE.findall(page):
        rows = []
        for chunk in _ITEM_RE.findall(body):
            head = _H3_RE.search(chunk)
            if not head:
                continue
            raw = head.group(1)
            theme = re.sub(r"<[^>]+>", "", raw).strip()
            badge = ""
            tag = _TAG_RE.search(raw)
            if tag:
                badge = tag.group(1).strip()
                theme = theme[: -len(badge)].strip() if theme.endswith(badge) else theme
            if not theme:
                continue
            rows.append(
                {
                    "theme": theme,
                    "badge": badge if _BADGE_RE.match(badge) else badge,
                    "signal": "",
                    "stocks": [
                        {"name": name.replace(" ", "").strip(), "tag": ""}
                        for name in _NAME_RE.findall(chunk)
                        if name.strip()
                    ],
                }
            )
        if rows:
            buckets[bucket] = rows
    if not buckets:
        return None
    return {"version": 0, "buckets": buckets, "blocked": []}


def carriers(doc: Optional[Dict[str, Any]], theme_name: str) -> Optional[Dict[str, Any]]:
    """晚报里这条题材的「市场载体」：涨停家数、龙头、逐只成员。

    早报的题材名来自新闻，晚报的题材名来自盘面，两套口径用 ``_related`` 对齐
    （同一套桥接，不另立标准）。对不上就返回 None——不跨题材搬运，是这一层
    唯一的硬约束。

    返回 ``{theme, count, leader, board, movers}``；``theme`` 是晚报那边的名字，
    渲染时要说清楚「市场载体（光刻机（胶）11 家涨停）」，否则读者不知道这个
    括号里的名字和本行标题不是一回事。
    """
    if not doc:
        return None
    leaders = doc.get("leaders") or []
    movers = doc.get("movers") or []
    hit = ""
    for row in leaders:
        if _related(str(row.get("theme") or ""), theme_name):
            hit = str(row.get("theme") or "")
            break
    if not hit:
        for row in movers:
            if _related(str(row.get("theme") or ""), theme_name):
                hit = str(row.get("theme") or "")
                break
    if not hit:
        return None
    lead = next((r for r in leaders if str(r.get("theme") or "") == hit), {})
    rows = [m for m in movers if str(m.get("theme") or "") == hit]
    return {
        "theme": hit,
        "count": lead.get("count"),
        "leader": str(lead.get("leader") or ""),
        "board": str(lead.get("board") or ""),
        "movers": rows,
    }


def buckets(doc: Optional[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """The three buckets as ``{bucket: [{theme, badge, stocks, signal}]}``."""
    if not doc:
        return {}
    raw = doc.get("buckets") or {}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for bucket in BUCKET_ORDER:
        rows = []
        for row in raw.get(bucket) or []:
            if not isinstance(row, dict):
                continue
            theme = str(row.get("theme") or "").strip()
            if not theme:
                continue
            rows.append(
                {
                    "theme": theme,
                    "badge": str(row.get("badge") or "").strip(),
                    "signal": str(row.get("signal") or "").strip(),
                    "stocks": [
                        str(s.get("name") if isinstance(s, dict) else s).strip()
                        for s in (row.get("stocks") or [])
                        if str(s.get("name") if isinstance(s, dict) else s).strip()
                    ],
                }
            )
        if rows:
            out[bucket] = rows
    return out


def cross(
    doc: Optional[Dict[str, Any]],
    morning_themes: Iterable[str],
) -> Dict[str, Any]:
    """Cross the brief's buckets with the themes the digest actually matched.

    Returns ``{"rows": [...], "fresh": [...], "source_date": str}``. Each row is
    one brief theme with the digest themes that answer to it and how many stories
    carried them; ``fresh`` is the digest's own themes that no bucket named —
    the lines that showed up without warning. ``fresh`` is what keeps this from
    being a one-way filter: a new line has to be able to appear.
    """
    themes = [str(t).strip() for t in morning_themes if str(t).strip()]
    rows: List[Dict[str, Any]] = []
    claimed: set[str] = set()
    for bucket in BUCKET_ORDER:
        for row in buckets(doc).get(bucket) or []:
            hit = [t for t in themes if _related(row["theme"], t)]
            claimed.update(hit)
            rows.append(
                {
                    "bucket": bucket,
                    "theme": row["theme"],
                    "badge": row["badge"],
                    "stocks": row["stocks"],
                    "matched": hit,
                    "stories": len(hit),
                }
            )
    fresh = [t for t in themes if t not in claimed]
    return {
        "rows": rows,
        "fresh": fresh,
        "source_date": str((doc or {}).get("_source_date") or ""),
        "gap_days": int((doc or {}).get("_gap_days") or 0),
    }


def _cell(text: str) -> str:
    """A markdown table cell: pipes and newlines would break the row."""
    return str(text or "").replace("|", "／").replace("\n", " ").strip()


def render_matrix(result: Dict[str, Any], labels: Optional[Dict[str, str]] = None) -> str:
    """The 题材坐标 block: the brief's three buckets crossed with today's stories.

    Two fields carry the whole idea. 晚报判断 is what last night's brief said
    the market was doing; 今日新闻 is whether this morning's digest has a story
    for it. A line with a count is a call that arrived with a catalyst; a line
    reading 无新消息 is a call the reader would otherwise never hear about,
    because the digest only prints themes it has a headline for.

    Three groups only: 主线 / 蓄势 / 活跃. ``cross`` still returns ``fresh``
    (the digest's themes that no bucket named) because that is what tells a
    caller the buckets missed something, but it is not rendered here — the
    block had grown a fourth heading whose one line was a comma-joined list of
    a dozen concepts, which reads as a second table of contents rather than as
    a call, and it sat at the bottom where it looked like an afterthought.

    Rendered as a list rather than a Markdown table: Server酱's desp does not
    render tables, so a table reaches WeChat as a wall of pipes plus the
    ``| --- | --- | --- | --- |`` separator row. One line per theme keeps the
    three fields and survives the renderer.
    """
    labels = labels or {}
    rows = result.get("rows") or []
    if not rows:
        return ""

    title = labels.get("title") or "今日建议关注题材"

    lines = [f"### {title}", ""]
    # 这一块讲的是「上一场收盘之后该怎么看」，不是今天盘面的读数。晚报的「当日」
    # 到了早报已经变成前一天，不写明来源日期，读者会拿它去对今天的涨停。
    source = str(result.get("source_date") or "")
    if source:
        try:
            short = _date.fromisoformat(source).strftime("%m-%d")
        except ValueError:
            short = source
        lines.extend([f"*据 {short} 晚报，不是今日盘面*", ""])
    order = ["主线", "蓄势", "活跃"]
    grouped: Dict[str, List[Dict[str, Any]]] = {name: [] for name in order}
    for row in rows:
        grouped.setdefault(str(row.get("bucket") or ""), []).append(row)

    for bucket in order:
        items = grouped.get(bucket) or []
        if not items:
            continue
        lines.append(f"**{bucket}：**")
        for row in items:
            theme = row["theme"]
            if row.get("badge"):
                theme = f"{theme}（{row['badge']}）"
            parts = [_cell(theme)]
            news = "、".join(row.get("matched") or [])
            if news:
                parts.append(_cell(news))
            stocks = "、".join(row.get("stocks") or [])
            if stocks:
                parts.append(_cell(stocks))
            lines.append("- " + " — ".join(parts))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
