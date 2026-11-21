"""Daily summary generation — pure programmatic rendering."""

import asyncio
import html
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import quote, urlsplit

from .localization import normalize_language
from ..models import ContentItem
from ..processing.ashare_themes import NEGATIVE, NEUTRAL, POSITIVE, source_footer
from ..processing.conduction import direction_note
from ..processing import next_day
from ..processing.overnight import fetch_overnight
from ..processing.premarket import fetch_premarket
from ..processing.digest_rules import (
    TECH_CHILD_IDS,
    TECH_PARENT_TITLE,
    nest_tech_sections,
)

logger = logging.getLogger(__name__)


_CJK = r"[\u4e00-\u9fff\u3400-\u4dbf]"
_ASCII = r"[A-Za-z0-9]"
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()<>#!|])")
_MARKDOWN_BLOCK_START = re.compile(r"(?m)^( {0,3})(>|[-+] |\d+[.)] )")
_URL_SAFE_CHARS = ":/?#[]@!$&'*,;=~%+"


def _escape_markdown(value: object) -> str:
    """Render untrusted text literally while retaining its readable content."""
    escaped = html.escape(str(value), quote=True)
    escaped = _MARKDOWN_SPECIAL.sub(r"\\\1", escaped)
    return _MARKDOWN_BLOCK_START.sub(r"\1\\\2", escaped)


def _quote_block(text: str) -> str:
    """Wrap one annotation block in a Markdown quote.

    Server酱 strips HTML, so font size and colour cannot be set directly. A
    quote is the strongest structural cue Markdown still offers: renderers give
    it its own indent and colour, which keeps these annotation blocks distinct
    from the news body.
    """
    return "\n".join("> " + line if line.strip() else ">" for line in text.splitlines())


# Tags that must lead the tag line and stand out from the plain ``#tag`` chips.
_PINNED_TAGS = ("未证实",)


def _format_tags(tags: list[str]) -> list[str]:
    """Render digest tags, pinning emphasis tags to the front and bolding them.

    Server酱 renders Markdown only, so font size cannot be changed; a bold
    full-width bracket is the strongest emphasis available.
    """
    pinned = [tag for tag in tags if tag in _PINNED_TAGS]
    rest = [tag for tag in tags if tag not in _PINNED_TAGS]
    formatted = [f"**【{_escape_markdown(tag)}】**" for tag in pinned]
    formatted.extend(f"`#{_escape_markdown(tag)}`" for tag in rest)
    return formatted


_TICKER_RE = re.compile(r"^(.*?)\s*[（(](\d{6})[)）]\s*$")


def _member_label(member: object) -> str:
    """``旋极信息（300324）`` → ``旋极信息 300324``.

    The bracket was half the readability problem: a ticker code, a direction
    reason and the disclaimer all wore the same full-width pair, so the eye
    could not tell one from another.
    """
    raw = str(member or "").strip()
    match = _TICKER_RE.match(raw)
    if match and match.group(1).strip():
        return f"{_escape_markdown(match.group(1).strip())} {match.group(2)}"
    return _escape_markdown(raw)


def _board_rank(label: str) -> int:
    """``3连板`` → 3，``首板`` → 1。只用来排序。"""
    if label == "首板":
        return 1
    digits = re.sub(r"\D", "", label or "")
    return int(digits) if digits else 0


