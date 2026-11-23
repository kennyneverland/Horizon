"""Stock -> theme reverse lookup, built from Tonghuashun's F10 concept page.

The digest ships lianban's *catalogue* but not its members: a theme page is
fetched only when a published story needs it, kept in memory for the run, and
capped at 90 themes. That is fine for the morning digest, which only ever asks
about the themes it already named. It is useless for the evening brief, which
has to answer "which theme does this ticker belong to" for names that arrived
from somewhere else — the dragon-tiger board, the three screening panels, the
watch pool — and where a wrong theme is worse than no theme.

So the lookup is inverted: one request per *stock*, not per theme. Tonghuashun's
F10 concept page lists every concept a stock belongs to, and for each one the
reason: the page's 概念解析 column is the company's own disclosure of why it
qualifies ("海立集团与微电子装备集团…封装光刻机得冷却系统配套"). That reason is
the part lianban cannot give — a theme label says a stock was bought, the
disclosure says what the business link is.

Two sources, two jobs, deliberately not merged:

* lianban names the themes the tape is actually trading today (``theme_watch``),
  and remains the only source of A-share names in the brief;
* this index says which themes a name *belongs* to, and is used only to
  attribute a name that came from elsewhere.

The concept vocabulary is Tonghuashun's, not lianban's. Only a normalised exact
match is treated as an alignment (光刻机 -> 光刻机, 家用电器 -> 家用电器); a
substring match is not, because 新能源汽车 must never resolve to 新能源. Concepts
that do not align are kept verbatim and handed to the model as context — a
label the reader can check, rather than a mapping this script guessed.

Rate limiting is the reason the index is a cache rather than a per-run source:
the site tolerates roughly one request every two seconds, so the fetcher spaces
requests, cools down on 429, and the builder caches every page on disk so a
re-run resumes instead of restarting.
"""

from __future__ import annotations

import base64
import gzip
import html as html_mod
import json
import logging
import re
import time
import unicodedata
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

BASE = "https://basic.10jqka.com.cn"
INDEX_PARTS = ["data/stock_concepts.json.gz.b64"] + [
    f"data/stock_concepts.json.gz.b64.p{i}" for i in range(2, 5)
]
THEME_PARTS = ["data/theme_index.json.gz.b64"] + [
    f"data/theme_index.json.gz.b64.p{i}" for i in range(2, 5)
]
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
SPACING = 2.2
COOLDOWN = 30.0
# Two attempts, not three: a page that times out twice in one run is not coming
# back inside that run, and the cost of giving up is a ticker rendered as
# unattributed — which the page already handles. Three attempts at a 20s socket
# timeout meant one dead handshake could burn 72s of the brief; run #21 lost
# four of them in a row.
ATTEMPTS = 2
# The disclosure is the useful part and the page is verbose; ~110 characters
# keeps the business link ("封装光刻机冷却系统配套") and drops the boilerplate tail.
DESC_LIMIT = 110
# A stock can belong to 48 concepts (中京电子); the brief needs the ones that
# name a tradeable theme, not the whole taxonomy.
MAX_CONCEPTS = 12
# Labels that describe a listing status or a shareholder base rather than a
# tradeable theme. Kept, but sorted behind anything that names a business.
WEAK_LABELS = (
    "次新股", "高股息精选", "专精特新", "证金持股", "融资融券", "深股通", "沪股通",
    "MSCI", "富时罗素", "标普", "同花顺中特估", "国企改革", "一带一路", "国际板",
    "创投", "参股银行", "参股券商", "股权转让", "预盈预增", "年报预增", "回购增持",
    "员工持股", "养老金", "社保重仓", "QFII", "机构重仓", "破净股", "低价股",
    "超跌反弹", "ST板块", "注册制", "科创板",
)

_TABLE_RE = re.compile(r'<table[^>]*class="gnContent"[^>]*>(.*?)</table>', re.S)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _is_weak(concept: str) -> bool:
    return any(label in concept for label in WEAK_LABELS)


def _clean(cell: str) -> str:
    text = html_mod.unescape(_TAG_RE.sub(" ", cell))
    text = _WS_RE.sub(" ", text).strip()
    # The page appends a collapsed-expander marker to every disclosure cell.
    return re.sub(r"\s*展开\s*$", "", text).strip()


