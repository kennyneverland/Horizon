#!/usr/bin/env python3
"""Read lianban's 主线追踪 matrix and turn it into per-line state.

The page carries a 10-day matrix of limit-up counts per industry line plus the
day's 情绪 phase, its 总龙头, and one 驱动逻辑 per line. On its own the matrix
answers "which lines were bought today"; what a picker needs is the trend —
whether a line is spreading or fading — so this script derives it.

Only the standard library is used: it runs inside the Actions job unchanged.

    python scripts/mainline_matrix.py              # readable table
    python scripts/mainline_matrix.py --json       # machine-readable
    python scripts/mainline_matrix.py --top 8      # first 8 lines only
"""

from __future__ import annotations

import argparse
import gzip
import html as _html
import json
import re
import sys
import urllib.request
from typing import Any, Dict, List, Optional

DEFAULT_URL = "https://lianban.net/mainline.html"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)
# A line at or above this many limit-ups is marked hot on the page itself.
# lianban's own backtest: a hot line halves the next day ~66% of the time.
OVERHEAT = 20
# Rows that are not industry lines: the market total and the leftovers.
TOTAL_ROW = "当日涨停"
PSEUDO_ROWS = ("未归类", "事件驱动")

_TABLE_RE = re.compile(r'<table[^>]*class="[^"]*mtx[^"]*"[^>]*>(.*?)</table>', re.S)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TH_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_DATE_RE = re.compile(r'<th[^>]*data-d="(\d{4}-\d{2}-\d{2})"', re.S)
_TAG_RE = re.compile(r"<[^>]+>")

_DAY_RE = re.compile(r'<section[^>]*class="mlday"[^>]*data-d="(\d{4}-\d{2}-\d{2})"(.*?)</section>', re.S)
_PHASE_RE = re.compile(r"<span>([^<]*?)\s*·\s*(\d+)\s*°</span>")
_LEADER_RE = re.compile(r'class="zlt2"[^>]*>(.*?)</span>', re.S)
_ZROW_RE = re.compile(r'<div class="z">(.*?)</div>', re.S)
_ZNAME_RE = re.compile(r"<b>(.*?)</b>", re.S)
_ZCOUNT_RE = re.compile(r'<span class="n[^"]*"[^>]*>(.*?)</span>', re.S)
_ZDRIVE_RE = re.compile(r'<span class="r"[^>]*>(.*?)</span>', re.S)
_ZLEAD_RE = re.compile(r'<span class="ld"[^>]*>(.*?)</span>', re.S)


def _text(raw: str) -> str:
    """Strip tags and entities so a cell reads as plain text."""
    return _html.unescape(_TAG_RE.sub("", raw)).strip()


def _int(raw: str) -> int:
    digits = re.sub(r"[^\d]", "", _text(raw))
    return int(digits) if digits else 0


def _hot(raw: str) -> bool:
    """The page marks an overheated cell with a flame; keep it as a cross-check."""
    return "\U0001F525" in raw


def fetch(url: str = DEFAULT_URL, timeout: float = 30.0) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept-Encoding": "gzip"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return body.decode("utf-8", "replace")


def parse_matrix(page: str) -> Dict[str, Any]:
    """``{dates, totals, lines}`` from the heat matrix.

    ``dates`` is newest first, which is the order the page renders. A cell the
    page leaves blank is a zero: the theme had no limit-up that day.
    """
    table = _TABLE_RE.search(page)
    if not table:
        raise ValueError("mainline matrix table not found (page layout changed?)")
    body = table.group(1)

    dates = _DATE_RE.findall(body)
    if not dates:
        raise ValueError("matrix header carries no data-d dates")

    totals: Dict[str, int] = {}
    lines: Dict[str, Dict[str, int]] = {}
    hot: Dict[str, List[bool]] = {}
    for row in _ROW_RE.findall(body):
        cells = _TH_RE.findall(row)
        if not cells:
            continue
        label = _text(cells[0])
        if not label or label.startswith("&"):
            continue
        raw_cells = _TD_RE.findall(row)
        # The header row carries only <th>; a data row always has <td> cells.
        # Without this guard a shifted header would land as a line called 产业线.
        if not raw_cells:
            continue
        values = [_int(cell) for cell in raw_cells]
        flags = [_hot(cell) for cell in raw_cells]
        if len(values) < len(dates):
            pad = len(dates) - len(values)
            values += [0] * pad
            flags += [False] * pad
        row_map = dict(zip(dates, values[: len(dates)]))
        if label == TOTAL_ROW:
            totals = row_map
        else:
            lines[label] = row_map
            hot[label] = flags[: len(dates)]
    return {"dates": dates, "totals": totals, "lines": lines, "hot": hot}


