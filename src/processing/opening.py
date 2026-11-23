"""The first ten minutes: sealed, broken, and how that compares with yesterday.

The digest is triggered at 09:35 but this block describes the tape at 09:40, so
the five minutes in between are spent on the news rather than on waiting: the
fetch is scheduled as a task that sleeps until 09:40 and the rest of the run
proceeds alongside it. Nothing downstream waits for it until the summary is
actually assembled, which is twenty-odd minutes later.

Three things are reported and two compared:

* which industries are moving (同花顺's industry table, one GET for all of them);
* how many names sealed the limit in the first ten minutes;
* how many broke;
* the same two counts for the previous trading day.

The comparison reads its own archive first. Every run writes its snapshot to
``data/opening/YYYY-MM-DD.json``, and the next run compares against the newest
file older than today. That keeps both sides of the comparison produced by the
same code at the same hour, which no third-party history can promise. 东方财富's
dated pools are still read when the archive has nothing — the first day, or a
gap — so the block is never blank for want of a baseline.

Two details decide whether the comparison means anything. ``fbt``, the time a
name first sealed, does not change after the fact, so counting either side by
``fbt <= 09:40:00`` measures the same window. And a name that sealed at 09:31
and broke at 10:00 sits in the 炸板池 rather than the 涨停池, so both pools are
read — otherwise the count would quietly drop whenever an early seal failed.

Nothing here is required by the digest. Every source is wrapped: a failed request
drops the block and leaves the rest of the brief alone.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 20.0
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
}
EM_HEADERS = {**HEADERS, "Referer": "https://quote.eastmoney.com/"}
THS_URL = "https://q.10jqka.com.cn/thshy/"
EM_ZT_URL = "https://push2ex.eastmoney.com/getTopicZTPool"
EM_ZB_URL = "https://push2ex.eastmoney.com/getTopicZBPool"
EM_UT = "7eea3edcaed734bea9cbfc24409ed989"

CST = timezone(timedelta(hours=8))
# The cut, in HHMMSS. The digest fires at 09:35 and this block reads 09:40, so a
# name whose first seal lands at or before 09:40:00 belongs to the window being
# described; anything later happened after this snapshot was taken.
CUT = 94000
CUT_LABEL = "09:40"
# 09:30:00 — sealed before this means the auction did it, which reads differently
# from a name that sealed on the first few ticks.
AUCTION = 93000
# A long weekend is the widest gap worth comparing across.
LOOKBACK_DAYS = 5
TOP_BOARDS = 5
POOL_PAGE = 400
# Where each run leaves its snapshot for the next one. Restored by the workflow's
# cache step; absent on the first run, which is why the archive is not the only
# way to a baseline.
STORE = Path("data/opening")
# A wait longer than this means the clock is not where it should be; take the
# reading rather than stall the run.
MAX_WAIT_SECONDS = 1800


def _fbt(row: Dict[str, Any]) -> Optional[int]:
    value = row.get("fbt")
    return value if isinstance(value, int) else None


async def _wait_until(hour: int, minute: int) -> None:
    """Sleep to the reading time. The run is triggered earlier than this on purpose."""
    now = datetime.now(CST)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    wait = (target - now).total_seconds()
    if 0 < wait <= MAX_WAIT_SECONDS:
        logger.info("Opening block waits %.0fs for %02d:%02d", wait, hour, minute)
        await asyncio.sleep(wait)


def _store_path(store: Path, date: str) -> Path:
    return Path(store) / f"{date}.json"


def load_previous(date: str, store: Path) -> Optional[Dict[str, Any]]:
    """The newest snapshot older than ``date``.

    Days are compared as ``YYYYMMDD`` strings, which sort correctly and sidestep
    parsing every filename. A missing directory is the first run, not an error.
    """
    directory = Path(store)
    if not directory.is_dir():
        return None
    best: Optional[str] = None
    for path in directory.glob("*.json"):
        stem = path.stem
        if len(stem) == 8 and stem.isdigit() and stem < date:
            if best is None or stem > best:
                best = stem
    if best is None:
        return None
    try:
        payload = json.loads(_store_path(store, best).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - a corrupt file is the same as no file
        logger.warning("Opening archive unreadable (%s): %s", best, exc)
        return None
    today = payload.get("today")
    if not isinstance(today, dict):
        return None
    return {"date": best, **today, "from_archive": True}


def save_snapshot(date: str, today: Dict[str, Any], store: Path) -> None:
    """Write today's counts for the next run to compare against."""
    try:
        directory = Path(store)
        directory.mkdir(parents=True, exist_ok=True)
        _store_path(store, date).write_text(
            json.dumps(
                {
                    "date": date,
                    "fetched_at": datetime.now(CST).isoformat(timespec="seconds"),
                    "today": today,
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 - an archive miss costs a baseline, not the block
        logger.warning("Opening archive write failed: %s", exc)


async def _get(client: httpx.AsyncClient, url: str, params: Dict[str, str], headers: Dict[str, str]) -> Optional[httpx.Response]:
    try:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response
    except Exception as exc:  # noqa: BLE001 - a missing source is not an error here
        logger.warning("Opening block source failed (%s): %s", url.rsplit("/", 1)[-1], exc)
        return None


def parse_boards(content: bytes) -> List[Dict[str, str]]:
    """同花顺's industry table, decoded as GBK.

    ``response.text`` guesses the charset and gets this page wrong, so the bytes
    are decoded here. Columns: rank, board, change %, volume, turnover, net
    inflow, advancers, decliners, average price, leading stock, price, change %.
    """
    page = content.decode("gbk", "ignore")
    table = re.search(r'<table class="m-table.*?</table>', page, re.S)
    if not table:
        return []
    out: List[Dict[str, str]] = []
    for row in re.findall(r"<tr>(.*?)</tr>", table.group(0), re.S):
        cells = [
            re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip()
            for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        ]
        if len(cells) < 12 or not cells[1]:
            continue
        out.append(
            {
                "board": cells[1],
                "change": cells[2],
                "inflow": cells[5],
                "up": cells[6],
                "down": cells[7],
                "leader": cells[9],
                "leader_change": cells[11],
            }
        )
    return out


async def _pool(client: httpx.AsyncClient, url: str, date: str) -> Optional[List[Dict[str, Any]]]:
    response = await _get(
        client,
        url,
        {
            "ut": EM_UT,
            "dpt": "wz.ztzt",
            "Pageindex": "0",
            "pagesize": str(POOL_PAGE),
            "sort": "fbt:asc",
            "date": date,
        },
        EM_HEADERS,
    )
    if response is None:
        return None
    try:
        data = response.json().get("data") or {}
    except Exception:  # noqa: BLE001
        return None
    return data.get("pool") or []


def _counts(sealed: List[Dict[str, Any]], broken: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One day's opening window, both pools, cut at ``fbt <= 09:40:00``.

    Sealed and broken do not overlap: a name that sealed and broke back is in the
    sealed pool with ``zbc > 0``, a name still broken is in the broken pool.
    Counting a name that sealed early and later failed needs both.
    """
    sealed_open = [r for r in sealed if (_fbt(r) or 10**9) <= CUT]
    broken_open = [r for r in broken if (_fbt(r) or 10**9) <= CUT]
    auction = [r for r in sealed_open + broken_open if (_fbt(r) or 10**9) < AUCTION]
    # 连板 reads from the sealed pool only: a broken name has no board to stand on.
    heights: Dict[int, int] = {}
    for row in sealed:
        lb = row.get("lbc")
        if isinstance(lb, int) and lb > 0:
            heights[str(lb)] = heights.get(str(lb), 0) + 1
    return {
        "sealed_open": len(sealed_open),
        "broken_open": len(broken_open),
        "auction": len(auction),
        "total_sealed": len(sealed),
        "total_broken": len(broken),
        "heights": heights,
        "max_board": max((int(k) for k in heights), default=0),
        "top_boards": [
            {"name": r.get("n"), "code": r.get("c"), "lbc": r.get("lbc"), "hybk": r.get("hybk")}
            for r in sorted(
                [x for x in sealed if isinstance(x.get("lbc"), int) and x["lbc"] >= 2],
                key=lambda x: (-(x.get("lbc") or 0), _fbt(x) or 10**9),
            )[:6]
        ],
    }


async def _previous_day(client: httpx.AsyncClient, date: str) -> Optional[Dict[str, Any]]:
    """Walk back to the last day with a pool; the gap can be a weekend or longer."""
    try:
        anchor = datetime.strptime(date, "%Y%m%d")
    except ValueError:
        return None
    for step in range(1, LOOKBACK_DAYS + 1):
        cand = (anchor - timedelta(days=step)).strftime("%Y%m%d")
        sealed = await _pool(client, EM_ZT_URL, cand)
        if not sealed:
            continue
        broken = await _pool(client, EM_ZB_URL, cand) or []
        return {"date": cand, **_counts(sealed, broken), "from_archive": False}
    return None


async def fetch_opening(
    date: str,
    *,
    at: Optional[tuple[int, int]] = None,
    store: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """One run, up to five GETs. Returns ``None`` when nothing usable came back.

    ``date`` is YYYYMMDD in Beijing time. ``at`` delays the read to a fixed clock
    time — the digest fires at 09:35 and this block describes 09:40. ``store``
    enables the archive: yesterday comes from the newest file, and today's counts
    are written back for tomorrow. A weekend or holiday returns no pool, which is
    not a failure: the block simply does not print.
    """
    if at is not None:
        await _wait_until(*at)
    started = datetime.now()
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
        boards_task = _get(client, THS_URL, {}, HEADERS)
        sealed_task = _pool(client, EM_ZT_URL, date)
        broken_task = _pool(client, EM_ZB_URL, date)
        boards_resp, sealed, broken = await asyncio.gather(
            boards_task, sealed_task, broken_task
        )
        today = _counts(sealed or [], broken or []) if sealed else None
        prev = load_previous(date, store) if store else None
        if prev is None:
            prev = await _previous_day(client, date)

    boards = parse_boards(boards_resp.content) if boards_resp is not None else []
    if today is None and not boards:
        logger.warning("Opening block unavailable: no pool and no boards")
        return None

    if today and store:
        save_snapshot(date, today, store)

    result = {
        "boards": boards[:TOP_BOARDS],
        "board_count": len(boards),
        "today": today,
        "prev": prev,
        "window": CUT_LABEL,
        "elapsed": round((datetime.now() - started).total_seconds(), 2),
        "sources": {
            "boards": bool(boards),
            "pool": sealed is not None,
            "broken": broken is not None,
            "prev": prev is not None,
        },
    }
    logger.info(
        "Opening block: boards=%s pool=%s broken=%s prev=%s prev_from=%s today_sealed_open=%s elapsed=%ss",
        bool(boards),
        sealed is not None,
        broken is not None,
        prev is not None,
        ("archive" if (prev or {}).get("from_archive") else "eastmoney") if prev else "none",
        (today or {}).get("sealed_open"),
        result["elapsed"],
    )
    return result


def _delta(today: Optional[int], prev: Optional[int]) -> str:
    if today is None or prev is None:
        return ""
    diff = today - prev
    if diff == 0:
        return "持平"
    return f"{'+' if diff > 0 else ''}{diff}"


def render_block(data: Optional[Dict[str, Any]], labels: Optional[Dict[str, str]] = None) -> str:
    """A list, not a table: Server酱's desp drops tables into a wall of pipes."""
    if not data:
        return ""
    labels = labels or {}
    title = labels.get("opening_title") or "开盘异动"
    today = data.get("today") or {}
    prev = data.get("prev") or {}
    boards = data.get("boards") or []
    # 当日涨停池为空说明今天不是交易日，或者池子这个源没通。两种情况下都不能
    # 只印板块：同花顺在周末仍挂着上一交易日的收盘榜，配上「09:40」就是把周五
    # 的收盘当成今天的开盘。宁缺不错。
    if not today:
        return ""

    lines = [f"### {title}（{data.get('window') or CUT_LABEL}）", ""]
    if boards:
        parts = []
        for b in boards:
            bit = f"{b['board']} {b['change']}%"
            if b.get("leader"):
                bit += f"（{b['leader']} {b['leader_change']}%）"
            parts.append(bit)
        lines.append("**板块** " + "、".join(parts))
        lines.append("")

    sealed = today.get("sealed_open")
    prev_sealed = prev.get("sealed_open")
    text = f"**开盘封板** {sealed} 只"
    if today.get("auction"):
        text += f"（其中竞价段 {today['auction']} 只）"
    if prev_sealed is not None:
        d = _delta(sealed, prev_sealed)
        text += f"，上一交易日同期 {prev_sealed} 只" + (f"，{d}" if d else "")
    lines.append(text)

    broken = today.get("broken_open")
    prev_broken = prev.get("broken_open")
    text = f"**炸板** {broken} 只"
    if prev_broken is not None:
        d = _delta(broken, prev_broken)
        text += f"，上一交易日同期 {prev_broken} 只" + (f"，{d}" if d else "")
    lines.append(text)

    heights = today.get("heights") or {}
    top = today.get("top_boards") or []
    if top:
        head = "、".join(f"{x['name']}{x['lbc']}板" for x in top if x.get("lbc"))
        if head:
            lines.append(f"**连板** 最高 {today.get('max_board')} 板 — {head}")
    elif heights:
        lines.append(f"**连板** 最高 {today.get('max_board')} 板")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"
