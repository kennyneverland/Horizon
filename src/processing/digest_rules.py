"""Digest selection rules: cross-group dedup, slot balancing, tech nesting.

These rules used to be installed as runtime monkey patches from
``src/processing/compat_patches.py``. They are plain functions now:
``HorizonOrchestrator.filter_items`` calls ``filter_items_with_cross_group_dedup``
and passes its own threshold pass in as ``base_filter``;
``HorizonOrchestrator.apply_balanced_digest`` calls ``apply_digest_with_rules``
with ``base_balance``. ``DailySummarizer.generate_summary`` calls
``nest_tech_sections`` on the rendered markdown.

Why the rules live here and not inline in ``src/orchestrator.py``: that file is
46 KB and was above the write limit of the tooling used to edit this repository.
Keeping the split is a deliberate maintenance trade-off; if the orchestrator is
ever edited by hand, these functions can move into it unchanged.
"""

from __future__ import annotations

from typing import List, Optional

# The three technology groups read as one section with sub-headings rather than
# as three peers of 财经新闻 and 中国股市.
TECH_CHILD_IDS = ("tech-news", "ai-hardware", "ai-app")
TECH_PARENT_TITLE = {"zh": "科技新闻", "en": "Technology"}

# Sources whose single daily story must survive a crowded group. Gawin Research
# publishes one stock a day as three report variants in two languages, so after
# dedup it contributes one item; losing it means losing the whole source.
_PRIORITY_SOURCES = ("Gawin Research",)
# How much score a reserved slot may give up. A larger gap means the guaranteed
# item is materially weaker than what it displaces, and the slot is not taken.
_PRIORITY_TOLERANCE = 1.0

# Groups whose configured limit is also the hard ceiling during backlog fill.
# The reader is told "每组最多 N 条" for these, so a 5-item group must never
# render 7.
_NO_OVERFLOW_GROUPS = ("ai-hardware", "ai-app")

# Explicit overflow ceilings. 其他科技动态 is configured at 5 so the balancer
# fills other groups first, but may grow to 8 when backlog items are left over.
_OVERFLOW_CAP_OVERRIDE = {"tech-news": 8}

# 配额是上限，不是目标；但连着两天出现「财经要闻 2/8」「中国股市 6/10」，说明
# 上限变成了目标的反面——不是没有候选，是候选在别的环节被拿走了。兜底补到
# limit 为止，两个来源，按优先级：
#   1. 被跨组去重并进别组的同组条目（它们本身已过阈值，只是主题重复）；
#   2. 未过阈值、但距离阈值不超过这个余量的同组条目（典型是中国股市里落标被
#      扣 0.3 分、从 6.2 掉到 5.9 的那一批——扣分本意是排序，不该变成淘汰）。
# 余量给 0.5：再多就等于把阈值往下调，而阈值是用户定的口径。
SPARE_MARGIN = 0.5


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


def _log_profile_pass_rate(orchestrator, before, after) -> None:
    """Print how many items each profile kept out of the ones it analysed.

    A group that renders 3/10 can be short of supply or short of items clearing
    its threshold, and the run log did not say which. This line separates them:
    ``3/41`` is a threshold problem, ``3/4`` is a supply problem.
    """
    default = orchestrator.profiles.default_profile
    analysed = _count_by_profile(before, default)
    kept = _count_by_profile(after, default)
    keys = sorted(set(analysed) | set(kept), key=lambda k: -analysed.get(k, 0))
    parts = [f"{key} {kept.get(key, 0)}/{analysed.get(key, 0)}" for key in keys]
    orchestrator.console.print(
        "      profile pass-rate (kept/analysed): " + ", ".join(parts)
    )


