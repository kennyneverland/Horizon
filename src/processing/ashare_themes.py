"""Attach the A-share theme an item touches, and the names listed under it.

The digest follows AI and computing power, so a story about Nvidia's CEO
leaving matters to the reader mainly through the mainland supply chain it
drags on. That link is not in the headline, and the analyser is told not to
speculate about impact, so the theme has to come from a lookup rather than
from the model.

Two public datasets are joined here: ``lianban.net`` publishes 750 theme
pages with the member list in schema.org ``ItemList`` JSON-LD (the only source
of *names* — the digest never invents a ticker; CC BY 4.0, attribution
required), and ``stockinsky.com`` publishes 635 concept descriptions used only
to widen a theme's vocabulary, never to pick a ticker.

Theme matching is lexical, not model-driven: a title hits a theme when it
contains one of that theme's terms. Terms come from three layers, in
descending weight — a hand-maintained alias table (英伟达 / 黄仁勋 / NVDA →
英伟达概念), the theme name and its variants, and stockinsky's description
phrases. Without the alias layer a headline like "黄仁勋离职后持股减持约束"
scores nothing, because it never says 英伟达.

When the heat list names nothing, the model picks from the whole index before
the lexical sweep is tried, so a story outside today's traded sectors still
gets a theme line.

A wording match is not yet a carrier: the conduction gate drops the themes of a
story that cannot be traced to an A-share segment within two hops, so an
overseas IPO that merely says 算力 no longer names five mainland tickers.

Members are fetched later, one request per theme the line will show, capped
per run. lianban sorts every theme page by three-month relative strength after
each close, so the page order *is* the ranking. A failed fetch drops the name
list and keeps the theme label, so a blocked request degrades the line instead
of the digest.

Everything here is a lookup, not a recommendation: the rendered line is marked
as inferred and carries the source attribution.
"""

from __future__ import annotations

import asyncio
import atexit
import base64
import gzip
import json
import logging
import re
import time
import unicodedata
import urllib.request
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .conduction import conduction_filter, direction_note

logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = Path("data/theme_index.json.gz.b64")
# Optional overlay: extra aliases maintained by hand, merged on top of the index.
OPTIONAL_ALIAS_PATH = Path("data/theme_aliases.json")

# A single term is enough to name a theme; below this the match is noise.
MIN_SCORE = 0.5
# The runner-up theme is only shown when it is nearly as strong as the leader,
# otherwise a weak second hit just adds a wrong name list.
RELATIVE_CUTOFF = 0.72
MAX_THEMES_PER_ITEM = 3
# Three names keeps a line readable now that it can carry three themes; the
# reader asked for at most three themes x three names per story.
MAX_MEMBERS = 3
# Requests are cheap but lianban rate-limits aggressively, so the run is capped.
# Fetches are serialised and cached per theme, so a repeated theme costs nothing.
# The lookup runs once per item now, in the enrichment pass, and only the items
# that reach the digest get there: at most 35 items x 3 themes = 105 lookups,
# and the repeated themes are served from the cache. The model fallback adds up
# to three more themes per item the heat list missed, so the cap is set to 90
# to cover the published set without leaving its tail without member lists.
MAX_THEME_FETCH = 90
# A page that answers without a member list is treated as a miss, not as an
# empty theme: lianban throttles by serving a stub page, so one retry after a
# short pause usually recovers it.
FETCH_ATTEMPTS = 2
FETCH_RETRY_WAIT = 6.0
# 0.4s tripped the limiter on 2026-11-18 once a story could carry three themes
# and the run asked for ~38 pages; 1.0s still fits inside the run.
FETCH_SPACING = 1.0
# A 429 pauses every later fetch, not just this one: lianban counts requests
# from the client address, so carrying on at the same rate only deepens it.
RATE_LIMIT_COOLDOWN = 12.0
# The theme lookup means something to every reader who follows the AI and
# computing supply chain, so the AI profiles carry it too; tech-blog does not.
# China-market items are the ones most likely to name a theme directly.
THEME_PROFILES = frozenset(
    {"finance-news", "china-market", "tech-news", "ai-hardware", "ai-app"}
)
FETCH_TIMEOUT = 12.0
SOURCE_LABEL = "第三方信源"
# A matched theme says the story is about that sector; it does not say whether
# the story helps or hurts it. The direction pass asks the model for that, and
# these are the only answers it may give.
POSITIVE = "positive"
NEGATIVE = "negative"
# A story can mention a theme without pushing it either way, and a miss must
# stay distinguishable from that, so neutral is a verdict and a missing one is
# not.
NEUTRAL = "neutral"
DIRECTION_LABELS = {
    POSITIVE: "积极影响",
    NEGATIVE: "负面影响",
    NEUTRAL: "可能相关",
}

