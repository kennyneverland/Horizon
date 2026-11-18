"""Weekly refresh of the lianban theme index.

The index ships as four base64 parts so no single file grows past what the
contents API accepts. It used to be rebuilt by hand, which is why it was still
carrying the 2026-11-15 snapshot on 2026-11-18 while the listing page had 44
more themes: 算力租赁 and 智算中心（AIDC） were missing from the catalogue the
model chooses from, so no prompt could ever pick them.

Sunday's run rebuilds the catalogue instead of publishing a digest. New themes
are appended with keywords derived from the name; an existing theme keeps its
row untouched, so a rebuilt index never moves a term to a different theme. The
commit goes through the Git trees API in one commit, using the token the
workflow already passes in.
"""

import base64
import json
import logging
import os
import re
import urllib.error
import urllib.request
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

LISTING_URL = "https://lianban.net/ticai/"
INDEX_NAME = "theme_index.json.gz.b64"
PART_COUNT = 4
API_ROOT = "https://api.github.com"
USER_AGENT = "Horizon-theme-index/1.0"

# The listing labels a theme either "AIGC概念热度第252 · 117只" or, for the
# tail of the page, "辅料— · 4只"; both carry the name and the member count.
_HOT_LABEL_RE = re.compile(r"^(.*?)\s*热度第\s*(\d+)\s*·\s*(\d+)\s*只")
_PLAIN_LABEL_RE = re.compile(r"^(.*?)—\s*·\s*(\d+)\s*只")
_LINK_RE = re.compile(r'href="(/ticai/[a-z0-9]+-[0-9a-f]{4}\.html)"[^>]*>(.*?)</a>', re.S)
_TAG_RE = re.compile(r"<[^>]+>")


def is_refresh_day(now: Optional[datetime] = None) -> bool:
    """True on Sunday in Asia/Shanghai, or when forced by the environment.

    ``HORIZON_THEME_REFRESH=always`` runs the refresh on any day (a manual
    workflow_dispatch on a weekday uses it); ``never`` skips it on Sunday.
    """
    mode = os.environ.get("HORIZON_THEME_REFRESH", "").strip().lower()
    if mode in {"always", "1", "true", "yes"}:
        return True
    if mode in {"never", "0", "false", "no"}:
        return False
    moment = now or datetime.now(ZoneInfo("Asia/Shanghai"))
    return moment.weekday() == 6


def fetch_listing(url: str = LISTING_URL, timeout: float = 30.0) -> str:
    """Read the listing page; the caller parses it."""
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


def parse_listing(html: str) -> Dict[str, Dict[str, Any]]:
    """Map a theme page path to its name and member count."""
    themes: Dict[str, Dict[str, Any]] = {}
    for match in _LINK_RE.finditer(html):
        path, label = match.group(1), _TAG_RE.sub("", match.group(2)).strip()
        hot = _HOT_LABEL_RE.match(label)
        if hot:
            themes[path] = {"name": hot.group(1).strip(), "count": int(hot.group(3))}
            continue
        plain = _PLAIN_LABEL_RE.match(label)
        if plain:
            themes[path] = {"name": plain.group(1).strip(), "count": int(plain.group(2))}
    return themes


def read_index(data_dir: Path) -> Dict[str, Any]:
    """Decode the four parts exactly the way the runtime reads them."""
    base = data_dir / INDEX_NAME
    parts = [base, *sorted(base.parent.glob(base.name + ".p[0-9]*"))]
    raw = b"".join(part.read_bytes() for part in parts if part.exists())
    if not raw:
        return {"meta": {"themes": 0, "sources": []}, "themes": []}
    return json.loads(zlib.decompress(base64.b64decode(raw)))


def auto_terms(name: str) -> tuple[str, str]:
    """Keywords derived from the name alone, for a theme the index lacks.

    A name is its own strongest term; a bracketed alias such as （AIDC） is
    split out so the English form matches too. Nothing is invented: the
    fallback is deliberately thin, because a wrong keyword moves unrelated
    stories onto this theme every day.
    """
    core = re.sub(r"[（(].*?[)）]", "", name).strip()
    strong = [name]
    bracketed = re.search(r"[（(]([^）)]+)[)）]", name)
    if bracketed:
        for token in re.split(r"[/,，、]", bracketed.group(1)):
            token = token.strip()
            if token:
                strong.append(token)
    if core and core != name:
        strong.append(core)
    medium = []
    for suffix in ("概念", "板块", "指数"):
        if core.endswith(suffix) and len(core) > len(suffix) + 1:
            medium.append(core[: -len(suffix)])
    return ",".join(dict.fromkeys(strong)), ",".join(dict.fromkeys(medium))