def _carrier_line(theme: dict, members: list, brief_doc: object) -> str:
    """题材行下面那行「市场载体」：晚报说这条线今天真被买了哪些票。

    只在「这些票还没出现在本行成员里」时出现——重复的不印，成员表长度与来源
    一个字都不动。载体是证据，不是推荐：所以带上晚报的题材名与涨停家数，让
    读者看得见这是盘面口径，不是本行标题的复述。
    """
    if not brief_doc:
        return ""
    name = str(theme.get("name") or "").strip()
    if not name:
        return ""
    try:
        carrier = next_day.carriers(brief_doc, name)
    except Exception:  # noqa: BLE001 - 载体缺一行不影响正文
        return ""
    if not carrier:
        return ""
    # 成员是「旋极信息（300324）」这种带代码的字符串，movers 里只有名字。
    # 直接比字符串永远对不上，去重会失效——先把括号和代码剥掉再比。
    have = set()
    for m in members or []:
        raw = str(m.get("name") if isinstance(m, dict) else m).strip()
        hit = _TICKER_RE.match(raw)
        have.add((hit.group(1) if hit else raw).replace(" ", "").strip())
    extra = [
        m
        for m in carrier.get("movers") or []
        if str(m.get("name") or "").replace(" ", "") not in have
    ]
    if not extra:
        return ""
    leader = carrier.get("leader") or ""
    extra.sort(
        key=lambda m: (
            0 if str(m.get("name") or "") == leader else 1,
            -_board_rank(str(m.get("board") or "")),
        )
    )
    label = f"市场载体（{carrier.get('theme') or ''}"
    if carrier.get("count"):
        label += f" {carrier['count']} 家涨停"
    label += "）"
    names = []
    for m in extra[:4]:
        bit = _escape_markdown(str(m.get("name") or ""))
        board = str(m.get("board") or "")
        if board:
            bit += f" {board}"
        if board and _board_rank(board) >= 3:
            bit += " · 位置偏高"
        names.append(bit)
    return "  - " + label + "：" + "、".join(names)


def _render_theme_annotation(themes: list, brief_doc: object = None) -> str:
    """One heading per direction, one line per theme, one disclaimer at the end.

    Before, three brackets shared a single paragraph — ticker, reason,
    disclaimer — and three themes with fifteen names ran together, so a reader
    could not tell where one theme ended and why it was read that way. The
    reason now sits beside the theme name it belongs to, codes lose their
    brackets, and the disclaimer stands on its own line.
    """
    blocks: list[str] = []
    for direction, heading in ((POSITIVE, "积极影响"), (NEGATIVE, "负面影响")):
        rows = [theme for theme in themes if theme.get("direction") == direction]
        if not rows:
            continue
        lines = [f"**{heading}**", ""]
        for theme in rows:
            parts = [f"**{_escape_markdown(theme.get('name') or '')}**"]
            reason = _escape_markdown(direction_note(theme))
            if reason:
                parts.append(reason)
            members = theme.get("members") or []
            if members:
                parts.append("、".join(_member_label(m) for m in members))
            lines.append("- " + " · ".join(parts))
            carrier_line = _carrier_line(theme, members, brief_doc)
            if carrier_line:
                lines.append(carrier_line)
        blocks.append("\n".join(lines))
    pending = [
        theme
        for theme in themes
        if theme.get("direction") not in (POSITIVE, NEGATIVE, NEUTRAL)
    ]
    if pending:
        lines = ["**方向待定**", ""]
        for theme in pending:
            row = f"- **{_escape_markdown(theme.get('name') or '')}**"
            members = theme.get("members") or []
            if members:
                row += " · " + "、".join(_member_label(m) for m in members)
            lines.append(row)
        blocks.append("\n".join(lines))
    if not blocks:
        return ""
    blocks.append("*题材为规则匹配、方向为模型推测，非投资建议*")
    return "\n\n".join(blocks)


def _safe_url(value: object) -> Optional[str]:
    """Return an HTML/Markdown-safe HTTP(S) URL, or None for unsafe URLs."""
    raw = str(value).strip()
    if not raw or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return None
        parsed.port
    except (TypeError, ValueError):
        return None
    encoded = quote(raw, safe=_URL_SAFE_CHARS)
    return html.escape(encoded, quote=True)


def _pangu(text: str) -> str:
    """Insert a space between CJK and ASCII letters/digits (Pangu spacing)."""
    text = re.sub(rf"({_CJK})({_ASCII})", r"\1 \2", text)
    text = re.sub(rf"({_ASCII})({_CJK})", r"\1 \2", text)
    return text


