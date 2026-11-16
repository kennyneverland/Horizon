"""Attach the A-share theme an item touches, and the names listed under it.

The digest follows AI and computing power, so a story about Nvidia's CEO
leaving matters to the reader mainly through the mainland supply chain it
drags on. That link is not in the headline, and the analyser is told not to
speculate about impact, so the theme has to come from a lookup rather than
from the model.

Two public datasets are joined here:

* ``lianban.net`` publishes 750 theme pages, each with the full member list in
  schema.org ``ItemList`` JSON-LD. It is the only source of *names* — the
  digest never invents a ticker. Licence: CC BY 4.0, attribution required.
* ``stockinsky.com`` publishes 635 concept pages with a one-paragraph
  description of what each concept covers. Those descriptions are used only to
  widen the vocabulary of a theme (so "AI 服务器" reaches 算力概念 even though
  the theme name does not contain it), never to pick a ticker.

Theme matching is lexical, not model-driven: a title hits a theme when it
contains one of that theme's terms. Terms come from three layers, in
descending weight — a hand-maintained alias table (英伟达 / 黄仁勋 / NVDA →
英伟达概念), the theme name and its variants, and stockinsky's description
phrases. Without the alias layer a headline like "黄仁勋离职后持股减持约束"
scores nothing, because it never says 英伟达.

Members are fetched at render time, one request per matched theme, capped per
run. lianban already sorts every theme page by three-month relative strength
and recomputes it after each close, so the page order *is* the ranking: the
first names are the strongest in the theme. No re-ranking happens here.

A failed fetch drops the name list and keeps the theme label, so a blocked
request degrades the line instead of the digest.

Everything here is a lookup, not a recommendation: the rendered line is marked
as inferred and carries the source attribution.
"""

from __future__ import annotations

import asyncio
import base64
import gzip
import json
import logging
import re
import unicodedata
import urllib.request
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

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
# Five names covers the leading row of a theme without turning the line into a list.
MAX_MEMBERS = 5
# Requests are cheap but lianban rate-limits aggressively, so the run is capped.
# Fetches are serialised and cached per theme, so a repeated theme costs nothing.
MAX_THEME_FETCH = 24
# The lookup runs twice per item: once on the headline and summary, once again
# after enrichment, when the background and impact blocks exist. Only the first
# sighting of a theme costs a request, so the cap covers both passes.
# A page that answers without a member list is treated as a miss, not as an
# empty theme: lianban throttles by serving a stub page, so one retry after a
# short pause usually recovers it.
FETCH_ATTEMPTS = 2
FETCH_RETRY_WAIT = 1.5
# Spacing two different themes apart keeps a burst from tripping the limiter.
FETCH_SPACING = 0.4
# The theme lookup means something to every reader who follows the AI and
# computing supply chain, so the AI profiles carry it too; tech-blog does not.
THEME_PROFILES = frozenset({"finance-news", "tech-news", "ai-hardware", "ai-app"})
FETCH_TIMEOUT = 12.0
SOURCE_LABEL = "连板网 lianban.net"
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