def parse_day(page: str) -> Optional[Dict[str, Any]]:
    """The newest 每日主线 block: date, 情绪 phase, 总龙头, and each line's driver.

    The page gates older days behind a paywall, so this returns at most one
    entry; a missing block is not an error.
    """
    match = _DAY_RE.search(page)
    if not match:
        return None
    date, body = match.group(1), match.group(2)

    phase = None
    degree = None
    found = _PHASE_RE.search(body)
    if found:
        phase = _text(found.group(1))
        degree = int(found.group(2))

    leader = None
    leader_badge = None
    hit = _LEADER_RE.search(body)
    if hit:
        text = _text(hit.group(1))
        leader = re.sub(r"^总龙头\s*", "", text).split()[0] if text else None
        badge = re.search(r"(\d+天\d+板)", text)
        leader_badge = badge.group(1) if badge else None

    rows = []
    for raw in _ZROW_RE.findall(body):
        name = _text(_ZNAME_RE.search(raw).group(1)) if _ZNAME_RE.search(raw) else ""
        if not name:
            continue
        count = _int(_ZCOUNT_RE.search(raw).group(1)) if _ZCOUNT_RE.search(raw) else 0
        drive = _text(_ZDRIVE_RE.search(raw).group(1)) if _ZDRIVE_RE.search(raw) else ""
        lead = _text(_ZLEAD_RE.search(raw).group(1)) if _ZLEAD_RE.search(raw) else ""
        rows.append({"name": name, "count": count, "driver": drive, "leader": lead})
    return {
        "date": date,
        "phase": phase,
        "degree": degree,
        "leader": leader,
        "leader_badge": leader_badge,
        "lines": rows,
    }


def _streak(series: List[int]) -> int:
    """How many consecutive days, counting back from today, the line was on."""
    run = 0
    for value in series:
        if value <= 0:
            break
        run += 1
    return run


def summarise(matrix: Dict[str, Any]) -> List[Dict[str, Any]]:
    """One record per line, ordered by today's count.

    ``trend`` compares today with the third previous session rather than with
    yesterday: a single day's wobble is noise, three sessions is a direction.
    """
    dates = matrix["dates"]
    totals = matrix["totals"]
    hot_map = matrix.get("hot") or {}
    total_today = totals.get(dates[0], 0) if dates else 0
    records = []
    for name, series in matrix["lines"].items():
        if name in PSEUDO_ROWS:
            continue
        values = [series.get(date, 0) for date in dates]
        today = values[0] if values else 0
        prev = values[1] if len(values) > 1 else 0
        prior = values[1:4]
        base3 = round(sum(prior) / len(prior)) if prior else 0
        streak = _streak(values)
        # The state reads the one-day move: a 22 -> 4 collapse is a 收缩 even
        # though the three-day average it fell from was low.
        if today >= OVERHEAT:
            state = "过热"
        elif today == 0:
            state = "缺席"
        elif prev == 0:
            state = "新上榜"
        elif today > prev:
            state = "扩散"
        elif today < prev:
            state = "收缩"
        else:
            state = "持平"
        records.append(
            {
                "line": name,
                "today": today,
                "prev": prev,
                "base3": base3,
                "delta1": today - prev,
                "delta3": today - base3,
                "streak": streak,
                "state": state,
                "share": round(today / total_today * 100, 1) if total_today else 0.0,
                "hot_mark": bool(hot_map.get(name, [False])[0]) if hot_map.get(name) else False,
                "series": dict(zip(dates, values)),
            }
        )
    records.sort(key=lambda item: (-item["today"], item["line"]))
    for rank, record in enumerate(records, start=1):
        record["rank"] = rank
    return records


