"""Model-assisted theme selection for stories the heat list does not name.

Theme matching is a literal term lookup: cheap, auditable, and blind to any
wording the index does not list. On top of that the digest looks at the top-200
heat list first, which on 2026-11-18 covered 181 of the 794 themes on the
listing page, so a story about a sector that is not being traded that day used
to fall through to a lexical sweep of the whole index and often to no theme
line at all.

This module is the middle pass: when the heat list names nothing, the model
reads the item and picks from the index. It is one short call per unmatched
item, and it may only return names that exist in the index, so the result
always resolves to a page with a real member list.

The model used to see the whole catalogue as bare names. That is what made it
answer 集成电路制造 for a story about the domestic compute chain: the name
looked like the biggest adjacent thing, and nothing in the prompt said what the
theme actually holds. The index carries three layers of keywords per theme, so
the picker now recalls the themes whose keywords the story touches and shows
each candidate with its member count and its keywords. The model chooses among
about forty described candidates instead of seven hundred and fifty names.

Every pick carries a 0-100 relevance score. A pick below ``MIN_PICK_SCORE`` is
dropped even when the model offered it: the failure mode of a free-choice pick
is padding the answer to three themes, and a score the model has to commit to
is what makes that padding visible.
"""

import base64
import json
import logging
import unicodedata
import zlib
from pathlib import Path
from typing import Any, List, Optional, Sequence

from pydantic import BaseModel, Field, field_validator, model_validator

from .utils import parse_json_response

logger = logging.getLogger(__name__)

# The model only needs the item's gist to name a sector; the candidate list is
# what makes the call long, so the excerpt stays short.
EXCERPT_CHARS = 1200
MAX_PICKS = 3
# 60 is "there is a real transmission path to this sector"; below it the model
# is only noting that the words are related, which the digest should not print.
MIN_PICK_SCORE = 60
# Keyword recall: candidates whose terms the story actually touches.
CANDIDATE_LIMIT = 30
# Plus the largest themes by member count, so a story that names no keyword at
# all still sees the broad sectors the market trades every day.
BIG_THEME_LIMIT = 5
INDEX_PATH = Path("data/theme_index.json.gz.b64")

SYSTEM_PROMPT = """你是 A 股题材匹配助手。给定一条新闻和一份候选题材（每个题材带成分股数量和关键词），请选出这条新闻最相关的题材并给出相关度评分。

规则：
- 先写传导链，再选题材：事件改变了哪个环节（供给/需求/价格/成本/政策）→ 该环节对应哪个题材的成分股。只有传导链直接落在成分股主营上的题材才算相关。
- 只能从给定候选里逐字选择，不得改写、合并或新造题材名。
- 优先细分环节：候选里同时有宽泛概念和具体环节时，选传导落点最具体的那个。例如讲 GPU 租赁涨价，选「算力租赁」而不是「算力概念」；讲封装扩产，选「先进封装」或「集成电路封测」而不是「半导体」。只有当新闻影响整个板块时才用宽题材。
- 不要选只是字面相近的题材。例如讲算力链的设备与服务，不等于「集成电路制造」；讲出口增速回落，不等于「AI芯片」。
- 最多选 3 个，按相关度从高到低排列，三个要覆盖不同环节；同义或几乎重叠的题材只留一个（AIGC概念 与 ChatGPT概念、AI芯片 与 芯片概念 不要并列）。
- 评分口径：80 以上 = 新闻直接改变该板块的景气或预期；60-79 = 有明确传导路径但间接；60 以下 = 只是沾边，不要输出。
- reason 不超过 12 个汉字，写传导环节，不要复述新闻内容。
- 候选里确实没有相关题材时返回空数组。

输出格式：只输出一个 JSON 对象，不要任何解释文字。
{"themes": [{"name": "<题材名>", "score": 85, "reason": "<传导环节>"}]}"""