def _clip(text: str, limit: int = DESC_LIMIT) -> str:
    """Cut at a sentence boundary so the disclosure never ends mid-word."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in ("。", "；", "，", "、"):
        pos = cut.rfind(mark)
        if pos >= limit // 2:
            return cut[: pos + 1]
    return cut


def _norm(name: str) -> str:
    """Comparison key: no parenthetical, no spaces, width-folded, upper-cased."""
    text = unicodedata.normalize("NFKC", name or "")
    text = re.sub(r"[（(].*?[)）]", "", text)
    return _WS_RE.sub("", text).upper()


def parse_concepts(html: str) -> Tuple[str, List[List[str]]]:
    """(stock name, [[concept, leaders, disclosure], ...]) from an F10 page."""
    name = ""
    match = re.search(r"<title>\s*([^<(]{2,12}?)\s*[(（](\d{6})[)）]", html)
    if match:
        name = match.group(1).strip()
    out: List[List[str]] = []
    seen = set()
    for table in _TABLE_RE.findall(html):
        for row in _ROW_RE.findall(table):
            cells = [_clean(c) for c in _CELL_RE.findall(row)]
            if len(cells) < 3 or not cells[0].isdigit():
                continue
            concept = cells[1]
            if not concept or concept in seen:
                continue
            if len(cells) >= 4:
                leaders, desc = cells[2], cells[3]
            else:
                leaders, desc = "", cells[2]
            seen.add(concept)
            out.append([concept, leaders[:60], _clip(desc)])
    return name, out


def fetch_page(code: str) -> str:
    request = urllib.request.Request(
        f"{BASE}/{code}/concept.html",
        headers={"User-Agent": UA, "Accept-Encoding": "gzip"},
    )
    # The F10 concept page is a few KB; 10s is generous for it and keeps a
    # hung TLS handshake from spending 20s per attempt.
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    return raw.decode("gbk", "ignore")


def fetch_stock(code: str) -> Tuple[str, List[List[str]]]:
    """Fetch with spacing, 429 cooldown and retries. Returns ("", []) on failure."""
    delay = SPACING
    for attempt in range(1, ATTEMPTS + 1):
        time.sleep(delay)
        try:
            return parse_concepts(fetch_page(code))
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 403):
                logger.warning(
                    "%s on %s (attempt %d), cooling %.0fs", exc.code, code, attempt, COOLDOWN
                )
                delay = COOLDOWN
                continue
            if exc.code == 404:
                logger.warning("404 for %s: no F10 concept page", code)
                return "", []
            logger.warning("HTTP %s for %s (attempt %d)", exc.code, code, attempt)
            delay = 5.0
        except Exception as exc:  # noqa: BLE001 - one bad page must not sink the build
            logger.warning("fetch failed for %s (attempt %d): %s", code, attempt, exc)
            delay = 5.0
    return "", []


def load_index(paths: Sequence[str] = INDEX_PARTS) -> Dict[str, Any]:
    """Read the shipped index; missing parts degrade to an empty index."""
    raw = ""
    for path in paths:
        p = Path(path)
        if p.exists():
            raw += "".join(p.read_text(encoding="utf-8").split())
    if not raw:
        return {"meta": {}, "stocks": {}}
    try:
        return json.loads(zlib.decompress(base64.b64decode(raw)).decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - a corrupt index must not stop a run
        logger.warning("stock concept index unreadable (%s); continuing empty", exc)
        return {"meta": {}, "stocks": {}}


def write_index(doc: Dict[str, Any], paths: Sequence[str] = INDEX_PARTS) -> List[Tuple[str, int]]:
    payload = zlib.compress(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), 9
    )
    b64 = base64.b64encode(payload).decode("ascii")
    size = (len(b64) + len(paths) - 1) // len(paths)
    written: List[Tuple[str, int]] = []
    for i, path in enumerate(paths):
        chunk = b64[i * size : (i + 1) * size]
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(chunk, encoding="utf-8")
        written.append((path, len(chunk)))
    return written


def load_theme_names(paths: Sequence[str] = THEME_PARTS) -> List[str]:
    raw = "".join(
        "".join(Path(p).read_text(encoding="utf-8").split())
        for p in paths
        if Path(p).exists()
    )
    if not raw:
        return []
    try:
        doc = json.loads(zlib.decompress(base64.b64decode(raw)).decode("utf-8"))
    except Exception:  # noqa: BLE001
        return []
    return [row[1] for row in doc.get("themes") or [] if len(row) > 1]


def align(concepts: Iterable[str], theme_names: Sequence[str]) -> Dict[str, List[str]]:
    """Concept -> lianban themes, exact-normalised only.

    A substring hit is rejected on purpose: 新能源汽车 would otherwise resolve to
    新能源, and 光刻机 to 光刻机（胶）, which is a different basket. Several
    catalogue names can fold to the same key (CPO / CPO概念), so the value is a
    list — dropping all but the last would silently lose a real theme.
    """
    exact: Dict[str, List[str]] = {}
    for name in theme_names:
        exact.setdefault(_norm(name), []).append(name)
    out: Dict[str, List[str]] = {}
    for concept in concepts:
        hit = exact.get(_norm(concept))
        if hit:
            out[concept] = list(hit)
    return out


def lookup(
    code: str,
    name: str,
    index: Dict[str, Any],
    theme_names: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """One stock's themes, ordered so an aligned theme comes first.

    ``themes`` are lianban names (exact alignment only); ``concepts`` are
    Tonghuashun labels kept verbatim, each with its disclosure snippet, so the
    model can read the business link instead of trusting a label.
    """
    entry = (index.get("stocks") or {}).get(code)
    if not entry:
        return {"name": name, "themes": [], "concepts": [], "source": "missing"}
    stock_name, concepts = entry[0], entry[1] or []
    names = theme_names if theme_names is not None else []
    mapping = align([c[0] for c in concepts], names) if names else {}
    ordered = sorted(
        concepts,
        key=lambda c: (
            0 if c[0] in mapping else 1,
            1 if _is_weak(c[0]) else 0,
        ),
    )[:MAX_CONCEPTS]
    return {
        "name": stock_name or name,
        "themes": [t for c in ordered if c[0] in mapping for t in mapping[c[0]]],
        "concepts": [
            {"name": c[0], "leaders": c[1], "why": c[2]} for c in ordered
        ],
        "source": "ths_f10",
    }
