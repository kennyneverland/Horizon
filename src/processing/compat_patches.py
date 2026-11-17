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


def _apply_balanced_digest_filling_unused(self, items, *, log: bool = True):
    """Apply the per-group quotas, then spend the slots they left unused."""
    result = _original_apply_balanced_digest(self, items, log=log)
    digest = self.config.digest
    max_items = digest.max_items
    if not max_items or len(result.items) >= max_items:
        return result

    groups = digest.category_groups
    category_to_group = {}
    for group_key, group in groups.items():
        for category in group.categories:
            category_to_group.setdefault(category, group_key)
    default_group = digest.default_group

    counts = dict(result.group_counts)
    limits = dict(result.group_limits)

    def _overflow_cap(group_key: str):
        limit = limits.get(group_key)
        if limit is None:
            return None
        return limit + max(2, limit // 2)

    chosen = {id(item) for item in result.items}
    leftovers = [item for item in items if id(item) not in chosen]
    leftovers.sort(key=_score_of, reverse=True)

    selected = list(result.items)
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

    if not added:
        return result
    if log:
        self.console.print(
            f"{self.icons['balance']} Filled {added} unused slots from the backlog "
            f"→ {len(selected)}/{max_items} items\n"
        )
    return BalancedDigestResult(
        items=selected,
        enabled=result.enabled,
        group_counts=counts,
        group_limits=limits,
        duplicate_categories=result.duplicate_categories,
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
