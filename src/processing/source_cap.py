"""Optional per-source cap for the balanced digest.

The balanced digest only enforces quotas per profile group, so a single
high-volume feed can consume most of a group's slots and crowd out every other
source in that group. This module adds an optional cap on how many items a
single publisher may contribute, while still letting the remaining slots be
filled by other sources.

The cap counts items per *publisher*, not per feed, so sibling feeds from the
same outlet (Bloomberg Business / Markets / Technology) share one quota instead
of each getting a full allowance.

The cap is read from ``data/digest_limits.json`` so it can be tuned without
touching the validated config schema::

    {"per_source_limit": 6}

Use ``null`` (or delete the file) to disable the cap.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


DEFAULT_LIMITS_PATH = Path("data/digest_limits.json")
_PUBLISHER_SPLIT_RE = re.compile(r"[\s(\u2013\u2014-]+")


def load_per_source_limit(path: Optional[Path] = None) -> Optional[int]:
    """Return the configured per-source cap, or ``None`` when disabled."""
    target = Path(path) if path is not None else DEFAULT_LIMITS_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = raw.get("per_source_limit") if isinstance(raw, dict) else None
    if value is None:
        return None
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return None
    return limit if limit > 0 else None


def _publisher_label(label: str) -> str:
    """Collapse a feed label to its publisher name.

    ``Bloomberg Business``, ``Bloomberg Markets`` and ``Bloomberg Technology``
    all reduce to ``bloomberg`` so they share a single quota.
    """
    parts = [part for part in _PUBLISHER_SPLIT_RE.split(label) if part]
    return parts[0].lower() if parts else label.lower()


def source_key(orchestrator: Any, item: Any) -> str:
    """Return a publisher-level ``source/label`` key for cap accounting."""
    label = orchestrator._sub_source_label(item)
    source_type = getattr(item.source_type, "value", item.source_type)
    return f"{source_type}/{_publisher_label(label)}"


def _score(item: Any) -> float:
    processing = getattr(item, "processing", None)
    analysis = getattr(processing, "analysis", None) if processing else None
    score = getattr(analysis, "score", None) if analysis else None
    return score if score is not None else -1.0


def apply_balanced_digest_with_cap(
    orchestrator: Any,
    items: List[Any],
    base: Callable[..., Any],
    *,
    limit: Optional[int],
    log: bool = True,
):
    """Run ``base`` until no single publisher exceeds ``limit`` selected items.

    Items are removed from the candidate pool (lowest score first) rather than
    from the result, so the freed slots are refilled by other sources instead of
    shrinking the digest.
    """
    if not limit:
        return base(items, log=log)

    pool = list(items)
    for _ in range(5):
        result = base(pool, log=False)
        counts = Counter(source_key(orchestrator, item) for item in result.items)
        over = {key: count for key, count in counts.items() if count > limit}
        if not over:
            break

        kept: List[Any] = []
        seen: Dict[str, int] = defaultdict(int)
        dropped: Dict[str, int] = defaultdict(int)
        for item in sorted(pool, key=_score, reverse=True):
            key = source_key(orchestrator, item)
            if key in over:
                seen[key] += 1
                if seen[key] > limit:
                    dropped[key] += 1
                    continue
            kept.append(item)

        if len(kept) == len(pool):
            break
        if log:
            for key, count in sorted(dropped.items()):
                orchestrator.console.print(
                    f"      {orchestrator.icons['detail']} per-publisher cap {limit}: "
                    f"trimmed {count} extra item(s) from {key}"
                )
        pool = kept

    return base(pool, log=log)
