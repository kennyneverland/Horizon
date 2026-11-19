#!/usr/bin/env python3
"""Post-close brief: the mainline matrix, the screened names, and a written read.

The morning digest answers "what happened". This one answers "where did the money
go today, and is that direction still alive tomorrow" — a question the matrix
alone cannot answer, because a count says a line was bought and nothing about
whether it was bought for the third day running.

Sources, all public:

  mainline.html   the 10-day matrix, the session's 情绪, and each line's driver
  opendata/       the site's own KPI block (limit-ups, seal rate, breadth)
  filter.html     the three screening templates' top five, with 60-day gain
  today.html      ｜主线强度 and 主力资金动向, which exist only as rendered DOM
  market.html     60 sessions of breadth, embedded as JSON
  MCP             lianban's own written review, published for agents

The written read is the model's, not this script's: it is handed the numbers and
lianban's own rotation rule (a line needs three consecutive days of leading to
count as a mainline; a one-day theme is next-day supply) and asked for a short
judgement. Nothing here is a trading instruction.

    python scripts/post_market.py --out-dir docs/post-market
    python scripts/post_market.py --no-llm --no-push    # numbers only
"""

from __future__ import annotations

import argparse
import gzip
import html as _html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mainline_matrix import build as build_matrix  # noqa: E402
from lianban_extra import collect_extra, mcp_review  # noqa: E402
from post_market_page import render_html  # noqa: E402

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)
BASE = "https://lianban.net"
MAINLINE_URL = f"{BASE}/mainline.html"
FILTER_URL = f"{BASE}/filter.html"
OPENDATA_URL = f"{BASE}/opendata/latest.json"

# Only these three panels are wanted; the page renders ten, each showing its
# top five for free. The map is data-p -> label as the page spells it.
FILTER_PANES = {"0": "主线强攻", "1": "优选蓄势", "3": "放量上攻"}

_TAG_RE = re.compile(r"<[^>]+>")
_PANE_RE = re.compile(
    r'<div class="ppane" data-p="(\d+)"[^>]*>(.*?)(?=<div class="ppane"|<div class="pfoot"|</section>|$)',
    re.S,
)
_TR_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_STK_RE = re.compile(r'data-stk="(\d{6})"\s+data-nm="([^"]+)"')
_BKT_RE = re.compile(r'<i class="bkt">([^<]+)</i>')
_MLT_RE = re.compile(r'<i class="mlt">([^<]+)</i>')
_PWHY_RE = re.compile(r'<div class="pwhy">(.*?)</div>', re.S)


def _text(raw: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(_TAG_RE.sub(" ", raw))).strip()


def fetch(url: str, referer: Optional[str] = None, timeout: float = 30.0) -> str:
    """Read a page as text. A gzip body is decompressed; other encodings pass through."""
    headers = {"User-Agent": UA, "Accept-Encoding": "gzip"}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return body.decode("utf-8", "replace")


def parse_filter(page: str) -> Dict[str, Dict[str, Any]]:
    """``{label: {why, total, rows}}`` for the three wanted panels.

    Each row carries the 60-day gain and the distance from the 60-day high,
    which is what turns a name into a position: +113% and 7.6% off the high is
    a different object from +15% and 4% off.
    """
    panes = {pid: body for pid, body in _PANE_RE.findall(page)}
    out: Dict[str, Dict[str, Any]] = {}
    for pid, label in FILTER_PANES.items():
        body = panes.get(pid)
        if not body:
            continue
        why = _PWHY_RE.search(body)
        rows = []
        for raw in _TR_RE.findall(body):
            stk = _STK_RE.search(raw)
            if not stk:
                continue
            cells = [_text(cell) for cell in _TD_RE.findall(raw)]
            if len(cells) < 8:
                continue
            bkt = _BKT_RE.search(raw)
            mlt = _MLT_RE.search(raw)
            rows.append(
                {
                    "rank": cells[0],
                    "code": stk.group(1),
                    "name": stk.group(2),
                    "sector": bkt.group(1).strip() if bkt else "",
                    "mark": mlt.group(1).strip() if mlt else "",
                    "s1m": cells[3],
                    "s3m": cells[4],
                    "s1y": cells[5],
                    "gain60": cells[6],
                    "from_high60": cells[7],
                    "ma20": cells[8] if len(cells) > 8 else "",
                    "vol_ud": cells[9] if len(cells) > 9 else "",
                }
            )
        # The page states how many names the template picked; the free view
        # shows five. Keeping the total keeps the page from implying five is all.
        total = None
        hit = re.search(r'data-tpl="' + re.escape(label) + r'"\s+data-total="(\d+)"', body)
        if hit:
            total = int(hit.group(1))
        out[label] = {
            "why": _text(why.group(1)) if why else "",
            "total": total,
            "rows": rows,
        }
    return out