# 题材池只取 lianban 列表页热度排名前 200 的题材。该列表每个交易日收盘后按
# 市场热度重排，前 200 是当天真正在被交易的题材；成员仍取页面自带的"近3月
# 相对强度"前 3。2026-11-18 实测：794 个题材里 rank<=200 的有 181 个。
# 前 200 一个都没命中时，先让模型在全量索引里选，再由词表匹配兜底。
HOT_THEME_LIMIT = 200

# 成员表跨运行缓存。runner 每次都是干净的，只有落盘 + actions/cache 才能把它带过
# run；目录与成员主营画像共用，workflow 里已经缓存了 data/member_profiles。
# 当天抓到的算新鲜；更早的只在抓取失败时拿出来用——题材行宁可旧一天，也不要只剩题材名。
MEMBERS_CACHE_DIR = Path("data/member_profiles")
MEMBERS_CACHE_FILE = "theme_members.json.gz.b64"

_ASCII_TERM_RE = re.compile(r"[a-z0-9&.\- ]+")
_ITEMLIST_RE = re.compile(
    r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S
)
_GU_ANCHOR_RE = re.compile(r'<a href="/gu/(\d{6})\.html">([^<]+)</a>')
# The page body states the ranking explicitly: "收录 66 只成员（按近3月相对
# 强度降序）——移远通信、阿尔特、…等。" The JSON-LD ItemList is in ticker-code
# order instead, so it is only used to attach codes to these names.
_RANKED_RE = re.compile(
    r"收录\s*\d+\s*只成员[（(]按近3月相对强度降序[）)]\s*[—\-–]+\s*([^。]+)"
)
_NAME_PREFIX_RE = re.compile(r"^(XD|XR|DR|\*?ST|N|C)")
# A JSON-LD member reads "移远通信(603236)".
_LISTED_RE = re.compile(r"^(.*?)\s*\((\d{6})\)\s*$")
# Theme pages moved from /ticai/<id>.html to /ticai/<pinyin>-<hash>.html and the
# old numeric URLs now answer 404. The listing page is the only place that pairs
# a theme name with its current URL, so it is read once per run.
_THEME_LINK_RE = re.compile(
    r'href="(/ticai/[a-z0-9]+-[0-9a-f]{4}\.html)"[^>]*>(.*?)</a>', re.S
)
_THEME_LINK_NAME_RE = re.compile(r"^(.*?)热度第")


