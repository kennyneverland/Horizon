"""早盘快讯 → Google News 检索 query。

早报的中国股市板块长期只有 6-8 条，缺的不是配额，是候选：一天里真正的 A 股
消息大多先以单行快讯的形式出现（东财早盘页、财联社电报），没有正文、没有背景，
AI 评分上不去，也落不到题材词上，最后只能挤在「要闻补充」那个小字块里。

快讯本身不是新闻，快讯指向的报道才是。所以这里把快讯标题转成检索 query，由
google_news 把背后的完整报道捞回来，再走正常的评分与落标。

query 的取法：标题按标点切段，取最长的一段——那通常是被压掉主语之后剩下的
事件本体；整条不超过 24 字。短于 8 字的（「三大指数集体高开」这类）没有检索
价值，跳过。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from ..models import GoogleNewsConfig

# 快讯标题里的分段符：中文标点、竖线、空白。
_SPLIT_RE = re.compile(r"[，。；：、｜|,.;:\s]+")
MAX_QUERY_CHARS = 24
MIN_QUERY_CHARS = 8
# 3 条够用：每条 5 个结果，最多补 15 个候选，填满 10 条配额还有余量；再多会
# 挤占日历事件和现有 query 的位置。
MAX_QUERIES = 3
RESULTS_PER_QUERY = 5


def _query_of(title: str) -> str:
    """一条快讯标题 → 一个检索词。

    有分段就取最长的一段：「期市早盘开盘，国内期货主力合约多数上涨」里，前半是
    时间场景、后半才是事件本体，整条拿去搜会召回一堆开盘综述。
    """
    title = (title or "").strip()
    parts = [part.strip() for part in _SPLIT_RE.split(title) if part.strip()]
    if len(parts) > 1:
        title = max(parts, key=len)
    return title[:MAX_QUERY_CHARS]


def to_queries(
    news: List[Dict[str, Any]], max_queries: int = MAX_QUERIES
) -> List[GoogleNewsConfig]:
    """快讯列表 → Google News query，按页面顺序取前几条。"""
    out: List[GoogleNewsConfig] = []
    seen: set[str] = set()
    for row in news or []:
        title = str((row or {}).get("title") or "").strip()
        if not title:
            continue
        query = _query_of(title)
        if len(query) < MIN_QUERY_CHARS or query in seen:
            continue
        seen.add(query)
        out.append(
            GoogleNewsConfig(
                enabled=True,
                query=query,
                language="zh-CN",
                country="CN",
                ceid="CN:zh-Hans",
                max_results=RESULTS_PER_QUERY,
                category="finance",
                profile="china-market",
            )
        )
        if len(out) >= max_queries:
            break
    return out