def build(page: str) -> Dict[str, Any]:
    matrix = parse_matrix(page)
    day = parse_day(page)
    latest = matrix["dates"][0] if matrix["dates"] else None
    if day is not None:
        # The matrix and the 每日主线 block do not republish on the same clock:
        # the table can already carry today while the block still shows the
        # previous session. Flag it so a caller never prints yesterday's
        # drivers under today's date.
        day["stale"] = bool(latest) and day.get("date") != latest
    return {
        "dates": matrix["dates"],
        "totals": matrix["totals"],
        "day": day,
        "lines": summarise(matrix),
    }


def render(data: Dict[str, Any], top: Optional[int] = None) -> str:
    dates = data["dates"]
    totals = data["totals"]
    day = data.get("day") or {}
    head = f"矩阵日期 {dates[-1]} → {dates[0]}（{len(dates)} 个交易日）"
    if day:
        phase = f"{day.get('phase') or '?'} · {day.get('degree')}°"
        lead = f"{day.get('leader') or '-'} {day.get('leader_badge') or ''}".strip()
        suffix = f"（{day.get('date')}）" if day.get("stale") else ""
        head += f"\n情绪 {phase}｜总龙头 {lead}{suffix}"
    head += "\n当日涨停 " + " ".join(str(totals.get(date, 0)) for date in dates)

    rows = data["lines"] if top is None else data["lines"][:top]
    width = max((len(record["line"]) for record in rows), default=8)
    width = min(max(width, 8), 14)
    out = [
        head,
        "",
        f"{'#':>2} {'产业线':<{width}}{'今日':>4}{'昨':>4}{'日Δ':>5}{'3日Δ':>6}"
        f"{'连续':>4}  {'状态':<5}{'占比':>6}  近5日",
    ]
    mismatched = []
    for record in rows:
        recent = [record["series"].get(date, 0) for date in dates[:5]]
        # The page's flame and our threshold should agree; a drift means the
        # site changed its cutoff and OVERHEAT needs revisiting.
        if record["state"] == "过热" and not record.get("hot_mark"):
            mismatched.append(record["line"])
        out.append(
            f"{record['rank']:>2} {record['line']:<{width}}{record['today']:>4}"
            f"{record['prev']:>4}{record['delta1']:>+5}{record['delta3']:>+6}"
            f"{record['streak']:>4}  {record['state']:<5}"
            f"{record['share']:>5.1f}%  {' '.join(str(v) for v in recent)}"
        )
    if mismatched:
        out += ["", "⚠ 过热判定与页面 🔥 不一致：" + "、".join(mismatched)]
    if day.get("lines"):
        label = "每日主线（驱动逻辑）"
        if day.get("stale"):
            label += f" · 页面为 {day.get('date')}，非当日"
        out += ["", label]
        for item in day["lines"]:
            out.append(
                f"  {item['name']} {item['count']}家 · {item['driver']} · {item['leader']}"
            )
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Parse lianban's 主线追踪 matrix")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--top", type=int, default=None, help="only the first N lines")
    parser.add_argument("--page", help="parse a saved page instead of fetching")
    parser.add_argument("--timeout", type=float, default=30.0, help="fetch timeout, seconds")
    args = parser.parse_args(argv)

    if args.page:
        try:
            page = open(args.page, encoding="utf-8").read()
        except OSError as exc:
            print(f"cannot read --page {args.page}: {exc}", file=sys.stderr)
            return 2
    else:
        try:
            page = fetch(args.url, timeout=args.timeout)
        except Exception as exc:  # noqa: BLE001 - surfaced verbatim to the job log
            print(f"fetch failed for {args.url}: {exc}", file=sys.stderr)
            return 2
    try:
        data = build(page)
    except ValueError as exc:
        print(f"parse failed: {exc}", file=sys.stderr)
        return 3

    if args.json:
        payload = dict(data)
        if args.top:
            payload["lines"] = data["lines"][: args.top]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render(data, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
