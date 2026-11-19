"""Daily mainline snapshot from lianban's 主线追踪 page.

The theme index answers "which sectors exist". This page answers a different
question: which industry lines the market actually traded on a given day. It is
a server-rendered table, eighteen lines down the side and the last ten trading
days across the top, each cell holding that line's limit-up count for the day,
with a fire mark on a line that ran hot.

Two consequences follow. The counts are a trading fact about the previous
close, so they are the only input in the digest that says whether a direction
is being bought right now. They are not evidence that a particular story moved
that line: a line with twenty-two limit-ups says "this direction is live", and
nothing about cause. The picker prompt is written to that distinction.

The page is public and costs one GET, so it is read once per run and cached in
``data/mainline_snapshot.json``. A failed fetch keeps the previous snapshot
rather than dropping the annotation for the whole run.
"""

import html as _html
import json
import logging
import re
import urllib.request
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

LISTING_URL = "https://lianban.net/mainline.html"
SNAPSHOT_PATH = Path("data/mainline_snapshot.json")
MAP_PATH = Path("data/mainline_map.json")

# The two rows that are not industry lines: limit-ups that belong to no single
# line, and limit-ups caused by company events rather than a sector.
TOTAL_LABEL = "当日涨停"
PSEUDO_LINES = ("未归类", "事件驱动")
HOT_MARK = "\U0001F525"

_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_DATE_RE = re.compile(r"^(\d{2}-\d{2})")
# The 每日主线 block is a <section>, not a table row: it carries the session's
# 情绪 phase and 总龙头, which the matrix alone cannot express.
_DAY_RE = re.compile(
    r'<section[^>]*class="mlday"[^>]*data-d="(\d{4}-\d{2}-\d{2})"(.*?)</section>', re.S
)
_PHASE_RE = re.compile(r"<span>([^<]*?)\s*·\s*(\d+)\s*°</span>")
_LEADER_RE = re.compile(r'class="zlt2"[^>]*>(.*?)</span>', re.S)
_ZROW_RE = re.compile(r'<div class="z">(.*?)</div>', re.S)
_ZNAME_RE = re.compile(r"<b>(.*?)</b>", re.S)
_ZCOUNT_RE = re.compile(r'<span class="n[^"]*"[^>]*>(.*?)</span>', re.S)
_ZDRIVE_RE = re.compile(r'<span class="r"[^>]*>(.*?)</span>', re.S)
_ZLEAD_RE = re.compile(r'<span class="ld"[^>]*>(.*?)</span>', re.S)


def _cell_text(raw: str) -> str:
    """Strip tags and entities so a cell reads as plain text."""
    return _html.unescape(_TAG_RE.sub("", raw)).strip()


