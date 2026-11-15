"""Boost foreign-outlet coverage of China markets and technology.

The digest fills a fixed number of finance slots by score, and foreign wires
cover China through a global lens: a Bloomberg story about Chinese chip policy
competes with a US earnings story and often loses, because the rubric rewards
breadth and the China angle reads as one region among many. This module adds a
bounded, rule-based boost so those items can reach the reader.

The boost stays deliberately narrow:

* the publisher must be an outlet outside mainland China,
* the text must carry a China subject *and* a market or technology angle,
* the item must already be above ``MIN_SCORE_TO_BOOST``, so noise stays below
  the profile thresholds instead of being lifted over them,
* items tagged unverified by the citation check are never boosted.

The rule only adds a constant; it never decides what matters. A boosted item
still has to compete on score, and the configured quotas still apply.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .citation_check import UNVERIFIED_TAG

logger = logging.getLogger(__name__)

# One point is enough to clear the finance threshold (6.0) from a mid score
# without letting a routine item outrank a systemic story.
BOOST = 1.0
# Below this an item is usually noise; boosting it would only fill quotas.
MIN_SCORE_TO_BOOST = 5.0
MAX_SCORE = 9.5

_FOREIGN_OUTLET_RE = re.compile(
    r"\b(?:bloomberg|reuters|cnbc|nikkei|bbc|marketwatch|wsj|scmp|axios|"
    r"techcrunch|wired|fortune|forbes|cnn)\b"
    r"|wall street journal|financial times|south china morning post"
    r"|the economist|associated press|business insider|the information"
    r"|the verge|the guardian|al jazeera|straits times|channel news asia"
    r"|barron",
    re.IGNORECASE,
)

# A China subject: the country, its markets, or a mainland company the reader
# can map onto an A-share theme.
_CHINA_SUBJECT_RE = re.compile(
    r"中国|A股|A 股|沪深|中概|港股|人民币|离岸人民币|北京|上海|深圳|广州|"
    r"China|Chinese|A-share|A share|Hong Kong|mainland|yuan|renminbi|CNY|"
    r"Shanghai|Shenzhen|Beijing|Hang Seng|CSI ?300|"
    r"阿里巴巴|腾讯|比亚迪|华为|百度|京东|拼多多|小米|宁德时代|中芯|寒武纪|"
    r"字节跳动|美团|网易|蔚来|理想|小鹏|"
    r"Alibaba|Tencent|BYD|Huawei|Baidu|JD\.com|Pinduoduo|Xiaomi|CATL|SMIC|"
    r"Cambricon|ByteDance|Meituan|NetEase|NIO|Li Auto|XPeng",
    re.IGNORECASE,
)

# A market or technology angle, so a passing mention of China is not enough.
_MARKET_TECH_RE = re.compile(
    r"股票|股市|股价|指数|市值|估值|财报|业绩|营收|利润|监管|政策|关税|出口管制|"
    r"芯片|半导体|算力|人工智能|大模型|电动车|新能源|光伏|"
    r"stock|stocks|shares|equity|equities|index|valuation|earnings|revenue|"
    r"regulat|policy|tariff|export control|chip|semiconductor|"
    r"artificial intelligence|data cent|battery|solar|\bAI\b",
    re.IGNORECASE,
)


def publisher_label(item: Any) -> str:
    """Return the feed label an item came from, lowercased."""
    meta = getattr(item, "metadata", None)
    if isinstance(meta, dict):
        for key in ("feed_name", "source_name", "channel", "watchlist"):
            value = meta.get(key)
            if value:
                return str(value).strip().lower()
    return str(getattr(item, "author", "") or "").strip().lower()


def is_foreign_outlet(item: Any) -> bool:
    """Return True when the item comes from an outlet outside mainland China."""
    label = publisher_label(item)
    return bool(label) and bool(_FOREIGN_OUTLET_RE.search(label))


def matches_china_focus(item: Any) -> bool:
    """Return True for foreign coverage that bears on China markets or tech."""
    if not is_foreign_outlet(item):
        return False
    title = str(getattr(item, "title", "") or "")
    content = str(getattr(item, "content", "") or "")[:4000]
    text = f"{title}\n{content}"
    return bool(_CHINA_SUBJECT_RE.search(text)) and bool(_MARKET_TECH_RE.search(text))


def boost_analysis(item: Any, analysis: Any, *, boost: float = BOOST) -> Any:
    """Return ``analysis`` unchanged, or a boosted copy for China-focused items."""
    score = getattr(analysis, "score", None)
    if score is None or score < MIN_SCORE_TO_BOOST or score >= MAX_SCORE:
        return analysis

    tags = list(getattr(analysis, "tags", None) or [])
    if UNVERIFIED_TAG in tags:
        return analysis
    if not matches_china_focus(item):
        return analysis

    adjusted = round(min(score + boost, MAX_SCORE), 1)
    reason = getattr(analysis, "reason", "") or ""
    note = f"境外机构涉华市场/科技报道，加权 +{boost:g} 分"

    logger.info(
        "china focus: %s boosted %.1f -> %.1f (publisher=%r)",
        getattr(item, "id", "?"),
        score,
        adjusted,
        publisher_label(item),
    )
    return analysis.model_copy(
        update={
            "score": adjusted,
            "reason": f"{reason}；{note}" if reason else note,
        }
    )