TERM_PROMPT = """你是 A 股行业分析师。读下面这条新闻，写出它影响 A 股的具体经营环节。

要求：
- 写环节，不写板块名：例如「服务器整机」「液冷」「IDC 机柜」「光模块」「晶圆代工」「存储颗粒」「封装基板」。
- 最多 5 个，每个 2-6 个字，按重要性排序。
- 只写环节本身，不写「利好」「受益」「关注」这类判断。
- 新闻与 A 股无关时返回空数组。

输出格式：只输出 JSON，不要解释。
{"terms": ["环节1", "环节2"]}"""


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
        max_tokens: int = 500,
        candidate_limit: int = CANDIDATE_LIMIT,
    ):
        self.client = ai_client
        self.max_picks = max(1, max_picks)
        self.max_tokens = max_tokens
        self.candidate_limit = max(1, candidate_limit)
        self._rows: Optional[List[dict]] = None
        self._known: dict[str, str] = {}

    def _load_rows(self) -> List[dict]:
        """Read the index once for name, member count and keyword layers.

        The picker reads the same file the theme index reads; a missing or
        unreadable file only costs the keyword recall, and the caller then sees
        the plain name list it saw before.
        """
        if self._rows is not None:
            return self._rows
        rows: List[dict] = []
        try:
            parts = [
                INDEX_PATH,
                *sorted(INDEX_PATH.parent.glob(INDEX_PATH.name + ".p[0-9]*")),
            ]
            raw = b"".join(part.read_bytes() for part in parts if part.exists())
            doc = json.loads(zlib.decompress(base64.b64decode(raw)))
            for row in doc.get("themes") or []:
                if not isinstance(row, list) or len(row) < 6 or not row[1]:
                    continue
                terms: List[tuple[str, float]] = []
                seen: set[str] = set()
                for layer, weight in ((row[3], 1.0), (row[4], 0.75), (row[5], 0.5)):
                    for term in str(layer or "").split(","):
                        term = term.strip()
                        if term and term not in seen:
                            seen.add(term)
                            terms.append((term, weight))
                rows.append(
                    {
                        "name": str(row[1]).strip(),
                        "count": int(row[2] or 0),
                        "terms": terms,
                    }
                )
        except (OSError, ValueError, zlib.error) as exc:
            logger.warning("Theme picker keyword recall unavailable: %s", exc)
        self._rows = rows
        return rows

    def recall(
        self, text: str, names: Sequence[str], terms: Sequence[str] = ()
    ) -> List[dict]:
        """Themes whose keywords the story or its extracted links touch.

        Recall is local and free: it only decides what the model gets to see,
        and every candidate still has to clear the model's own score floor.
        ``terms`` are the operating links the model named first; a theme whose
        keywords cover one of them is recalled even when the story never uses
        that word, which is how 算力链 reaches 服务器整机 or 液冷.
        """
        rows = self._load_rows()
        allowed = {str(name).strip() for name in names}
        if not rows:
            return [
                {"name": name, "count": 0, "terms": []}
                for name in names[: self.candidate_limit]
            ]
        hay = _fold(text)
        links = [_fold(term) for term in terms if str(term).strip()]
        scored: List[tuple[float, dict]] = []
        for row in rows:
            if row["name"] not in allowed:
                continue
            score = 0.0
            if _fold(row["name"]) in hay:
                score += 3.0
            for term, weight in row["terms"]:
                folded = _fold(term)
                if folded in hay:
                    score += weight * min(len(term), 6) / 6.0
                elif any(link and (link in folded or folded in link) for link in links):
                    score += 1.5 * weight
            if score > 0:
                scored.append((score, row))
        scored.sort(key=lambda pair: (-pair[0], -pair[1]["count"]))
        picked = [row for _, row in scored[: self.candidate_limit]]
        have = {row["name"] for row in picked}
        # A thin recall would otherwise leave the model choosing among the same
        # five mega-sectors for every story, so only top up a short list.
        if len(picked) < 15:
            for row in sorted(rows, key=lambda item: -item["count"])[:BIG_THEME_LIMIT]:
                if row["name"] in allowed and row["name"] not in have:
                    picked.append(row)
                    have.add(row["name"])
        return picked

    @staticmethod
    def _catalogue(candidates: Sequence[dict]) -> str:
        """One line per candidate: name, member count, leading keywords."""
        lines = []
        for row in candidates:
            desc = "、".join(term for term, _ in row["terms"][:4])[:28]
            count = row["count"]
            lines.append(
                f"{row['name']}｜成员{count}｜{desc}" if desc else f"{row['name']}｜成员{count}"
            )
        return "\n".join(lines)

    async def _extract_terms(self, excerpt: str) -> List[str]:
        """Name the operating links the story hits, before any theme is chosen.

        Picking a theme name directly asks the model to guess what a name holds;
        naming the link first is a much smaller question, and the answer is what
        lets recall reach the specific theme instead of the broad one.
        """
        try:
            response = await self.client.complete(
                system=TERM_PROMPT,
                user=f"新闻内容：{excerpt}",
                temperature=0,
                max_tokens=150,
            )
        except Exception as exc:  # noqa: BLE001 - recall still works on the text
            logger.warning("Theme link extraction failed: %s", exc)
            return []
        parsed = parse_json_response(response or "")
        if not isinstance(parsed, dict):
            return []
        raw = parsed.get("terms")
        if not isinstance(raw, list):
            return []
        terms = []
        for item in raw:
            term = str(item or "").strip()
            if term and term not in terms:
                terms.append(term)
        logger.warning("Theme links: %s", "、".join(terms[:5]) or "none")
        return terms[:5]

    async def pick(self, text: str, names: Sequence[str]) -> List[str]:
        """Return up to ``max_picks`` theme names, all present in ``names``.

        Raises on a provider failure; the caller treats that as "no pick" and
        falls through to the lexical sweep.
        """
        if not names:
            return []
        excerpt = " ".join(str(text or "").split())[:EXCERPT_CHARS]
        if not excerpt:
            return []
        terms = await self._extract_terms(excerpt)
        candidates = self.recall(excerpt, names, terms)
        if not candidates:
            return []
        self._known = {_fold(row["name"]): row["name"] for row in candidates}
        catalogue = self._catalogue(candidates)
        response = await self.client.complete(
            system=SYSTEM_PROMPT,
            user=(
                f"新闻内容：{excerpt}\n\n"
                f"候选题材（共 {len(candidates)} 个，格式：题材名｜成分股数量｜关键词）：\n"
                f"{catalogue}\n\n"
                f"请从候选中选出这条新闻最相关的至多 {self.max_picks} 个题材，"
                "给出相关度评分和传导环节，按给定格式输出 JSON。"
            ),
            temperature=0,
            max_tokens=self.max_tokens,
        )
        picked = self._clean(self._parse(response or ""))
        # WARNING so the counts reach the Actions log: they are the only record
        # of how much the keyword recall narrowed the choice.
        logger.warning(
            "Theme picker recall: %d candidates from %d names, kept %d",
            len(candidates),
            len(names),
            len(picked),
        )
        return picked

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