def fetch_listing(url: str = LISTING_URL, timeout: float = 30.0) -> str:
    """Read the mainline page; the caller parses it."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
            ),
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = zlib.decompress(body, 16 + zlib.MAX_WBITS)
    return body.decode("utf-8", "replace")


def parse_mainline(page: str) -> Dict[str, Any]:
    """Read the matrix into ``{dates, totals, lines, overheat}``.

    The header row is the one whose first cell is empty and whose second cell
    starts with a ``MM-DD`` date; every data row carries one label plus one
    cell per date. Rows of any other shape belong to the page's help tables and
    are skipped, which is what keeps a layout tweak from silently producing
    wrong numbers.
    """
    dates: List[str] = []
    totals: Dict[str, int] = {}
    lines: Dict[str, Dict[str, int]] = {}
    overheat: Dict[str, List[str]] = {}

    for row in _ROW_RE.findall(page):
        cells = [_cell_text(cell) for cell in _CELL_RE.findall(row)]
        if not cells:
            continue
        if not dates:
            if cells[0] == "" and len(cells) > 2 and _DATE_RE.match(cells[1] or ""):
                dates = [_DATE_RE.match(cell).group(1) for cell in cells[1:]]
            continue
        if len(cells) != len(dates) + 1:
            continue
        label = cells[0]
        if not label:
            continue
        counts: Dict[str, int] = {}
        for day, raw in zip(dates, cells[1:]):
            digits = re.sub(r"[^0-9]", "", raw or "")
            counts[day] = int(digits) if digits else 0
            if HOT_MARK in (raw or ""):
                overheat.setdefault(label, []).append(day)
        if label == TOTAL_LABEL:
            totals = counts
        else:
            lines[label] = counts

    return {
        "built": dates[0] if dates else "",
        "dates": dates,
        "totals": totals,
        "lines": lines,
        "overheat": overheat,
        "day": parse_day(page),
    }


def parse_day(page: str) -> Optional[Dict[str, Any]]:
    """The newest 每日主线 block: 情绪 phase, 总龙头, and each line's driver.

    The matrix says how many limit-ups a line drew; this block says why the
    page thinks they happened. The two are kept apart on purpose — the driver
    is the site's attribution, not a fact this digest verified.

    Older days sit behind a paywall, so at most one block is readable and a
    missing block is not an error.
    """
    match = _DAY_RE.search(page)
    if not match:
        return None
    date, body = match.group(1), match.group(2)

    phase = None
    degree = None
    found = _PHASE_RE.search(body)
    if found:
        phase = _cell_text(found.group(1))
        degree = int(found.group(2))

    leader = None
    badge = None
    hit = _LEADER_RE.search(body)
    if hit:
        text = _cell_text(hit.group(1))
        leader = re.sub(r"^总龙头\s*", "", text).split()[0] if text else None
        mark = re.search(r"(\d+天\d+板)", text)
        badge = mark.group(1) if mark else None

    rows = []
    for raw in _ZROW_RE.findall(body):
        name_hit = _ZNAME_RE.search(raw)
        name = _cell_text(name_hit.group(1)) if name_hit else ""
        if not name:
            continue
        count_hit = _ZCOUNT_RE.search(raw)
        drive_hit = _ZDRIVE_RE.search(raw)
        lead_hit = _ZLEAD_RE.search(raw)
        rows.append(
            {
                "name": name,
                "count": _int_of(count_hit.group(1)) if count_hit else 0,
                "driver": _cell_text(drive_hit.group(1)) if drive_hit else "",
                "leader": _cell_text(lead_hit.group(1)) if lead_hit else "",
            }
        )
    return {
        "date": date[5:],  # MM-DD, the same shape the matrix columns use
        "phase": phase,
        "degree": degree,
        "leader": leader,
        "leader_badge": badge,
        "lines": rows,
    }


def _int_of(raw: str) -> int:
    digits = re.sub(r"[^0-9]", "", raw or "")
    return int(digits) if digits else 0


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _shape(today: int, prev: int, hot: bool) -> str:
    """One word for a line's day-over-day shape.

    The one-day move decides it: 22 -> 4 is a 收缩 even though the three-day
    average it fell from was low. A first appearance is called out because
    "前日0" alone reads like an absence rather than an arrival.
    """
    if hot:
        return "过热"
    if today == 0:
        return "缺席"
    if prev == 0:
        return "新上榜"
    if today > prev:
        return "扩散"
    if today < prev:
        return "收缩"
    return "持平"


def format_state(state: Optional[Dict[str, Any]]) -> str:
    """One compact line describing a line's trading shape.

    Shared by the picker's candidate list and the direction judge, so the two
    prompts cannot drift apart on what the fire mark or 今日归零 means. The
    previous day's count rides along because a bare count cannot tell a line
    that just accelerated (22 today, 5 yesterday) from one already rolling
    over (22 today, 26 yesterday).
    """
    if not state:
        return ""
    today = int(state.get("today") or 0)
    tag = f"主线{state.get('line', '-')} 涨停{today}"
    if state.get("hot"):
        tag += HOT_MARK
    if today > 0:
        if state.get("state") == "新上榜":
            tag += " 新上榜"
        else:
            tag += f" 前日{int(state.get('prev') or 0)}"
        # The three-day move is the one figure the row cannot be derived from:
        # today and 前日 are both on the line, the prior average is not.
        delta3 = int(state.get("delta3") or 0)
        if delta3:
            tag += f" 3日{delta3:+d}"
    if int(state.get("streak") or 0) >= 3:
        tag += f" 连{state['streak']}日"
    if today == 0 and int(state.get("sum10") or 0) > 0:
        tag += " 今日归零"
    return tag


class MainlineState:
    """The day's mainline matrix, joined to the theme catalogue.

    ``for_theme`` is the only entry point the rest of the digest needs: it turns
    a theme name into the industry line that carries it and that line's trading
    state. A theme no line covers simply has no state, which is the honest
    answer rather than a zero.
    """

    def __init__(self, snapshot: Optional[Dict[str, Any]] = None, mapping: Optional[Dict[str, Any]] = None):
        self._snapshot = snapshot or {}
        self._mapping = mapping or {}
        self._line_of: Dict[str, List[str]] = {}
        for line, themes in (self._mapping.get("lines") or {}).items():
            for name in themes or []:
                self._line_of.setdefault(str(name).strip(), []).append(str(line))
        self.dates: List[str] = list(self._snapshot.get("dates") or [])
        self.today = self.dates[0] if self.dates else ""

    @property
    def available(self) -> bool:
        """True when a snapshot and at least one line were both read."""
        return bool(self.dates and self._snapshot.get("lines"))

    @property
    def market(self) -> Dict[str, Any]:
        """The newest 每日主线 block: 情绪 phase, 总龙头, per-line drivers."""
        return self._snapshot.get("day") or {}

    def market_line(self) -> str:
        """The session's 情绪 phase and 总龙头, as one prompt-ready line.

        It belongs above the candidate list, not on each row: it describes the
        whole session, and repeating it per theme would both inflate the prompt
        and suggest it bears on that theme in particular.
        """
        day = self.market
        if not day:
            return ""
        parts = []
        if day.get("phase"):
            degree = day.get("degree")
            parts.append(
                f"{day['phase']} · {degree}°" if degree is not None else str(day["phase"])
            )
        if day.get("leader"):
            lead = f"总龙头 {day['leader']}"
            if day.get("leader_badge"):
                lead += f" {day['leader_badge']}"
            parts.append(lead)
        return " ｜".join(parts)

    def line_state(self, line: str) -> Optional[Dict[str, Any]]:
        """Trading state of one industry line, or None when the page lacks it."""
        counts = (self._snapshot.get("lines") or {}).get(line) or {}
        if not counts:
            return None
        today = int(counts.get(self.today) or 0)
        prev = int(counts.get(self.dates[1]) or 0) if len(self.dates) > 1 else 0
        streak = 0
        for day in self.dates:
            if int(counts.get(day) or 0) > 0:
                streak += 1
            else:
                break
        prior = [int(counts.get(day) or 0) for day in self.dates[1:4]]
        base3 = round(sum(prior) / len(prior)) if prior else 0
        hot = self.today in ((self._snapshot.get("overheat") or {}).get(line) or [])
        return {
            "line": line,
            "today": today,
            "prev": prev,
            "base3": base3,
            "delta3": today - base3,
            "sum10": sum(int(counts.get(day) or 0) for day in self.dates),
            "streak": streak,
            "hot": hot,
            "state": _shape(today, prev, hot),
        }

    def for_theme(self, name: Any) -> Optional[Dict[str, Any]]:
        """The strongest line covering this theme, or None."""
        if not self.available:
            return None
        lines = self._line_of.get(str(name or "").strip()) or []
        best: Optional[Dict[str, Any]] = None
        for line in lines:
            state = self.line_state(line)
            if state is None:
                continue
            if best is None or state["today"] > best["today"]:
                best = state
        return best

    def label(self, name: Any) -> str:
        """Compact prompt field: which line, how many limit-ups, and its shape."""
        return format_state(self.for_theme(name))

    def annotate(self, theme: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attach the line state to a theme record, in place."""
        state = self.for_theme(theme.get("name"))
        if state:
            theme["mainline"] = state
        return state