def parse_kpi(doc: Dict[str, Any]) -> Dict[str, Any]:
    """The site's own KPI block, kept verbatim plus its attribution."""
    kpi = dict(doc.get("kpi") or {})
    kpi["_source"] = doc.get("source")
    kpi["_license"] = doc.get("license")
    kpi["_updated_at"] = doc.get("updated_at")
    kpi["_status"] = doc.get("status_label")
    return kpi


# The site's own rotation rule, quoted rather than paraphrased: the model is
# asked to apply lianban's standard, not this script's opinion of it.
ROTATION_RULE = (
    "连续 3 日以上保持涨停家数领先的才配叫主线；只上榜一天的是一日游题材，"
    "次日接力大概率是给别人抬轿。"
)

# The prompt is a judgement protocol, not a style guide. It exists to close the
# four ways a model turns this page into a transcript: it repeats the numbers
# (banned: a number may only appear as a comparison), it turns sequence into
# cause (banned), it hedges instead of taking a position (every section opens
# with a verdict), and it never commits to anything tomorrow's data could refute
# (two falsifiable checks are mandatory).
#
# The six headings are the product's, not the model's: a reader deciding what to
# do tomorrow wants the session read, the signals worth remembering, why the tape
# moved, what happens next, and which theme and names to keep watching — in that
# order. Letting the model choose its own headings produced six variations of
# "today's mainline".
SUMMARY_PROMPT = """你是 A 股收盘复盘的主笔，写的是盘后洞察，不是数据播报。

你会收到一份结构化 JSON：六个分类指数的涨跌、当日情绪与市场宽度、与前一日的变化、昨日涨停股今日表现、60 个交易日的宽度分布与今天所处的分位、产业线趋势、当日题材的驱动与龙头、主力资金流向、三张选股模板的候选、外盘、连板网自己的次日推演与复盘正文。

读者明天要据此做判断。所以六段各回答一个问题：先给结论，再给依据。

【口径，先读，读错会得出反向结论】
- indices 是六个分类指数当日涨跌。重点在它们的离散度：科创50 涨而创业板跌，说明资金在换方向，不是普跌。
- breadth 是当日宽度；breadth_history.today 是同一批指标，pct_rank_60d 是它在近 60 个交易日里的分位（0-100，越高表示该指标在窗口内越高）。方向不同：up_ratio、turnover、above_ma20 越高越好；new_low_63 与 stage4（处于下跌阶段的个股占比）越高越差。
- industry_lines[].delta_1d 是与前一交易日的差，delta_3d 是与前三个交易日均值的差。差值已经算好，不要再自己减。
- share_of_all_limit_up_pct 是集中度，不是强度。sector_strength_pct 是板块当日涨跌幅：涨停家数多而板块在跌，是个股突围，不是板块行情。
- relay 衡量接力还赚不赚钱，不衡量今天强不强。
- next_day_base_rate 是连板网用同情绪阶段的历史样本算出的次日频率，是基准率，不是预测。
- 题材级（today_themes）与产业线级（industry_lines）是两套口径，数量不可相加、不可互相换算。
- 涨停家数只说明资金今天在买什么，不能证明某条新闻驱动了它。
- theme_watch 是「每条当日题材 + 它的个股池」。detail_available=true 表示 members 就是连板网的逐只涨停明细（题材与个股同源）；false 表示该题材没有逐只明细，members 是按子题材标签关联来的候选，要按 sub 与题材的关系挑，不要全用。
- members[].board 是连板高度（3连板／3天2板／首板），sub 是连板网的子题材标签，source 标明来源：limit_up 当日涨停股、related 其他题材里子题材相关的涨停股、candidate 三张模板里的非涨停股、leader 题材龙头。
- gain60 与 from_high 只有出现在三张模板前 5 的个股才有；为 null 表示没有这个数，不是 0，也不要替它估。

【六段，各回答一个问题】
1. 盘面总结：今天是什么市（冰点／退潮／分歧／修复／主升，选一个并说明强度）。必须用"指数分化"和"宽度分位"各一条证据，并指出至少一处互相矛盾的信号——例如涨停高度集中在一条线，但成交额创 60 日新低、新低家数创新高。
2. 重点信号：给 3 个今天最值得记住的异常，每个都要带"相对于什么"（60 日分位、昨日值、或与其他指数/板块的背离）。能挂上已有历史基准的就挂——next_day_base_rate 的样本量与频率、pct_rank_60d 的分位；挂不上的只描述异常本身，不要替它编历史统计。这一段是替读者划重点，不要把所有指标都念一遍。
3. 盘面变动归因：钱从哪来、到哪去。用成交额相对 20 日均、各线 delta_1d、板块资金流判断今天是缩量撤退、存量搬家还是增量入场，并说清跌的是哪一类（小盘／双创／主板）。一条线涨停变多、另一条线变少，只能说明钱的分布变了；除非板块资金流也指向同一方向，否则直说"这一步无法证实"，不要写成资金迁移。
4. 趋势展望：先给出连板网的基准率（next_day_base_rate），再明确说同意还是不同意、为什么；然后给两个"如果……则……；否则……"的观察点，必须明天能从同一份数据里读到。
5. 重点关注题材：给 3 到 4 条，不是 1 到 2 条。每条用一句话说清为什么是它（连续天数、集中度、驱动、板块强弱里挑最有说服力的两点），再给一个明天能从同一份数据里读到、能证伪它的信号。题材只能从 theme_watch 取，不要自己造，也不要把 theme_watch 里的每一条都写进来；theme_watch 不足 3 条时就给 2 条，不要凑数，也不要把 industry_lines 的产业线当成当日题材。
6. 重点关注个股：这一段不写成大段文字，改由 watchlist 字段承载——每个重点题材配 2 到 4 只，全篇合计 6 到 12 只。每只写清它在题材里的角色（龙头／跟随／补涨）、连板高度，以及位置；有 gain60 与 from_high 的必须用上，没有的就写"无 60 日位置数据"，不要估。名字只能从该题材的 members 里取。

【硬性禁止】
- 禁止罗列数字。数字只能作为比较出现："从 3 家到 11 家"可以，单独一句"涨停 11 家"不可以。
- 禁止把先后关系写成因果关系。"英伟达宣布合作"与"芯片涨停"同时出现，不等于前者驱动了后者。
- 禁止买卖建议、目标价、仓位、点位、任何荐股语气。
- 禁止"综上所述""值得关注""后市可期""静待方向选择"这类空话。
- 禁止复述页面上已有的表格。
- 禁止编造样本量、命中率、历史概率与形态统计；除了 next_day_base_rate 与 pct_rank_60d，任何统计数字都不许出现在正文里。
- 输入里没有的东西就写"数据未提供"，不要用推测补齐，也不要把"没有这个消息"写成"没有催化"。

【输出格式】
只输出一个 JSON 对象，不要 markdown 代码块，不要任何解释文字：
{{"headline": "一句话定性，不超过 18 字，必须是判断而不是描述",
 "sections": [
  {{"h": "盘面总结", "p": "70-110 字"}},
  {{"h": "重点信号", "p": "70-110 字"}},
  {{"h": "盘面变动归因", "p": "70-110 字"}},
  {{"h": "趋势展望", "p": "70-110 字"}},
  {{"h": "重点关注题材", "p": "90-130 字，点出 3 到 4 条题材"}}
 ],
 "watchlist": [
  {{"theme": "题材名，必须与第 5 段点名的一致",
   "signal": "这个题材明天确认或证伪的信号，一句话，不超过 40 字",
   "stocks": [{{"name": "个股名，必须来自该题材 members",
              "tag": "连板高度 · 子题材，如 3连板 · 光刻机；不超过 14 字",
              "note": "它在题材里的角色与位置，不超过 36 字"}}]}}
 ],
 "dissent": "与连板网复盘的分歧，一句话；没有分歧就填空字符串，不要编"}}

watchlist 的硬性要求：条数与第 5 段题材数一致；每个题材 2 到 4 只（该题材 members 不足 2 只时给 1 只并在 note 里说明）；全篇合计 6 到 12 只；不要把所有 members 原样罗列，也不要在 members 之外造名字。"""