def _normalise(text: Any) -> str:
    """Fold width and case so a term matches regardless of how it was typed."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", str(text)).lower()


def _parse_theme_links(html: str) -> Dict[str, str]:
    """Map a theme name to its current page path, from the listing page.

    Each entry reads ``AIGC概念热度第252 · 117只``, so the name is everything
    before 热度第. Names are folded, so a match does not depend on width or case.
    """
    slugs: Dict[str, str] = {}
    for match in _THEME_LINK_RE.finditer(html):
        path, label = match.group(1), match.group(2)
        text = re.sub(r"<[^>]+>", "", label).strip()
        name_match = _THEME_LINK_NAME_RE.match(text)
        name = (name_match.group(1) if name_match else text).strip()
        if name:
            slugs.setdefault(_normalise(name), path)
    return slugs


def _parse_hot_names(html: str, limit: int) -> set[str]:
    """Theme names ranked inside the top ``limit`` of the listing page.

    The listing reads ``AIGC概念热度第252 · 117只``; the rank is the market-heat
    order recomputed after every close. Names are folded the same way as
    ``_parse_theme_links`` so the two maps agree.
    """
    hot: set[str] = set()
    for match in _THEME_LINK_RE.finditer(html):
        label = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        entry = re.match(r"^(.*?)\s*热度第\s*(\d+)\s*·\s*(\d+)\s*只", label)
        if not entry:
            continue
        if int(entry.group(2)) <= limit:
            hot.add(_normalise(entry.group(1).strip()))
    return hot


class ThemeIndex:
    """Term lookup over the prebuilt theme index."""

    def __init__(self, path: Optional[Path | str] = None) -> None:
        self.path = Path(path) if path else DEFAULT_INDEX_PATH
        self.themes: Dict[str, Dict[str, Any]] = {}
        self._substring_terms: List[tuple[str, int, float, str]] = []
        self._ascii_terms: List[tuple[re.Pattern[str], str, int, float, str]] = []
        self.available = False
        self._load()

    def _read_index(self) -> Optional[dict]:
        """The index ships zlib-compressed and base64-encoded to stay small.

        It is split over a few part files so that no single one grows past what
        the contents API will accept; the parts are byte-concatenated before
        decoding, and base64 ignores the newlines between them.
        """
        parts = [self.path, *sorted(self.path.parent.glob(self.path.name + ".p[0-9]*"))]
        try:
            raw = b"".join(part.read_bytes() for part in parts if part.exists())
        except OSError as exc:
            logger.warning("A-share theme index unreadable (%s); skipping", exc)
            return None
        if not raw:
            logger.info("A-share theme index not found at %s; skipping", self.path)
            return None
        try:
            if raw[:1] in (b"{", b"["):
                return json.loads(raw)
            return json.loads(zlib.decompress(base64.b64decode(raw)))
        except (ValueError, zlib.error) as exc:
            logger.warning("A-share theme index is corrupt (%s); skipping", exc)
            return None

    def _add_term(self, term: str, weight: float, slug: str) -> None:
        term = _normalise(term)
        if len(term) < 2 or weight <= 0:
            return
        # A bare "ar" inside "L3Harris" is not a mention of AR glasses, so ASCII
        # terms only match on a letter boundary.
        if _ASCII_TERM_RE.fullmatch(term):
            pattern = re.compile(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])")
            self._ascii_terms.append((pattern, term, len(term), weight, slug))
        else:
            self._substring_terms.append((term, len(term), weight, slug))

    def _load(self) -> None:
        doc = self._read_index()
        if not doc:
            return

        # v2: each theme is one row [id, name, member_count, strong, medium,
        # weak, leaders]. The trailing leaders column is no longer read: the
        # page's own strength ranking replaced it, and the index is kept as-is
        # to avoid a rebuild just to drop a column.
        rows = doc.get("themes")
        if not isinstance(rows, list):
            logger.warning("A-share theme index has no themes; skipping")
            return

        for row in rows:
            if not isinstance(row, list) or len(row) < 7:
                continue
            sid, name, count, strong, medium, weak = row[:6]
            if not name:
                continue
            slug = f"/ticai/{sid}.html"
            self.themes[slug] = {"name": name, "n": count}
            for layer, weight in ((strong, 1.0), (medium, 0.75), (weak, 0.5)):
                for term in str(layer or "").split(","):
                    self._add_term(term, weight, slug)

        self._load_alias_overlay()

        self.available = bool(self.themes)
        logger.info(
            "A-share theme index loaded: %d themes, %d substring terms, %d ascii terms",
            len(self.themes),
            len(self._substring_terms),
            len(self._ascii_terms),
        )

    def _load_alias_overlay(self) -> None:
        """Merge data/theme_aliases.json when present, so aliases stay editable."""
        try:
            doc = json.loads(OPTIONAL_ALIAS_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, ValueError):
            return
        by_name = {theme["name"]: slug for slug, theme in self.themes.items()}
        added = 0
        for group in doc.get("groups") or []:
            weight = float(group.get("w", 1.0))
            for theme_name in group.get("themes") or []:
                slug = by_name.get(theme_name)
                if not slug:
                    continue
                for term in group.get("terms") or []:
                    self._add_term(term, weight, slug)
                    added += 1
        if added:
            logger.info("A-share alias overlay merged: %d terms", added)

    def match(
        self,
        text: str,
        top_n: int = MAX_THEMES_PER_ITEM,
        allowed: Optional[set[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return the themes this text names, strongest first.

        ``allowed`` restricts the answer to a set of folded theme names (the
        top-N heat list). None means no restriction, which is also the fallback
        when the listing page could not be read.
        """
        if not self.available:
            return []
        haystack = _normalise(text)
        if not haystack:
            return []

        best: Dict[str, float] = {}
        hit_term: Dict[str, str] = {}
        # Description-layer terms are stored at a low weight. They may only
        # reinforce a theme the text already named, never introduce one: a
        # stockinsky blurb for PCB mentions AI servers as demand, and letting
        # that phrase stand alone would tag every server story as PCB.
        weak_bonus: Dict[str, float] = {}

        def consider(slug: str, term: str, weight: float, length: int) -> None:
            # Longer terms are more specific, so they edge out a short generic one.
            score = weight * (1 + 0.05 * min(length, 12))
            if weight < 0.6:
                weak_bonus[slug] = max(weak_bonus.get(slug, 0), score)
                return
            if score > best.get(slug, 0):
                best[slug] = score
                hit_term[slug] = term

        for term, length, weight, slug in self._substring_terms:
            if term in haystack:
                consider(slug, term, weight, length)
        for pattern, term, length, weight, slug in self._ascii_terms:
            if pattern.search(haystack):
                consider(slug, term, weight, length)

        if not best:
            return []

        for slug, bonus in weak_bonus.items():
            if slug in best:
                best[slug] += bonus * 0.3

        ranked = sorted(best.items(), key=lambda pair: -pair[1])
        leader = ranked[0][1]
        chosen: List[Dict[str, Any]] = []
        seen_terms: set[str] = set()
        chosen_names: List[str] = []

        for slug, score in ranked:
            if len(chosen) >= top_n or score < MIN_SCORE:
                break
            if score < leader * RELATIVE_CUTOFF:
                break
            term = hit_term[slug]
            name = self.themes[slug]["name"]
            if allowed is not None and _normalise(name) not in allowed:
                continue
            # One mention should not produce two name lists: 券商 hits both
            # 证券 and 券商概念, and 电池 is contained in 固态电池.
            if term in seen_terms:
                continue
            if any(name in other or other in name for other in chosen_names):
                continue
            seen_terms.add(term)
            chosen_names.append(name)
            theme = self.themes[slug]
            chosen.append(
                {
                    "slug": slug,
                    "name": name,
                    "score": round(score, 2),
                    "term": term,
                    "members_count": theme.get("n"),
                }
            )
        return chosen

    def all_names(self) -> List[str]:
        """Every theme name in the index, deduplicated and sorted.

        The candidate list handed to the model when the heat list names
        nothing; it comes from the index, so every pick has members to fetch.
        """
        names = {str(theme.get("name") or "").strip() for theme in self.themes.values()}
        names.discard("")
        return sorted(names)

    def _nearest_slug(self, key: str) -> Optional[str]:
        """Resolve a near-miss name to an index theme, or None.

        For 芯片 the index holds both AI芯片 and 芯片概念, and the name that
        *starts* with the answer is the one the model meant; the last step
        covers a model that wrote a longer phrase than the theme name.
        """
        folded = [(slug, _normalise(theme["name"])) for slug, theme in self.themes.items()]
        for predicate, order in (
            (lambda name: name.startswith(key), len),
            (lambda name: key in name, len),
            (lambda name: len(name) >= 3 and name in key, lambda name: -len(name)),
        ):
            hits = [(order(name), slug) for slug, name in folded if predicate(name)]
            if hits:
                return min(hits)[1]
        return None

    def match_names(
        self,
        names: Sequence[str],
        top_n: int = MAX_THEMES_PER_ITEM,
    ) -> List[Dict[str, Any]]:
        """Resolve model-chosen theme names back to index rows.

        The model is told to copy names verbatim; a near miss still resolves
        through ``_nearest_slug`` instead of dropping the whole pick. A name
        nothing matches is dropped, so a rendered line never carries a theme
        without a member list behind it.
        """
        if not self.available:
            return []
        by_folded: Dict[str, str] = {
            _normalise(theme["name"]): slug for slug, theme in self.themes.items()
        }
        chosen: List[Dict[str, Any]] = []
        chosen_names: List[str] = []
        seen_slugs: set[str] = set()

        for raw in names:
            key = _normalise(raw).strip()
            if not key:
                continue
            slug = by_folded.get(key)
            if slug is None:
                slug = self._nearest_slug(key)
            if slug is None or slug in seen_slugs:
                continue
            name = self.themes[slug]["name"]
            # One story should not carry two name lists for the same theme.
            if any(name in other or other in name for other in chosen_names):
                continue
            seen_slugs.add(slug)
            chosen_names.append(name)
            chosen.append(
                {
                    "slug": slug,
                    "name": name,
                    "score": 1.0,
                    "term": str(raw),
                    "members_count": self.themes[slug].get("n"),
                }
            )
            if len(chosen) >= top_n:
                break
        return chosen