LABELS = {
    "en": {
        "header": "Kenny's Horizon Daily",
        "source": "Source",
        "background": "Background",
        "discussion": "Discussion",
        "references": "References",
        "tags": "Tags",
        "themes": "Themes",
        "premarket": "Overnight tape",
        "overnight_map": "US movers → A-share themes",
        "overnight_asof": "US close {date}",
        "calendar": "Today's calendar",
        "premarket_note": "Backdrop only; the map is not a recommendation",
        "selected_items": "From {total} items, {selected} important content pieces were selected",
        "empty_analyzed": "Analyzed {total} items, but none met the importance threshold.",
        "empty_body": (
            "No significant developments today. This might indicate:\n"
            "- A quiet day in your tracked sources\n"
            "- The AI score threshold is too high\n"
            "- Your information sources need expansion\n\n"
            "Consider:\n"
            "1. Lowering the configured profile threshold\n"
            "2. Adding more diverse information sources\n"
            "3. Checking if the AI model is working correctly\n"
        ),
    },
    "zh": {
        "header": "Kenny's Horizon 每日精选新闻速递",
        "source": "来源",
        "background": "背景",
        "discussion": "社区讨论",
        "references": "参考链接",
        "tags": "标签",
        "themes": "A股题材",
        "premarket": "隔夜外围",
        "overnight_map": "关键个股 → A股映射",
        "overnight_asof": "美东 {date} 收盘",
        "calendar": "今日日历",
        "premarket_note": "隔夜情绪参考，非题材推荐",
        "selected_items": "从 {total} 条内容中筛选出 {selected} 条重要资讯。",
        "empty_analyzed": "已分析 {total} 条内容，但没有达到重要性阈值的条目。",
        "empty_body": (
            "今日暂无重要动态，可能原因：\n"
            "- 今天关注的信息源较平静\n"
            "- AI 评分阈值设置过高\n"
            "- 信息源种类有待扩充\n\n"
            "建议：\n"
            "1. 降低当前 Profile 的过滤阈值\n"
            "2. 添加更多多样化的信息源\n"
            "3. 检查 AI 模型是否正常工作\n"
        ),
    },
}


@dataclass(frozen=True)
class SummaryItemView:
    item: ContentItem
    index: int
    global_index: int
    group_count: int
    title: str
    score: float | str
    anchor_id: str


@dataclass(frozen=True)
class SummaryGroupView:
    profile_id: str
    name: str
    items: List[SummaryItemView]


@dataclass(frozen=True)
class DailySummaryView:
    groups: List[SummaryGroupView]
    item_count: int


