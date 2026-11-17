"""Make the per-source ``max_items`` that the config declares actually apply.

``RSSSourceConfig`` has no ``max_items`` field, so pydantic drops the value at
validation time and ``RSSScraper`` falls back to the global cap for every feed.
``data/config.github.json`` sets a different cap per feed (3/4/5/6/8/10/12/14/15),
so the whole set was dead configuration: 华尔街见闻 declared 6 and still yielded 8.

Three pieces, because the schema route alone is not enough:

1. ``extra="allow"`` on ``RSSSourceConfig``, then rebuild every model in
   ``src.models``. Pydantic copies a nested model's schema into its parent when
   the parent is built, so rebuilding the child alone leaves ``Config``
   validating with the old ``extra="ignore"`` schema and the value is dropped
   again. Rebuilding the parents too lets the extras survive validation and
   round-trip through ``model_dump``, so the setup wizard cannot silently lose
   them.
2. A ``Config.model_validate`` hook that copies ``max_items`` from the raw
   mapping onto the validated sources. This is the layer that guarantees the
   value reaches the scraper even when a schema rebuild fails, and it reports
   the cap distribution once per run.
3. A wrapper around ``RSSScraper.fetch`` that logs how many feeds stopped at
   their cap. Without it a silently ignored cap and a working one look exactly
   the same in the run log.

The real fix is one field on ``RSSSourceConfig`` in ``src/models.py``
(``max_items: Optional[int] = None``); that file is larger than the single-write
limit of the tooling used here, so the schema is adjusted at import time.
Delete this module once the field exists.
"""

from __future__ import annotations

import logging
import sys
from collections import Counter
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .. import models as _models
from ..models import Config, RSSSourceConfig

logger = logging.getLogger(__name__)

# Mirrors the fallback in scrapers/rss.py; used only to describe the effective
# cap of a feed that declares none.
GLOBAL_DEFAULT_CAP = 8


def _enable_extra_keys() -> None:
    """Let ``RSSSourceConfig`` keep keys the model does not declare."""
    try:
        RSSSourceConfig.model_config["extra"] = "allow"
    except Exception:  # noqa: BLE001 - the validate hook still applies the caps
        logger.debug("could not switch RSSSourceConfig to extra=allow", exc_info=True)
        return

    # Two passes: a container caches the child schema it was built with, so it
    # has to be rebuilt after the child. A model that refuses to rebuild keeps
    # its old schema; layer 2 covers that case.
    for _ in range(2):
        for obj in list(vars(_models).values()):
            if not isinstance(obj, type) or obj is BaseModel:
                continue
            if not issubclass(obj, BaseModel):
                continue
            try:
                obj.model_rebuild(force=True)
            except Exception:  # noqa: BLE001 - unresolved forward ref, keep going
                logger.debug(
                    "model_rebuild skipped for %s", obj.__name__, exc_info=True
                )


def _set_cap(source: Any, cap: Optional[int]) -> None:
    """Store the cap where attribute lookup will find it.

    With ``extra="allow"`` active the value lives in ``__pydantic_extra__``;
    writing there keeps ``model_dump`` consistent, so a later ``save_config``
    cannot write back a stale or unusable value.
    """
    extra = getattr(source, "__pydantic_extra__", None)
    if isinstance(extra, dict):
        if cap is None:
            extra.pop("max_items", None)
        else:
            extra["max_items"] = cap
        return
    object.__setattr__(source, "max_items", cap)


def _coerce_cap(value: Any) -> Optional[int]:
    """Return a usable cap, or ``None`` when the value is not a positive integer."""
    try:
        cap = int(value)
    except (TypeError, ValueError):
        return None
    return cap if cap > 0 else None