def _normalise(text: Any) -> str:
    """Fold width and case so a term matches regardless of how it was typed."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", str(text)).lower()


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

    def match(self, text: str, top_n: int = MAX_THEMES_PER_ITEM) -> List[Dict[str, Any]]:
        """Return the themes this text names, strongest first."""
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


class MemberFetcher:
    """Fetch and cache one theme's member list from lianban."""

    # lianban limits by client address, not by object, so the cache, the request
    # budget and the lock belong to the process. The analyser and the enricher
    # each hold a fetcher; separate budgets would double the requests per run.
    _shared_cache: Dict[str, List[str]] = {}
    _shared_used = 0
    _shared_lock: Optional[asyncio.Lock] = None

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

    def _fetch_sync(self, slug: str) -> List[str]:
        url = self.base_url + slug
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
        html = raw.decode("utf-8", "ignore")
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

    async def get(self, slug: str, expected: Optional[int] = None) -> List[str]:
        async with self._lock:
            if slug in self._cache:
                return self._cache[slug]
            if MemberFetcher._shared_used >= self.budget:
                logger.warning(
                    "Theme member budget (%d) exhausted; %s and later themes "
                    "render without members",
                    self.budget,
                    slug,
                )
                return []
            MemberFetcher._shared_used += 1
            names: List[str] = []
            for attempt in range(1, FETCH_ATTEMPTS + 1):
                await asyncio.sleep(
                    FETCH_SPACING if attempt == 1 else FETCH_RETRY_WAIT
                )
                try:
                    names = await asyncio.to_thread(self._fetch_sync, slug)
                except Exception as exc:  # noqa: BLE001 - a blocked fetch must not fail the run
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
            if not names:
                logger.warning(
                    "No members parsed for theme %s (index lists %s); the page "
                    "answered without a member list",
                    slug,
                    expected if expected is not None else "?",
                )
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

    Every theme page is sorted by three-month relative strength and recomputed
    after each close, so no re-ranking is applied here: the page order is the
    ranking the reader asked for.
    """
    return list(members[:limit])


def format_theme_line(themes: Sequence[Dict[str, Any]]) -> str:
    """Render the reader-facing line for one item, or '' when nothing matched.

    Themes are grouped by the direction the story was judged to have on their
    constituents: positive, then negative, then neutral. A theme the direction
    pass left without a verdict (its call failed, or the item never reached it)
    is still shown, but in a group that claims no direction at all, so a miss is
    never read as a neutral verdict.
    """
    groups: Dict[str, List[str]] = {POSITIVE: [], NEGATIVE: [], NEUTRAL: [], "": []}
    for theme in themes:
        members = theme.get("members") or []
        label = str(theme["name"])
        if members:
            # Full-width brackets keep the line out of the markdown escaper.
            shown = [m.replace("(", "（").replace(")", "）") for m in members]
            label = f"{label} → {'、'.join(shown)}"
        # The one-line reason is the only record of why a theme was read that
        # way: items are never serialised, so nothing else survives the run.
        reason = str(theme.get("direction_reason") or "").strip()
        if reason:
            label = f"{label}（{reason}）"
        direction = theme.get("direction")
        groups[direction if direction in DIRECTION_LABELS else ""].append(label)

    parts: List[str] = []
    for direction in (POSITIVE, NEGATIVE, NEUTRAL):
        if groups[direction]:
            parts.append(f"{DIRECTION_LABELS[direction]}：{'，'.join(groups[direction])}")
    if groups[""]:
        parts.append(f"方向待定：{'，'.join(groups[''])}")
    if not parts:
        return ""
    return f"{'；'.join(parts)}（题材为规则匹配、方向为模型推测，非投资建议）"


def matching_text(item: Any) -> str:
    """Everything the lookup may read: headline, summary, enriched blocks.

    The analysis pass only has the first two, so most theme terms stay unseen
    until the background and impact blocks exist.
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


async def attach_themes(
    item: Any,
    index: ThemeIndex,
    fetcher: MemberFetcher,
) -> None:
    """Match the item against the index and store the result on its metadata.

    Runs twice per item: after analysis, and again after enrichment. The second
    call reads a superset of the first call's text, so it replaces the list; the
    member lists come from the shared cache and cost no extra request.
    """
    if not index.available or item.metadata is None:
        return
    profile = item.processing.classification.profile if item.processing else None
    if profile not in THEME_PROFILES:
        return

    themes = index.match(matching_text(item))
    if not themes:
        return

    for theme in themes:
        members = await fetcher.get(theme["slug"], theme.get("members_count"))
        theme["members"] = pick_members(members)
    item.metadata["ashare_themes"] = themes


def source_footer() -> str:
    """Attribution required by lianban's CC BY 4.0 licence."""
    return f"题材成员数据来源：{SOURCE_LABEL}（CC BY 4.0）"
