"""The first ten minutes: sealed, broken, and how that compares with yesterday.

The digest is triggered at 09:02 but this block describes the tape at 09:40, so
the thirty-eight minutes in between are spent on the news rather than on idling:
the fetch is scheduled as a task that sleeps until 09:40 and the rest of the run
proceeds alongside it. Nothing downstream waits for it until the summary is
actually assembled, which is half an hour later.

Three things are reported and two compared:

* which industries are moving (同花顺's industry table, one GET for all of them);
* how many names sealed the limit in the first ten minutes;
* how many broke;
* the same two counts for the previous trading day.

The comparison reads its own archive first. Every run writes its snapshot to
``data/opening/YYYYMMDD.json``, and the next run compares against the newest
file older than today. That keeps both sides of the comparison produced by the
same code at the same hour, which no third-party history can promise. 东方财富's
dated pools are still read when the archive has nothing — the first day, or a
gap — so the block is never blank for want of a baseline.

The archive is not trusted blindly. Only mornings whose pool came back write a
file, so a failed read leaves a hole and the newest file can be two trading days
back; its counts would then print under 「上一交易日同期」 as if they were
yesterday's. 2026-11-25 is that case: the 09:40 read timed out, nothing was
written, and 11-26 would have compared against 11-24. The dated pools answer
"which day was the last trading day" directly, so the archive is checked against
them, and a mismatch drops the comparison instead of printing it.

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
# The cut, in HHMMSS. The digest now fires at 09:02 and this block reads 09:40,
# so a name whose first seal lands at or before 09:40:00 belongs to the window
# being described; anything later happened after this snapshot was taken.
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
# reading rather than stall the run. The trigger is 09:02 and this block reads
# 09:40, so the cap has to cover 38 minutes of waiting — 1800s was sized for the
# old 09:35 trigger and would have skipped the wait entirely, reading 09:02
# instead of 09:40 and printing the auction window as if it were the first ten
# minutes.
MAX_WAIT_SECONDS = 3600
# GitHub's scheduler routinely starts a run 30-60 minutes late (2026-11-24: asked
# for 01:35Z, started 02:35Z). The pool counts survive that — ``fbt`` is a fixed
# timestamp, so ``fbt <= 09:40`` still means the same thing at 10:35 — but the
# industry table is a live snapshot: printing a 10:35 move under a "（09:40）"
# heading is the kind of quiet lie this block must not tell. Past this much
# lateness the board line is dropped and the counts print alone.
LATE_BOARDS_SECONDS = 900
# 09:40 那一次读数是整块的地基，而涨停池和炸板池各只发一次请求：一次瞬时超时
# 就把整块打掉（2026-11-25 两个池子同时 20s 超时，页面少了一整节）。重试不会
# 改变口径 —— ``_counts()`` 判的是 ``fbt <= 09:40:00`` 这个固定时间戳，晚十几秒
# 再读，09:40 之前封板的还是同一批。实时性敏感的只有同花顺板块表，它另有
# ``LATE_BOARDS_SECONDS`` 保护。所以只补池子，间隔也压在一分钟内。
POOL_RETRIES = 3
POOL_RETRY_DELAYS = (5.0, 10.0)


def _fbt(row: Dict[str, Any]) -> Optional[int]:
    value = row.get("fbt")
    return value if isinstance(value, int) else None


async def _wait_until(hour: int, minute: int) -> float:
    """Sleep to the reading time; return how many seconds late the clock already is.

    The run is triggered well before this on purpose. A positive return means the
    wait happened and the read is on time; a negative one means the target had
    already passed when the run started — GitHub's scheduler can start an hour
    late — and the caller decides which parts of the block still hold at that
    point. WARNING rather than INFO: this is the line that says whether the block
    describes 09:40 or the moment the runner finally woke up.
    """
    now = datetime.now(CST)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    wait = (target - now).total_seconds()
    if 0 < wait <= MAX_WAIT_SECONDS:
        logger.warning("Opening block waits %.0fs for %02d:%02d", wait, hour, minute)
        await asyncio.sleep(wait)
        return 0.0
    if wait > MAX_WAIT_SECONDS:
        logger.warning(
            "Opening block: %02d:%02d is %.0fs away, past the %.0fs cap; reading now",
            hour, minute, wait, MAX_WAIT_SECONDS,
        )
        return 0.0
    return -wait


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


async def _pool(
    client: httpx.AsyncClient,
    url: str,
    date: str,
    *,
    retries: int = 1,
) -> Optional[List[Dict[str, Any]]]:
    """One day's pool; ``None`` means the source did not answer.

    ``retries`` is raised only for the 09:40 read. A walk back through the calendar
    keeps the default of one attempt: a missing past day is the normal answer there,
    and retrying it would multiply the cost of every weekend.
    """
    params = {
        "ut": EM_UT,
        "dpt": "wz.ztzt",
        "Pageindex": "0",
        "pagesize": str(POOL_PAGE),
        "sort": "fbt:asc",
        "date": date,
    }
    attempts = max(1, retries)
    for attempt in range(1, attempts + 1):
        response = await _get(client, url, params, EM_HEADERS)
        if response is not None:
            try:
                data = response.json().get("data") or {}
            except Exception:  # noqa: BLE001 - a garbled body is a failed read
                data = {}
            if data:
                return data.get("pool") or []
        if attempt >= attempts:
            return None
        delay = POOL_RETRY_DELAYS[min(attempt - 1, len(POOL_RETRY_DELAYS) - 1)]
        logger.warning(
            "Opening block pool retry in %.0fs (%s, %d/%d)",
            delay, url.rsplit("/", 1)[-1], attempt + 1, attempts,
        )
        await asyncio.sleep(delay)
    return None


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


async def _verified_previous(
    client: httpx.AsyncClient,
    date: str,
    archived: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """The previous trading day's counts, or ``None`` when that cannot be pinned.

    The archive only holds days whose pool came back, so a failed morning leaves a
    hole: the newest file older than today can be two trading days back, and its
    numbers would print under 「上一交易日同期」 as if they were yesterday's. The
    dated pools say which day was really the last trading day, so they are asked
    every run and the archive is checked against them.

    A mismatch is not repaired by printing the older file, and not repaired by
    switching to the newer one either: both would be a number the reader cannot
    trace. The comparison is dropped and the counts print alone.
    """
    truth = await _previous_day(client, date)
    if archived is None:
        # 首次运行或存档损坏：dated pool 就是基线，这是原来就有的兜底。
        return truth
    if truth is None:
        logger.warning(
            "Opening block baseline unverified (archive %s, dated pool unavailable); "
            "comparison dropped",
            archived.get("date"),
        )
        return None
    if archived.get("date") != truth["date"]:
        logger.warning(
            "Opening block baseline gap: archive has %s, last trading day is %s; "
            "comparison dropped",
            archived.get("date"), truth["date"],
        )
        return None
    return archived


async def fetch_opening(
    date: str,
    *,
    at: Optional[tuple[int, int]] = None,
    store: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """One run, a handful of GETs. Returns ``None`` when nothing usable came back.

    ``date`` is YYYYMMDD in Beijing time. ``at`` delays the read to a fixed clock
    time — the digest fires at 09:02 and this block describes 09:40. ``store``
    enables the archive: yesterday comes from the newest file, and today's counts
    are written back for tomorrow. A weekend or holiday returns no pool, which is
    not a failure: the block simply does not print.
    """
    late = 0.0
    if at is not None:
        late = await _wait_until(*at)
    started = datetime.now()
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
        boards_task = _get(client, THS_URL, {}, HEADERS)
        sealed_task = _pool(client, EM_ZT_URL, date, retries=POOL_RETRIES)
        broken_task = _pool(client, EM_ZB_URL, date, retries=POOL_RETRIES)
        boards_resp, sealed, broken = await asyncio.gather(
            boards_task, sealed_task, broken_task
        )
        today = _counts(sealed or [], broken or []) if sealed else None
        # 炸板池没通时 ``_counts`` 会算出 0，再配上同比就成了「炸板 0 只，-13」
        # 这种假话。把未知写成 None，让 render_block 整行不印。
        if today is not None and broken is None:
            today["broken_open"] = None
        prev = await _verified_previous(
            client, date, load_previous(date, store) if store else None
        )

    boards = parse_boards(boards_resp.content) if boards_resp is not None else []
    # A late run still counts seals correctly, but its board table is a live
    # reading. Drop it rather than relabel it: a missing line reads as "no data",
    # a 10:35 move under a 09:40 heading reads as a fact.
    if late > LATE_BOARDS_SECONDS and boards:
        logger.warning(
            "Opening block read %.0fs after %s; board moves are a live snapshot, dropped",
            late, CUT_LABEL,
        )
        boards = []
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
        "late": round(late, 1),
        "elapsed": round((datetime.now() - started).total_seconds(), 2),
        "sources": {
            "boards": bool(boards),
            "pool": sealed is not None,
            "broken": broken is not None,
            "prev": prev is not None,
        },
    }
    logger.warning(
        "Opening block: boards=%s pool=%s broken=%s prev=%s prev_from=%s today_sealed_open=%s late=%ss elapsed=%ss",
        bool(boards),
        sealed is not None,
        broken is not None,
        prev is not None,
        ("archive" if (prev or {}).get("from_archive") else "eastmoney") if prev else "none",
        (today or {}).get("sealed_open"),
        result["late"],
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

    # 炸板池没取到的那天，这一行整行不印：0 会被读成「今天没人炸板」。
    broken = today.get("broken_open")
    if broken is not None:
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