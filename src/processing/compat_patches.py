"""Runtime patches for digest behaviours that cannot be edited in place.

The repository connector rejects writes above roughly 20 KB, so
``src/orchestrator.py`` (46 KB) and ``src/ai/summarizer.py`` (20 KB) cannot be
changed through it. The fixes are installed here at import time instead:

* ``HorizonOrchestrator.filter_items`` deduplicated topics inside each profile
  bucket separately, so one event could survive in several sections under
  different titles. On 2026-11-17 the same US chip-export story ran in five
  groups. The patched version deduplicates the whole candidate pool once.
* ``DailySummarizer.generate_summary`` rendered 科技新闻, AI硬件与算力 and
  AI应用与智能体 as three peer sections. The patched version nests them under
  a single 科技新闻 heading.
* ``scrapers.google_news`` issued its queries 1.2 s apart and retried a 429
  twice; on 2026-11-17 four of nineteen queries were still lost and twelve more
  needed a retry. The module reads its pacing from module-level constants, so
  raising them here is enough to slow every query down.
* ``HorizonOrchestrator.apply_balanced_digest`` stopped at the per-group caps
  and never spent the slots a starved group left unused, so the digest shipped
  25 of 35 items on 2026-11-17 while 21 eligible items were dropped. The patched
  version fills the leftover slots from the backlog, allowing a group to
  overflow by half its limit so one section cannot swallow the digest.
* The cross-group dedup pass cost 24 minutes on 2026-11-17 because it compared
  all 80 candidates against each other. Only the top few per group can ever be
  published, so the pool is trimmed to ``limit + max(5, limit // 2)`` per group
  before the AI pass runs.
* Research sources listed in ``_PRIORITY_SOURCES`` publish at most one distinct
  story a day, so a busy group can crowd them out. The balancer now reserves
  one slot for each of them inside its own group.

All of these are behaviour-preserving outside their stated scope. Delete this
module and apply the edits to the source files directly once they can be
written.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from ..ai.summarizer import DailySummarizer, _escape_markdown, _pangu
from ..scrapers import google_news as _google_news
from ..orchestrator import (
    BalancedDigestResult,
    FilteringPipelineResult,
    HorizonOrchestrator,
)

logger = logging.getLogger(__name__)

_original_filter_items = HorizonOrchestrator.filter_items
_original_apply_balanced_digest = HorizonOrchestrator.apply_balanced_digest
_original_generate_summary = DailySummarizer.generate_summary

# Google News answers 429 aggressively to shared CI IPs. The scraper reads these
# at call time, so overriding them here paces every query without touching the
# module.
_google_news.REQUEST_INTERVAL_SEC = 5.0
_google_news.RETRY_AFTER_429_SEC = 15.0
_google_news.MAX_429_RETRIES = 3

# The three technology groups read as one section with sub-headings rather than
# as three peers of 财经新闻 and 中国股市.
_TECH_CHILD_IDS = ("tech-news", "ai-hardware", "ai-app")
_TECH_PARENT_TITLE = {"zh": "科技新闻", "en": "Technology"}

# Sources whose single daily story must survive a crowded group. Gawin Research
# publishes one stock a day as three report variants in two languages, so after
# dedup it contributes one item; losing it means losing the whole source.
_PRIORITY_SOURCES = ("Gawin Research",)
# How much score a reserved slot may give up. A larger gap means the guaranteed
# item is materially weaker than what it displaces, and the slot is not taken.
_PRIORITY_TOLERANCE = 1.0


def _score_of(item) -> float:
    analysis = item.processing.analysis if item.processing else None
    if analysis is None or analysis.score is None:
        return -1.0
    return float(analysis.score)


def _profile_of(item, default: str) -> str:
    """Resolved profile id for an item, falling back to the configured default."""
    classification = item.processing.classification if item.processing else None
    profile_id = classification.profile if classification else None
    return profile_id if isinstance(profile_id, str) and profile_id else default


def _source_name(item) -> str:
    """Feed name an item came from, as the RSS scraper records it."""
    metadata = getattr(item, "metadata", None) or {}
    return str(metadata.get("feed_name") or metadata.get("source_name") or "")


def _count_by_profile(items, default: str) -> dict:
    counts: dict = {}
    for item in items:
        profile_id = _profile_of(item, default)
        counts[profile_id] = counts.get(profile_id, 0) + 1
    return counts


def _log_profile_pass_rate(self, before, after) -> None:
    """Print how many items each profile kept out of the ones it analysed.

    A group that renders 3/10 can be short of supply or short of items clearing
    its threshold, and the run log did not say which. This line separates them:
    ``3/41`` is a threshold problem, ``3/4`` is a supply problem.
    """
    default = self.profiles.default_profile
    analysed = _count_by_profile(before, default)
    kept = _count_by_profile(after, default)
    keys = sorted(set(analysed) | set(kept), key=lambda k: -analysed.get(k, 0))
    parts = [f"{key} {kept.get(key, 0)}/{analysed.get(key, 0)}" for key in keys]
    self.console.print(
        "      profile pass-rate (kept/analysed): " + ", ".join(parts)
    )


def _trim_for_dedup(self, candidates):
    """Keep only the per-group items that could still reach the digest.

    The balancer never publishes more than ``limit`` items from a group and can
    only overflow to ``limit + max(2, limit // 2)`` when filling unused slots,
    so anything below that cut is dropped later regardless. Trimming before the
    AI pass keeps the pairwise comparison small: 80 candidates cost 24 minutes
    on 2026-11-17, and that grows faster than the item count.
    """
    groups = self.config.digest.category_groups
    budgets = {}
    for group_key, group in groups.items():
        if group.limit:
            budgets[group_key] = group.limit + max(5, group.limit // 2)
    if not budgets:
        return candidates

    kept = []
    taken: dict = {}
    for item in candidates:
        profile_id = _profile_of(item, self.profiles.default_profile)
        budget = budgets.get(profile_id)
        if budget is None:
            kept.append(item)
            continue
        used = taken.get(profile_id, 0)
        if used >= budget:
            continue
        taken[profile_id] = used + 1
        kept.append(item)

    if len(kept) < len(candidates):
        self.console.print(
            f"      dedup pool trimmed {len(candidates)} → {len(kept)} items "
            f"(每组保留 限额+5 名)\n"
        )
    return kept


async def _filter_items_with_cross_group_dedup(
    self,
    items,
    *,
    threshold: Optional[float] = None,
    topic_dedup: bool = True,
    apply_balance: bool = True,
    log: bool = True,
):
    """Threshold and sort as before, then deduplicate across every profile.

    The original ran one AI dedup pass per profile bucket, which is why the same
    event could appear in five groups at once: no two copies shared a bucket.
    """
    base = await _original_filter_items(
        self,
        items,
        threshold=threshold,
        topic_dedup=False,
        apply_balance=False,
        log=log,
    )
    deduped = base.items

    if log:
        _log_profile_pass_rate(self, items, deduped)

    removed = 0
    if topic_dedup and deduped:

        def _enabled(item) -> bool:
            profile_id = (
                item.processing.classification.profile
                if item.processing
                else self.profiles.default_profile
            )
            settings = self.config.processing.profile_settings.get(profile_id)
            return settings is None or settings.topic_dedup

        candidates = [item for item in deduped if _enabled(item)]
        untouched = [item for item in deduped if not _enabled(item)]
        candidates.sort(key=_score_of, reverse=True)
        candidates = _trim_for_dedup(self, candidates)
        merged = await self.merge_topic_duplicates(candidates, log=log)
        removed = len(candidates) - len(merged)
        deduped = untouched + merged
        deduped.sort(key=_score_of, reverse=True)

    if log and removed:
        self.console.print(
            f"{self.icons['cleanup']} Removed {removed} topic duplicates "
            f"→ {len(deduped)} unique items (cross-group)\n"
        )

    balanced = (
        self.apply_balanced_digest(deduped, log=log)
        if apply_balance
        else BalancedDigestResult(items=deduped)
    )
    return FilteringPipelineResult(
        items=balanced.items,
        threshold_count=base.threshold_count,
        topic_dedup_count=len(deduped),
        topic_dedup_removed=removed,
        balanced_digest=balanced,
    )


def _group_key_for(self, item) -> str:
    """Digest group an item belongs to, using the configured category mapping."""
    digest = self.config.digest
    if digest.group_by == "profile":
        category = item.processing.classification.profile if item.processing else None
    else:
        category = (getattr(item, "metadata", None) or {}).get("category")
    if isinstance(category, str):
        for group_key, group in digest.category_groups.items():
            if category in group.categories:
                return group_key
    return digest.default_group


def _ensure_priority_slots(self, pool, selected, log: bool = True):
    """Reserve one slot per priority source inside its own group.

    A priority source contributes at most one distinct item a day, so the score
    ranking keeps it most days; this only matters on a crowded day. The reserved
    slot displaces the weakest selected item of the same group from another
    source, and is skipped when the score gap exceeds the tolerance.
    """
    if not selected:
        return selected, 0

    swaps = 0
    for name in _PRIORITY_SOURCES:
        if any(_source_name(item) == name for item in selected):
            continue
        candidates = [item for item in pool if _source_name(item) == name]
        if not candidates:
            continue
        best = max(candidates, key=_score_of)
        group_key = _group_key_for(self, best)

        weakest_index = None
        for index, item in enumerate(selected):
            if _source_name(item) == name:
                continue
            if _group_key_for(self, item) != group_key:
                continue
            if weakest_index is None or _score_of(item) < _score_of(
                selected[weakest_index]
            ):
                weakest_index = index
        if weakest_index is None:
            continue

        dropped = selected[weakest_index]
        if _score_of(best) < _score_of(dropped) - _PRIORITY_TOLERANCE:
            if log:
                self.console.print(
                    f"      priority source {name}: best {_score_of(best):.1f} "
                    f"vs {_score_of(dropped):.1f} exceeds tolerance "
                    f"{_PRIORITY_TOLERANCE:.1f}; slot not reserved"
                )
            continue

        selected[weakest_index] = best
        swaps += 1
        if log:
            self.console.print(
                f"      priority source {name}: slot reserved "
                f"({_score_of(best):.1f} replaces {_score_of(dropped):.1f})\n"
            )
    return selected, swaps


def _apply_balanced_digest_filling_unused(self, items, *, log: bool = True):
    """Apply the per-group quotas, reserve priority slots, fill unused slots."""
    result = _original_apply_balanced_digest(self, items, log=log)
    selected = list(result.items)
    selected, _ = _ensure_priority_slots(self, items, selected, log=log)

    digest = self.config.digest
    max_items = digest.max_items
    counts = dict(result.group_counts)
    limits = dict(result.group_limits)
    duplicate_categories = result.duplicate_categories

    if max_items and len(selected) < max_items:
        groups = digest.category_groups
        category_to_group = {}
        for group_key, group in groups.items():
            for category in group.categories:
                category_to_group.setdefault(category, group_key)
        default_group = digest.default_group

        def _overflow_cap(group_key: str):
            limit = limits.get(group_key)
            if limit is None:
                return None
            return limit + max(2, limit // 2)

        chosen = {id(item) for item in selected}
        leftovers = [item for item in items if id(item) not in chosen]
        leftovers.sort(key=_score_of, reverse=True)

        added = 0
        for item in leftovers:
            if len(selected) >= max_items:
                break
            if digest.group_by == "profile":
                category = (
                    item.processing.classification.profile if item.processing else None
                )
            else:
                category = item.metadata.get("category")
            group_key = (
                category_to_group.get(category, default_group)
                if isinstance(category, str)
                else default_group
            )
            cap = _overflow_cap(group_key)
            if cap is not None and counts.get(group_key, 0) >= cap:
                continue
            selected.append(item)
            counts[group_key] = counts.get(group_key, 0) + 1
            added += 1

        if added and log:
            self.console.print(
                f"{self.icons['balance']} Filled {added} unused slots from the "
                f"backlog → {len(selected)}/{max_items} items\n"
            )

    return BalancedDigestResult(
        items=selected,
        enabled=result.enabled,
        group_counts=counts,
        group_limits=limits,
        duplicate_categories=duplicate_categories,
    )


def _nest_tech_sections(text: str, child_names, parent_title: str) -> str:
    """Move the technology groups one heading level down under a parent."""
    lines: List[str] = []
    opened = False
    in_tech = False
    for line in text.splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            if name in child_names:
                if not opened:
                    lines.append(f"## {parent_title}")
                    lines.append("")
                    opened = True
                lines.append(f"### {name}")
                in_tech = True
                continue
            in_tech = False
        elif in_tech and line.startswith("### ["):
            line = "#" + line
        lines.append(line)
    return "\n".join(lines)


async def _generate_summary_with_tech_section(
    self, items, date, total_fetched, language: str = "en"
) -> str:
    text = await _original_generate_summary(
        self, items, date, total_fetched, language=language
    )
    child_names = set()
    for profile_id in _TECH_CHILD_IDS:
        name = _escape_markdown(self.profile_name(profile_id, language))
        if language == "zh":
            name = _pangu(name)
        child_names.add(name)
    parent_title = _escape_markdown(
        _TECH_PARENT_TITLE.get(language, _TECH_PARENT_TITLE["en"])
    )
    if language == "zh":
        parent_title = _pangu(parent_title)
    return _nest_tech_sections(text, child_names, parent_title)


HorizonOrchestrator.apply_balanced_digest = _apply_balanced_digest_filling_unused
HorizonOrchestrator.filter_items = _filter_items_with_cross_group_dedup
DailySummarizer.generate_summary = _generate_summary_with_tech_section