_STATE: Optional[MainlineState] = None


def load_state() -> MainlineState:
    """The process-wide state, read from the snapshot and map files once."""
    global _STATE
    if _STATE is None:
        _STATE = MainlineState(_read_json(SNAPSHOT_PATH), _read_json(MAP_PATH))
    return _STATE


def reset_state() -> None:
    """Drop the cached state after a refresh so the next read sees it."""
    global _STATE
    _STATE = None


def refresh(data_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Fetch the page, write the snapshot, and reset the cached state."""
    target = (Path(data_dir) / SNAPSHOT_PATH.name) if data_dir else SNAPSHOT_PATH
    try:
        page = fetch_listing()
    except (OSError, zlib.error) as exc:
        logger.warning("Mainline page unreachable (%s); keeping the last snapshot", exc)
        return None
    snapshot = parse_mainline(page)
    if not snapshot.get("dates") or not snapshot.get("lines"):
        logger.warning("Mainline page has no matrix any more; keeping the last snapshot")
        return None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Mainline snapshot not written: %s", exc)
    # Build the state from what was just parsed rather than re-reading the file:
    # a caller running with a non-default data dir would otherwise find nothing.
    global _STATE
    _STATE = MainlineState(snapshot, _read_json(MAP_PATH))
    today = snapshot["dates"][0]
    leading = sorted(
        ((name, counts) for name, counts in snapshot["lines"].items() if name not in PSEUDO_LINES),
        key=lambda item: -item[1].get(today, 0),
    )[:5]
    day = snapshot.get("day") or {}
    mood = (
        f"{day.get('phase')} {day.get('degree')}°"
        if day.get("phase") and day.get("degree") is not None
        else "-"
    )
    logger.warning(
        "Mainline %s: %d lines, %s limit-ups total, %s, leading %s",
        snapshot["built"],
        len(snapshot["lines"]),
        snapshot["totals"].get(today, 0),
        mood,
        "、".join(f"{name}{counts.get(today, 0)}" for name, counts in leading),
    )
    return snapshot
