"""Cross-check Chinese write-ups that credit a foreign outlet.

Chinese outlets often republish a foreign report as "据彭博社报道…". When the
underlying report does not exist — or exists only as another Chinese republish —
the item still scores well on importance, so unverified claims can crowd out
solid reporting. This module looks for an independent, non-Chinese source for
the same story and lowers the score when none is found.

The check is deliberately conservative: it only subtracts ``CITATION_PENALTY``
and tags the item as ``未证实``. It never drops the item, because a paywalled or
exclusive story can legitimately have no reachable source.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

CITATION_PENALTY = 0.5
# Below this score an item rarely survives the profile thresholds, so the extra
# lookup would only burn search credits.
MIN_SCORE_TO_CHECK = 6.0
# Hard budget per run: the digest runs once a day and Tavily's free tier is
# 1000 credits/month shared with the enrichment stage.
MAX_CHECKS_PER_RUN = 12
UNVERIFIED_TAG = "未证实"

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_ATTRIBUTION_RE = re.compile(
    r"据[^，。；！？\s]{1,14}(?:报道|消息|援引|透露|称|披露)"
    r"|援引[^，。；！？\s]{1,14}"
    r"|引述[^，。；！？\s]{1,14}"
    r"|(?:知情|消息)人士"
    r"|外媒(?:报道|消息)?"
    r"|据报(?:道|称)?"
)
# Chinese outlet and aggregator domains: a hit here is a republish, not proof.
_CHINESE_MEDIA_SUFFIXES = (
    "wallstreetcn.com", "cls.cn", "yicai.com", "caixin.com", "stcn.com",
    "eastmoney.com", "sina.com.cn", "sina.cn", "163.com", "qq.com",
    "sohu.com", "ifeng.com", "thepaper.cn", "jiemian.com", "36kr.com",
    "huxiu.com", "tmtpost.com", "jiqizhixin.com", "ithome.com",
    "cnbeta.com", "chinanews.com.cn", "chinanews.com", "chinadaily.com.cn",
    "cnr.cn", "people.com.cn", "xinhuanet.com", "news.cn", "cctv.com",
    "bjd.com.cn", "china.com", "jrj.com.cn", "guancha.cn", "thecover.cn",
)
# Foreign outlets and first-party newsrooms that count as corroboration.
_TRUSTED_SUFFIXES = (
    "reuters.com", "bloomberg.com", "wsj.com", "ft.com", "cnbc.com",
    "nytimes.com", "businessinsider.com", "apnews.com", "axios.com",
    "theinformation.com", "techcrunch.com", "theverge.com", "wired.com",
    "sec.gov", "bloomberg.co.jp", "nikkei.com", "scmp.com",
    "nvidianews.nvidia.com", "about.nvidia.com", "investor.nvidia.com",
    "openai.com", "anthropic.com", "microsoft.com", "apple.com",
    "about.fb.com", "blog.google", "tesla.com", "samsung.com",
)
_OUTLET_NAMES = {
    "彭博": "Bloomberg",
    "商业周刊": "Bloomberg Businessweek",
    "路透": "Reuters",
    "华尔街日报": "Wall Street Journal",
    "金融时报": "Financial Times",
    "纽约时报": "New York Times",
    "商业内幕": "Business Insider",
    "美联社": "Associated Press",
    "阿克西奥斯": "Axios",
    "日经": "Nikkei",
    "南华早报": "South China Morning Post",
    "CNBC": "CNBC",
    "TechCrunch": "TechCrunch",
    "The Information": "The Information",
    "The Verge": "The Verge",
}

_checks_used = 0


@dataclass(frozen=True)
class CitationVerdict:
    """Outcome of the cross-check for one item."""

    applicable: bool = False
    verified: bool = True
    query: str = ""
    evidence: str = ""

    @property
    def unverified(self) -> bool:
        return self.applicable and not self.verified


def reset_budget() -> None:
    """Reset the per-run lookup budget (used by tests)."""
    global _checks_used
    _checks_used = 0


def is_attributed_chinese_item(item: Any) -> bool:
    """Return True for a Chinese write-up that credits a foreign report."""
    title = getattr(item, "title", "") or ""
    if not _CJK_RE.search(title):
        return False
    text = f"{title}\n{getattr(item, 'content', '') or ''}"
    return bool(_ATTRIBUTION_RE.search(text))


def build_query(item: Any) -> str:
    """Build a search query that pulls the credited outlet into the results."""
    text = f"{getattr(item, 'title', '')}\n{getattr(item, 'content', '') or ''}"
    outlets = [english for chinese, english in _OUTLET_NAMES.items() if chinese in text]
    prefix = " ".join(dict.fromkeys(outlets))
    title = re.sub(r"\s+", " ", getattr(item, "title", "") or "").strip()
    return f"{prefix} {title}".strip() if prefix else title


def _host(url: str) -> str:
    try:
        return (urlsplit(url).netloc or "").lower()
    except ValueError:
        return ""


def _matches(host: str, suffixes: tuple[str, ...]) -> bool:
    return any(host == suffix or host.endswith("." + suffix) for suffix in suffixes)


def is_corroborated(results: list[dict[str, str]]) -> Optional[str]:
    """Return the first foreign or first-party URL, or None."""
    for result in results:
        host = _host(str(result.get("url", "")))
        if not host or _matches(host, _CHINESE_MEDIA_SUFFIXES):
            continue
        if _matches(host, _TRUSTED_SUFFIXES):
            return str(result.get("url", ""))
    return None


async def verify_item(
    item: Any,
    search: Optional[Callable[[str], Any]] = None,
) -> CitationVerdict:
    """Look for an independent source behind an attributed Chinese write-up."""
    global _checks_used

    if not is_attributed_chinese_item(item):
        return CitationVerdict()
    if _checks_used >= MAX_CHECKS_PER_RUN:
        logger.info("citation check budget exhausted, skipping %s", getattr(item, "id", "?"))
        return CitationVerdict()

    query = build_query(item)
    _checks_used += 1

    if search is None:
        from .tools import WebSearchTool

        async def search(text: str) -> list[dict[str, str]]:
            return await WebSearchTool().execute({"query": text})

    try:
        results = await search(query)
    except Exception as exc:  # network failure must not change the digest
        logger.warning("citation check failed for %s: %s", getattr(item, "id", "?"), exc)
        return CitationVerdict(applicable=True, verified=True, query=query)

    evidence = is_corroborated(results or [])
    return CitationVerdict(
        applicable=True,
        verified=evidence is not None,
        query=query,
        evidence=evidence or "",
    )


async def adjust_analysis(
    item: Any,
    analysis: Any,
    search: Optional[Callable[[str], Any]] = None,
) -> Any:
    """Return ``analysis`` unchanged, or a downgraded copy when unverified."""
    score = getattr(analysis, "score", None)
    if score is None or score < MIN_SCORE_TO_CHECK:
        return analysis

    verdict = await verify_item(item, search=search)
    if not verdict.unverified:
        return analysis

    adjusted = round(max(score - CITATION_PENALTY, 0.0), 1)
    reason = getattr(analysis, "reason", "") or ""
    note = f"引述境外机构但未找到一手来源，降 {CITATION_PENALTY:g} 分"
    tags = list(getattr(analysis, "tags", []) or [])
    if UNVERIFIED_TAG not in tags:
        tags.append(UNVERIFIED_TAG)

    logger.info(
        "citation check: %s unverified via %r, score %.1f -> %.1f",
        getattr(item, "id", "?"),
        verdict.query,
        score,
        adjusted,
    )
    return analysis.model_copy(
        update={
            "score": adjusted,
            "reason": f"{reason}；{note}" if reason else note,
            "tags": tags,
        }
    )