def _panel_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    return {
        x["label"].replace(" ", ""): x for x in ((payload.get("extra") or {}).get("panel") or [])
    }


def _num(raw: str) -> Optional[float]:
    hit = re.search(r"-?\d+(?:\.\d+)?", str(raw or ""))
    return float(hit.group(0)) if hit else None


def _trim(text: str, limit: int = 1500) -> str:
    """Cut at a sentence end, never mid-clause: a review that stops on 逗号
    reads as a bug, and the model may quote it as if it were the whole view."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind("。"), cut.rfind("\n"))
    return cut[: stop + 1] if stop > limit * 0.6 else cut


# 当日题材名是矩阵口径（粗，如「光刻机（胶）」），逐只明细里的子题材是连板网自己的
# 标签（细，如「光刻机」「光刻胶」）。两者字面不同，靠一张显式桥接表对上，不让模型猜。
_THEME_SUBS = {
    "光刻机（胶）": ("光刻机", "光刻胶", "光刻"),
    "国产芯片": ("先进封装", "半导体", "芯片", "集成电路", "存储", "封测"),
    "芯片": ("芯片", "半导体", "集成电路", "先进封装", "存储", "封测"),
    "云计算数据中心": ("算力", "数据中心", "IDC", "云计算", "液冷", "服务器"),
    "算力": ("算力", "数据中心", "IDC", "液冷", "服务器", "光模块", "CPO"),
    "机器人": ("机器人", "机器视觉", "减速器", "丝杠", "人形机器人"),
    "机器人概念": ("机器人", "机器视觉", "减速器", "丝杠", "人形机器人"),
    "家电": ("家电", "家用电器", "小家电", "智能家居", "白色家电"),
}


def _theme_watch(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """每条当日题材配一份可点名的个股池。

    The matrix gives a theme and a count; the site's detail panel gives the names
    behind that count, with board height and sub-theme. Without the panel a theme
    can only be described, never named — which is why the brief used to offer one
    or two stocks in total. This joins the two and marks, per theme, whether the
    list is the site's own detail (``detail_available``) or names pulled in by
    sub-theme label, so the model can tell a roster from a neighbourhood.

    ``gain60``/``from_high`` exist only for the fifteen names in the three free
    screening panels; the rest carry position as ``null`` rather than a guess.
    """
    day = (payload.get("matrix") or {}).get("day") or {}
    extra = payload.get("extra") or {}
    detail = extra.get("theme_members") or []
    cards = {x.get("theme"): x for x in detail if x.get("theme")}

    # 全站逐只明细池：给没有直连面板的题材按子题材标签找相关票
    pool: List[Dict[str, Any]] = []
    for card in detail:
        for m in card.get("members") or []:
            pool.append(dict(m, from_theme=card.get("theme") or ""))

    # 60 日位置只覆盖三张模板各前 5 只，其余留空
    pos: Dict[str, Dict[str, Any]] = {}
    for label, block in (payload.get("filter") or {}).items():
        for row in block.get("rows") or []:
            pos[row["name"].replace(" ", "")] = {
                "panel": label,
                "gain60": row.get("gain60"),
                "from_high": row.get("from_high60"),
                "sector": row.get("sector") or "",
            }

    out: List[Dict[str, Any]] = []
    for line in day.get("lines") or []:
        name = line.get("name") or ""
        card = cards.get(name) or {}
        subs = _THEME_SUBS.get(name, ())
        members: List[Dict[str, Any]] = []
        seen = set()

        def add(item: Dict[str, Any], key: str) -> None:
            if not key or key in seen:
                return
            seen.add(key)
            hit = pos.get(key) or {}
            item.setdefault("gain60", hit.get("gain60"))
            item.setdefault("from_high", hit.get("from_high"))
            item.setdefault("sector", hit.get("sector") or "")
            members.append(item)

        for m in card.get("members") or []:
            add(
                {
                    "name": m.get("name"),
                    "code": m.get("code"),
                    "board": m.get("board") or "",
                    "sub": m.get("sub") or "",
                    "source": "limit_up",
                },
                (m.get("name") or "").replace(" ", ""),
            )

        if not card.get("exact"):
            # 没有逐只明细：用子题材标签取相关涨停股，sub 保留给模型判断亲疏
            for m in pool:
                sub = m.get("sub") or ""
                if subs and any(x in sub for x in subs):
                    add(
                        {
                            "name": m.get("name"),
                            "code": m.get("code"),
                            "board": m.get("board") or "",
                            "sub": sub,
                            "source": "related",
                            "from_theme": m.get("from_theme") or "",
                        },
                        (m.get("name") or "").replace(" ", ""),
                    )
            # 三张模板里板块标签能对上的（未必涨停），作为位置可查的补充
            for key, hit in pos.items():
                sector = hit.get("sector") or ""
                if subs and any(x in sector or sector in x for x in subs if sector):
                    add(
                        {
                            "name": key,
                            "code": "",
                            "board": "",
                            "sub": sector,
                            "source": "candidate",
                        },
                        key,
                    )

        leader = card.get("leader") or {}
        if leader.get("name"):
            key = leader["name"].replace(" ", "")
            for m in members:
                if (m.get("name") or "").replace(" ", "") == key and not m.get("board"):
                    m["board"] = card.get("leader_board") or ""
            add(
                {
                    "name": leader["name"],
                    "code": leader.get("code") or "",
                    "board": card.get("leader_board") or "",
                    "sub": "",
                    "source": "leader",
                },
                leader["name"].replace(" ", ""),
            )

        out.append(
            {
                "theme": name,
                "limit_up": line.get("count"),
                "driver": line.get("driver") or "",
                "leader": " ".join(
                    x for x in [leader.get("name") or "", card.get("leader_board") or ""] if x
                ),
                "detail_available": bool(card.get("exact")),
                "members": members[:12],
            }
        )
    return out


def build_model_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    """The day's numbers arranged as relations, not as a list of facts.

    A flat set of counts gives a model nothing to do but repeat them. What makes
    a judgement possible is that every number arrives with something to be
    compared against: yesterday beside today, the three-day average beside both,
    a line's share of all limit-ups beside its sector's return, the day's breadth
    beside its concentration, and the site's own written read beside the numbers.

    Two taxonomies are kept apart on purpose. ``today_themes`` is the page's
    same-day breakdown (fine-grained, carries the driver and the leader);
    ``industry_lines`` is the ten-day matrix (coarse, carries the trend). Their
    counts do not add up to the same total, so they are never merged here and the
    prompt forbids the model from adding them.
    """
    kpi = payload.get("kpi") or {}
    matrix = payload.get("matrix") or {}
    day = matrix.get("day") or {}
    panel = _panel_map(payload)
    extra = payload.get("extra") or {}

    def value(label: str) -> Optional[str]:
        row = panel.get(label)
        return row["value"] if row else None

    def sub(label: str) -> str:
        row = panel.get(label)
        return row["sub"] if row else ""

    def delta(label: str) -> Optional[float]:
        hit = re.search(r"较前值\s*([+-]?[\d.]+)", sub(label))
        return float(hit.group(1)) if hit else None

    zb_sub = sub("炸板")
    zb_rate = re.search(r"率\s*([\d.]+)%", zb_sub)
    zb_prev = re.search(r"昨\s*([\d.]+)%", zb_sub)
    breadth_sub = sub("上涨/下跌")
    up_ratio = re.search(r"红盘\s*([\d.]+)%", breadth_sub)
    trin = re.search(r"TRIN\s*([\d.]+)", breadth_sub)
    yl = panel.get("昨涨停今表现") or {}
    yl_sub = yl.get("sub", "")
    yl_median = re.search(r"中位\s*(-?[\d.]+)%", yl_sub)
    yl_red = re.search(r"翻红\s*([\d.]+)%", yl_sub)
    margin = panel.get("融资余额11-18") or {}

    strength = {x["name"]: x for x in (extra.get("strength") or [])}

    lines = []
    for row in sorted(matrix.get("lines") or [], key=lambda x: (-x.get("today", 0), -x.get("prev", 0)))[:8]:
        # A line dark for two sessions is history, not a candidate for tomorrow.
        if row.get("today", 0) == 0 and row.get("prev", 0) == 0 and row.get("streak", 0) == 0:
            continue
        series = row.get("series") or {}
        recent = [series.get(d, 0) for d in (matrix.get("dates") or [])[:5]]
        item: Dict[str, Any] = {
            "line": row["line"],
            "limit_up": row["today"],
            "prev": row["prev"],
            "avg3_prior": row.get("base3"),
            "delta_1d": row["delta1"],
            "delta_3d": row["delta3"],
            "streak": row["streak"],
            "state": row["state"],
            "share_of_all_limit_up_pct": row.get("share"),
            "peak_10d": max(series.values()) if series else row["today"],
            "recent5": recent,
        }
        if row["line"] in strength:
            item["sector_strength_pct"] = strength[row["line"]]["pct"]
        lines.append(item)

    # The same-day breakdown, kept whole: this is the only place the driver text
    # and the named leader exist. It used to be joined onto the matrix rows by
    # name, and the names never match (光刻机（胶） vs 芯片), so both fields were
    # silently dropped and the model had no catalyst at all.
    themes = [
        {
            "theme": x.get("name"),
            "limit_up": x.get("count"),
            "driver": x.get("driver") or "",
            "leader": x.get("leader") or "",
        }
        for x in (day.get("lines") or [])
        if x.get("name")
    ]

    flows = {
        label: [{"name": r["name"], "amount": r["amount"], "pct": r["pct"]} for r in rows[:5]]
        for label, rows in (extra.get("flows") or {}).items()
    }
    screeners = {
        label: [
            {
                "name": r["name"],
                "sector": r["sector"],
                "gain60": r["gain60"],
                "from_high": r["from_high60"],
            }
            for r in block.get("rows", [])[:5]
        ]
        for label, block in (payload.get("filter") or {}).items()
    }
    overseas = {
        g["label"]: {x["name"]: x["pct"] for x in g["items"]}
        for g in (extra.get("overseas") or [])
    }
    third_party = _trim((payload.get("lianban") or {}).get("ai_review") or "")

    return {
        "date": kpi.get("date"),
        "session": {
            "phase": kpi.get("emotion_phase"),
            "degree": day.get("degree"),
            "settled": (payload.get("lianban") or {}).get("status") or kpi.get("_status"),
            "leader": day.get("leader"),
            "leader_badge": day.get("leader_badge"),
        },
        "breadth": {
            "limit_up": kpi.get("limit_up"),
            "limit_down": kpi.get("limit_down"),
            "lianban": kpi.get("lianban"),
            "max_board": kpi.get("max_board"),
            "seal_rate_pct": kpi.get("seal_rate_pct"),
            "zhaban": kpi.get("zhaban"),
            "zhaban_rate_pct": float(zb_rate.group(1)) if zb_rate else None,
            "zhaban_rate_prev_pct": float(zb_prev.group(1)) if zb_prev else None,
            "adv": kpi.get("adv"),
            "dec": kpi.get("dec"),
            "up_ratio_pct": float(up_ratio.group(1)) if up_ratio else None,
            "trin": float(trin.group(1)) if trin else None,
            "new_high_63": value("新高/新低63日"),
            "turnover": value("两市成交"),
            "margin_balance": margin.get("value"),
            "margin_change": margin.get("sub"),
        },
        "change_vs_prev": {
            "limit_up": delta("涨停"),
            "limit_down": delta("跌停"),
            "lianban": delta("连板"),
            "max_board": delta("最高板"),
            "seal_rate_pt": delta("封板率"),
            "zhaban_rate_pt": round(
                (float(zb_rate.group(1)) - float(zb_prev.group(1))), 1
            ) if zb_rate and zb_prev else None,
        },
        "relay": {
            "mean_pct": _num(yl.get("value")),
            "median_pct": float(yl_median.group(1)) if yl_median else None,
            "red_ratio_pct": float(yl_red.group(1)) if yl_red else None,
        },
        "indices": extra.get("indices") or [],
        "breadth_history": extra.get("breadth") or {},
        "industry_lines": lines,
        "today_themes": themes,
        "theme_watch": _theme_watch(payload),
        "money_flow": flows,
        "candidates": screeners,
        "overseas": overseas,
        "next_day_base_rate": extra.get("forecast") or {},
        "third_party_review": third_party,
    }


def _parse_read(text: str) -> Dict[str, Any]:
    """Accept the JSON contract; fall back to paragraphs so a bad reply still prints.

    The model is told to emit bare JSON. Models sometimes wrap it in a fence or
    add a sentence before it, so the fence and any leading prose are stripped
    before parsing rather than thrown away.
    """
    raw = (text or "").strip()
    if not raw:
        return {}
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start:
        try:
            doc = json.loads(raw[start : end + 1])
        except ValueError:
            doc = None
        if isinstance(doc, dict):
            sections = [
                {"h": str(s.get("h") or ""), "p": str(s.get("p") or "").strip()}
                for s in (doc.get("sections") or [])
                if isinstance(s, dict) and str(s.get("p") or "").strip()
            ]
            dissent = doc.get("dissent")
            if isinstance(dissent, dict):
                # Older replies used {agree, disagree}; keep reading them.
                text = str(dissent.get("disagree") or dissent.get("agree") or "").strip()
            else:
                text = str(dissent or "").strip()
            watch = []
            for item in doc.get("watchlist") or []:
                if not isinstance(item, dict):
                    continue
                theme = str(item.get("theme") or "").strip()
                stocks = []
                for st in item.get("stocks") or []:
                    if isinstance(st, dict):
                        name = str(st.get("name") or "").strip()
                        if name:
                            stocks.append(
                                {
                                    "name": name,
                                    "tag": str(st.get("tag") or "").strip(),
                                    "note": str(st.get("note") or "").strip(),
                                }
                            )
                    elif isinstance(st, str) and st.strip():
                        stocks.append({"name": st.strip(), "tag": "", "note": ""})
                if theme and stocks:
                    watch.append(
                        {
                            "theme": theme,
                            "signal": str(item.get("signal") or "").strip(),
                            "stocks": stocks,
                        }
                    )
            return {
                "headline": str(doc.get("headline") or "").strip(),
                "sections": sections,
                "watchlist": watch,
                "dissent": text,
            }
    paras = [p.strip() for p in re.split(r"\n+", raw) if p.strip()]
    return {"headline": "", "sections": [{"h": "", "p": p} for p in paras], "dissent": ""}


def llm_read(payload: Dict[str, Any], conf: Dict[str, Any], timeout: float = 150.0) -> Dict[str, Any]:
    """Ask the model for the written read. A failure costs the page only that block."""
    key_env = conf.get("api_key_env") or "DASHSCOPE_API_KEY"
    api_key = os.environ.get(key_env, "").strip()
    if not api_key:
        print(f"no {key_env}; skipping the written read", file=sys.stderr)
        return {}
    url = str(conf.get("base_url") or "").rstrip("/") + "/chat/completions"
    body = {
        "model": conf.get("model") or "qwen3.8-flash",
        "messages": [
            {"role": "system", "content": SUMMARY_PROMPT.format(rule=ROTATION_RULE)},
            {"role": "user", "content": json.dumps(build_model_input(payload), ensure_ascii=False)},
        ],
        "temperature": 0.4,
        "max_tokens": 2600,
        "response_format": {"type": "json_object"},
    }
    def _post(payload_body: Dict[str, Any]) -> Dict[str, Any]:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload_body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8", "replace"))

    try:
        try:
            doc = _post(body)
        except urllib.error.HTTPError as exc:
            # Not every endpoint accepts response_format; the prompt already
            # demands bare JSON, so dropping the constraint costs only insurance.
            if exc.code != 400:
                raise
            print("response_format rejected; retrying without it", file=sys.stderr)
            body.pop("response_format", None)
            doc = _post(body)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"written read failed: {exc}", file=sys.stderr)
        return {}
    try:
        text = doc["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("written read: unexpected response shape", file=sys.stderr)
        return {}
    return _parse_read(str(text or ""))


def push_webhook(url: str, title: str, desp: str, timeout: float = 30.0) -> bool:
    """POST the Server酱-shaped body the daily digest already uses."""
    body = json.dumps({"title": title, "desp": desp}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as exc:
        print(f"webhook failed: {exc}", file=sys.stderr)
        return False
    print(f"webhook response: {raw[:200]}")
    try:
        doc = json.loads(raw)
    except ValueError:
        return True
    code = doc.get("code", doc.get("errno", 0))
    return code in (0, "0", None)


def _load_ai_conf(path: Path) -> Dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc.get("ai") or {}


def collect(no_browser: bool = False) -> Dict[str, Any]:
    """Fetch the public sources and parse them into one payload.

    Each source is allowed to fail on its own: a page that will not load costs
    its section, not the whole brief. The browser half is the only one that
    needs a dependency, so it is also the only one that can be switched off.
    """
    payload: Dict[str, Any] = {
        "matrix": {},
        "kpi": {},
        "filter": {},
        "extra": {},
        "lianban": {},
        "errors": [],
    }
    try:
        payload["matrix"] = build_matrix(fetch(MAINLINE_URL))
    except Exception as exc:  # noqa: BLE001 - reported, then the page degrades
        payload["errors"].append(f"mainline: {exc}")
    try:
        payload["kpi"] = parse_kpi(json.loads(fetch(OPENDATA_URL)))
    except Exception as exc:  # noqa: BLE001
        payload["errors"].append(f"opendata: {exc}")
    try:
        payload["filter"] = parse_filter(fetch(FILTER_URL, referer=MAINLINE_URL))
    except Exception as exc:  # noqa: BLE001
        payload["errors"].append(f"filter: {exc}")
    if not no_browser:
        try:
            payload["extra"] = collect_extra()
        except Exception as exc:  # noqa: BLE001
            payload["errors"].append(f"browser: {exc}")
    return payload


def _short_read(read: Dict[str, Any], limit: int = 220) -> str:
    """The push card's two lines: the call first, then the first section that defends it."""
    if not read:
        return ""
    head = read.get("headline") or ""
    first = next((s.get("p") for s in read.get("sections") or [] if s.get("p")), "")
    flat = " ".join((head + "。" + first).split()) if head else " ".join(first.split())
    return flat[:limit] + ("…" if len(flat) > limit else "")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Post-close brief: matrix, screens, written read")
    parser.add_argument("--out-dir", default="docs/post-market")
    parser.add_argument("--base-url", default="https://kennyneverland.github.io/Horizon/post-market")
    parser.add_argument("--config", default="data/config.github.json")
    parser.add_argument("--date", help="override the date in the filename (debug)")
    parser.add_argument("--no-llm", action="store_true", help="skip the written read")
    parser.add_argument("--no-browser", action="store_true", help="skip the rendered blocks")
    parser.add_argument("--no-mcp", action="store_true", help="skip lianban's own review")
    parser.add_argument("--no-push", action="store_true", help="write the page, do not push")
    parser.add_argument("--dump-model-input", action="store_true", help="print the model payload and exit")
    args = parser.parse_args(argv)

    payload = collect(no_browser=args.no_browser)
    matrix = payload["matrix"]
    kpi = payload["kpi"]
    date = args.date or kpi.get("date") or (matrix.get("dates") or [""])[0]
    if not date:
        print("no date from any source; aborting", file=sys.stderr)
        return 2
    payload["date"] = date

    if not args.no_mcp:
        try:
            payload["lianban"] = mcp_review(date)
        except Exception as exc:  # noqa: BLE001
            payload["errors"].append(f"mcp: {exc}")
    for err in payload["errors"]:
        print(f"source failed: {err}", file=sys.stderr)

    if args.dump_model_input:
        print(json.dumps(build_model_input(payload), ensure_ascii=False, indent=2))
        return 0

    summary: Dict[str, Any] = {}
    if not args.no_llm:
        summary = llm_read(payload, _load_ai_conf(Path(args.config)))

    page_url = f"{args.base_url.rstrip('/')}/{date}.html"
    html = render_html(payload, summary, page_url)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    day_path = out_dir / f"{date}.html"
    day_path.write_text(html, encoding="utf-8")
    # index.html is the same bytes rather than a redirect: WeChat opens the
    # link in a webview where an extra hop is one more thing to fail.
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"page: {day_path} ({len(html)} B)")

    if args.no_push:
        print("push skipped (--no-push)")
        return 0

    hook = os.environ.get("HORIZON_WEBHOOK_URL", "").strip()
    if not hook:
        print("HORIZON_WEBHOOK_URL not set; push skipped", file=sys.stderr)
        return 0
    day = matrix.get("day") or {}
    lead = " ".join(
        x for x in [day.get("leader") or "", day.get("leader_badge") or ""] if x
    )
    top = [l for l in matrix.get("lines") or [] if l.get("today", 0) > 0][:3]
    headline = "、".join(f"{l['line']}{l['today']}" for l in top) or "无涨停线"
    title = f"Horizon 盘后洞察 {date[5:]} {kpi.get('emotion_phase') or ''} {headline}".strip()
    desp = "\n\n".join(
        part
        for part in [
            f"**{kpi.get('emotion_phase') or ''}** 涨停{kpi.get('limit_up')} 跌停{kpi.get('limit_down')}"
            f" 封板率{kpi.get('seal_rate_pct')}%"
            + (f"｜总龙头 {lead}" if lead else ""),
            _short_read(summary) if summary else "",
            f"[查看盘后总结 →]({page_url})",
        ]
        if part
    )
    ok = push_webhook(hook, title, desp)
    print(f"push: {'ok' if ok else 'failed'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