def _trim_for_dedup(orchestrator, candidates):
    """Keep only the per-group items that could still reach the digest.

    The balancer never publishes more than ``limit`` items from a group. The
    backlog fill may use ``limit + max(2, limit // 2)`` for 财经要闻 and 中国股市,
    an explicit 8 for 其他科技动态, and ``limit`` for the two AI groups; the
    margin kept here covers all of them, plus priority slots. Trimming before the
    AI pass keeps the pairwise comparison small: 80 candidates cost 24 minutes
    on 2026-11-17, and that grows faster than the item count.
    """
    groups = orchestrator.config.digest.category_groups
    budgets = {}
    for group_key, group in groups.items():
        if group.limit:
            budgets[group_key] = group.limit + max(5, group.limit // 2)
    if not budgets:
        return candidates

    kept = []
    taken: dict = {}
    for item in candidates:
        profile_id = _profile_of(item, orchestrator.profiles.default_profile)
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
        orchestrator.console.print(
            f"      dedup pool trimmed {len(candidates)} → {len(kept)} items "
            f"(每组保留 限额+5 名)\n"
        )

    # The reserved slot is checked after the balancer, but this trim runs before
    # it. A priority source that cleared the threshold yet ranked below the
    # group budget was dropped here and could never be reserved: on 2026-11-18
    # Gawin Research fetched 6 items, china-market kept 16 above threshold, and
    # none of them reached the digest. Keep its best item in the pool; it costs
    # one extra row in the dedup pass.
    kept_ids = {id(item) for item in kept}
    for name in _PRIORITY_SOURCES:
        best = None
        for item in candidates:
            if _source_name(item) != name or id(item) in kept_ids:
                continue
            if best is None or _score_of(item) > _score_of(best):
                best = item
        if best is None:
            continue
        kept.append(best)
        kept_ids.add(id(best))
        orchestrator.console.print(
            f"      priority source {name}: kept in the dedup pool "
            f"({_score_of(best):.1f}, outside the group budget)\n"
        )
    return kept


async def filter_items_with_cross_group_dedup(
    orchestrator,
    items,
    base_filter,
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
    base = await base_filter(
        items,
        threshold=threshold,
        topic_dedup=False,
        apply_balance=False,
        log=log,
    )
    deduped = base.items

    if log:
        _log_profile_pass_rate(orchestrator, items, deduped)

    from ..orchestrator import BalancedDigestResult, FilteringPipelineResult

    removed = 0
    dropped: List = []
    if topic_dedup and deduped:

        def _enabled(item) -> bool:
            profile_id = (
                item.processing.classification.profile
                if item.processing
                else orchestrator.profiles.default_profile
            )
            settings = orchestrator.config.processing.profile_settings.get(profile_id)
            return settings is None or settings.topic_dedup

        candidates = [item for item in deduped if _enabled(item)]
        untouched = [item for item in deduped if not _enabled(item)]
        candidates.sort(key=_score_of, reverse=True)
        candidates = _trim_for_dedup(orchestrator, candidates)
        merged = await orchestrator.merge_topic_duplicates(candidates, log=log)
        removed = len(candidates) - len(merged)
        # 被并走的条目留一份：它们的主题和别组重复，但属于本组，配额空着时
        # 由 _fill_group_quotas 按分数取回。
        kept_ids = {id(item) for item in merged}
        dropped = [item for item in candidates if id(item) not in kept_ids]
        dropped.sort(key=_score_of, reverse=True)
        deduped = untouched + merged
        deduped.sort(key=_score_of, reverse=True)

    if log and removed:
        orchestrator.console.print(
            f"{orchestrator.icons['cleanup']} Removed {removed} topic duplicates "
            f"→ {len(deduped)} unique items (cross-group)\n"
        )

    # 差一点没过阈值的同组条目：只在配额补不满时才用，见 SPARE_MARGIN。
    passed_ids = {id(item) for item in deduped} | {id(item) for item in dropped}
    below: List = []
    for item in items:
        if id(item) in passed_ids:
            continue
        threshold = _threshold_of(orchestrator, item)
        if threshold is None:
            continue
        if _score_of(item) >= threshold - SPARE_MARGIN:
            below.append(item)
    below.sort(key=_score_of, reverse=True)

    balanced = (
        orchestrator.apply_balanced_digest(deduped, log=log)
        if apply_balance
        else BalancedDigestResult(items=deduped)
    )
    if apply_balance:
        balanced = _fill_group_quotas(
            orchestrator, balanced, deduped, dropped, below, log=log
        )
    return FilteringPipelineResult(
        items=balanced.items,
        threshold_count=base.threshold_count,
        topic_dedup_count=len(deduped),
        topic_dedup_removed=removed,
        balanced_digest=balanced,
    )


def _group_key_for(orchestrator, item) -> str:
    """Digest group an item belongs to, using the configured category mapping."""
    digest = orchestrator.config.digest
    if digest.group_by == "profile":
        category = item.processing.classification.profile if item.processing else None
    else:
        category = (getattr(item, "metadata", None) or {}).get("category")
    if isinstance(category, str):
        for group_key, group in digest.category_groups.items():
            if category in group.categories:
                return group_key
    return digest.default_group


def _group_name(group, key: str) -> str:
    """Display name of a digest group, whether it is a model or a plain dict."""
    if group is None:
        return key
    name = getattr(group, "name", None)
    if name:
        return str(name)
    if isinstance(group, dict):
        return str(group.get("name") or key)
    return key


def _threshold_of(orchestrator, item) -> Optional[float]:
    """The profile's configured threshold, or ``None`` when it has none."""
    profile_id = (
        item.processing.classification.profile
        if item.processing
        else orchestrator.profiles.default_profile
    )
    settings = orchestrator.config.processing.profile_settings.get(profile_id)
    return settings.threshold if settings is not None else None


def _fill_group_quotas(
    orchestrator, result, pool, dropped, below, *, log: bool = True
):
    """把没选满的组补到它的 limit。

    ``pool`` 是去重后已过阈值的全部条目，``dropped`` 是被跨组去重并进别组的
    同组条目，``below`` 是差一点没过阈值的同组条目。三个来源依次取，每取一条
    就把该组计数加一，取到 limit 或来源用尽为止；总数不超过 ``digest.max_items``。

    去重本身是对的——同一条新闻不该在五个板块各出现一次——但它不该把某个板块
    饿死：财经要闻的 13 条候选里有 11 条因为主题和别的组重复被并走，balanced
    只看剩下 2 条，配额 8 就空着 6 个。这里补回去的是同组条目，不是拿别的组的
    东西填。
    """
    limits = dict(result.group_limits or {})
    if not limits:
        return result

    from ..orchestrator import BalancedDigestResult

    digest = orchestrator.config.digest
    max_items = getattr(digest, "max_items", None)
    counts = dict(result.group_counts or {})
    selected = list(result.items)
    chosen = {id(item) for item in selected}

    short = []
    for group_key, limit in limits.items():
        if not limit:
            continue
        need = limit - counts.get(group_key, 0)
        if need > 0:
            short.append((group_key, need))
    if not short:
        return result

    restored = {}
    for group_key, need in short:
        if max_items and len(selected) >= max_items:
            break
        before = counts.get(group_key, 0)
        for source in (pool, dropped, below):
            if need <= 0 or (max_items and len(selected) >= max_items):
                break
            for item in source:
                if need <= 0 or (max_items and len(selected) >= max_items):
                    break
                if id(item) in chosen:
                    continue
                if _group_key_for(orchestrator, item) != group_key:
                    continue
                selected.append(item)
                chosen.add(id(item))
                counts[group_key] = counts.get(group_key, 0) + 1
                need -= 1
        gained = counts.get(group_key, 0) - before
        if gained:
            restored[group_key] = (before, counts.get(group_key, 0))

    if restored and log:
        groups = getattr(digest, "category_groups", {}) or {}
        detail = "、".join(
            f"{_group_name(groups.get(key), key)} {before}→{after}"
            for key, (before, after) in restored.items()
        )
        orchestrator.console.print(
            f"{orchestrator.icons['balance']} Filled group quotas from the dedup pool: "
            f"{detail}\n"
        )

    return BalancedDigestResult(
        items=selected,
        enabled=result.enabled,
        group_counts=counts,
        group_limits=limits,
        duplicate_categories=result.duplicate_categories,
    )


def _ensure_priority_slots(orchestrator, pool, selected, log: bool = True):
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
            # Silent skips made "never reserved" indistinguishable from "nothing
            # to reserve"; say which one it is.
            if log:
                orchestrator.console.print(
                    f"      priority source {name}: no candidate in the pool "
                    f"(below threshold or dropped earlier)\n"
                )
            continue
        best = max(candidates, key=_score_of)
        group_key = _group_key_for(orchestrator, best)

        weakest_index = None
        for index, item in enumerate(selected):
            if _source_name(item) == name:
                continue
            if _group_key_for(orchestrator, item) != group_key:
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
                orchestrator.console.print(
                    f"      priority source {name}: best {_score_of(best):.1f} "
                    f"vs {_score_of(dropped):.1f} exceeds tolerance "
                    f"{_PRIORITY_TOLERANCE:.1f}; slot not reserved"
                )
            continue

        selected[weakest_index] = best
        swaps += 1
        if log:
            orchestrator.console.print(
                f"      priority source {name}: slot reserved "
                f"({_score_of(best):.1f} replaces {_score_of(dropped):.1f})\n"
            )
    return selected, swaps


def apply_digest_with_rules(orchestrator, items, base_balance, *, log: bool = True):
    """Apply the per-group quotas, reserve priority slots, fill unused slots."""
    from ..orchestrator import BalancedDigestResult

    result = base_balance(items, log=log)
    selected = list(result.items)
    selected, _ = _ensure_priority_slots(orchestrator, items, selected, log=log)

    digest = orchestrator.config.digest
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
            # AI 硬件与 AI 应用是硬上限：溢出曾让这两组从 5 条变成 7 条。
            # 其他科技动态按显式上限 8 条补位，其余组按 limit + max(2, limit//2)。
            limit = limits.get(group_key)
            if limit is None:
                return None
            if group_key in _NO_OVERFLOW_GROUPS:
                return limit
            override = _OVERFLOW_CAP_OVERRIDE.get(group_key)
            if override is not None:
                return override
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
            orchestrator.console.print(
                f"{orchestrator.icons['balance']} Filled {added} unused slots from the "
                f"backlog → {len(selected)}/{max_items} items\n"
            )

    return BalancedDigestResult(
        items=selected,
        enabled=result.enabled,
        group_counts=counts,
        group_limits=limits,
        duplicate_categories=duplicate_categories,
    )


def nest_tech_sections(text: str, child_names, parent_title: str) -> str:
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