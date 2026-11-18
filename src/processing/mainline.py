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
    }


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return {}
    return doc if isinstance(doc, dict) else {}


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
        hot = self.today in ((self._snapshot.get("overheat") or {}).get(line) or [])
        return {
            "line": line,
            "today": today,
            "prev": prev,
            "sum10": sum(int(counts.get(day) or 0) for day in self.dates),
            "streak": streak,
            "hot": hot,
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
        state = self.for_theme(name)
        if not state:
            return ""
        tag = f"主线{state['line']} 涨停{state['today']}"
        if state["hot"]:
            tag += HOT_MARK
        if state["streak"] >= 3:
            tag += f" 连{state['streak']}日"
        if state["today"] == 0 and state["sum10"] > 0:
            tag += " 今日归零"
        return tag

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
        snapshot["lines"].items(), key=lambda item: -item[1].get(today, 0)
    )[:5]
    logger.warning(
        "Mainline %s: %d lines, %s limit-ups total, leading %s",
        snapshot["built"],
        len(snapshot["lines"]),
        snapshot["totals"].get(today, 0),
        "、".join(f"{name}{counts.get(today, 0)}" for name, counts in leading),
    )
    return snapshot