def _raw_rss_entries(raw: Any) -> List[Dict[str, Any]]:
    """Return the ``sources.rss`` entries of a raw config mapping."""
    if not isinstance(raw, dict):
        return []
    sources = raw.get("sources")
    if not isinstance(sources, dict):
        return []
    entries = sources.get("rss")
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def apply_item_caps(config: Any, raw: Any) -> int:
    """Copy ``max_items`` from the raw config onto the validated RSS sources.

    Returns the number of feeds that ended up carrying a cap.
    """
    rss = list(getattr(getattr(config, "sources", None), "rss", None) or [])
    applied = 0
    for entry, source in zip(_raw_rss_entries(raw), rss):
        value = entry.get("max_items")
        if value is None:
            continue
        cap = _coerce_cap(value)
        if cap is None:
            # ``extra="allow"`` kept the raw value, and the scraper compares
            # ``len(items) >= cap``, so a non-integer would raise mid-fetch.
            logger.warning(
                "RSS source %r: ignoring unusable max_items %r", entry.get("name"), value
            )
            try:
                _set_cap(source, None)
            except Exception:  # noqa: BLE001 - keep the other feeds going
                pass
            continue
        if getattr(source, "max_items", None) != cap:
            try:
                # Falls back to an instance attribute when the schema rebuild
                # did not take; the scraper only reads with getattr.
                _set_cap(source, cap)
            except Exception:  # noqa: BLE001 - keep the other feeds going
                logger.warning(
                    "RSS source %r: could not apply max_items %d",
                    entry.get("name"),
                    cap,
                    exc_info=True,
                )
                continue
        applied += 1
    return applied


_reported = False


def _report_caps(config: Any) -> None:
    """Print the effective cap distribution once, in a form the log can be grepped for."""
    global _reported
    if _reported:
        return
    sources = list(getattr(getattr(config, "sources", None), "rss", None) or [])
    if not sources:
        return
    _reported = True
    distribution = Counter(
        _coerce_cap(getattr(source, "max_items", None)) or GLOBAL_DEFAULT_CAP
        for source in sources
    )
    spread = ", ".join(f"{cap}×{count}" for cap, count in sorted(distribution.items()))
    # A plain line instead of logger.info: the daily workflow runs at the default
    # WARNING level, and this is the only startup proof the caps were applied.
    print(
        f"[source-caps] {len(sources)} RSS feed(s), caps {spread} "
        f"(default {GLOBAL_DEFAULT_CAP})",
        file=sys.stderr,
    )


def _install_validate_hook() -> None:
    """Apply the caps whenever a ``Config`` is validated."""
    original = Config.model_validate.__func__
    if getattr(original, "_horizon_source_caps", False):
        return

    def model_validate(cls, obj, *args, **kwargs):
        config = original(cls, obj, *args, **kwargs)
        if apply_item_caps(config, obj):
            _report_caps(config)
        return config

    model_validate._horizon_source_caps = True  # type: ignore[attr-defined]
    Config.model_validate = classmethod(model_validate)


def _log_fetch_report(scraper: Any, result: Any, default_cap: int) -> None:
    sources = [
        source
        for source in scraper.config.get("sources", [])
        if getattr(source, "enabled", True)
    ]
    if not sources:
        return
    caps = {
        source.name: _coerce_cap(getattr(source, "max_items", None)) or default_cap
        for source in sources
    }
    counts = Counter(
        (getattr(item, "metadata", None) or {}).get("feed_name")
        for item in result.items
    )
    at_cap = sorted(name for name, cap in caps.items() if counts.get(name, 0) >= cap)
    distribution = Counter(caps.values())
    spread = ", ".join(f"{cap}×{count}" for cap, count in sorted(distribution.items()))
    logger.warning(
        "RSS per-source caps: %d feed(s), %d reached their cap, caps %s",
        len(sources),
        len(at_cap),
        spread,
    )
    if at_cap:
        logger.warning("RSS feeds at cap: %s", ", ".join(at_cap))


def _install_fetch_report() -> None:
    """Log the caps that were actually in force during a fetch."""
    try:
        from ..scrapers.rss import MAX_ITEMS_PER_FEED, RSSScraper
    except Exception:  # noqa: BLE001 - reporting only, never block the run
        logger.debug("could not install the RSS cap report", exc_info=True)
        return

    original = RSSScraper.fetch
    if getattr(original, "_horizon_cap_report", False):
        return

    async def fetch(self, since):
        result = await original(self, since)
        try:
            _log_fetch_report(self, result, MAX_ITEMS_PER_FEED)
        except Exception:  # noqa: BLE001 - a log line must not fail the fetch
            logger.debug("RSS cap report failed", exc_info=True)
        return result

    fetch._horizon_cap_report = True  # type: ignore[attr-defined]
    RSSScraper.fetch = fetch


_enable_extra_keys()
_install_validate_hook()
_install_fetch_report()