class MemberFetcher:
    """Fetch and cache one theme's member list from lianban."""

    # lianban limits by client address, not by object, so the cache, the request
    # budget and the lock belong to the process. The enrichment pass holds the
    # only fetcher now, so a per-run budget is not double-spent.
    _shared_cache: Dict[str, List[str]] = {}
    _shared_slugs: Optional[Dict[str, str]] = None
    _shared_used = 0
    _shared_lock: Optional[asyncio.Lock] = None
    # Folded names inside the top-N heat list; None until the listing is read.
    _shared_hot: Optional[set[str]] = None
    # The budget is reported once, not once per theme that ran into it.
    _shared_exhausted = False
    # Monotonic time before which no fetch may start (set on a 429).
    _shared_cooldown_until = 0.0
    # 跨运行缓存（按题材名归一化后索引），None 表示还没读盘。
    _shared_members: Optional[Dict[str, Dict[str, Any]]] = None
    _shared_members_dirty = False
    _shared_registered = False

    def __init__(
        self,
        budget: int = MAX_THEME_FETCH,
        timeout: float = FETCH_TIMEOUT,
        base_url: str = "https://lianban.net",
    ) -> None:
        self.budget = budget
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self._cache = MemberFetcher._shared_cache
        if MemberFetcher._shared_lock is None:
            MemberFetcher._shared_lock = asyncio.Lock()
        # Fetches are serialised: parallel requests are what trips the limiter.
        self._lock = MemberFetcher._shared_lock

    def _get(self, url: str) -> str:
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
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
        return raw.decode("utf-8", "ignore")

    def _load_slugs(self) -> Dict[str, str]:
        """Read the listing page once and keep the name-to-URL map for the run."""
        try:
            html = self._get(self.base_url + "/ticai/")
        except Exception as exc:  # noqa: BLE001 - a stale URL must not fail the run
            logger.warning(
                "Theme listing page unavailable (%s); keeping the stored URLs", exc
            )
            return {}
        slugs = _parse_theme_links(html)
        MemberFetcher._shared_hot = _parse_hot_names(html, HOT_THEME_LIMIT)
        # WARNING so the line reaches the Actions log: the default level is
        # WARNING, and this is the only evidence that the heat filter loaded.
        logger.warning(
            "lianban theme listing: %d current page URLs, %d inside the top %d",
            len(slugs),
            len(MemberFetcher._shared_hot),
            HOT_THEME_LIMIT,
        )
        return slugs

    def hot_names(self) -> Optional[set[str]]:
        """Top-N heat names, or None when the listing page could not be read.

        Reading the listing is the same request ``_resolve_slug`` needs, so this
        only triggers it early; the result is cached for the run.
        """
        if MemberFetcher._shared_slugs is None:
            MemberFetcher._shared_slugs = self._load_slugs()
        return MemberFetcher._shared_hot

    @classmethod
    def _load_members(cls) -> Dict[str, Dict[str, Any]]:
        """题材成员表的跨运行缓存，落在 data/member_profiles。"""
        if cls._shared_members is not None:
            return cls._shared_members
        items: Dict[str, Dict[str, Any]] = {}
        path = MEMBERS_CACHE_DIR / MEMBERS_CACHE_FILE
        try:
            raw = base64.b64decode(path.read_text(encoding="ascii"))
            doc = json.loads(zlib.decompress(raw).decode("utf-8"))
            if isinstance(doc, dict):
                items = {str(k): v for k, v in doc.items() if isinstance(v, dict)}
        except FileNotFoundError:
            pass
        except Exception as exc:  # noqa: BLE001 - a bad cache must not stop a digest
            logger.warning("Theme member cache unreadable (%s): %s", path, exc)
        cls._shared_members = items
        return items

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

    @classmethod
    def _cached_on(cls, key: str) -> str:
        return str((cls._load_members().get(key) or {}).get("date") or "")

    @classmethod
    def _members(cls, key: str, allow_stale: bool = False) -> List[str]:
        """缓存里的成员表。当天抓的算新鲜，更早的只有明确要旧值时才给。"""
        entry = cls._load_members().get(key) or {}
        names = [str(n) for n in entry.get("members") or [] if str(n).strip()]
        if not names:
            return []
        if entry.get("date") == cls._today() or allow_stale:
            return names
        return []

    @classmethod
    def _remember(cls, key: str, names: List[str]) -> None:
        cls._load_members()[key] = {"date": cls._today(), "members": list(names)}
        cls._shared_members_dirty = True
        if not cls._shared_registered:
            cls._shared_registered = True
            atexit.register(cls.flush_members)

    @classmethod
    def flush_members(cls) -> None:
        """写回缓存。只读 checkout 或坏路径只记一条日志，不影响出报。"""
        if not cls._shared_members_dirty or not cls._shared_members:
            return
        path = MEMBERS_CACHE_DIR / MEMBERS_CACHE_FILE
        try:
            MEMBERS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            raw = zlib.compress(
                json.dumps(cls._shared_members, ensure_ascii=False).encode("utf-8"), 9
            )
            path.write_text(base64.b64encode(raw).decode("ascii"), encoding="ascii")
            # 写成功就清脏，避免 atexit 再写一遍同内容。
            cls._shared_members_dirty = False
            logger.warning(
                "Theme member cache: %d themes written to %s",
                len(cls._shared_members),
                path,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Theme member cache not written (%s): %s", path, exc)


    def _resolve_slug(self, slug: str, name: Optional[str]) -> str:
        """Return the theme's current page path, falling back to the stored one."""
        if not name:
            return slug
        if MemberFetcher._shared_slugs is None:
            MemberFetcher._shared_slugs = self._load_slugs()
        return MemberFetcher._shared_slugs.get(_normalise(name)) or slug

    def _fetch_sync(self, slug: str) -> List[str]:
        html = self._get(self.base_url + slug)
        listed = _parse_itemlist(html)
        ranked = _parse_ranked_names(html)
        if ranked:
            return _merge_ranked_with_codes(ranked, listed)
        if listed:
            return listed

        # Fallback for a page without JSON-LD: the member grid links to /gu/.
        seen: set[str] = set()
        names = []
        for match in _GU_ANCHOR_RE.finditer(html):
            code, name = match.group(1), match.group(2).strip()
            if code in seen:
                continue
            seen.add(code)
            names.append(f"{name}({code})")
        return names

    async def get(
        self,
        slug: str,
        expected: Optional[int] = None,
        name: Optional[str] = None,
    ) -> List[str]:
        async with self._lock:
            # The stored path may predate a change of URL scheme on the site.
            slug = self._resolve_slug(slug, name)
            if slug in self._cache:
                return self._cache[slug]
            # 当天已经抓过这个题材，就不必再花一次请求，也不必赌 lianban 这次不返回 429。
            key = _normalise(name or slug)
            fresh = self._members(key)
            if fresh:
                self._cache[slug] = fresh
                return fresh
            if MemberFetcher._shared_used >= self.budget:
                # Reported once per run: a digest that runs out of budget
                # would otherwise log the same line for every later theme.
                if not MemberFetcher._shared_exhausted:
                    MemberFetcher._shared_exhausted = True
                    logger.warning(
                        "Theme member budget (%d) exhausted after %d fetches; "
                        "%s and the themes after it render without members",
                        self.budget,
                        MemberFetcher._shared_used,
                        slug,
                    )
                return []
            MemberFetcher._shared_used += 1
            names: List[str] = []
            throttled = False
            for attempt in range(1, FETCH_ATTEMPTS + 1):
                await asyncio.sleep(
                    FETCH_SPACING if attempt == 1 else FETCH_RETRY_WAIT
                )
                pause = MemberFetcher._shared_cooldown_until - time.monotonic()
                if pause > 0:
                    await asyncio.sleep(pause)
                try:
                    names = await asyncio.to_thread(self._fetch_sync, slug)
                except Exception as exc:  # noqa: BLE001 - a blocked fetch must not fail the run
                    if getattr(exc, "code", None) == 429:
                        throttled = True
                        MemberFetcher._shared_cooldown_until = (
                            time.monotonic() + RATE_LIMIT_COOLDOWN
                        )
                    logger.warning(
                        "Member fetch failed for %s (attempt %d/%d): %s",
                        slug,
                        attempt,
                        FETCH_ATTEMPTS,
                        exc,
                    )
                    names = []
                if names:
                    break
            if names:
                self._remember(key, names)
            else:
                # 抓不到就用上次那份：题材行宁可旧一天，也不要整行只剩题材名。
                stale = self._members(key, allow_stale=True)
                if stale:
                    logger.warning(
                        "Member fetch empty for theme %s; using the list cached on %s",
                        slug,
                        self._cached_on(key),
                    )
                    self._cache[slug] = stale
                    return stale
                logger.warning(
                    "No members parsed for theme %s (index lists %s); the page "
                    "answered without a member list",
                    slug,
                    expected if expected is not None else "?",
                )
            # A throttled page is not cached: caching it would spread one 429
            # over every later item that uses the same theme.
            if names or not throttled:
                self._cache[slug] = names
            return names


def _parse_itemlist(html: str) -> List[str]:
    """Member names in ticker-code order, straight from the page's JSON-LD."""
    for match in _ITEMLIST_RE.finditer(html):
        try:
            payload = json.loads(match.group(1))
        except ValueError:
            continue
        if payload.get("@type") != "ItemList":
            continue
        names = [
            (entry.get("name") or "").strip()
            for entry in payload.get("itemListElement") or []
        ]
        names = [name for name in names if name]
        if names:
            return names
    return []


def _strip_name_prefix(name: str) -> str:
    """Drop the XD/ST/N markers so a name matches across the two listings."""
    return _NAME_PREFIX_RE.sub("", name).strip()


def _parse_ranked_names(html: str) -> List[str]:
    """The body's ranked list: strongest first, recomputed every close."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    match = _RANKED_RE.search(text)
    if not match:
        return []
    names = []
    for raw_name in match.group(1).split("、"):
        name = re.sub(r"等$", "", raw_name.strip()).strip()
        if name:
            names.append(name)
    return names


def _merge_ranked_with_codes(ranked: Sequence[str], listed: Sequence[str]) -> List[str]:
    """Keep the ranked order and attach a ticker code to each name.

    The body lists only the leading names before "等", so the remaining members
    follow in the JSON-LD order. Only the first few are ever shown, and those
    always come from the ranked list.
    """
    code_of: Dict[str, str] = {}
    for entry in listed:
        match = _LISTED_RE.match(entry)
        if not match:
            continue
        name, code = match.group(1).strip(), match.group(2)
        code_of.setdefault(name, code)
        code_of.setdefault(_strip_name_prefix(name), code)

    merged: List[str] = []
    used: set[str] = set()
    for name in ranked:
        code = code_of.get(name) or code_of.get(_strip_name_prefix(name))
        if code and code in used:
            continue
        if code:
            used.add(code)
            merged.append(f"{name}({code})")
        else:
            merged.append(name)
    for entry in listed:
        match = _LISTED_RE.match(entry)
        if match and match.group(2) not in used:
            used.add(match.group(2))
            merged.append(entry)
    return merged


def pick_members(members: Sequence[str], limit: int = MAX_MEMBERS) -> List[str]:
    """Take the leading names in the order lianban already ranked them.

    Every theme page is sorted by three-month relative strength after each
    close, so the page order is the ranking the reader asked for.
    """
    return list(members[:limit])


def format_theme_line(themes: Sequence[Dict[str, Any]]) -> str:
    """Render the reader-facing line for one item, or '' when nothing matched.

    Only the two directional verdicts are shown: "可能相关" carried nothing the
    headline did not, and on 2026-11-18 it was 22 of 32 lines. A theme whose
    direction call failed still shows under 方向待定, so a miss never reads as
    a neutral verdict. The two verdicts sit in separate paragraphs.

    A theme arrives from the heat list, a model pick or the lexical sweep;
    either way its names are the page's strength ranking, cut to three.
    """
    groups: Dict[str, List[str]] = {POSITIVE: [], NEGATIVE: [], "": []}
    for theme in themes:
        direction = theme.get("direction")
        if direction == NEUTRAL:
            continue
        members = theme.get("members") or []
        label = str(theme["name"])
        if members:
            # Full-width brackets keep the line out of the markdown escaper.
            shown = [m.replace("(", "（").replace(")", "）") for m in members]
            label = f"{label} → {'、'.join(shown)}"
        # The one-line reason is the only record of why a theme was read that
        # way: items are never serialised, so nothing else survives the run.
        reason = direction_note(theme)
        if reason:
            label = f"{label}（{reason}）"
        groups[direction if direction in groups else ""].append(label)

    parts: List[str] = []
    for direction in (POSITIVE, NEGATIVE):
        if groups[direction]:
            parts.append(f"{DIRECTION_LABELS[direction]}：{'，'.join(groups[direction])}")
    if groups[""]:
        parts.append(f"方向待定：{'，'.join(groups[''])}")
    if not parts:
        return ""
    parts[-1] = f"{parts[-1]}（题材为规则匹配、方向为模型推测，非投资建议）"
    return "\n\n".join(parts)


def matching_text(item: Any) -> str:
    """Everything the lookup may read: headline, summary, enriched blocks.

    The enrichment pass calls this once per item, after the background and
    impact blocks exist, so the terms that only appear there are still seen.
    """
    parts: List[str] = [item.title or ""]
    processing = getattr(item, "processing", None)
    analysis = processing.analysis if processing else None
    if analysis and analysis.summary:
        parts.append(analysis.summary)
    if processing:
        for artifact in processing.artifacts.values():
            for block in artifact.blocks:
                if block.content:
                    parts.append(block.content)
    return " ".join(part for part in parts if part)


async def _model_themes(
    text: str,
    index: ThemeIndex,
    picker: Optional[Any],
) -> List[Dict[str, Any]]:
    """Let the model pick themes when the heat list names none.

    The heat list only covers what is traded today and the lexical pass only
    fires on words the index lists; a story outside both used to render with no
    theme line. The model reads the item and picks from the whole index, and
    every pick resolves back to an index row with a real member list.
    """
    if picker is None:
        return []
    names = index.all_names()
    if not names or not text.strip():
        return []
    try:
        picked = await picker.pick(text, names)
    except Exception as exc:  # noqa: BLE001 - a pick miss must not fail the item
        logger.warning("Theme model picker failed: %s", exc)
        return []
    themes = index.match_names(picked)
    if themes:
        # WARNING so the line reaches the Actions log: this is the only record
        # of which pass chose a theme once the item is rendered.
        logger.warning(
            "Theme model pick (no heat match): %s",
            "、".join(str(theme["name"]) for theme in themes),
        )
    return themes


async def attach_themes(
    item: Any,
    index: ThemeIndex,
    fetcher: MemberFetcher,
    picker: Optional[Any] = None,
) -> None:
    """Match the item against the index and store the result on its metadata.

    Runs once per item, from the enrichment pass, and only decides which themes
    the story touches: the member lists are fetched after the direction pass,
    so a theme the line will not show costs no request. A wording match is not
    a carrier, so the conduction gate runs before anything is stored.
    """
    if not index.available or item.metadata is None:
        return
    profile = item.processing.classification.profile if item.processing else None
    if profile not in THEME_PROFILES:
        return

    text = matching_text(item)
    hot = fetcher.hot_names()
    themes = index.match(text, allowed=hot)
    if themes:
        # ``hot is None`` means the listing page could not be read, so the heat
        # filter was off and the match above already covered the whole index.
        source = "full" if hot is None else "heat"
    else:
        source = ""
    if not themes:
        # Nothing in the top-200 heat list names this story. The model reads
        # the item and picks from the whole index, which is the only pass that
        # can reach a theme the text never names outright.
        themes = await _model_themes(text, index, picker)
        source = "model" if themes else ""
    if not themes:
        # Last resort, and the only pass left when the model is unavailable:
        # the full-index lexical sweep keeps the line from vanishing entirely.
        themes = index.match(text)
        source = "lexical" if themes else ""
    if not themes:
        return

    themes = conduction_filter(themes, text, str(getattr(item, "id", "")))
    if not themes:
        return

    for theme in themes:
        # ``hot`` means the theme is inside today's top-200 heat list, whichever
        # pass reached it; a model pick of a hot theme is still a hot theme.
        theme["hot"] = source == "heat" or (
            hot is not None and _normalise(theme["name"]) in hot
        )
        # Which pass chose the theme: heat / model / lexical / full. Kept on the
        # record so a noisy fallback can be told apart from a hot match.
        theme["picked"] = source
    item.metadata["ashare_themes"] = themes


def source_footer() -> str:
    """Attribution required by lianban's CC BY 4.0 licence."""
    return f"题材成员数据来源：{SOURCE_LABEL}（CC BY 4.0）"
