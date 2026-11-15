"""Boost foreign-institution rating calls on China markets and stocks.

When Goldman, Morgan Stanley or UBS changes its view on Chinese equities or on
a mainland technology name, that is a signal this reader tracks directly: the
sell side is marking a position on the exact names and themes the digest
follows. Those stories usually arrive as a short wire item and score
mid-range, because one rating change is not systemic, so they lose the fixed
finance slots to broader macro pieces.

This module adds a bounded boost for that narrow case. All three conditions
are required:

* the text names a foreign investment bank, broker or asset manager,
* it carries a rating action (upgrade, downgrade, overweight, target price,
  initiation, or the Chinese equivalents),
* it concerns China equities as a market or a mainland company.

A rating change on a US name is left alone, and so is a China story with no
rating action. The rule only adds a constant; the item still competes on score
and the configured quotas still apply. Items the citation check tagged
unverified are never boosted.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from .citation_check import UNVERIFIED_TAG

logger = logging.getLogger(__name__)

# A rating call is the reader's core signal, so it clears the finance
# threshold from a low starting score without outranking a systemic event.
RATING_BOOST = 1.5
# Rating items often score low as "routine analyst opinion"; this floor keeps
# genuine noise out while still lifting a mid-range call.
MIN_SCORE_TO_BOOST = 4.5
MAX_SCORE = 9.5

# Sell-side houses whose calls the reader acts on, in both naming conventions.
_FOREIGN_INSTITUTION_RE = re.compile(
    r"\b(?:goldman|morgan stanley|jpmorgan|jp morgan|ubs|citi|citigroup|"
    r"bank of america|bofa|nomura|hsbc|barclays|macquarie|blackrock|"
    r"bridgewater|jefferies|bernstein|clsa|daiwa|mizuho|evercore|wedbush|stifel)\b"
    r"|deutsche bank|societe generale|wells fargo|"
    r"|高盛|摩根士丹利|大摩|小摩|摩根大通|瑞银|花旗|美银|美国银行|野村|汇丰|"
    r"巴克莱|麦格理|贝莱德|桥水|德意志银行|杰富瑞|伯恩斯坦|里昂|大和|瑞穗",
    re.IGNORECASE,
)

# A rating action, not merely an opinion. `\brating\b` keeps "operating" out.
_RATING_ACTION_RE = re.compile(
    r"\bupgrade[sd]?\b|\bdowngrade[sd]?\b|\boverweight\b|\bunderweight\b|"
    r"\boutperform\w*\b|\bunderperform\w*\b|\bprice target\b|\btarget price\b|"
    r"\brating\b|\binitiat\w+ coverage\b|\binitiation\b|"
    r"(?:raise[sd]?|cut[s]?|lift[s]?|lower[s]?|hike[s]?|slash(?:es)?|trim[s]?)"
    r"\s+(?:\w+\s+){0,4}(?:rating|target)|"
    r"上调|下调|评级|目标价|增持|减持|首次覆盖|维持",
    re.IGNORECASE,
)

# The China side of the call: the market itself or a mainland company.
_CHINA_MARKET_RE = re.compile(
    r"中国|A股|A 股|沪深|中概|港股|中资|人民币|离岸人民币|恒生|上证|创业板|科创板|"
    r"北京|上海|深圳|广州|"
    r"China|Chinese|A-share|A share|Hong Kong|mainland|yuan|renminbi|CNY|"
    r"Shanghai|Shenzhen|Beijing|Hang Seng|HSCEI|CSI ?300|MSCI China|"
    r"阿里巴巴|腾讯|比亚迪|华为|百度|京东|拼多多|小米|宁德时代|中芯|寒武纪|"
    r"字节跳动|美团|网易|蔚来|理想|小鹏|"
    r"Alibaba|Tencent|BYD|Huawei|Baidu|JD\.com|Pinduoduo|Xiaomi|CATL|SMIC|"
    r"Cambricon|ByteDance|Meituan|NetEase|NIO|Li Auto|XPeng",
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


def matches_rating_action(item: Any) -> bool:
    """Return True for a foreign rating call on China equities or a China name."""
    title = str(getattr(item, "title", "") or "")
    content = str(getattr(item, "content", "") or "")[:4000]
    text = f"{title}\n{content}"
    return (
        bool(_FOREIGN_INSTITUTION_RE.search(text))
        and bool(_RATING_ACTION_RE.search(text))
        and bool(_CHINA_MARKET_RE.search(text))
    )


def boost_analysis(item: Any, analysis: Any, *, boost: float = RATING_BOOST) -> Any:
    """Return ``analysis`` unchanged, or a boosted copy for a China rating call."""
    score = getattr(analysis, "score", None)
    if score is None or score < MIN_SCORE_TO_BOOST or score >= MAX_SCORE:
        return analysis

    tags = list(getattr(analysis, "tags", None) or [])
    if UNVERIFIED_TAG in tags:
        return analysis
    if not matches_rating_action(item):
        return analysis

    adjusted = round(min(score + boost, MAX_SCORE), 1)
    reason = getattr(analysis, "reason", "") or ""
    note = f"境外机构对中国市场/个股的评级调整，加权 +{boost:g} 分"

    logger.info(
        "rating watch: %s boosted %.1f -> %.1f (publisher=%r)",
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
