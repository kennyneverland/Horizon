"""Runtime patches for two digest behaviours that cannot be edited in place.

The repository connector rejects writes above roughly 20 KB, so
``src/orchestrator.py`` (46 KB) and ``src/ai/summarizer.py`` (20 KB) cannot be
changed through it. Both fixes are installed here at import time instead:

* ``HorizonOrchestrator.filter_items`` deduplicated topics inside each profile
  bucket separately, so one event could survive in several sections under
  different titles. On 2026-11-17 the same US chip-export story ran in five
  groups. The patched version deduplicates the whole candidate pool once.
* ``DailySummarizer.generate_summary`` rendered 科技新闻, AI硬件与算力 and
  AI应用与智能体 as three peer sections. The patched version nests them under
  a single 科技新闻 heading.

Both are behaviour-preserving outside their stated scope. Delete this module and
apply the edits to the two source files directly once they can be written.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from ..ai.summarizer import DailySummarizer, _escape_markdown, _pangu
from ..orchestrator import (
    BalancedDigestResult,
    FilteringPipelineResult,
    HorizonOrchestrator,
)

logger = logging.getLogger(__name__)

_original_filter_items = HorizonOrchestrator.filter_items
_original_generate_summary = DailySummarizer.generate_summary

# The three technology groups read as one section with sub-headings rather than
# as three peers of 财经新闻 and 中国股市.
_TECH_CHILD_IDS = ("tech-news", "ai-hardware", "ai-app")
_TECH_PARENT_TITLE = {"zh": "科技新闻", "en": "Technology"}


def _score_of(item) -> float:
    analysis = item.processing.analysis if item.processing else None
    if analysis is None or analysis.score is None:
        return -1.0
    return float(analysis.score)


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
        deduped = untouched + await self.merge_topic_duplicates(candidates, log=log)
        deduped.sort(key=_score_of, reverse=True)

    removed = base.threshold_count - len(deduped)
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


HorizonOrchestrator.filter_items = _filter_items_with_cross_group_dedup
DailySummarizer.generate_summary = _generate_summary_with_tech_section