class DailySummarizer:
    """Generates daily Markdown summaries from pre-analyzed content items."""

    def __init__(
        self,
        profile_names: Optional[Dict[str, Dict[str, str]]] = None,
        profile_order: Optional[List[str]] = None,
    ):
        self.profile_names = profile_names or {}
        self.profile_order = profile_order or []

    @staticmethod
    def _profile_id(item: ContentItem) -> str:
        if item.processing:
            return item.processing.classification.profile
        return item.profile if isinstance(item.profile, str) else "unclassified"

    def profile_name(self, profile_id: str, language: str) -> str:
        names = self.profile_names.get(profile_id, {})
        return names.get(
            language,
            names.get(
                "default",
                profile_id.replace("-", " ").replace("_", " ").title(),
            ),
        )

    def build_view(
        self,
        items: List[ContentItem],
        language: str,
    ) -> DailySummaryView:
        grouped_items: Dict[str, List[ContentItem]] = {}
        for item in items:
            grouped_items.setdefault(self._profile_id(item), []).append(item)

        ordered_groups = list(grouped_items.items())
        if self.profile_order:
            order = {
                profile_id: index
                for index, profile_id in enumerate(self.profile_order)
            }
            ordered_groups = sorted(
                ordered_groups,
                key=lambda group: order.get(group[0], len(order)),
            )

        groups = []
        global_index = 1
        for profile_id, profile_items in ordered_groups:
            view_items = []
            for index, item in enumerate(profile_items, start=1):
                artifact = (
                    item.processing.artifacts.get(language)
                    if item.processing
                    else None
                )
                analysis = item.processing.analysis if item.processing else None
                view_items.append(
                    SummaryItemView(
                        item=item,
                        index=index,
                        global_index=global_index,
                        group_count=len(profile_items),
                        title=normalize_language(
                            artifact.title if artifact else item.title, language
                        ),
                        score=(
                            analysis.score
                            if analysis and analysis.score is not None
                            else "?"
                        ),
                        anchor_id=self._item_anchor(profile_id, index),
                    )
                )
                global_index += 1
            groups.append(
                SummaryGroupView(
                    profile_id=profile_id,
                    name=normalize_language(
                        self.profile_name(profile_id, language), language
                    ),
                    items=view_items,
                )
            )
        return DailySummaryView(groups=groups, item_count=len(items))

    @staticmethod
    def _item_anchor(profile_id: str, index: int) -> str:
        safe_profile_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", profile_id).strip("-")
        return f"item-{safe_profile_id or 'unclassified'}-{index}"

    async def generate_summary(
        self,
        items: List[ContentItem],
        date: str,
        total_fetched: int,
        language: str = "en",
    ) -> str:
        """Generate daily summary in Markdown format.

        Items are rendered in score-descending order (already sorted by orchestrator).

        Args:
            items: High-scoring content items (already enriched)
            date: Date string (YYYY-MM-DD)
            total_fetched: Total number of items fetched before filtering
            language: Output language, either "en" or "zh"

        Returns:
            str: Markdown formatted summary
        """
        labels = LABELS.get(language, LABELS["en"])

        if not items:
            return self._generate_empty_summary(date, total_fetched, labels)

        header = (
            f"# {labels['header']} - {date}\n\n"
            f"{labels['selected_items'].format(total=total_fetched, selected=len(items))}\n\n"
            "---\n\n"
        )

        toc_sections = []
        body_sections = []
        view = self.build_view(items, language)
        for group in view.groups:
            profile_name = _escape_markdown(group.name)
            if language == "zh":
                profile_name = _pangu(profile_name)
            toc_entries = [f"**{profile_name}**"]
            for view_item in group.items:
                title = _escape_markdown(view_item.title)
                if language == "zh":
                    title = _pangu(title)
                toc_entries.append(
                    f"{view_item.index}. [{title}](#{view_item.anchor_id}) "
                    f"\u2b50\ufe0f {view_item.score}/10"
                )
            toc_sections.append("\n".join(toc_entries))
            section_title = (
                f"{profile_name}（标题汇总如下，详情下滑阅读）"
                if language == "zh"
                else profile_name
            )
            body_sections.append(f"## {section_title}\n\n")
            body_sections.extend(
                self._format_item(
                    view_item.item,
                    labels,
                    language,
                    view_item.index,
                    heading_level=3,
                    anchor_id=view_item.anchor_id,
                    title_override=view_item.title,
                    score_override=view_item.score,
                )
                for view_item in group.items
            )

        toc = "\n\n".join(toc_sections) + "\n\n---\n\n"
        premarket = await self._overnight_block(labels) if language == "zh" else ""
        calendar = await self._calendar_block(labels) if language == "zh" else ""
        # 晚报只读一次：三类桶和「市场载体」都要用，分两处各拉一遍没必要。
        self._brief_doc = None
        if language == "zh":
            try:
                self._brief_doc = await asyncio.to_thread(next_day.load, date)
            except Exception as exc:  # noqa: BLE001 - 拿不到晚报不该拖垮早报
                logger.warning("Next-day brief unavailable: %s", exc)
        nextday = await self._next_day_block(items, date) if language == "zh" else ""
        body = header + premarket + calendar + toc + "".join(body_sections) + nextday
        # 读者不需要看数据来源署名：题材成员已经内嵌在「今日建议关注题材」里，
        # 页脚再挂一行只会把正文挤长。
        text = normalize_language(body, language)
        # The three technology groups render as one section with sub-headings
        # rather than as peers of 财经新闻 and 中国股市.
        child_names = set()
        for profile_id in TECH_CHILD_IDS:
            name = _escape_markdown(self.profile_name(profile_id, language))
            if language == "zh":
                name = _pangu(name)
            child_names.add(name)
        parent_title = _escape_markdown(
            TECH_PARENT_TITLE.get(language, TECH_PARENT_TITLE["en"])
        )
        if language == "zh":
            parent_title = _pangu(parent_title)
        return nest_tech_sections(text, child_names, parent_title)

    async def _next_day_block(self, items: List[ContentItem], date: str) -> str:
        """昨晚晚报的三类判断，与今早的新闻覆盖交叉成一张坐标。

        晚报回答的是「钱明天往哪走」，早报回答的是「今天发生了什么」，而早报只从
        标题措辞里找答案。两边过去没有接口：2026-11-19 晚报点了六条线，11-20 早报
        只碰上一条，因为一条被晚报称作主线的题材，只有当天恰好有对应的新闻才会出现
        在早报里。

        这里把晚报读回来做交叉，得到四格：有判断且有新闻、有判断但今天没新闻、
        有新闻但晚报没点名。第三格是早报自己长出来的新苗头，缺了它，早报就退化
        成复述昨晚的结论。
        """
        themes: List[str] = []
        for item in items:
            for theme in (item.metadata or {}).get("ashare_themes") or []:
                name = str(theme.get("name") or "").strip()
                if name and name not in themes:
                    themes.append(name)
        if not themes:
            return ""
        doc = getattr(self, "_brief_doc", None)
        if not doc:
            return ""
        result = next_day.cross(doc, themes)
        if not result.get("rows"):
            return ""
        block = next_day.render_matrix(result)
        if not block:
            return ""
        return "\n\n---\n\n" + block

    async def _overnight_block(self, labels: dict) -> str:
        """Overnight US tape as backdrop, printed above the table of contents.

        Never a pick: across the five sessions to 2026-11-20, none of the
        thirty mapped themes reached the top 100 of lianban's heat board
        (median rank 575), so the block carries the move and the map and says
        in one line that it is not a recommendation.

        The source answers on weekends as well, so a Saturday digest prints
        Friday's close and a Monday digest prints that same close again — which
        is why the line names the session instead of the run date.
        """
        brief = await fetch_overnight()
        if not brief:
            return ""
        lines: list[str] = []
        indices = brief.get("indices") or []
        if indices:
            tape = " ｜ ".join(
                f"{_escape_markdown(row['name'])} {row['pct']:+.2f}%" for row in indices
            )
            lines.append(f"{labels['premarket']}：{tape}")
        movers = brief.get("movers") or []
        if movers:
            rows = []
            for row in movers:
                label = f"{_escape_markdown(row['ticker'])} {row['pct']:+.2f}%"
                themes = "·".join(_escape_markdown(name) for name in row["themes"])
                rows.append(f"{label}（{themes}）" if themes else label)
            lines.append(f"{labels['overnight_map']}：" + " ｜ ".join(rows))
        if not lines:
            return ""
        close = brief.get("close_date") or ""
        note = labels["premarket_note"]
        if close:
            note = f"{labels['overnight_asof'].format(date=close)} · {note}"
        lines.append(f"*{note}*")
        return "\n\n".join(lines) + "\n\n---\n\n"

    async def _calendar_block(self, labels: dict) -> str:
        """Today's scheduled events, printed under the overnight tape.

        A calendar belongs in the morning: by 19:10 the limit-up board has
        already answered what happened today, and what the reader needs then is
        tomorrow's list, not today's. The page carries the day's macro prints,
        unlocks and ex-rights dates from 06:00, so 08:00 sees the whole set. On
        a weekend the page has no snapshot and the block is skipped, which is
        right: there is no session to schedule.
        """
        brief = await fetch_premarket()
        if not brief:
            return ""
        events = (brief.get("events") or "").strip()
        calendar = brief.get("calendar") or []
        if not events and not calendar:
            return ""
        # Full-width brackets keep the macro line out of the Markdown escaper.
        if events:
            events = events.replace("(", "（").replace(")", "）")
        lines: list[str] = []
        if events:
            lines.append(f"**「{labels['calendar']}」** {_escape_markdown(events)}")
        grouped: dict[str, list] = {}
        for row in calendar:
            grouped.setdefault(str(row.get("tag") or ""), []).append(row)
        for tag, rows in grouped.items():
            names = "、".join(
                f"{_escape_markdown(row.get('name') or '')} {row.get('code') or ''}".strip()
                for row in rows
            )
            lines.append(f"**{_escape_markdown(tag)}**：{names}")
        return _quote_block("\n\n".join(lines)) + "\n\n---\n\n"

    def generate_webhook_overview(
        self,
        items: List[ContentItem],
        date: str,
        total_fetched: int,
        language: str = "en",
    ) -> str:
        """Generate a compact overview for multi-message webhook delivery."""
        labels = LABELS.get(language, LABELS["en"])
        if not items:
            return self._generate_empty_summary(date, total_fetched, labels)

        if language == "zh":
            header = (
                f"# {labels['header']} - {date}\n\n"
                f"从 {total_fetched} 条内容中筛选出 {len(items)} 条重要资讯。\n\n"
                "下面会按内容逐条发送详情，你可以只看感兴趣的标题。\n\n"
            )
        else:
            header = (
                f"# {labels['header']} - {date}\n\n"
                f"Selected {len(items)} important items from {total_fetched} fetched items.\n\n"
                "Details will be sent item by item so you can read only the topics you care about.\n\n"
            )

        sections = []
        view = self.build_view(items, language)
        for group in view.groups:
            profile_name = _escape_markdown(group.name)
            if language == "zh":
                profile_name = _pangu(profile_name)
            entries = [f"**{profile_name}**"]
            for view_item in group.items:
                title = _escape_markdown(view_item.title)
                if language == "zh":
                    title = _pangu(title)
                url = _safe_url(view_item.item.url)
                title_link = f"[{title}]({url})" if url else title
                entries.append(
                    f"{view_item.index}. {title_link} "
                    f"\u2b50\ufe0f {view_item.score}/10"
                )
            sections.append("\n".join(entries))

        return normalize_language(header + "\n\n".join(sections), language)

    def generate_webhook_item(
        self,
        item: ContentItem,
        language: str,
        index: int,
        total: int,
        *,
        title: Optional[str] = None,
        score: float | str | None = None,
    ) -> str:
        """Generate one item message for multi-message webhook delivery."""
        labels = LABELS.get(language, LABELS["en"])
        prefix = f"第 {index}/{total} 条\n\n" if language == "zh" else f"Item {index}/{total}\n\n"
        return normalize_language(
            prefix
            + self._format_item(
                item,
                labels,
                language,
                index,
                title_override=title,
                score_override=score,
            ).rstrip("-\n "),
            language,
        )

    def _format_item(
        self,
        item: ContentItem,
        labels: dict,
        language: str,
        index: int,
        *,
        heading_level: int = 2,
        anchor_id: Optional[str] = None,
        title_override: Optional[str] = None,
        score_override: float | str | None = None,
    ) -> str:
        """Format a single ContentItem into Markdown."""
        artifact = item.processing.artifacts.get(language) if item.processing else None
        analysis = item.processing.analysis if item.processing else None
        _title = title_override or (artifact.title if artifact else item.title)
        title = _escape_markdown(_title)
        raw_url = str(item.url)
        url = _safe_url(raw_url)
        score = (
            score_override
            if score_override is not None
            else analysis.score
            if analysis and analysis.score is not None
            else "?"
        )
        meta = item.metadata

        summary = analysis.summary if not artifact and analysis else ""
        primary_block = (
            next((block for block in artifact.blocks if block.primary), None)
            if artifact
            else None
        )

        summary = _escape_markdown(summary)
        primary_content = (
            _escape_markdown(primary_block.content) if primary_block else ""
        )

        if language == "zh":
            title = _pangu(title)
            summary = _pangu(summary)
            primary_content = _pangu(primary_content)

        # Source line with parts joined by " · ", link appended at end
        source_type = item.source_type.value
        source_parts = [_escape_markdown(source_type)]
        if meta.get("subreddit"):
            source_parts.append(_escape_markdown(f"r/{meta['subreddit']}"))
        if meta.get("feed_name"):
            source_parts.append(_escape_markdown(meta["feed_name"]))
        else:
            source_parts.append(_escape_markdown(item.author or "unknown"))
        if item.published_at:
            if language == "zh":
                source_parts.append(
                    f"{item.published_at.month}月{item.published_at.day}日 "
                    f"{item.published_at:%H:%M}"
                )
            else:
                day = item.published_at.strftime("%d").lstrip("0")
                source_parts.append(item.published_at.strftime(f"%b {day}, %H:%M"))
        source_line = " \u00b7 ".join(source_parts)  # ·

        discussion_url = meta.get("discussion_url")
        if discussion_url:
            safe_discussion_url = _safe_url(discussion_url)
            if safe_discussion_url and str(discussion_url) != raw_url:
                source_line += f' · [{labels["discussion"]}]({safe_discussion_url})'

        title_link = f"[{title}]({url})" if url else title

        lines = [
            f'<a id="{anchor_id or f"item-{index}"}"></a>',
            f"{'#' * heading_level} {title_link} \u2b50\ufe0f {score}/10",  # ⭐️
        ]
        if summary.strip():
            lines.extend(["", summary])
        if primary_content.strip():
            lines.extend(["", primary_content])
        lines.extend(["", source_line])

        if artifact:
            for block in artifact.blocks:
                if block.primary:
                    continue
                block_title = _escape_markdown(block.title)
                block_content = _escape_markdown(block.content)
                if language == "zh":
                    block_title = _pangu(block_title)
                    block_content = _pangu(block_content)
                lines.extend(["", f"「{block_title}」 {block_content}"])

        # A-share theme lookup: a plain rule match, so it is labelled as inferred
        # and never phrased as advice. Only the Chinese digest carries it.
        if language == "zh":
            themes = (item.metadata or {}).get("ashare_themes") or []
            theme_block = _render_theme_annotation(
                themes, getattr(self, "_brief_doc", None)
            )
            if theme_block:
                lines.extend(["", f"「{labels['themes']}」\n\n{theme_block}"])

        sources = artifact.sources if artifact else []
        if sources:
            reference_items = []
            for source in sources:
                reference_title = html.escape(source.title, quote=True)
                reference_url = _safe_url(source.url)
                if reference_url:
                    reference_items.append(f'<li><a href="{reference_url}">{reference_title}</a></li>\n')
                else:
                    reference_items.append(f"<li>{reference_title}</li>\n")
            items_html = "".join(reference_items)
            lines += [
                "",
                f'<details><summary>{labels["references"]}</summary>\n<ul>\n{items_html}\n</ul>\n</details>',
            ]

        if analysis and analysis.tags:
            tags_str = ", ".join(_format_tags(analysis.tags))
            lines.append("")
            lines.append(f"{labels['tags']}: {tags_str}")

        lines.append("")
        lines.append("---")

        return "\n".join(lines) + "\n\n"

    def _generate_empty_summary(self, date: str, total_fetched: int, labels: dict) -> str:
        """Generate summary when no high-scoring items were found."""
        return (
            f"# {labels['header']} - {date}\n\n"
            f"> {labels['empty_analyzed'].format(total=total_fetched)}\n\n"
            + labels["empty_body"]
        )