def build_document(listing: Dict[str, Dict[str, Any]], current: Dict[str, Any]) -> Dict[str, Any]:
    """Append the themes the index lacks; keep every existing row as it is."""
    rows: List[List[Any]] = list(current.get("themes") or [])
    known_paths = {f"/ticai/{row[0]}.html" for row in rows if row}
    taken: set[str] = set()
    for row in rows:
        for layer in row[3:6]:
            for term in str(layer or "").split(","):
                if term.strip():
                    taken.add(term.strip())

    added: List[str] = []
    for path, info in sorted(listing.items(), key=lambda item: -item[1]["count"]):
        if path in known_paths:
            continue
        name = info["name"]
        strong, medium = auto_terms(name)
        # A theme may claim its own name even when another theme already lists
        # it as a keyword: 算力租赁 was a keyword of 算力概念, and without this
        # the new theme would be recalled only by its rarer aliases.
        kept_strong = [
            term
            for term in strong.split(",")
            if term and (term == name or term not in taken)
        ]
        kept_medium = [
            term for term in medium.split(",") if term and term not in taken
        ]
        sid = path.replace("/ticai/", "").replace(".html", "")
        rows.append([sid, name, info["count"], ",".join(kept_strong), ",".join(kept_medium), "", ""])
        for term in kept_strong + kept_medium:
            taken.add(term)
        known_paths.add(path)
        added.append(name)

    gone = [
        row[1]
        for row in rows
        if f"/ticai/{row[0]}.html" not in listing
    ]
    document = {
        "meta": {
            "built": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d"),
            "themes": len(rows),
            "sources": current.get("meta", {}).get("sources", []),
        },
        "themes": rows,
    }
    logger.warning(
        "Theme index rebuilt: %d themes (%d added, %d no longer listed)",
        len(rows),
        len(added),
        len(gone),
    )
    if added:
        logger.warning("Theme index added: %s", "、".join(added[:30]))
    if gone:
        logger.warning("Theme index still keeps: %s", "、".join(gone[:15]))
    return document


def write_parts(document: Dict[str, Any], data_dir: Path) -> List[Path]:
    """Split the encoded index into the parts the runtime concatenates."""
    payload = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode()
    blob = base64.b64encode(zlib.compress(payload, 9))
    step = max(1, -(-len(blob) // PART_COUNT))
    chunks = [blob[i * step : (i + 1) * step] for i in range(PART_COUNT)]
    chunks = [chunk for chunk in chunks if chunk]
    names = [INDEX_NAME] + [f"{INDEX_NAME}.p{i}" for i in range(2, len(chunks) + 1)]
    written = []
    for name, chunk in zip(names, chunks):
        path = data_dir / name
        path.write_bytes(chunk)
        written.append(path)
    return written


def _api(method: str, path: str, token: str, payload: Optional[dict] = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        API_ROOT + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read() or b"{}")


def commit_parts(paths: Sequence[Path], repo: str, token: str, branch: str = "main") -> str:
    """Commit every part in one commit through the Git trees API."""
    ref = _api("GET", f"/repos/{repo}/git/ref/heads/{branch}", token)
    head = ref["object"]["sha"]
    base_tree = _api("GET", f"/repos/{repo}/git/commits/{head}", token)["tree"]["sha"]
    tree = []
    for path in paths:
        blob = _api(
            "POST",
            f"/repos/{repo}/git/blobs",
            token,
            {"content": base64.b64encode(path.read_bytes()).decode(), "encoding": "base64"},
        )
        tree.append({"path": f"data/{path.name}", "mode": "100644", "type": "blob", "sha": blob["sha"]})
    new_tree = _api(
        "POST",
        f"/repos/{repo}/git/trees",
        token,
        {"base_tree": base_tree, "tree": tree},
    )
    commit = _api(
        "POST",
        f"/repos/{repo}/git/commits",
        token,
        {
            "message": f"chore(index): 每周日更新 lianban 题材库（{len(paths)} 个分片）",
            "tree": new_tree["sha"],
            "parents": [head],
        },
    )
    _api(
        "PATCH",
        f"/repos/{repo}/git/refs/heads/{branch}",
        token,
        {"sha": commit["sha"], "force": False},
    )
    return commit["sha"]


async def refresh_theme_index(data_dir: Path) -> int:
    """Rebuild the index and commit it; returns the theme count left on disk.

    A listing that cannot be read leaves the shipped index alone: a Sunday
    without a refresh costs nothing, a half-written catalogue costs the whole
    next week's picks. The return value is 0 only when nothing could be read.
    """
    try:
        html = fetch_listing()
    except (OSError, zlib.error) as exc:
        logger.warning("Theme listing unreachable (%s); keeping the current index", exc)
        return 0
    listing = parse_listing(html)
    if len(listing) < 100:
        kept = len(read_index(data_dir).get("themes") or [])
        logger.warning(
            "Theme listing looks truncated (%d themes); keeping the current %d themes",
            len(listing),
            kept,
        )
        return kept
    current = read_index(data_dir)
    before = len(current.get("themes") or [])
    document = build_document(listing, current)
    if len(document["themes"]) == before:
        logger.warning("Theme index unchanged (%d themes); nothing to commit", before)
        return before
    paths = write_parts(document, data_dir)
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if repo and token:
        try:
            commit = commit_parts(paths, repo, token)
            logger.warning("Theme index committed: %s", commit)
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            logger.warning("Theme index commit failed: %s", exc)
    else:
        logger.warning("Theme index rebuilt locally; no repository token to commit with")
    return len(document["themes"])
