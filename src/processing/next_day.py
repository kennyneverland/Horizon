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
}
_NOISE_RE = re.compile(r"[（(][^）)]*[）)]|\s+")


def _fold(text: Any) -> str:
    """Drop brackets, spaces and the 概念/板块 suffix so two names can be compared."""
    out = _NOISE_RE.sub("", str(text or ""))
    for suffix in ("概念", "板块", "指数", "行业"):
        if out.endswith(suffix) and len(out) > len(suffix) + 1:
            out = out[: -len(suffix)]
    return out


def _shift(day: str, back: int) -> str:
    try:
        base = _date.fromisoformat(str(day))
    except ValueError:
        return ""
    return (base - timedelta(days=back)).isoformat()


def _get(url: str, timeout: float = 20.0) -> str:
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            import gzip

            body = gzip.decompress(body)
    return body.decode("utf-8", "replace")


def load(day: str, base: str = BRIEF_URL, lookback: int = LOOKBACK_DAYS) -> Optional[Dict[str, Any]]:
    """The most recent brief published before ``day``, or None.

    ``day`` is the digest's own date. The brief for the previous session is what
    the reader saw last night, so the walk starts one day back and stops at the
    first page that carries the block — a Monday digest reaches back to Friday.
    """
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
    rather than a theme.
    """
    left, right = _fold(late_theme), _fold(morning_theme)
    if not left or not right:
        return False
    if left == right:
        return True
    if len(left) >= 2 and left in right:
        return True
    if len(right) >= 2 and right in left:
        return True
    for key, aliases in _BUCKET_BRIDGE.items():
        folded = _fold(key)
        if folded in (left, right):
            for alias in aliases:
                alias_folded = _fold(alias)
                if alias_folded in (left, right) or alias_folded in left or alias_folded in right:
                    return True
    return False


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
    """Cross the brief's themes with the digest's, one row per morning theme.

    The three columns are deliberately asymmetric: a row exists because the
    morning digest has a story, so "brief named it and we have news" and
    "brief named it and we have none" are the same row with different marks,
    while "news but the brief was silent" is its own row with no brief data.
    """
    rows: List[Dict[str, Any]] = []
    morning = [str(x).strip() for x in morning_themes if str(x).strip()]
    seen: set = set()
    for name in morning:
        if name in seen:
            continue
        seen.add(name)
        hit = None
        hit_bucket = ""
        for bucket, items in buckets(doc).items():
            for item in items:
                if _related(item["theme"], name):
                    hit, hit_bucket = item, bucket
                    break
            if hit:
                break
        rows.append(
            {
                "themes": [name],
                "brief_theme": hit["theme"] if hit else "",
                "bucket": hit_bucket,
                "signal": (hit or {}).get("signal") or "",
                "stocks": (hit or {}).get("stocks") or [],
            }
        )
    return {"rows": rows}


def _cell(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().replace("|", "／")


def render_matrix(result: Dict[str, Any], labels: Optional[Dict[str, str]] = None) -> str:
    """The cross as a Markdown table, one row per morning theme."""
    rows = result.get("rows") or []
    if not rows:
        return ""
    labels = labels or {}
    head = labels.get("next_day_head") or "昨晚晚报 × 今早新闻"
    lines = [f"**「{head}」**", ""]
    lines.append("| 今早题材 | 昨晚判断 | 昨晚点名个股 |")
    lines.append("|---|---|---|")
    for row in rows:
        theme = _cell("、".join(row.get("themes") or []))
        brief = _cell(row.get("brief_theme") or "")
        bucket = _cell(row.get("bucket") or "")
        mark = f"{bucket}·{brief}" if brief else "晚报未点名"
        stocks = "、".join(_cell(s.get("name") if isinstance(s, dict) else s) for s in (row.get("stocks") or []))
        lines.append(f"| {theme} | {mark} | {stocks or '—'} |")
    return "\n".join(lines)
