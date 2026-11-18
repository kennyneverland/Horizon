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
"""

import logging
import unicodedata
from typing import Any, List, Optional, Sequence

from pydantic import BaseModel, Field

from .utils import parse_json_response

logger = logging.getLogger(__name__)

# The model only needs the item's gist to name a sector, and the catalogue is
# what makes the call long; keeping the excerpt short bounds the prompt.
EXCERPT_CHARS = 1200
MAX_PICKS = 3

SYSTEM_PROMPT = """你是 A 股题材匹配助手。给定一条新闻和一份题材名单，请从名单中选出这条新闻最相关的题材。

规则：
- 只能从给定名单里逐字选择，不得改写、合并或新造题材名。
- 最多选 3 个，按相关度从高到低排列。
- 相关度看新闻内容对该题材成分股的基本面或预期有没有实质影响；只是字面提到该题材不算相关。
- 同一件事可能同时影响上游和下游两个题材，可以都选；但不要为了凑满三个而选弱相关的。
- 确实没有相关题材时返回空数组。

输出格式：只输出一个 JSON 对象，不要任何解释文字。
{"themes": ["<题材名>", "<题材名>"]}"""


def _fold(text: Any) -> str:
    """Fold width and case so a copied name matches the catalogue entry."""
    return unicodedata.normalize("NFKC", str(text or "")).strip().lower()


class ThemePick(BaseModel):
    """The model's answer: theme names copied from the given catalogue."""

    themes: List[str] = Field(default_factory=list)


class ThemePicker:
    """Ask the model which index themes a heat-list miss touches."""

    def __init__(
        self,
        ai_client: Any,
        *,
        max_picks: int = MAX_PICKS,
        max_tokens: int = 200,
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
                "按给定格式输出 JSON。"
            ),
            temperature=0,
            max_tokens=self.max_tokens,
        )
        return self._clean(self._parse(response or ""))

    def _clean(self, picked: Sequence[str]) -> List[str]:
        """Keep only names the catalogue carries, in the model's order."""
        kept: List[str] = []
        unknown: List[str] = []
        for name in picked:
            original = self._known.get(_fold(name))
            if original is None:
                unknown.append(str(name))
                continue
            if original in kept:
                continue
            kept.append(original)
            if len(kept) >= self.max_picks:
                break
        if unknown:
            # WARNING so the line reaches the Actions log: a model that invents
            # names would otherwise look like a clean pick.
            logger.warning(
                "Theme picker dropped %d name(s) outside the index: %s",
                len(unknown),
                "、".join(unknown[:5]),
            )
        return kept

    @staticmethod
    def _parse(response: str) -> List[str]:
        parsed = parse_json_response(response)
        if not isinstance(parsed, dict):
            return []
        try:
            batch = ThemePick.model_validate(parsed)
        except Exception:
            return []
        return [str(name).strip() for name in batch.themes if str(name).strip()]