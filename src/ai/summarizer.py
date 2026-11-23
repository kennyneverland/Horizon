"""Daily summary generation — pure programmatic rendering."""

import asyncio
import html
import logging
import re
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import quote, urlsplit

from .localization import normalize_language
from ..models import ContentItem
from ..processing.ashare_themes import NEGATIVE, NEUTRAL, POSITIVE, source_footer
from ..processing.conduction import direction_note
from ..processing import next_day
from ..processing.asia_open import fetch_asia_open
from ..processing.overnight import fetch_overnight
from ..processing.premarket import fetch_premarket
from ..processing import opening

logger = logging.getLogger(__name__)


_WEEKDAYS_CN = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
_WEEKDAYS_CN_LONG = (
    "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日",
)
# 早报的固定出刊时刻。定时在 09:30 起跑，标题写的就是这个时刻而不是运行时刻，
# 否则手动重跑一次，标题里的时间就跟着变了。
DIGEST_CLOCK = "09:30"
# 早间要闻补充挂在这个板块的新闻之后，作为它的子板块。
CHINA_MARKET_PROFILE = "china-market"


def _weekday_cn(date: str, *, long: bool = False) -> str:
    """``2026-11-23`` → ``周一``（``long=True`` 时 ``星期一``）；解析不了返回空串。"""
    try:
        day = datetime.strptime(str(date)[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return ""
    return (_WEEKDAYS_CN_LONG if long else _WEEKDAYS_CN)[day.weekday()]


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


def _pct_value(raw: object) -> float:
    """``"-16.1%"`` 与 ``-16.1`` 都读成 ``-16.1``：两个源一个给字符串一个给浮点。"""
    try:
        return float(str(raw).strip().rstrip("%"))
    except (TypeError, ValueError):
        return 0.0


def _title_grams(title: object) -> set[str]:
    """标题去标点后取相邻两字，用来比「说的是不是同一件事」。"""
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", str(title or "")).lower()
    return {text[i : i + 2] for i in range(len(text) - 1)}


def _same_topic(left: object, right: object) -> bool:
    """短标题的措辞基本被长标题包住时，判为同题。

    「沪深北交易所调整融资保证金比例」有 14 个二元组，其中 11 个出现在
    「沪深北交易所降低融资保证金比例下限至80%…」里，重合 0.79；而
    「沪深北交易所优化退市制度」与它只重合 0.45。阈值取 0.6。
    """
    first, second = _title_grams(left), _title_grams(right)
    if len(first) < 4 or len(second) < 4:
        return False
    shared = len(first & second)
    return shared >= 4 and shared / min(len(first), len(second)) >= 0.6


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
        "morning_news": "Morning headlines we did not cover",
        "overnight_asof": "US close {date}",
        "calendar": "Today's calendar",
        "asia_open": "Asia open",
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
        "header": "Kenny's Horizon 新闻精选早报",
        "source": "来源",
        "background": "背景",
        "discussion": "社区讨论",
        "references": "参考链接",
        "tags": "标签",
        "themes": "A股题材",
        "premarket": "隔夜外围",
        "overnight_map": "关键个股 → A股映射",
        "morning_news": "要闻补充",
        "overnight_asof": "美东 {date} 收盘",
        "calendar": "今日日历",
        "asia_open": "亚太今日开盘",
        "opening_title": "开盘异动",
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
        opening_snapshot: Optional[Dict] = None,
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
            return self._generate_empty_summary(date, total_fetched, labels, language)

        if language == "zh":
            header = (
                f"# 新闻早报 {date} {_weekday_cn(date, long=True)} {DIGEST_CLOCK}\n\n"
                f"{labels['selected_items'].format(total=total_fetched, selected=len(items))}\n\n"
                "---\n\n"
            )
        else:
            header = (
                f"# {labels['header']} - {date}\n\n"
                f"{labels['selected_items'].format(total=total_fetched, selected=len(items))}\n\n"
                "---\n\n"
            )

        toc_sections = []
        body_sections = []
        view = self.build_view(items, language)
        # 早盘页一次请求就够：隔夜映射、今早要闻与今日日历共用同一份，重复请求
        # 只会多撞一次 429。要闻要落进中国股市板块，所以取数得排在正文之前。
        brief = await fetch_premarket() if language == "zh" else None
        morning_placed = False
        for group in view.groups:
            profile_name = _escape_markdown(group.name)
            if language == "zh":
                profile_name = _pangu(profile_name)
            # 板块名用 span 挂样式：字号要压过下面的数字列表，同时保持与正文
            # 板块标题同色。profile_name 已经过 _escape_markdown，这里不能再转义，
            # 否则 span 的尖括号会被写成 \<。
            # 板块名之后必须空一行：列表紧贴段落时，渲染器会把「1. …」当成
            # 正文而不是有序列表，几条标题就挤在同一行里。
            toc_entries = [
                f'<span class="toc-group">{profile_name}</span>'
                "（标题汇总如下，详情下滑阅读）",
                "",
            ]
            for view_item in group.items:
                title = _escape_markdown(view_item.title)
                if language == "zh":
                    title = _pangu(title)
                toc_entries.append(
                    f"{view_item.index}. [{title}](#{view_item.anchor_id}) "
                    f"\u2b50\ufe0f {view_item.score}/10"
                )
            toc_sections.append("\n".join(toc_entries))
            # 要闻补充跟在「中国股市」这份标题汇总之后，属于汇总区，不进正文详情区。
            if language == "zh" and group.profile_id == CHINA_MARKET_PROFILE:
                entries = self._morning_news_entries(items, labels, brief)
                if entries:
                    toc_sections.append(
                        "\n".join([f"**{labels['morning_news']}**", "", *entries])
                    )
                    morning_placed = True
            body_sections.append(f"## {profile_name}\n\n")
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
        # 中国股市当天没有达标新闻时，没有可挂的汇总段落，退到汇总末尾。
        if language == "zh" and not morning_placed:
            entries = self._morning_news_entries(items, labels, brief)
            if entries:
                toc_sections.append(
                    "\n".join([f"**{labels['morning_news']}**", "", *entries])
                )

        toc = "\n\n".join(toc_sections) + "\n\n---\n\n"
        premarket = await self._overnight_block(labels, brief) if language == "zh" else ""
        opening_block = await self._opening_block(labels, date, opening_snapshot) if language == "zh" else ""
        calendar = self._calendar_block(labels, brief) if language == "zh" else ""
        # 晚报只读一次：三类桶和「市场载体」都要用，分两处各拉一遍没必要。
        self._brief_doc = None
        if language == "zh":
            try:
                self._brief_doc = await asyncio.to_thread(next_day.load, date)
            except Exception as exc:  # noqa: BLE001 - 拿不到晚报不该拖垮早报
                logger.warning("Next-day brief unavailable: %s", exc)
        nextday = await self._next_day_block(items, date) if language == "zh" else ""
        # 前缀辅助内容（今日日历、开盘异动、今日建议关注题材）连续排在新闻正文
        # 之前，与五个板块之间用一条分隔线断开：它们回答「今天要注意什么」，
        # 板块回答「发生了什么」，读者先扫前者再进正文。
        aux = "\n\n".join(
            block.rstrip() for block in (calendar, opening_block, nextday) if block.strip()
        )
        body = (
            header + premarket
            + (aux + "\n\n---\n\n" if aux else "")
            + toc + "".join(body_sections)
        )
        if language == "zh":
            body += "\n\n---\n\n*本报告由 Kenny’s Horizon 智能体基于市场信息自动生成，不构成任何投资建议。*\n"
        # 读者不需要看数据来源署名：题材成员已经内嵌在「今日建议关注题材」里，
        # 页脚再挂一行只会把正文挤长。
        text = normalize_language(body, language)
        # 五个板块平级。科技三组过去被折成「其他科技行业动态」下的三级标题，
        # 于是同一层目录里出现了两种颜色和字号（二级蓝、三级绿）；现在都走
        # 二级标题，板块名一致放大，板块之间靠样式拉开间距。
        return text

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

    async def _overnight_block(
        self, labels: dict, brief: Optional[dict] = None
    ) -> str:
        """Overnight US tape as backdrop, printed above the table of contents.

        Never a pick: across the five sessions to 2026-11-20, none of the
        thirty mapped themes reached the top 100 of lianban's heat board
        (median rank 575), so the block carries the move and the map and says
        in one line that it is not a recommendation.

        盘面与映射优先取早盘页：那张表是连板网按当天题材热度自己排的，还带
        「当日热度第N」——题材当天有没有进热度榜，是它比固定票单多出来的东西。
        新浪那份是固定票单按涨跌幅排的，只在早盘页取不到（周末、限流）时兜底，
        另外还负责给出美东收盘日期，早盘页不带这个日期。
        """
        # 亚太开盘与新浪互不依赖：一边断了，另一边照常。
        asia, sina = await asyncio.gather(
            fetch_asia_open(), fetch_overnight(), return_exceptions=True
        )
        if isinstance(asia, BaseException):
            logger.warning("Asia open tape failed: %s", asia)
            asia = None
        if isinstance(sina, BaseException):
            logger.warning("Overnight tape failed: %s", sina)
            sina = None

        indices = (brief or {}).get("indices") or []
        mapping = (brief or {}).get("mapping") or []
        close = (sina or {}).get("close_date") or ""
        if not indices and sina:
            indices = sina.get("indices") or []
        if not mapping and sina:
            mapping = [
                {
                    "us": row["ticker"],
                    "pct": row["pct"],
                    "themes": [{"name": name, "rank": 0} for name in row["themes"]],
                }
                for row in (sina.get("movers") or [])
            ]

        indices_line = ""
        if indices:
            tape = " ｜ ".join(
                f"{_escape_markdown(row['name'])} {_pct_value(row['pct']):+.2f}%"
                for row in indices
            )
            indices_line = f"{labels['premarket']}：{tape}"
        movers_line = ""
        if mapping:
            rows = []
            for row in mapping:
                label = f"{_escape_markdown(row['us'])} {_pct_value(row['pct']):+.2f}%"
                themes = "、".join(
                    f"{_escape_markdown(theme['name'])}·热度{theme['rank']}"
                    if theme.get("rank")
                    else _escape_markdown(theme["name"])
                    for theme in row["themes"]
                )
                rows.append(f"{label}（{themes}）" if themes else label)
            movers_line = f"{labels['overnight_map']}：" + " ｜ ".join(rows)

        # 顺序按时间走：隔夜美股 → 个股映射 → 美东收盘那句注 → 今早亚太开盘。
        # 亚太压到最后，因为它是这一屏里唯一「正在发生」的数据，紧挨着正文更好找。
        lines: list[str] = []
        if indices_line:
            lines.append(indices_line)
        if movers_line:
            lines.append(movers_line)

        if not lines and not asia:
            return ""
        note = labels["premarket_note"]
        if close:
            note = f"{labels['overnight_asof'].format(date=close)} · {note}"
        # 这句注解释的是上面那几行美股数据，所以只在有美股行的时候才挂。
        if lines:
            lines.append(f"*{note}*")
        # 09:30 这一跑，东京与首尔已交易一个半小时、台北半小时、香港刚开盘，
        # 所以这行给的是各市场今日的开盘价，是全天唯一当日的数据。
        if asia:
            tape = " ｜ ".join(
                f"{_escape_markdown(row['name'])} {row['last']:,.2f} {row['pct']:+.2f}%"
                for row in asia["rows"]
            )
            lines.append(f"{labels['asia_open']}：{tape}")
        return "\n\n".join(lines) + "\n\n---\n\n"

    async def _opening_block(
        self, labels: dict, date: str, snapshot: Optional[Dict] = None
    ) -> str:
        """开盘五分钟：封板、炸板，与上一交易日同口径对比。

        早报 09:35 触发，晚到开盘已经有形状，早到形状还是新闻。块是可选的：
        任何一个源不通就整块不印，日志留一行诊断，第二天能查是哪个源断的。

        ``snapshot`` 是 orchestrator 在流程开头就抓好的那一份。不自己再抓一次：
        炸板池会随盘中推移继续变长，晚抓的炸板数偏高。
        """
        if snapshot is not None:
            block = opening.render_block(snapshot, labels)
            return f"{block}\n" if block else ""
        compact = str(date or "").replace("-", "")
        if len(compact) != 8:
            return ""
        try:
            data = await opening.fetch_opening(compact)
        except Exception as exc:  # noqa: BLE001 - 少一块不该让早报失败
            logger.warning("Opening block unavailable: %s", exc)
            return ""
        block = opening.render_block(data, labels)
        return f"{block}\n" if block else ""

    def _calendar_block(self, labels: dict, brief: Optional[dict] = None) -> str:
        """Today's scheduled events, printed under the overnight tape.

        A calendar belongs in the morning: by 19:10 the limit-up board has
        already answered what happened today, and what the reader needs then is
        tomorrow's list, not today's. The calendar page lists the whole day —
        new listings, ex-rights dates and unlocks, with the amount or the plan
        attached — and keeps today's group through the session, so a 09:30 run
        sees the full set. The morning page's own list is not read at all: it
        carries unlocks only and no amounts.
        """
        brief = brief or {}
        if not brief:
            return ""
        events = (brief.get("events") or "").strip()
        calendar = brief.get("calendar") or []
        if not events and not calendar:
            return ""
        # Full-width brackets keep the macro line out of the Markdown escaper.
        if events:
            events = events.replace("(", "（").replace(")", "）")
        # 前缀辅助块，层级低于五个新闻板块：标题用三级，宏观另起一行。
        # 那天没有三星宏观时，标题也要留下：否则下面三类股票就是没头没尾的一串代码。
        lines: list[str] = [f"### {labels['calendar']}"]
        if events:
            lines.append(_escape_markdown(events))
        grouped: dict[str, list] = {}
        for row in calendar:
            grouped.setdefault(str(row.get("tag") or ""), []).append(row)
        # 当天能不能动手，比谁压力更大更要紧：新股申购要决定打不打，除权除息
        # 改的是持仓的价格基准，限售解禁只是往后的供给。
        order = {"新股申购": 0, "除权除息": 1, "限售解禁": 2}
        for tag in sorted(grouped, key=lambda name: (order.get(name, 9), name)):
            cells = []
            for row in grouped[tag]:
                cell = f"{_escape_markdown(row.get('name') or '')} {row.get('code') or ''}".strip()
                note = str(row.get("note") or "").strip()
                if note:
                    cell += f"（{_escape_markdown(note)}）"
                cells.append(cell)
            lines.append(f"**{_escape_markdown(tag)}**：{'、'.join(cells)}")
        return "\n\n".join(lines) + "\n\n"

    def _morning_news_entries(
        self, items: List[ContentItem], labels: dict, brief: Optional[dict] = None
    ) -> list[str]:
        """The morning headlines the digest does not already carry, as list rows.

        The 09:25 snapshot is newer than most of the digest's own sources, but
        it overlaps both with our items and with itself: the site listed
        「沪深北交易所降低融资保证金比例下限至80%」 next to 「沪深北交易所调整融资
        保证金比例」 as two separate lines. A headline is kept only when no
        selected item and no earlier kept headline says the same thing, compared
        on two-character grams so a reworded version still matches.
        """
        news = (brief or {}).get("news") or []
        if not news:
            return []
        existing = [getattr(item, "title", "") for item in items]
        kept: list[dict] = []
        for row in news:
            title = str(row.get("title") or "").strip()
            if not title:
                continue
            if any(_same_topic(title, other) for other in existing):
                continue
            if any(_same_topic(title, other["title"]) for other in kept):
                continue
            kept.append({**row, "title": title})
        if not kept:
            return []
        rows = []
        for row in kept:
            stamp = " ".join(
                part
                for part in (_escape_markdown(row.get("time") or ""), _escape_markdown(row.get("tone") or ""))
                if part
            )
            rows.append(f"- **{stamp}** {_escape_markdown(row['title'])}")
        return rows

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
            return self._generate_empty_summary(date, total_fetched, labels, language)

        if language == "zh":
            # 推送正文的第一屏就是这个标题：品牌一行、刊期一行。
            header = (
                "# Kenny's Horizon\n\n"
                f"# 新闻早报 {date} {_weekday_cn(date, long=True)} {DIGEST_CLOCK}\n\n"
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

    def _generate_empty_summary(
        self, date: str, total_fetched: int, labels: dict, language: str = "en"
    ) -> str:
        """Generate summary when no high-scoring items were found."""
        header = (
            f"# 新闻早报 {date} {_weekday_cn(date, long=True)} {DIGEST_CLOCK}"
            if language == "zh"
            else f"# {labels['header']} - {date}"
        )
        return (
            f"{header}\n\n"
            f"> {labels['empty_analyzed'].format(total=total_fetched)}\n\n"
            + labels["empty_body"]
        )
