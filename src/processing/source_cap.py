"""Optional per-source and language-origin caps for the balanced digest.

The balanced digest only enforces quotas per profile group, so a single
high-volume feed can consume most of a group's slots and crowd out every other
source in that group. This module adds two optional limits on top of it:

* a cap on how many items a single publisher may contribute, counted per
  *publisher* rather than per feed, so sibling feeds from the same outlet
  (Bloomberg Business / Markets / Technology) share one quota;
* a domestic-source balance rule, so Chinese-language outlets together never
  outnumber foreign outlets.

Limits are read from ``data/digest_limits.json`` so they can be tuned without
touching the validated config schema::

    {
      "per_source_limit": 8,
      "publisher_limits": {"华尔街见闻": 4},
      "domestic_publishers": ["zaihuapd", "speckx"]
    }

``per_source_limit`` is the default for every publisher; ``publisher_limits``
overrides it for the named outlets, either tighter (a noisy feed) or wider (a
high-value feed). Publishers whose name contains CJK characters count as
domestic automatically, so ``domestic_publishers`` only needs the romanised
names. Use ``null`` for ``per_source_limit`` (or delete the file) to disable
the publisher cap; the domestic balance rule stays active whenever the file
lists domestic outlets.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


DEFAULT_LIMITS_PATH = Path("data/digest_limits.json")
_PUBLISHER_SPLIT_RE = re.compile(r"[\s(\u2013\u2014-]+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# Safety valve so the balance loop can never spin on a pathological pool.
_MAX_BALANCE_ROUNDS = 30


def _load_limits(path: Optional[Path] = None) -> Dict[str, Any]:
    """Return the parsed limits file, or an empty mapping when unreadable."""
    target = Path(path) if path is not None else DEFAULT_LIMITS_PATH
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def load_per_source_limit(path: Optional[Path] = None) -> Optional[int]:
    """Return the configured default per-source cap, or ``None`` when disabled."""
    value = _load_limits(path).get("per_source_limit")
    if value is None:
        return None
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return None
    return limit if limit > 0 else None


def load_publisher_limits(path: Optional[Path] = None) -> Dict[str, int]:
    """Return per-publisher cap overrides keyed by normalized publisher name."""
    overrides = _load_limits(path).get("publisher_limits")
    if not isinstance(overrides, dict):
        return {}

    result: Dict[str, int] = {}
    for name, value in overrides.items():
        if not isinstance(name, str) or not name.strip():
            continue
        try:
            cap = int(value)
        except (TypeError, ValueError):
            continue
        if cap > 0:
            result[_publisher_label(name.strip())] = cap
    return result


def load_domestic_publishers(path: Optional[Path] = None) -> Set[str]:
    """Return explicitly configured domestic publishers, normalized."""
    configured = _load_limits(path).get("domestic_publishers")
    if not isinstance(configured, list):
        return set()
    return {
        _publisher_label(name.strip())
        for name in configured
        if isinstance(name, str) and name.strip()
    }


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


def _publisher_of(key: str) -> str:
    return key.split("/", 1)[1] if "/" in key else key


def _score(item: Any) -> float:
    processing = getattr(item, "processing", None)
    analysis = getattr(processing, "analysis", None) if processing else None
    score = getattr(analysis, "score", None) if analysis else None
    return score if score is not None else -1.0


def _is_domestic(orchestrator: Any, item: Any, extra: Set[str]) -> bool:
    publisher = _publisher_of(source_key(orchestrator, item))
    return publisher in extra or bool(_CJK_RE.search(publisher))


def _average_score(items: List[Any]) -> float:
    return sum(_score(item) for item in items) / len(items) if items else -1.0


def _trim_by_publisher_cap(
    orchestrator: Any,
    pool: List[Any],
    base: Callable[..., Any],
    limit: int,
    *,
    log: bool,
) -> List[Any]:
    """Drop the lowest-scoring items above a publisher's cap from the pool."""
    overrides = load_publisher_limits()

    def cap_for(key: str) -> int:
        # An explicit override replaces the default, so it can either tighten a
        # noisy outlet or widen a high-value one.
        return overrides.get(_publisher_of(key), limit)

    for _ in range(5):
        result = base(pool, log=False)
        counts = Counter(source_key(orchestrator, item) for item in result.items)
        over = {key: count for key, count in counts.items() if count > cap_for(key)}
        if not over:
            break

        kept: List[Any] = []
        seen: Dict[str, int] = defaultdict(int)
        dropped: Dict[str, int] = defaultdict(int)
        for item in sorted(pool, key=_score, reverse=True):
            key = source_key(orchestrator, item)
            if key in over:
                seen[key] += 1
                if seen[key] > cap_for(key):
                    dropped[key] += 1
                    continue
            kept.append(item)

        if len(kept) == len(pool):
            break
        if log:
            for key, count in sorted(dropped.items()):
                orchestrator.console.print(
                    f"      {orchestrator.icons['detail']} per-publisher cap "
                    f"{cap_for(key)}: trimmed {count} extra item(s) from {key}"
                )
        pool = kept

    return pool


def _trim_by_domestic_balance(
    orchestrator: Any,
    pool: List[Any],
    base: Callable[..., Any],
    *,
    log: bool,
) -> List[Any]:
    """Drop domestic items until they no longer outnumber foreign ones."""
    extra = load_domestic_publishers()
    if not extra and not any(
        _CJK_RE.search(_publisher_of(source_key(orchestrator, item))) for item in pool
    ):
        return pool

    dropped = 0
    for _ in range(_MAX_BALANCE_ROUNDS):
        result = base(pool, log=False)
        domestic = [
            item for item in result.items if _is_domestic(orchestrator, item, extra)
        ]
        foreign = len(result.items) - len(domestic)
        if len(domestic) < foreign:
            break
        if not domestic:
            break

        # Trim from the largest domestic contributor so smaller outlets keep
        # their slots instead of being wiped out by the score ordering.
        by_publisher: Dict[str, List[Any]] = defaultdict(list)
        for item in domestic:
            by_publisher[_publisher_of(source_key(orchestrator, item))].append(item)
        target = max(
            by_publisher,
            key=lambda name: (len(by_publisher[name]), -_average_score(by_publisher[name])),
        )
        victim = min(by_publisher[target], key=_score)
        pool = [item for item in pool if item is not victim]
        dropped += 1

    if log and dropped:
        orchestrator.console.print(
            f"      {orchestrator.icons['detail']} domestic balance: trimmed {dropped} "
            "domestic item(s) to keep Chinese sources below foreign sources"
        )
    return pool


def apply_balanced_digest_with_cap(
    orchestrator: Any,
    items: List[Any],
    base: Callable[..., Any],
    *,
    limit: Optional[int],
    log: bool = True,
):
    """Run ``base`` after enforcing the publisher cap and the domestic balance rule.

    Items are removed from the candidate pool (lowest score first) rather than
    from the result, so freed slots are refilled by other sources instead of
    shrinking the digest.
    """
    pool = list(items)
    if limit:
        pool = _trim_by_publisher_cap(orchestrator, pool, base, limit, log=log)
    pool = _trim_by_domestic_balance(orchestrator, pool, base, log=log)
    return base(pool, log=log)
