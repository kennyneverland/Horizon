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
run. A failed fetch drops the name list and keeps the theme label, so a
blocked request degrades the line instead of the digest.

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
MAX_THEMES_PER_ITEM = 2
# Three names is what fits on one line next to the theme label.
MAX_MEMBERS = 3
# Requests are cheap but lianban rate-limits aggressively, so the run is capped.
MAX_THEME_FETCH = 6
# The theme lookup only means something to the finance reader; other profiles
# keep their items untouched.
THEME_PROFILES = frozenset({"finance-news"})
FETCH_TIMEOUT = 12.0
SOURCE_LABEL = "连板网 lianban.net"

_ASCII_TERM_RE = re.compile(r"[a-z0-9&.\- ]+")
_CODE_RE = re.compile(r"(\d{6})")
_ITEMLIST_RE = re.compile(
    r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S
)
_GU_ANCHOR_RE = re.compile(r'<a href="/gu/(\d{6})\.html">([^<]+)</a>')


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
        """The index ships zlib-compressed and base64-encoded to stay small."""
        try:
            raw = self.path.read_bytes()
        except FileNotFoundError:
            logger.info("A-share theme index not found at %s; skipping", self.path)
            return None
        except OSError as exc:
            logger.warning("A-share theme index unreadable (%s); skipping", exc)
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
        # weak, leaders] with the term layers as comma-joined strings.
        rows = doc.get("themes")
        if not isinstance(rows, list):
            logger.warning("A-share theme index has no themes; skipping")
            return

        for row in rows:
            if not isinstance(row, list) or len(row) < 7:
                continue
            sid, name, count, strong, medium, weak, leaders = row[:7]
            if not name:
                continue
            slug = f"/ticai/{sid}.html"
            self.themes[slug] = {
                "name": name,
                "n": count,
                "leaders": [code for code in str(leaders or "").split(",") if code],
            }
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
                    "leaders": theme.get("leaders") or [],
                }
            )
        return chosen


class MemberFetcher:
    """Fetch and cache one theme's member list from lianban."""

    def __init__(
        self,
        budget: int = MAX_THEME_FETCH,
        timeout: float = FETCH_TIMEOUT,
        base_url: str = "https://lianban.net",
    ) -> None:
        self.budget = budget
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")
        self._cache: Dict[str, List[str]] = {}
        self._used = 0
        # Fetches are serialised: parallel requests are what trips the limiter.
        self._lock = asyncio.Lock()

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

    async def get(self, slug: str) -> List[str]:
        async with self._lock:
            if slug in self._cache:
                return self._cache[slug]
            if self._used >= self.budget:
                return []
            self._used += 1
            try:
                names = await asyncio.to_thread(self._fetch_sync, slug)
            except Exception as exc:  # noqa: BLE001 - a blocked fetch must not fail the run
                logger.info("Member fetch failed for %s: %s", slug, exc)
                names = []
            self._cache[slug] = names
            return names


def pick_members(
    members: Sequence[str], leaders: Sequence[str], limit: int = MAX_MEMBERS
) -> List[str]:
    """Prefer the industry leaders from stockinsky, then keep the page order.

    lianban lists members by ticker code, not by how central they are to the
    theme, so the first three rows of a 66-name theme can include a cable maker
    that merely trades on the label. Intersecting with stockinsky's leader list
    puts the actual supply-chain names first without inventing anything: every
    name returned here is still a member of the lianban theme.
    """
    by_code: Dict[str, str] = {}
    for member in members:
        match = _CODE_RE.search(member)
        if match:
            by_code.setdefault(match.group(1), member)

    picked: List[str] = []
    for code in leaders:
        member = by_code.get(code)
        if member and member not in picked:
            picked.append(member)
        if len(picked) >= limit:
            return picked

    for member in members:
        if member not in picked:
            picked.append(member)
        if len(picked) >= limit:
            break
    return picked


def format_theme_line(themes: Sequence[Dict[str, Any]]) -> str:
    """Render the reader-facing line for one item, or '' when nothing matched."""
    parts: List[str] = []
    for theme in themes:
        members = theme.get("members") or []
        label = theme["name"]
        if members:
            # Full-width brackets keep the line out of the markdown escaper.
            shown = [m.replace("(", "（").replace(")", "）") for m in members]
            parts.append(f"{label} → {'、'.join(shown)}")
        else:
            parts.append(label)
    if not parts:
        return ""
    return f"可能相关：{'；'.join(parts)}（规则匹配推测，非投资建议）"


async def attach_themes(
    item: Any,
    index: ThemeIndex,
    fetcher: MemberFetcher,
) -> None:
    """Match the item against the index and store the result on its metadata."""
    if not index.available or item.metadata is None:
        return
    if item.metadata.get("ashare_themes"):
        return
    profile = item.processing.classification.profile if item.processing else None
    if profile not in THEME_PROFILES:
        return

    analysis = item.processing.analysis if item.processing else None
    text = " ".join(
        part
        for part in (
            item.title or "",
            analysis.summary if analysis else "",
        )
        if part
    )
    themes = index.match(text)
    if not themes:
        return

    for theme in themes:
        members = await fetcher.get(theme["slug"])
        theme["members"] = pick_members(members, theme.get("leaders") or [])
    item.metadata["ashare_themes"] = themes


def source_footer() -> str:
    """Attribution required by lianban's CC BY 4.0 licence."""
    return f"题材成员数据来源：{SOURCE_LABEL}（CC BY 4.0）"
