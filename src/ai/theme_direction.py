"""Two-way impact direction for the A-share themes matched to one item.

Theme matching is a literal word lookup: it can only tell that a story mentions
a theme. Whether the story helps or hurts that theme's constituents is a
reading judgement, so it is asked of the model separately - one short call per
item, and only for themes that already matched.

The direction judge is where a theme's wording is actually produced, so it is
also where the mainline state has to arrive. The picker sees the limit-up count
when it chooses a theme, but the sentence a reader ends up with - "业绩提振需求"
versus "该方向已过热" - is written here. Passing the state only to the picker
left the fire mark with nothing to act on: on 2026-11-18 a theme sitting on 22
limit-ups and marked hot still rendered as a fresh positive.
"""

import asyncio
import logging
from typing import Any, Dict, List, Literal, Optional, Sequence

from pydantic import BaseModel, Field

from .utils import gather_ai_tasks, parse_json_response
from ..processing.ashare_themes import NEGATIVE, NEUTRAL, POSITIVE, matching_text
from ..processing.mainline import format_state

logger = logging.getLogger(__name__)

EXCERPT_CHARS = 1200

SYSTEM_PROMPT = """你是 A 股题材影响判定助手。给定一条新闻和它已经匹配上的题材，判断这条新闻对每个题材是积极影响、负面影响，还是多空交织。

判定规则：
- 逐个题材独立判断。不要用整条新闻的情绪套给所有题材。
- 判断对象是该题材所对应板块及其成分股的基本面或预期，不是新闻里被点名的那家公司本身。
- 同一件事对不同题材经常方向相反。例如出口管制对国产替代题材偏积极、对依赖海外供应链的题材偏消极；价格战对头部厂商偏积极、对二线厂商偏消极。
- 三个方向：positive（积极影响）、negative（负面影响）、neutral（多空交织，或只是提到该题材、看不出明确方向）。
- 不要为了凑方向强行二选一：消息只是顺带提及该题材，或者利好利空同时存在且量级相当，就判 neutral。
- 题材后面若带主线状态（如「主线算力 涨停22🔥 前日5」），它说明该产业线上一交易日的涨停家数，只说明资金当天是否在交易这个方向，不是这条新闻导致它涨的证据。
- 带 🔥 表示该方向已进入过热区（该站口径：单日 ≥20 家；其对 2022 年以来 946 个交易日的回测显示，达到该量级的主线次日家数腰斩概率约 66%）。方向仍按新闻本身判断，但 reason 必须体现该方向已被充分交易、追高风险上升，不得只写成新增利好。其中「涨停N🔥 前日低」属突然加速、消息驱动，持续性待次日验证；「涨停N🔥 前日也高」属连续亢奋，接近衰竭。
- 标了「今日归零」表示该方向已退潮：方向仍按新闻本身判断，但 reason 应说明已回落，不得写成「正在发酵」。
- reason 不超过 15 个汉字，说明方向依据，不要复述新闻内容。

输出格式：只输出一个 JSON 对象，不要任何解释文字。
{"themes": [{"name": "<题材名>", "direction": "positive|negative|neutral", "reason": "<方向依据>"}]}
name 必须与给定题材名逐字一致，不要新增题材，不要漏掉给定题材。"""


class ThemeVerdict(BaseModel):
    """One theme's direction for one item."""

    name: str
    direction: Literal["positive", "negative", "neutral"]
    reason: str = ""


class ThemeVerdictBatch(BaseModel):
    themes: List[ThemeVerdict] = Field(default_factory=list)


class ThemeDirectionJudge:
    """Ask the model which way a story pushes each already-matched theme."""

    def __init__(
        self,
        ai_client: Any,
        *,
        concurrency: int = 5,
        max_tokens: int = 400,
    ):
        self.client = ai_client
        self.concurrency = max(concurrency, 1)
        self.max_tokens = max_tokens

    @staticmethod
    def _themes(item: Any) -> List[Dict[str, Any]]:
        metadata = getattr(item, "metadata", None) or {}
        themes = metadata.get("ashare_themes") or []
        return [theme for theme in themes if isinstance(theme, dict) and theme.get("name")]

    async def judge_batch(self, items: Sequence[Any]) -> int:
        """Judge every item that has matched themes; returns the success count.

        A failed item keeps its themes without a direction, and the digest
        renders those under a separate, direction-free label.
        """
        pending = [item for item in items if self._themes(item)]
        if not pending:
            return 0
        semaphore = asyncio.Semaphore(self.concurrency)

        async def run(item: Any) -> bool:
            async with semaphore:
                return await self.judge(item)

        results = await gather_ai_tasks([run(item) for item in pending])
        return sum(1 for ok in results if ok)

    async def judge(self, item: Any) -> bool:
        themes = self._themes(item)
        if not themes:
            return True
        try:
            response = await self.client.complete(
                system=SYSTEM_PROMPT,
                user=self._user_prompt(item, themes),
                temperature=0,
                max_tokens=self.max_tokens,
            )
            verdicts = self._parse(response or "")
        except Exception as exc:  # a direction miss must never fail the item
            logger.warning(
                "Theme direction judge failed for %s: %s", getattr(item, "id", "?"), exc
            )
            return False
        if not verdicts:
            logger.warning(
                "Theme direction judge returned no usable verdict for %s",
                getattr(item, "id", "?"),
            )
            return False
        for theme in themes:
            verdict = verdicts.get(theme["name"])
            if verdict is None:
                continue
            theme["direction"] = verdict.direction
            if verdict.reason:
                theme["direction_reason"] = verdict.reason
        return True

    @staticmethod
    def _parse(response: str) -> Dict[str, ThemeVerdict]:
        parsed = parse_json_response(response)
        if not isinstance(parsed, dict):
            return {}
        try:
            batch = ThemeVerdictBatch.model_validate(parsed)
        except Exception:
            return {}
        return {
            verdict.name.strip(): verdict
            for verdict in batch.themes
            if verdict.name and verdict.name.strip()
        }

    @staticmethod
    def _user_prompt(item: Any, themes: Sequence[Dict[str, Any]]) -> str:
        text = " ".join(matching_text(item).split())[:EXCERPT_CHARS]
        labelled = []
        for theme in themes:
            tag = format_state(theme.get("mainline"))
            labelled.append(f"{theme['name']}（{tag}）" if tag else str(theme["name"]))
        names = "；".join(labelled)
        return (
            f"新闻内容：{text}\n\n"
            f"已匹配题材：{names}\n\n"
            f"请判断这条新闻对上述每一个题材是 {POSITIVE}（积极影响）、"
            f"{NEGATIVE}（负面影响）还是 {NEUTRAL}（多空交织），按给定格式输出 JSON。"
        )
