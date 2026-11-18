"""Model-assisted theme selection for stories the heat list does not name.

Theme matching is a literal term lookup: cheap, auditable, and blind to any
wording the index does not list. On top of that the digest looks at the top-200
heat list first, which on 2026-11-18 covered 181 of the 794 themes on the
listing page, so a story about a sector that is not being traded that day used
to fall through to a lexical sweep of the whole index and often to no theme
line at all.

This module is the middle pass: when the heat list names nothing, the model
reads the item and picks from the whole index. It is one short call per
unmatched item, and it may only return names that exist in the index, so the
result always resolves to a page with a real member list.

Every pick carries a 0-100 relevance score. A pick below ``MIN_PICK_SCORE`` is
dropped even when the model offered it: the failure mode of a free-choice pick
is padding the answer to three themes, and a score the model has to commit to
is what makes that padding visible.
"""

import logging
import unicodedata
from typing import Any, List, Optional, Sequence

from pydantic import BaseModel, Field, field_validator, model_validator

from .utils import parse_json_response

logger = logging.getLogger(__name__)

# The model only needs the item's gist to name a sector, and the catalogue is
# what makes the call long; keeping the excerpt short bounds the prompt.
EXCERPT_CHARS = 1200
MAX_PICKS = 3
# 60 is "there is a real transmission path to this sector"; below it the model
# is only noting that the words are related, which the digest should not print.
MIN_PICK_SCORE = 60

SYSTEM_PROMPT = """你是 A 股题材匹配助手。给定一条新闻和一份题材名单，请从名单中选出这条新闻最相关的题材，并给出相关度评分。

规则：
- 只能从给定名单里逐字选择，不得改写、合并或新造题材名。
- 最多选 3 个，按相关度从高到低排列。
- 相关度看新闻内容对该题材成分股的基本面或预期有没有实质影响；只是字面提到该题材不算相关。
- 同一件事可能同时影响上游和下游两个题材，可以都选；但不要为了凑满三个而选弱相关的。
- 评分口径：80 以上 = 新闻直接改变该板块的景气或预期；60-79 = 有明确的传导路径但间接；60 以下 = 只是沾边，不要输出。
- reason 不超过 12 个汉字，说明传导路径，不要复述新闻内容。
- 确实没有相关题材时返回空数组。

输出格式：只输出一个 JSON 对象，不要任何解释文字。
{"themes": [{"name": "<题材名>", "score": 85, "reason": "<传导路径>"}]}"""


def _fold(text: Any) -> str:
    """Fold width and case so a copied name matches the catalogue entry."""
    return unicodedata.normalize("NFKC", str(text or "")).strip().lower()


class ThemePickItem(BaseModel):
    """One theme the model named, with the score it committed to."""

    name: str
    score: int = 70
    reason: str = ""

    @model_validator(mode="before")
    @classmethod
    def accept_bare_name(cls, value: Any) -> Any:
        # A model that answers with plain names still gets read, at a neutral
        # score: dropping the whole pick over a format slip costs more than the
        # score is worth.
        if isinstance(value, str):
            return {"name": value}
        return value

    @field_validator("score", mode="before")
    @classmethod
    def coerce_score(cls, value: Any) -> int:
        try:
            return int(float(str(value).strip().rstrip("分")))
        except (TypeError, ValueError):
            return 70


class ThemePick(BaseModel):
    themes: List[ThemePickItem] = Field(default_factory=list)


class ThemePicker:
    """Ask the model which index themes a heat-list miss touches."""

    def __init__(
        self,
        ai_client: Any,
        *,
        max_picks: int = MAX_PICKS,
        max_tokens: int = 300,
    ):
        self.client = ai_client
        self.max_picks = max(1, max_picks)
        self.max_tokens = max_tokens
        self._catalogue_text: Optional[str] = None
        self._catalogue_size = 0
        self._known: dict[str, str] = {}

    def _catalogue(self, names: Sequence[str]) -> str:
        """One line per theme, built once per run.

        The index is the same for every item, so the joined text and the folded
        lookup are cached; a different list (a test, or a rebuilt index) simply
        rebuilds them.
        """
        if self._catalogue_text is None or len(names) != self._catalogue_size:
            self._catalogue_text = "\n".join(names)
            self._catalogue_size = len(names)
            self._known = {_fold(name): name for name in names}
        return self._catalogue_text

    async def pick(self, text: str, names: Sequence[str]) -> List[str]:
        """Return up to ``max_picks`` theme names, all present in ``names``.

        Raises on a provider failure; the caller treats that as "no pick" and
        falls through to the lexical sweep.
        """
        if not names:
            return []
        catalogue = self._catalogue(names)
        excerpt = " ".join(str(text or "").split())[:EXCERPT_CHARS]
        if not excerpt:
            return []
        response = await self.client.complete(
            system=SYSTEM_PROMPT,
            user=(
                f"新闻内容：{excerpt}\n\n"
                f"题材名单（共 {len(names)} 个，每行一个）：\n{catalogue}\n\n"
                f"请从名单中选出这条新闻最相关的至多 {self.max_picks} 个题材，"
                "给出相关度评分和传导路径，按给定格式输出 JSON。"
            ),
            temperature=0,
            max_tokens=self.max_tokens,
        )
        return self._clean(self._parse(response or ""))

    def _clean(self, picks: Sequence[ThemePickItem]) -> List[str]:
        """Keep the picks that clear the score floor, in the model's order.

        A name the catalogue does not carry verbatim is forwarded as written:
        the index side resolves 人形机器人 to 机器人 and drops what it cannot
        place, so a near miss survives instead of losing the whole pick here.
        """
        kept: List[str] = []
        kept_labels: List[str] = []
        foreign: List[str] = []
        weak: List[str] = []
        for pick in picks:
            if pick.score < MIN_PICK_SCORE:
                weak.append(f"{pick.name}({pick.score})")
                continue
            original = self._known.get(_fold(pick.name))
            if original is None:
                foreign.append(pick.name)
                original = str(pick.name).strip()
            if original in kept:
                continue
            kept.append(original)
            reason = "".join(pick.reason.split())[:12]
            kept_labels.append(f"{original} {pick.score}" + (f"（{reason}）" if reason else ""))
            if len(kept) >= self.max_picks:
                break
        # WARNING so the lines reach the Actions log: they are the only record
        # of why a story got these themes, and of how much the model padded.
        if kept_labels:
            logger.warning("Theme picker kept: %s", "、".join(kept_labels))
        if weak:
            logger.warning(
                "Theme picker dropped %d below-score name(s): %s",
                len(weak),
                "、".join(weak[:5]),
            )
        if foreign:
            logger.warning(
                "Theme picker forwarded %d name(s) not in the catalogue verbatim: %s",
                len(foreign),
                "、".join(foreign[:5]),
            )
        return kept

    @staticmethod
    def _parse(response: str) -> List[ThemePickItem]:
        parsed = parse_json_response(response)
        if not isinstance(parsed, dict):
            return []
        try:
            batch = ThemePick.model_validate(parsed)
        except Exception:
            return []
        return [item for item in batch.themes if str(item.name).strip()]
