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
  lhb.html        龙虎榜 net-buy top fifteen, with reason and buy-side top seat
  zaopan.html     监管异动（异常波动公告提醒），只作风险展示，不进候选
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
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
# 东财客户端住在 digest 包里（早报的日历块也用它），从脚本目录再上一层才够得着。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mainline_matrix import build as build_matrix  # noqa: E402
from src.processing import eastmoney  # noqa: E402
from lianban_extra import (  # noqa: E402
    collect_extra,
    mcp_review,
    parse_signals,
    render_day,
)
from post_market_page import (  # noqa: E402
    _FOCUS_DESC,
    _filter_pos,
    _lhb_map,
    _loose,
    _theme_meta,
    render_html,
)
from stock_concepts import _is_weak as _concept_is_weak  # noqa: E402
from stock_concepts import _norm as _theme_key  # noqa: E402
from stock_concepts import load_index as load_concept_index  # noqa: E402
from stock_concepts import fetch_stock as concept_fetch  # noqa: E402
from stock_concepts import load_theme_names, lookup as concept_lookup  # noqa: E402
from stock_concepts import write_index as write_concept_index  # noqa: E402

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)
BASE = "https://lianban.net"
MAINLINE_URL = f"{BASE}/mainline.html"
FILTER_URL = f"{BASE}/filter.html"
OPENDATA_URL = f"{BASE}/opendata/latest.json"
LHB_URL = f"{BASE}/lhb.html"
# 监管异动只出现在晚报：早盘页 09:25 定版，08:00 的早报看到的还是半成品，
# 19:10 再取才是当天完整的一份。
ZAOPAN_URL = f"{BASE}/zaopan.html"

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
_LHB_ITEM_RE = re.compile(r'<div class="lr1">(.*?)</div></div>', re.S)
_LHB_STK_RE = re.compile(r'data-stk="(\d{6})"\s+data-nm="([^"]+)"')
_LHB_CHG_RE = re.compile(r'<span class="cg mono[^"]*">([^<]+)</span>')
_LHB_NET_RE = re.compile(r'<span class="net mono[^"]*">([^<]+)</span>')
_LHB_RS_RE = re.compile(r'<span class="rs">([^<]*)</span>')
# 早盘页把当天快照日期印在标题旁，取它来挡住跨日误印。
_ZAOPAN_SNAPSHOT_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\s*早盘情报快照")
_ALERT_RE = re.compile(
    r'<span class="pmk warn" data-stk="(\d{6})" data-nm="([^"]+)">[^<]*<i>([^<]+)</i></span>'
)


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


def parse_lhb(page: str) -> Dict[str, Any]:
    """龙虎榜：净买额前 15 只，带净额、上榜原因与买一席位。

    The board answers a question the theme panels cannot: who was on the other
    side of today's move. A name can be limit-up with a net *outflow* — the
    buying seats were retail and the selling seat was a known 游资 — and that is
    a different object from a limit-up with a net inflow. Only the top fifteen by
    net amount are server-rendered; the full list loads on demand and is not
    fetched here, because fifteen is already more than the brief can use.
    """
    head = re.search(r'<div class="shh">([^<]+)</div>', page)
    items: List[Dict[str, Any]] = []
    for block in _LHB_ITEM_RE.findall(page):
        stk = _LHB_STK_RE.search(block)
        if not stk:
            continue
        chg = _LHB_CHG_RE.search(block)
        net = _LHB_NET_RE.search(block)
        rs = _LHB_RS_RE.search(block)
        reason = (rs.group(1) if rs else "").strip()
        seat = ""
        # The page glues the buy-side top seat onto the reason with a " · "
        if " · " in reason:
            reason, seat = reason.rsplit(" · ", 1)
        items.append(
            {
                "name": stk.group(2),
                "code": stk.group(1),
                "chg": chg.group(1).strip() if chg else "",
                "net": net.group(1).strip() if net else "",
                "reason": reason.strip(),
                "seat": seat.strip(),
            }
        )
    return {"header": head.group(1).strip() if head else "", "items": items}


def parse_alerts(page: str) -> Dict[str, Any]:
    """监管异动：交易所异常波动公告提醒，按今年连板数排序。

    This is a risk roster, not a candidate pool. Every name is on it because the
    exchange flagged an abnormal move, which is the opposite of a reason to buy
    tomorrow; the list is parsed and printed as-is and never enters
    ``theme_watch``, ``candidates`` or the model's input, so it cannot leak into
    the 活跃 bucket. Sorting is the site's: the names with the most limit-ups
    this year come first, which is also the order a reader wants them in.
    """
    stamp = _ZAOPAN_SNAPSHOT_RE.search(page)
    items: List[Dict[str, Any]] = []
    for code, name, note in _ALERT_RE.findall(page):
        kind, _, boards = _text(note).partition("·")
        hit = re.search(r"(\d+)", boards)
        items.append(
            {
                "code": code,
                "name": _text(name),
                "kind": kind.strip(),
                "boards": int(hit.group(1)) if hit else None,
            }
        )
    return {"snapshot": stamp.group(1) if stamp else "", "items": items}


def _payload_codes(payload: Dict[str, Any]) -> List[str]:
    """Every ticker the brief can name, collected once.

    The dragon-tiger board, the three screening panels and the theme watch pool
    are the three places a name can arrive from. Anything not in this list is
    never shown, so this is also the exact set worth looking up.
    """
    codes: List[str] = []

    def add(code: Any) -> None:
        text = str(code or "").strip()
        if len(text) == 6 and text.isdigit() and text not in codes:
            codes.append(text)

    for item in (payload.get("lhb") or {}).get("items") or []:
        add(item.get("code"))
    for block in (payload.get("filter") or {}).values():
        for row in block.get("rows") or []:
            add(row.get("code"))
    for card in (payload.get("extra") or {}).get("theme_members") or []:
        for member in card.get("members") or []:
            add(member.get("code"))
    # 涨停池里的票大多不在面板和龙虎榜上，但它们是题材归位唯一的逐只来源，
    # 所以也要进概念查询的范围。
    for row in payload.get("em_zt") or []:
        add(row.get("c"))
    return codes


def attach_concepts(
    payload: Dict[str, Any], fetch_missing: bool = True, save: bool = False
) -> Dict[str, Dict[str, Any]]:
    """Ticker -> the themes it belongs to, read from the shipped index.

    The board and the panels label a stock with one sector, and only for the
    five names each panel shows for free; a dragon-tiger name outside those five
    had no attribution at all. The index answers the same question for every
    ticker it covers, and carries the company's own disclosure of the business
    link, which a sector label never does.

    This is a lookup, not a guess: a ticker neither the index nor the live fetch
    can resolve comes back absent, and the caller renders it as unattributed
    rather than borrowing a neighbour's theme.

    The index is a cache, not the source of truth. A ticker it does not carry is
    fetched from the same page the index was built from — the brief covers 30-40
    names a day and the site tolerates one request every ~2.3s, so a cold day
    costs about a minute and a warm one costs nothing. ``save`` writes the
    fetched pages back so the next run starts warmer.
    """
    codes = _payload_codes(payload)
    if not codes:
        return {}
    index = load_concept_index()
    names = load_theme_names()
    stocks = index.setdefault("stocks", {})
    out: Dict[str, Dict[str, Any]] = {}
    fetched = 0
    for code in codes:
        hit = concept_lookup(code, "", index, names)
        if hit.get("source") == "missing" and fetch_missing:
            name, concepts = concept_fetch(code)
            if concepts:
                stocks[code] = [name, concepts]
                fetched += 1
                hit = concept_lookup(code, "", index, names)
        if hit.get("source") != "missing":
            out[code] = hit
    if fetched:
        print(f"concepts: {fetched}/{len(codes)} fetched live, {len(stocks)} in index")
        if save:
            try:
                write_concept_index(index)
                print("concepts: index written back")
            except Exception as exc:  # noqa: BLE001 - a read-only checkout must not fail the run
                print(f"concepts: index not written ({exc})")
    return out


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
# The four headings are the product's, not the model's: a reader deciding what to
# do tomorrow wants the session read, the signals worth remembering, why the tape
# moved, and what happens next. The names to watch are a separate structure —
# three buckets, because "already running", "not yet moving" and "moved today"
# are three different bets, and a flat list makes the reader sort them himself.
SUMMARY_PROMPT = """你是 A 股收盘复盘的主笔，写的是盘后洞察，不是数据播报。

你会收到一份结构化 JSON：六个分类指数的涨跌、当日情绪与市场宽度、与前一日的变化、昨日涨停股今日表现、60 个交易日的宽度分布与今天所处的分位、产业线趋势、当日题材的驱动与龙头、主力资金流向、三张选股模板的候选、龙虎榜、外盘、连板网自己的次日推演与复盘正文。

读者明天要据此做判断。所以四段各回答一个问题：先给结论，再给依据。

【口径，先读，读错会得出反向结论】
- indices 是六个分类指数当日涨跌。重点在它们的离散度：科创50 涨而创业板跌，说明资金在换方向，不是普跌。
- breadth 是当日宽度；breadth_history.today 是同一批指标，pct_rank_60d 是它在近 60 个交易日里的分位（0-100，越高表示该指标在窗口内越高）。方向不同：up_ratio、turnover、above_ma20 越高越好；new_low_63 与 stage4（处于下跌阶段的个股占比）越高越差。
- industry_lines[].delta_1d 是与前一交易日的差，delta_3d 是与前三个交易日均值的差。差值已经算好，不要再自己减。
- share_of_all_limit_up_pct 是集中度，不是强度。sector_strength_pct 是板块当日涨跌幅：涨停家数多而板块在跌，是个股突围，不是板块行情。
- relay 衡量接力还赚不赚钱，不衡量今天强不强。
- next_day_base_rate 是连板网用同情绪阶段的历史样本算出的次日频率，是基准率，不是预测。
- third_party_review 是连板网自己写的复盘正文，已核对为当日定版，写的是它的判断而不是数据。它和你的读法不同时，分歧点就在那里；它为空表示今天没有可取的第二意见，dissent 也必须为空。
- 题材级（today_themes）与产业线级（industry_lines）是两套口径，数量不可相加、不可互相换算。today_themes 的条目若带 fallback=industry_lines，表示页面当日题材块尚未发布，这里给的是当日产业线（与 industry_lines 是同一批数字的另一种视角），不要重复计数，也不要为它们编造驱动逻辑或龙头。
- 涨停家数只说明资金今天在买什么，不能证明某条新闻驱动了它。
- theme_watch 是「每条当日题材 + 它的个股池」。detail_available=true 表示 members 就是连板网的逐只涨停明细（题材与个股同源）；false 表示该题材没有逐只明细，members 是按子题材标签关联来的候选，要按 sub 与题材的关系挑，不要全用。
- members[].board 是连板高度（3连板／3天2板／首板），sub 是连板网的子题材标签，source 标明来源：limit_up 当日涨停股、panel 三张免费面板里归位到该题材的票（未必涨停，是「主线里结构就绪、还没走」的那类）、eastmoney 当日涨停股（连板网题材明细改版后不再提供逐只名单，这一路来自东财涨停池，按同花顺概念／行业板块归位）、related 其他题材里子题材相关的涨停股、candidate 三张模板里的非涨停股、leader 题材龙头。eastmoney 这一路的 sub 是它的概念或行业标签，不是连板网的子题材，亲疏自己判断。members 的排列顺序就是取用优先级：panel（面板里归位到该题材、通常还没涨停）→ eastmoney（当日涨停池）→ related → candidate → leader。明日关注优先用排在前面的：要的是「结构就绪、还没走」，不是已经封板的结果。board 有值说明它今天已经涨停，3 连板及以上必须在 signal 或 tag 里写明位置偏高，不许当成低位机会；board 为空才是没封板的。
- gain60 与 from_high 只有出现在三张模板前 5 的个股才有；为 null 表示没有这个数，不是 0，也不要替它估。
- lhb 是龙虎榜净买额前 15，net 是买入前五合计减卖出前五合计，正=席位端净流入；上榜原因只说明它为什么被披露（涨幅／跌幅／换手／振幅偏离），不说明题材；seat 是买一席位。席位数据只反映过去一日的行为，不预示次日方向。sector 是它在三张面板里的板块标签，theme 是它在当日题材明细里所属的题材。themes 是本地题材索引倒查出的归属——索引取自同花顺 F10 概念页，已与 lianban 题材库做归一化精确对齐，覆盖范围比面板宽得多，归位优先用它；concepts 是同花顺原始概念名，why 是公司自己披露的业务关联原文，可以用来交代它凭什么算这个题材，但只能引用原文意思，不要替公司补话。today_themes 是把 themes 按名称归一化对回当日题材口径的结果——只做去括号同名匹配，对上的可以直接归位；对不上不代表不属于，例如「光刻胶」对不上「光刻机（胶）」但它就是那条线，这种情况你自己判断。四者都空才表示归属未知。
- candidates 按模板名分组：candidates[模板名] = {{why, total, rows}}。rows 是当日入选的前 5 只（name／sector／mainline／gain60／from_high／above_ma20／vol_ud／themes）。sector 是这只票的题材归属标签，直接用，不要改写成别的名字；themes 是同一套索引倒查出的题材名，sector 为空或只是一个宽泛标签（次新股、高股息、国企改革这类）时用它；mainline 为「🔥主线」表示它本身就在当日主线板块内；above_ma20 是它站上 20 日线的幅度，vol_ud 是涨跌量比。total 是这只模板当天一共选了多少只（免费只显示前 5），why 是连板网自己写的模板口径，照它理解，不要改写。三张模板的分工：主线强攻＝主线资金聚集处的最强个体，通常已经在涨；优选蓄势＝收敛度质量口径过滤后的蓄势股，未涨停但结构就绪，是明日候选的主要来源；放量上攻＝涨时放量、跌时缩量的吸筹形态。

- 判断主线用连板网自己的口径，不另立标准：{rule}（这条是连板网的原文口径，引用它来判断，不要换成更宽的「连续两天」或更严的「五天」。）

【四段，各回答一个问题】
1. 盘面总结：今天是什么市（冰点／退潮／分歧／修复／主升，选一个并说明强度）。必须用"指数分化"和"宽度分位"各一条证据，并指出至少一处互相矛盾的信号——例如涨停高度集中在一条线，但成交额创 60 日新低、新低家数创新高。
2. 重点信号：给 3 个今天最值得记住的异常，每个都要带"相对于什么"（60 日分位、昨日值、或与其他指数/板块的背离）。能挂上已有历史基准的就挂——next_day_base_rate 的样本量与频率、pct_rank_60d 的分位；挂不上的只描述异常本身，不要替它编历史统计。这一段是替读者划重点，不要把所有指标都念一遍。
3. 盘面变动归因：钱从哪来、到哪去。用成交额相对 20 日均、各线 delta_1d、板块资金流判断今天是缩量撤退、存量搬家还是增量入场，并说清跌的是哪一类（小盘／双创／主板）。一条线涨停变多、另一条线变少，只能说明钱的分布变了；除非板块资金流也指向同一方向，否则直说"这一步无法证实"，不要写成资金迁移。
4. 趋势展望：先给出连板网的基准率（next_day_base_rate），再明确说同意还是不同意、为什么；然后给两个"如果……则……；否则……"的观察点，必须明天能从同一份数据里读到。

【明日关注，分三类】
第 5、6 段取消，改由结构化字段 focus 承载：三类题材，每类下面挂该题材的重点个股。三类是读者明天开盘的三种看法，边界必须守住，同一只票、同一条题材只许出现在一类里。

- 蓄势：票池就是 candidates 的「优选蓄势」前 5 只（total 是当日共选了多少只，你只看到前 5）。这一类的题材取这些票的 sector，sector 为空或只是宽泛标签时用 themes——它们本来就不在当日主线上，题材就是"它自己所属的板块"，不要硬套当日题材名；当这个题材名与某条当日题材或产业线明显同义时（例如「厨房小家电」与「家电」、「华为概念」与「云计算数据中心」），写成"sector（对应当日题材 X）"。个股只能从这 5 只里取，不许拿别的面板补。sector 相同的票合成一条题材，给 2 到 3 条，每条 1 到 3 只。优选蓄势当日为空时，这一类给空数组，不要凑。
- 主线：题材从 theme_watch 取，且必须是已经有连续性的线——streak、连续天数、share_of_all_limit_up_pct 里能看出它不是第一天；个股只能从该题材的 members 里取，members 为空表示当日没有逐只明细，这条题材就只写 signal、stocks 给空数组，不许从面板、别的题材或龙虎榜凑一只填进去。给 2 到 3 条题材，每条 0 到 3 只。
- 活跃：题材也从 theme_watch 取，但取的是今天刚动、持续性还没验证的线——新上榜、首板集中、streak 只有 1、或板块在跌而个股突围。个股有三个来源：该题材的 members；「放量上攻」「主线强攻」里 sector 对得上的票；以及龙虎榜 lhb 里的个股。lhb 这一路要挑净额为正、且上榜原因指向涨幅偏离／换手／振幅的——那是「今天刚动」最直接的证据；净额为负的是资金在出，只能当风险提示，不要当候选。龙虎榜的票，只要 theme、themes 或 sector 能对上某条活跃题材就放进去，tag 里标明「龙虎榜」。三者都空、对不上任何题材的，最多允许另起一条题材名为「龙虎榜净买入」——只收净额为正、涨跌幅为正的票，2 只以内，signal 里必须写明这几只没有题材归属、只是资金面信号；这条题材可以没有，但一旦有，就不许往里塞有归属的票。除此之外不许为个股单独造题材。给 2 到 3 条题材，每条 2 到 3 只。监管异动（异常波动公告提醒）不在活跃候选之内：那份名单只说明交易所已经盯上它，不是「今天刚动」的证据，不要拿它补票，也不要在正文里把这些票写成活跃或明日方向。

三条纪律：
1. 三类不重复。蓄势与另两类的边界是"还没涨 vs 已经在动"；主线与活跃的边界是"有连续性 vs 只有一天"。同一只票出现在两类里，等于这一块没做。
2. 数字由页面回填。note 里不要复述 gain60、from_high、above_ma20、vol_ud，也不要写涨停家数或龙虎榜净额——组头和标签会显示。note 只写它在题材里的角色和明天为什么值得看，不超过 36 字。
3. 名字不许造。蓄势只能来自优选蓄势前 5；主线只能来自对应题材的 members；活跃只能来自对应题材的 members、两张面板的 rows，或 lhb 里 theme／themes／sector 对得上的票；监管异动名单不在此列。

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
  {{"h": "趋势展望", "p": "70-110 字"}}
 ],
 "focus": {{
  "蓄势": [
   {{"theme": "该票在面板里的 sector 题材标签；与当日题材同义时写成 sector（对应当日题材 X）",
    "signal": "这个题材明天确认或证伪的信号，一句话，不超过 40 字",
    "stocks": [{{"name": "个股名，只能来自优选蓄势前 5",
               "tag": "它在题材里的角色，如 收敛最紧的一档；不超过 14 字",
               "note": "位置与明天为什么值得看；不超过 36 字"}}]}}
  ],
  "主线": [
   {{"theme": "题材名，必须与 theme_watch 里的一致",
    "signal": "这个题材明天确认或证伪的信号，一句话，不超过 40 字",
    "stocks": [{{"name": "个股名，必须来自该题材 members",
               "tag": "连板高度 · 子题材，如 3连板 · 光刻机；不超过 14 字",
               "note": "它在题材里的角色与位置，不超过 36 字"}}]}}
  ],
  "活跃": [
   {{"theme": "题材名，必须与 theme_watch 里的一致；龙虎榜兜底那条写 龙虎榜净买入",
    "signal": "这个题材明天确认或证伪的信号，一句话，不超过 40 字",
    "stocks": [{{"name": "个股名，来自该题材 members、两张面板的 rows，或 lhb 里 theme／sector 对得上的票",
               "tag": "连板高度 · 子题材；来自龙虎榜的写 龙虎榜；不超过 14 字",
               "note": "它在题材里的角色与位置，不超过 36 字"}}]}}
  ]
 }},
 "dissent": "针对 third_party_review 的表态，一句话：判断不同就写不同在哪、依据哪条数据；完全一致就写「与连板网复盘判断一致」；third_party_review 为空则留空字符串。不许复述它的内容，也不许编造它没说过的观点"}}

focus 的硬性要求：三类各 2 到 3 条题材（蓄势可为空），每条题材 1 到 3 只个股，全篇合计不超过 20 只；题材名不许自造；同一只票只出现在一类里；三类都不要把 members 原样罗列。"""


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
    "光刻机（胶）": ("光刻机", "光刻胶", "光刻", "电子化学"),
    "国产芯片": ("先进封装", "半导体", "芯片", "集成电路", "存储", "封测"),
    "芯片": ("芯片", "半导体", "集成电路", "先进封装", "存储", "封测", "电子化学"),
    "PCB": ("PCB", "印制电路", "覆铜板", "线路板", "元件"),
    "PCB概念": ("PCB", "印制电路", "覆铜板", "线路板", "元件"),
    "农业": ("农业", "种植", "饲料", "农产品", "渔业", "农化", "养殖", "种业", "食品"),
    "云计算数据中心": ("算力", "数据中心", "IDC", "云计算", "液冷", "服务器", "IT服务"),
    "算力": ("算力", "数据中心", "IDC", "液冷", "服务器", "光模块", "CPO", "IT服务"),
    "机器人": ("机器人", "机器视觉", "减速器", "丝杠", "人形机器人", "通用设备"),
    "机器人概念": ("机器人", "机器视觉", "减速器", "丝杠", "人形机器人", "通用设备"),
    "AI应用(AI视频)": ("人工智能", "AIGC", "数字媒体", "传媒", "视频", "软件", "广告营销", "出版"),
    "AI应用": ("人工智能", "AIGC", "数字媒体", "传媒", "视频", "软件", "广告营销", "出版"),
    "家电": ("家电", "家用电器", "小家电", "智能家居", "白色家电"),
}


def _board_label(lbc: Any) -> str:
    """东财 ``lbc`` 的连板数 → 页面上的说法。1 板是首板，0 空着。"""
    try:
        n = int(lbc or 0)
    except (TypeError, ValueError):
        return ""
    if n <= 0:
        return ""
    return "首板" if n == 1 else f"{n}连板"


def _board_num(label: Any) -> int:
    """``3连板`` → 3，``首板`` → 1，其余 0。只用来排序，不进正文。"""
    text = str(label or "")
    if text == "首板":
        return 1
    m = re.match(r"(\d+)\s*连板", text)
    return int(m.group(1)) if m else 0


def _em_members(
    payload: Dict[str, Any], themes: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """当日涨停股按题材归位，来源是东财涨停池加同花顺概念。

    lianban 的题材明细面板改版后不再出现在 ``days/<date>.html`` 上——11-20 整页
    渲染完 ``.zxc``／``#zxm`` 各出现 0 次，``parse_themes`` 只能返回空，兜底池
    （也是从 detail 建的）跟着一起空。东财涨停池是唯一还活着的逐只来源：每只票
    带行业板块 ``hybk`` 与连板数 ``lbc``，本地概念索引再补同花顺概念。

    标签与 lianban 的题材名不是同一套口径（盛剑科技的行业是环保设备，真视通是
    IT服务Ⅱ），所以只按 ``_THEME_SUBS`` 做子串归位，命不中就留空，不猜。命中的
    票带 ``source=eastmoney``，让模型知道这是当日真实涨停，不是板块候选。
    """
    rows = payload.get("em_zt") or []
    concepts = payload.get("concepts") or {}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        code = row.get("c") or ""
        name = row.get("n") or ""
        if not name:
            continue
        hit = concepts.get(code) or {}
        raw = hit.get("concepts") or []
        # 蹭热点的标签（次新股、国企改革、专精特新……）不参与归位：它们不说明
        # 这家公司做什么，只说明它被谁持有过。行业板块同理，只在完全没有概念
        # 可用时兜底，否则盛剑科技会按「环保设备」被挂到环保上去。
        labels = [c.get("name") or "" for c in raw if c.get("name") and not _concept_is_weak(c.get("name") or "")]
        fallback = "" if labels else (row.get("hybk") or "")
        if fallback:
            labels = [fallback]
        for theme in themes:
            subs = _THEME_SUBS.get(theme, ())
            if not subs:
                continue
            # sub 记真正命中的那个标签，不是列表第一个：模型要能看出凭什么归到
            # 这条题材，读者也是。命不中就不进，宁缺不猜。
            hit_label = next(
                (lab for lab in labels for sub in subs if sub and sub in lab), ""
            )
            if not hit_label:
                continue
            out.setdefault(theme, []).append(
                {
                    "name": name,
                    "code": code,
                    "board": _board_label(row.get("lbc")),
                    "sub": hit_label,
                    "source": "eastmoney",
                }
            )
    for theme, items in out.items():
        items.sort(key=lambda m: -_board_num(m.get("board")))
        out[theme] = items[:8]
    return out


def _panel_members(
    payload: Dict[str, Any], themes: List[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """三张免费面板里的票，按概念归位到当日题材。

    面板自己带的 ``sector`` 是「AI制药（医疗）」「可控核聚变」「多元金融」这类
    全市场主线板块，和晚报的当日题材不是一套口径——拿它做子串匹配，11-20 的
    15 只里只有北纬科技一只撞得上。改成和涨停池同一套概念归位，命中率才上来。

    这一路的票多半没有涨停（真视通、龙版传媒除外），价值也在这里：涨停池只
    回答「谁已经封板」，面板回答「谁在主线里、结构就绪但还没走」。所以它只做
    补充，不单独撑起一条题材。
    """
    concepts = payload.get("concepts") or {}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for label, block in (payload.get("filter") or {}).items():
        for row in block.get("rows") or []:
            code = row.get("code") or ""
            name = row.get("name") or ""
            if not name:
                continue
            hit = concepts.get(code) or {}
            raw = hit.get("concepts") or []
            labels = [
                c.get("name") or ""
                for c in raw
                if c.get("name") and not _concept_is_weak(c.get("name") or "")
            ]
            if not labels:
                continue
            for theme in themes:
                subs = _THEME_SUBS.get(theme, ())
                if not subs:
                    continue
                hit_label = next(
                    (lab for lab in labels for sub in subs if sub and sub in lab), ""
                )
                if not hit_label:
                    continue
                out.setdefault(theme, []).append(
                    {
                        "name": name,
                        "code": code,
                        "board": "",
                        "sub": hit_label,
                        "source": "panel",
                        "panel": label,
                        "gain60": row.get("gain60"),
                        "from_high": row.get("from_high60"),
                        "sector": row.get("sector") or "",
                    }
                )
    return out


def _day_lines(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """当日该用哪一份题材清单。

    每日主线块常常滞后一个交易日（``day.date != matrix.dates[0]``），它的
    name／count／driver 都属于上一场。11-20 的「明日关注」因此写着光刻机（胶）
    和国产芯片，而当日矩阵是芯片、PCB、农业、机器人——题材名错位之后，模型
    再拿面板里的票去填，就出现「国产芯片」下面挂一只算力股。

    滞后的块只保留 phase／degree／leader（另有 stale 判断），题材名一律改用
    矩阵当日列：那是同一天的数据，代价是分类更粗、没有 driver 和龙头。
    """
    matrix = payload.get("matrix") or {}
    day = matrix.get("day") or {}
    dates = matrix.get("dates") or []
    stale = day.get("stale")
    if stale is None:
        stale = bool(day.get("date") and dates and day.get("date") != dates[0])
    if not stale:
        return list(day.get("lines") or [])
    return [
        {
            "name": row.get("line") or "",
            "count": row.get("today"),
            "driver": "",
            "leader": "",
            "streak": row.get("streak"),
        }
        for row in (matrix.get("lines") or [])
        if row.get("line") and (row.get("today") or 0) > 0
    ]


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

    lines = _day_lines(payload)
    names = [x.get("name") or "" for x in lines]
    em_pool = _em_members(payload, names)
    panel_pool = _panel_members(payload, names)

    out: List[Dict[str, Any]] = []
    for line in lines:
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
            # 面板票排在涨停池前面：明日关注要的是「结构就绪、还没走」，不是
            # 已经封板的结果。同一只票若也在涨停池里，board 借涨停池的连板数，
            # 让它自己显出今天已经涨过，模型才不会把它当低位候选。
            em_by_name = {
                (m.get("name") or "").replace(" ", ""): m for m in em_pool.get(name, [])
            }
            for m in panel_pool.get(name, []):
                item = dict(m)
                key = (m.get("name") or "").replace(" ", "")
                up = em_by_name.get(key)
                if up:
                    item["board"] = up.get("board") or ""
                add(item, key)
            # 再接东财涨停池：当日真实涨停，按概念／行业标签归位
            for m in em_pool.get(name, []):
                add(dict(m), (m.get("name") or "").replace(" ", ""))
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
                "streak": line.get("streak"),
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
    # 个股题材归属：本地索引（同花顺 F10 概念页）倒查，按代码对齐。
    concepts = payload.get("concepts") or {}
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
    if day.get("stale"):
        # The page's 每日主线 block is still on the previous session, but the
        # matrix column for today is current. Fall back to it: same 产业线
        # taxonomy as industry_lines, no driver text, and marked so the model
        # knows the two views carry the same numbers.
        themes = [
            {
                "theme": x["line"],
                "limit_up": x["today"],
                "driver": "",
                "leader": "",
                "fallback": "industry_lines",
            }
            for x in lines
            if x.get("today", 0) > 0
        ]
    else:
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
    # The panel's own one-line rule and its total travel with the names: without
    # them "优选蓄势" is just five tickers, and a model cannot know that this
    # template is the one built for tomorrow rather than for today's strength.
    screeners = {
        label: {
            "why": block.get("why") or "",
            "total": block.get("total"),
            "rows": [
                {
                    "name": r["name"],
                    "code": r.get("code") or "",
                    "themes": (concepts.get(r.get("code") or "") or {}).get("themes") or [],
                    "sector": r["sector"],
                    "mainline": r.get("mark") or "",
                    "gain60": r["gain60"],
                    "from_high": r["from_high60"],
                    "above_ma20": r.get("ma20"),
                    "vol_ud": r.get("vol_ud"),
                }
                for r in block.get("rows", [])[:5]
            ],
        }
        for label, block in (payload.get("filter") or {}).items()
    }
    overseas = {
        g["label"]: {x["name"]: x["pct"] for x in g["items"]}
        for g in (extra.get("overseas") or [])
    }
    # 双保险：mcp_review 已把没过当日校验的正文清空，这里再按凭证挡一次，
    # 防止别的路径把 ai_review 直接塞进 payload。旧缓存没有 date_verified
    # 字段（None），按可信处理，免得回补历史日期时整段消失。
    lianban = payload.get("lianban") or {}
    third_party = (
        _trim(lianban.get("ai_review") or "")
        if lianban.get("date_verified") is not False
        else ""
    )

    # 龙虎榜的票大多不在三张面板前 5，所以归属要两个来源一起查：面板的 sector，
    # 和当日题材明细的 members（海立股份、江化微这类只在 members 里）。两个都查不到
    # 就留空——让模型知道"归属未知"，好过替它猜一个。
    theme_watch = _theme_watch(payload)
    theme_of: Dict[str, str] = {}
    for t in theme_watch:
        for m in t.get("members") or []:
            theme_of.setdefault(
                (m.get("name") or "").replace(" ", ""), t.get("theme") or ""
            )
    sector_of: Dict[str, str] = {}
    for block in (payload.get("filter") or {}).values():
        for row in block.get("rows") or []:
            sector_of[row["name"].replace(" ", "")] = row.get("sector") or ""
    # 当日题材名先摆好，好把索引倒查出的题材名对回当日口径。
    today_names = [t.get("theme") or "" for t in theme_watch if t.get("theme")]
    today_key = {_theme_key(n): n for n in today_names}

    def _today_of(themes: List[str]) -> List[str]:
        """索引题材名 -> 当日题材名，只做去括号后的同名匹配。

        这只是名称归一化，不是业务同义：光刻胶与「光刻机（胶）」能对上，
        但「家用电器」与「家电」对不上，那种情况留给模型自己判断。
        """
        out: List[str] = []
        for name in themes:
            hit = today_key.get(_theme_key(name))
            if hit and hit not in out:
                out.append(hit)
        return out

    lhb_raw = payload.get("lhb") or {}
    lhb_rows = []
    for x in (lhb_raw.get("items") or [])[:15]:
        key = (x.get("name") or "").replace(" ", "")
        hit = concepts.get(x.get("code") or "") or {}
        lhb_rows.append(
            {
                "name": x.get("name"),
                "sector": sector_of.get(key, ""),
                "theme": theme_of.get(key, ""),
                # 索引倒查的归属：themes 是 lianban 题材库里的标准名，
                # concepts 是同花顺原始概念，why 是公司自己披露的业务关联。
                "themes": hit.get("themes") or [],
                "today_themes": _today_of(hit.get("themes") or []),
                "concepts": [
                    c.get("name") for c in (hit.get("concepts") or [])[:6] if c.get("name")
                ],
                "why": ((hit.get("concepts") or [{}])[0] or {}).get("why") or "",
                "chg": x.get("chg"),
                "net": x.get("net"),
                "reason": x.get("reason"),
                "seat": x.get("seat"),
            }
        )

    return {
        "date": kpi.get("date"),
        "session": {
            "phase": kpi.get("emotion_phase"),
            # degree / leader / leader_badge all ride on the 每日主线 block; a
            # stale block means they describe the previous session, so they are
            # withheld rather than passed off as today's.
            "degree": None if day.get("stale") else day.get("degree"),
            # 只有通过当日校验的 status 才能代表「今天定版了」：前一天那份
            # 也是 final，拿它当代理会把今天的盘面说成已定版。
            "settled": (
                (payload.get("lianban") or {}).get("status")
                if (payload.get("lianban") or {}).get("date_verified")
                else kpi.get("_status")
            ),
            "leader": None if day.get("stale") else day.get("leader"),
            "leader_badge": None if day.get("stale") else day.get("leader_badge"),
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
        "theme_watch": theme_watch,
        "money_flow": flows,
        "candidates": screeners,
        "overseas": overseas,
        "next_day_base_rate": extra.get("forecast") or {},
        "lhb": {"header": lhb_raw.get("header") or "", "items": lhb_rows},
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
            tomorrow = []
            for item in doc.get("tomorrow_candidates") or []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if name:
                    tomorrow.append(
                        {
                            "name": name,
                            "theme": str(item.get("theme") or "").strip(),
                            "note": str(item.get("note") or "").strip(),
                        }
                    )
            focus = {}
            raw_focus = doc.get("focus")
            if isinstance(raw_focus, dict):
                for bucket in ("蓄势", "主线", "活跃"):
                    items = []
                    for item in raw_focus.get(bucket) or []:
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
                            items.append(
                                {
                                    "theme": theme,
                                    "signal": str(item.get("signal") or "").strip(),
                                    "stocks": stocks,
                                }
                            )
                    if items:
                        focus[bucket] = items
            return {
                "headline": str(doc.get("headline") or "").strip(),
                "sections": sections,
                "watchlist": watch,
                "tomorrow_candidates": tomorrow,
                "focus": focus,
                "dissent": text,
            }
    paras = [p.strip() for p in re.split(r"\n+", raw) if p.strip()]
    return {"headline": "", "sections": [{"h": "", "p": p} for p in paras], "dissent": ""}


def llm_read(payload: Dict[str, Any], conf: Dict[str, Any], timeout: float = 420.0) -> Dict[str, Any]:
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
        "max_tokens": 3000,
        # qwen3 默认开思考，一次能跑满五分钟；这份活要的是按模板填判断，
        # 不需要思维链，关掉后通常三十秒内返回。
        "enable_thinking": False,
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
            print("response_format/enable_thinking rejected; retrying without them", file=sys.stderr)
            body.pop("response_format", None)
            body.pop("enable_thinking", None)
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


def _post_card(
    url: str, title: str, desp: str, timeout: float, short: str = ""
) -> "tuple[bool, str]":
    """One POST attempt. Returns (delivered, detail) instead of raising."""
    # Server酱 parses the body as a form. Posting JSON leaves ``title`` unset and
    # the API answers 400 "title 不能为空" — the field is simply not there as far
    # as its parser is concerned.
    fields = {"title": title, "desp": desp}
    # ``short`` is the line the WeChat card prints before the body is opened.
    # Left out, the card falls back to the first line of ``desp`` — which is now
    # Markdown, so the recipient would read ``## 冰点极致分化`` with the hashes.
    if short:
        fields["short"] = short
    body = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")[:500]
        except Exception:  # noqa: BLE001 - the body is a bonus, not a requirement
            pass
        return False, f"HTTP {exc.code} {detail}".strip()
    except (urllib.error.URLError, OSError) as exc:
        return False, str(exc)
    print(f"webhook response: {raw[:300]}")
    try:
        doc = json.loads(raw)
    except ValueError:
        # An error page is not a delivery receipt. Treating it as success is how a
        # broken endpoint keeps printing "push: ok" while nothing ever lands.
        return False, f"non-JSON response: {raw[:120]}"
    code = doc.get("code", doc.get("errno", 0))
    if code in (0, "0", None):
        return True, ""
    return False, f"code={code} {raw[:200]}"


def _load_webhook_banners() -> List[str]:
    """Read data/webhook_banners.json: one greeting per endpoint, by position.

    The same file the morning digest reads, so a recipient sees the same line in
    both cards. A missing or malformed file simply means no banners.
    """
    candidates = [Path("data/webhook_banners.json")]
    here = globals().get("__file__")
    if here:
        candidates.append(Path(here).resolve().parent.parent / "data" / "webhook_banners.json")
    for path in candidates:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rows = doc.get("banners") if isinstance(doc, dict) else None
        if isinstance(rows, list):
            return [str(row or "").strip() for row in rows]
        return []
    return []


def push_webhook(
    urls: str, title: str, desp: str, timeout: float = 30.0, short: str = ""
) -> bool:
    """POST one card to every endpoint listed in HORIZON_WEBHOOK_URL.

    The morning digest reads the same variable as a list — comma or newline
    separated, one entry per recipient — and pairs each entry with a greeting
    from data/webhook_banners.json, by position. The evening card mirrors that,
    so both cards reach the same people in the same shape. Posting the raw value
    as a single URL would build a malformed address the moment a second
    subscriber is appended.

    No retry: a rejected request still counts against the free daily quota, so a
    second attempt on a bad payload only burns another message.
    """
    targets = [u.strip() for u in re.split(r"[,\n]+", urls or "") if u.strip()]
    if not targets:
        print("webhook failed: no endpoint", file=sys.stderr)
        return False
    banners = _load_webhook_banners()
    # The pairing is positional, so a short banner list silently means "no
    # greeting" for the tail recipients. Printing both counts makes a
    # mis-ordered or truncated list visible in the run log.
    print(f"push: {len(targets)} endpoints, {len(banners)} banners")
    delivered = 0
    for index, url in enumerate(targets):
        banner = banners[index] if index < len(banners) else ""
        # Bold, so the greeting reads as a dedication above the card rather
        # than as the first sentence of the brief. Skipped when the entry
        # already carries its own emphasis.
        if banner and "*" not in banner:
            banner = f"**{banner}**"
        body = f"{banner}\n\n{desp}" if banner else desp
        # Position and presence only: the URL carries the send key, the banner
        # carries a name, and neither belongs in a public Actions log.
        print(f"push[{index + 1}/{len(targets)}]: banner={'yes' if banner else 'no'}")
        ok, detail = _post_card(url, title, body, timeout, short)
        # The URL carries the send key, so only the position is logged.
        print(f"push[{index + 1}/{len(targets)}]: {'ok' if ok else 'failed'}")
        if ok:
            delivered += 1
        else:
            print(f"webhook failed: {detail}", file=sys.stderr)
    return delivered == len(targets)


def _load_ai_conf(path: Path) -> Dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return doc.get("ai") or {}


def collect(no_browser: bool = False, fetch_concepts: bool = True, save_concepts: bool = False) -> Dict[str, Any]:
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
        "lhb": {},
        "regulatory": {},
        "concepts": {},
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
    try:
        payload["lhb"] = parse_lhb(fetch(LHB_URL, referer=MAINLINE_URL))
    except Exception as exc:  # noqa: BLE001
        payload["errors"].append(f"lhb: {exc}")
    try:
        payload["regulatory"] = parse_alerts(fetch(ZAOPAN_URL, referer=MAINLINE_URL))
    except Exception as exc:  # noqa: BLE001
        payload["errors"].append(f"regulatory: {exc}")
    if not no_browser:
        try:
            payload["extra"] = collect_extra()
        except Exception as exc:  # noqa: BLE001
            payload["errors"].append(f"browser: {exc}")
    # 个股题材归属：先查本地索引，索引里没有的票现抓（限速 ~2.3s/只），
    # 抓不到的留空，不借邻座的题材。
    try:
        payload["concepts"] = attach_concepts(
            payload, fetch_missing=fetch_concepts, save=save_concepts
        )
    except Exception as exc:  # noqa: BLE001
        payload["errors"].append(f"concepts: {exc}")
    return payload


# Section heads carry one icon each: the emoji are fixed-colour glyphs, so they
# read the same on a light and a dark background, which is exactly what a CSS
# colour cannot promise here. Body text stays plain — decoration everywhere is
# what makes a long card hard to scan.
_SECTION_ICONS = {
    "盘面总结": "📊",
    "重点信号": "🔍",
    "盘面变动归因": "🔄",
    "趋势展望": "🔭",
}
_FOCUS_ICONS = {"主线": "🎯", "活跃": "🔥", "蓄势": "🌱"}


_NUMBERED_MARK_RE = re.compile(r"(?:(?<=[。；;])|^)\s*([1-9])\s*[.、．]\s*")


def _split_numbered(text: str) -> List[str]:
    """Break a run-on "1. … 2. … 3. …" paragraph into separate items.

    The model writes the key-signals section as one paragraph with inline
    numbering, which arrives as a single wall of text. Splitting on the marks
    only when there are at least two keeps ordinary prose — and sentences that
    merely mention a figure — untouched.
    """
    marks = list(_NUMBERED_MARK_RE.finditer(text))
    if len(marks) < 2:
        return [text]
    items: List[str] = []
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        seg = text[mark.end():end].strip()
        if seg:
            items.append(f"{mark.group(1)}. {seg}")
    return items if len(items) >= 2 else [text]


def _head(level: int, icon: str, text: str) -> str:
    """One heading line: level, optional icon, then the label."""
    marks = "#" * level
    return f"{marks} {icon} {text}" if icon else f"{marks} {text}"


# 页面 header 的第二行。推文补上同一句，两边标题下的引导语才不是两套说法。
_TAGLINE = "盘面总结 · 重点信号 · 变动归因 · 趋势展望 · 蓄势 / 主线 / 活跃"


def _read_markdown(
    read: Dict[str, Any], note: str = "", payload: Optional[Dict[str, Any]] = None
) -> str:
    """The push body: the same read the page renders, as Markdown.

    Server酱 renders Markdown only — no HTML and no CSS — so no colour can be
    set from here, and an inline ``<font color>`` would arrive as literal text.
    What survives both the light and the dark WeChat webview is structure:
    heading levels, blockquotes and horizontal rules carry the hierarchy, and
    the icons sit on section heads where they work as anchors. Nothing in the
    body depends on a background colour to stay legible, so neither theme can
    swallow a line.

    The counts, the 60-day position and the dragon-tiger net amount are read
    from the payload, never from the model's prose: a figure the model retypes
    is a figure it can get wrong, and the page already holds the right one.
    """
    if not read:
        return f"> 🌡️ {note}" if note else ""
    payload = payload or {}
    meta = _theme_meta(payload)
    loose_meta = {_loose(k): v for k, v in meta.items()}
    pos = _filter_pos(payload)
    board_map = _lhb_map(payload)

    out: List[str] = [_TAGLINE]
    headline = str(read.get("headline") or "").strip()
    if headline:
        out.append(f"## {headline}")
    # The stats line stays a blockquote under the verdict: grey, indented and
    # visibly a footnote, so it never competes with the call above it.
    if note:
        out.append(f"> 🌡️ {note}")
    for sec in read.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        head = str(sec.get("h") or "").strip()
        body = str(sec.get("p") or "").strip()
        if head:
            out.append("---")
            out.append(_head(3, _SECTION_ICONS.get(head, ""), head))
        if body:
            items = _split_numbered(body)
            # One blank-line-joined block per section: keeping the numbered
            # items on adjacent lines lets Markdown render them as one list.
            out.append("\n".join(items) if len(items) > 1 else body)
    focus = read.get("focus") or {}
    if any(focus.get(b) for b in ("主线", "活跃", "蓄势")):
        out.append("---")
        out.append(_head(2, "", "明日关注"))
    for bucket in ("主线", "活跃", "蓄势"):
        rows = focus.get(bucket) or []
        if not rows:
            continue
        out.append(_head(3, _FOCUS_ICONS.get(bucket, ""), bucket))
        # 页面在每类标题下有一句“这一类回答什么问题”，推文照搬同一句。
        desc = _FOCUS_DESC.get(bucket)
        if desc:
            out.append(f"> {desc}")
        for row in rows:
            if not isinstance(row, dict):
                continue
            theme = str(row.get("theme") or "").strip()
            signal = str(row.get("signal") or "").strip()
            info = meta.get(theme) or loose_meta.get(_loose(theme)) or {}
            # 蓄势的题材是票自己的板块，不是当日涨停线，不挂涨停家数。
            chip = (
                f"{info['count']} 家涨停"
                if bucket != "蓄势" and info.get("count")
                else ""
            )
            if theme:
                # 题材名本身常带括号（光刻机（胶）），再套一层括号会挤成一团，
                # 用间隔号把家数分出去。
                out.append(f"**{theme}**" + (f" · {chip}" if chip else ""))
            if signal:
                out.append(f"> {signal}")
            stocks_md = []
            for stock in row.get("stocks") or []:
                if not isinstance(stock, dict):
                    continue
                name = str(stock.get("name") or "").strip()
                if not name:
                    continue
                key = name.replace(" ", "")
                hit = pos.get(key) or {}
                bits = []
                tag = str(stock.get("tag") or "").strip()
                if tag:
                    bits.append(tag)
                if hit.get("gain60"):
                    bits.append(f"60日 {hit['gain60']}")
                if hit.get("from_high"):
                    bits.append(f"距高点 {hit['from_high']}")
                board = board_map.get(key) or {}
                if bucket == "活跃" and board.get("net"):
                    bits.append(f"龙虎榜 {board['net']}")
                line = f"- **{name}**" + (f" · {' · '.join(bits)}" if bits else "")
                stocks_md.append(line)
            if stocks_md:
                out.append("\n".join(stocks_md))
    dis = read.get("dissent")
    if isinstance(dis, dict):
        text = str(dis.get("disagree") or dis.get("agree") or "").strip()
    else:
        text = str(dis or "").strip()
    # 代码侧兜底：lianban 的复盘没过当日校验时 ai_review 已被清空，模型手里
    # 根本没有第三方内容，它写出来的「分歧」就是对着空气反驳。这一节由数据
    # 决定去留，不指望 prompt 让模型自己闭嘴。
    if text and not str((payload or {}).get("lianban", {}).get("ai_review") or "").strip():
        text = ""
    if text:
        out.append("---")
        out.append(_head(3, "⚖️", "与连板网复盘的分歧"))
        out.append(f"> {text}")
    return "\n\n".join(out)


def _card_short(read: Dict[str, Any], note: str = "", limit: int = 48) -> str:
    """The one line WeChat shows on the card, before the body is opened.

    Server酱 renders ``desp`` as Markdown but prints ``short`` as plain text on
    the notification card. Without it the card shows the raw ``##`` and ``**``
    of the first line; with it the recipient sees a sentence.
    """
    head = str((read or {}).get("headline") or "").strip()
    stats = note.strip().strip("（）()").strip()
    line = f"{head}｜{stats}" if head and stats else (head or stats)
    line = " ".join(line.split())
    if len(line) > limit:
        # Drop a dangling separator before the ellipsis: a card ending in "｜…"
        # reads as a rendering bug rather than as a shortened sentence.
        line = line[:limit].rstrip("｜|·、，, ") + "…"
    return line


from typing import Any, Dict, List


def _join(items: List[str], sep: str = " · ") -> str:
    return sep.join(x for x in items if x)


def _rows(items: List[str], per_line: int = 4) -> List[str]:
    """长列表按 per_line 折行：一行塞十项在手机上会横向溢出。"""
    return [_join(items[i:i + per_line]) for i in range(0, len(items), per_line)]


def _panel_list(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    return ((payload.get("extra") or {}).get("panel") or [])


def _kpi_lines(payload: Dict[str, Any]) -> List[str]:
    kpi = payload.get("kpi") or {}
    panel = _panel_map(payload)

    def val(label: str) -> str:
        return str((panel.get(label) or {}).get("value") or "").strip()

    def sub(label: str) -> str:
        return str((panel.get(label) or {}).get("sub") or "").strip()

    out: List[str] = []
    out.append(_join([
        f"涨停 **{kpi['limit_up']}**" if kpi.get("limit_up") is not None else "",
        f"跌停 **{kpi['limit_down']}**" if kpi.get("limit_down") is not None else "",
        f"封板率 **{kpi['seal_rate_pct']}%**" if kpi.get("seal_rate_pct") is not None else "",
        f"炸板 {kpi['zhaban']}" if kpi.get("zhaban") is not None else "",
        f"连板 {kpi['lianban']}" if kpi.get("lianban") is not None else "",
        f"最高 {kpi['max_board']} 板" if kpi.get("max_board") is not None else "",
    ]))
    if kpi.get("adv") is not None and kpi.get("dec") is not None:
        out.append(_join([
            f"上涨 {kpi['adv']} / 下跌 {kpi['dec']}",
            f"两市成交 {val('两市成交')}" if val("两市成交") else "",
        ]))
    phase = str(kpi.get("emotion_phase") or "").strip() or val("情绪周期")
    hl = val("新高/新低63日")
    out.append(_join([
        f"情绪 **{phase}**" if phase else "",
        sub("情绪周期"),
        f"新高/新低 {hl}" if hl else "",
    ]))
    # 较前值逐项来自面板的 sub，按页面顺序拼成一行。
    deltas = [
        f"{str(r.get('label') or '').strip()} {str(r.get('sub') or '').replace('较前值', '').strip()}"
        for r in _panel_list(payload)
        if str(r.get("sub") or "").startswith("较前值")
    ]
    if deltas:
        out.append("较前值：" + _join(deltas))
    yl_v, yl_s = val("昨涨停今表现"), sub("昨涨停今表现")
    if yl_v:
        out.append(_join([f"昨涨停今表现 **{yl_v}**", yl_s,
                          f"炸板率 {sub('炸板').replace('率 ', '')}" if sub("炸板") else ""]))
    return [x for x in out if x]


def _strength_lines(payload: Dict[str, Any]) -> List[str]:
    rows = (payload.get("extra") or {}).get("strength") or []
    items = [f"{r['name']} {r['pct']}" for r in rows if r.get("name")]
    return _rows(items, 4)


def _flow_lines(payload: Dict[str, Any]) -> List[str]:
    flows = (payload.get("extra") or {}).get("flows") or {}
    out = []
    for label, rows in flows.items():
        cells = [
            f"{r['name']} {r['amount']}" + (f"（{r['pct']}）" if r.get("pct") else "")
            for r in (rows or [])[:5] if r.get("name")
        ]
        if cells:
            out.append(f"**{label}** " + " · ".join(cells))
    return out


def _matrix_lines(payload: Dict[str, Any]) -> List[str]:
    matrix = payload.get("matrix") or {}
    out = []
    for row in matrix.get("lines") or []:
        today, prev = row.get("today", 0), row.get("prev", 0)
        if today == 0 and prev == 0:
            continue
        bits = [f"昨 {prev}", f"日Δ {row['delta1']:+d}", f"连续 {row['streak']} 天"]
        if row.get("state"):
            bits.append(str(row["state"]))
        out.append(f"- **{row['line']}** {today} 家（" + " · ".join(bits) + "）")
        if len(out) >= 8:
            break
    return out


def _driver_lines(payload: Dict[str, Any]) -> List[str]:
    matrix = payload.get("matrix") or {}
    day = matrix.get("day") or {}
    dates = matrix.get("dates") or []
    stale = day.get("stale")
    if stale is None:
        stale = bool(day.get("date") and dates and day.get("date") != dates[0])
    if stale or not day.get("lines"):
        # 每日主线块滞后时用矩阵当日列，并写明口径，别让读者以为那是原表。
        fb = [x for x in (matrix.get("lines") or []) if x.get("today", 0) > 0][:6]
        if not fb:
            return []
        items = [f"**{x['line']}** {x['today']} 家" for x in fb]
        return ["（产业线口径 · 页面每日主线为 " + str(day.get("date") or "前一日") + "）"] + _rows(items, 3)
    out = []
    for x in day["lines"]:
        line = f"- **{x['name']}** {x['count']} 家"
        if x.get("driver"):
            line += f"｜{x['driver']}"
        if x.get("leader"):
            line += f"｜龙头 {x['leader']}"
        out.append(line)
    return out


def _pick_lines(payload: Dict[str, Any], limit: int = 4) -> List[str]:
    out = []
    for label, block in (payload.get("filter") or {}).items():
        rows = block.get("rows") or []
        if not rows:
            continue
        total = block.get("total")
        head = f"**{label}**" + (f" 共 {total} 只" if total else "")
        out.append(head)
        for r in rows[:limit]:
            bits = _join([str(r.get("sector") or ""), f"60日 {r.get('gain60')}" if r.get("gain60") else "",
                          f"距高点 {r.get('from_high60')}" if r.get("from_high60") else ""])
            out.append(f"- **{r.get('name')}**" + (f" {bits}" if bits else ""))
    return out


def _lhb_lines(payload: Dict[str, Any], limit: int = 8) -> List[str]:
    items = (payload.get("lhb") or {}).get("items") or []
    concepts = payload.get("concepts") or {}
    out = []
    for it in items[:limit]:
        theme = ""
        for t in ((concepts.get(it.get("code") or "") or {}).get("themes") or [])[:1]:
            theme = t
        bits = _join([str(it.get("net") or ""), str(it.get("chg") or ""), theme])
        out.append(f"- **{it.get('name')}**" + (f" {bits}" if bits else ""))
    return out


def _regulatory_lines(payload: Dict[str, Any], limit: int = 8) -> List[str]:
    items = (payload.get("regulatory") or {}).get("items") or []
    out = []
    for it in items[:limit]:
        bits = _join([str(it.get("kind") or ""),
                      f"今年 {it['boards']} 板" if it.get("boards") else ""])
        out.append(f"- **{it.get('name')}**" + (f" {bits}" if bits else ""))
    return out


def _review_lines(payload: Dict[str, Any]) -> List[str]:
    doc = payload.get("lianban") or {}
    text = str(doc.get("ai_review") or "").strip()
    if not text:
        return []
    # 全文照登，理由同页面侧：第二段「重点游资」才是席位信息最密的地方。
    body = text
    if len(body) > 600:
        body = body[:600].rstrip() + "…"
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    # 每段一个引用行、段间留一个空引用行：Markdown 里这仍是同一个引用块的两段，
    # 不会裂成两个灰框。
    return ["\n>\n".join("> " + p.replace("\n", "\n> ") for p in paras)]


def _signal_lines(payload: Dict[str, Any]) -> List[str]:
    """今日信号面：形态 + 历史统计，一条一段。

    标签自带 🔴/🔵/❄️，那是连板网用来区分「风险 / 机会 / 防守」的唯一标记，
    去掉这三个 emoji 就只剩三行长得一样的话。
    """
    out: List[str] = []
    for row in ((payload.get("extra") or {}).get("signals")) or []:
        chip = str(row.get("chip") or "").strip()
        text = str(row.get("text") or "").strip()
        if chip and text:
            out.append(f"**{chip}** {text}")
    return out


def _overseas_lines(payload: Dict[str, Any]) -> List[str]:
    groups = (payload.get("extra") or {}).get("overseas") or []
    out = []
    for g in groups:
        items = [f"{x['name']} {x['pct']}" for x in (g.get("items") or []) if x.get("name")]
        if items:
            out.append(f"**{str(g.get('label') or '').split(' · ')[0]}** " + " · ".join(items))
    return out


def _pack(lines: List[str]) -> List[str]:
    """连续的列表行用单换行连成一块。

    Markdown 把空行分隔的 ``- `` 项渲染成松散列表，每项套一层 <p>，
    手机上间距翻倍；同一块里的项只换行不空行，才是紧凑列表。
    """
    out: List[str] = []
    buf: List[str] = []
    for x in lines:
        if x.startswith(("- ", "> ")):
            buf.append(x)
            continue
        if buf:
            out.append("\n".join(buf))
            buf = []
        out.append(x)
    if buf:
        out.append("\n".join(buf))
    return out


def data_markdown(payload: Dict[str, Any]) -> str:
    """页面上的数字板块，按页面顺序排成 Markdown。

    研判是主角，这里是支撑：所以整段只用 ``##`` 标题分节，不再逐个加图标，
    视觉上比上面的研判低一层。
    """
    sections: List[tuple] = []

    def add(title: str, lines: List[str]) -> None:
        if lines:
            sections.append((title, _pack(lines)))

    add("盘面", _kpi_lines(payload))
    add("主线强度", _strength_lines(payload))
    add("主力资金", _flow_lines(payload))
    add("主线矩阵", _matrix_lines(payload))
    add("当日主线", _driver_lines(payload))
    add("筛选面板", _pick_lines(payload))
    add("龙虎榜 · 题材归属", _lhb_lines(payload))
    add("监管异动", _regulatory_lines(payload))
    add("连板网复盘", _review_lines(payload))
    add("今日信号面", _signal_lines(payload))
    add("外盘参考", _overseas_lines(payload))
    if not sections:
        return ""
    out: List[str] = ["---"]
    for title, lines in sections:
        out.append(f"## {title}")
        out.extend(lines)
    return "\n\n".join(out)


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
    parser.add_argument(
        "--no-fetch-concepts",
        action="store_true",
        help="only use the shipped concept index; do not fetch missing tickers",
    )
    parser.add_argument(
        "--save-concepts",
        action="store_true",
        help="write newly fetched tickers back into the concept index",
    )
    args = parser.parse_args(argv)

    payload = collect(
        no_browser=args.no_browser,
        fetch_concepts=not args.no_fetch_concepts,
        save_concepts=args.save_concepts,
    )
    matrix = payload["matrix"]
    kpi = payload["kpi"]
    date = args.date or kpi.get("date") or (matrix.get("dates") or [""])[0]
    if not date:
        print("no date from any source; aborting", file=sys.stderr)
        return 2
    payload["date"] = date
    # 今日信号面只存在于 days/<date>.html，而且那块要等页面自己的脚本跑完才
    # 出现（直接 HTTP 抓回来的是 6 KB 空壳）。date 是上面几个源合出来的，
    # 所以放在这里抓：进 collect() 的时候还不知道该抓哪一天。
    if not args.no_browser:
        try:
            payload["extra"]["signals"] = parse_signals(render_day(date))
        except Exception as exc:  # noqa: BLE001 - 少一块，不影响别的
            payload["errors"].append(f"signals: {exc}")
    # 东财涨停池：lianban 的题材明细面板改版后，这是唯一还能逐只拿到的当日涨停
    # 名单。一次请求换 28 行，比翻十页便宜；拿不到就少一块，不挡整份晚报。
    try:
        payload["em_zt"] = (eastmoney.pool("ZT", date) or {}).get("rows") or []
        # 这 28 只大多不在面板／龙虎榜上，第一次 attach_concepts 没覆盖到；
        # 补抓一次，题材归位才有概念标签可用。抓不到的票留空，不影响别的块。
        if payload["em_zt"] and not args.no_fetch_concepts:
            more = attach_concepts(payload, fetch_missing=True, save=args.save_concepts)
            payload["concepts"].update(more)
    except Exception as exc:  # noqa: BLE001
        payload["errors"].append(f"eastmoney pool: {exc}")
    # 监管异动带的是早盘页当天那一份；日期对不上就整块丢掉，宁可少一块，
    # 也不要把上一交易日的异常波动名单当成今天的印出来。
    regulatory = payload.get("regulatory") or {}
    if regulatory and regulatory.get("snapshot") != date:
        payload["errors"].append(
            f"regulatory: snapshot {regulatory.get('snapshot') or '(none)'} != {date};"
            " block skipped"
        )
        payload["regulatory"] = {}

    # 六个盘面数字是公开交易事实，不是某家站点的判断：东财与连板网在 2026-11-19
    # 逐个相等（涨停 23、跌停 68、炸板 24、封板率 48.9%、连板 5、最高 3 板）。
    # 东财做第一来源，连板网只补它独有的字段（情绪阶段、degree、资金面文字）。
    try:
        em_kpi = eastmoney.kpi(date)
    except Exception as exc:  # noqa: BLE001 - a missing block, not a failed brief
        payload["errors"].append(f"eastmoney kpi: {exc}")
        em_kpi = {}
    if em_kpi:
        kpi_block = payload.get("kpi") or {}
        for field in (
            "limit_up",
            "limit_down",
            "zhaban",
            "seal_rate_pct",
            "lianban",
            "max_board",
        ):
            if em_kpi.get(field) is not None:
                kpi_block[field] = em_kpi[field]
        kpi_block.setdefault("date", date)
        kpi_block["_breadth_source"] = "eastmoney"
        payload["kpi"] = kpi_block

    # 龙虎榜同理：东财两个报表给名称、涨跌幅、净额、上榜原因与买一席位，与连板网
    # 引的是同一批交易所披露。取不到就留着连板网那份，不因为换源把这块弄没。
    try:
        em_lhb = eastmoney.lhb(date)
    except Exception as exc:  # noqa: BLE001
        payload["errors"].append(f"eastmoney lhb: {exc}")
        em_lhb = {}
    # 龙虎榜是收盘后陆续披露的，盘中跑到这里可能只有几只；不足 10 只就认为还没出全，
    # 留着连板网那份完整的，不拿半张榜顶掉它。
    if len(em_lhb.get("items") or []) >= 10:
        payload["lhb_site"] = payload.get("lhb") or {}
        payload["lhb"] = em_lhb
        # 换过来的票未必在连板网那份前 15 里，题材归属得按新名单再查一遍。
        try:
            payload["concepts"] = attach_concepts(
                payload,
                fetch_missing=not args.no_fetch_concepts,
                save=args.save_concepts,
            )
        except Exception as exc:  # noqa: BLE001
            payload["errors"].append(f"concepts(lhb): {exc}")

    # 资金面：连板网的 today.html 只有浏览器渲染才拿得到；缺了就用东财板块资金流补，
    # 只补净流入/净流出两列，不碰它的主线强度评分——那是它自己的模型，换不来。
    if not ((payload.get("extra") or {}).get("flows")):
        try:
            inflow = eastmoney.sector_flow(5, descending=True)
            outflow = eastmoney.sector_flow(5, descending=False)
        except Exception as exc:  # noqa: BLE001
            payload["errors"].append(f"eastmoney flow: {exc}")
            inflow, outflow = [], []
        if inflow:
            payload.setdefault("extra", {})["flows"] = {
                "主力净流入（东财）": inflow,
                "主力净流出（东财）": outflow,
            }

    if not args.no_mcp:
        try:
            review = mcp_review(date)
            payload["lianban"] = review
            # 这一段是「模型拿去对比的是不是当天」的唯一凭证，跑完必须能在
            # 日志里看到，而不是等推送出来才发现对错了日子。
            check = review.get("date_check") or {}
            if review.get("date_verified"):
                print(
                    f"mcp review: date={date} verified"
                    f" kpi={check.get('kpi_date')}"
                    f" updated={check.get('updated_at')}"
                    f" status={check.get('status')}"
                    f" text_counts={check.get('text_counts_matched')}/3",
                    file=sys.stderr,
                )
            else:
                print(
                    f"mcp review: date={date} REJECTED"
                    f" reasons={check.get('reasons')}"
                    f" dropped={review.get('rejected')}",
                    file=sys.stderr,
                )
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
    # 页面要把「题材 → 逐只成员」写进 next-day-brief JSON 块给早报读。theme_watch
    # 只在 build_model_input 里算过一次，--no-llm 时根本不会算，所以这里落一份。
    if not payload.get("theme_watch"):
        payload["theme_watch"] = _theme_watch(payload)
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
    # 总龙头 lives in the same 每日主线 block; when that block is a session
    # behind, the name belongs to the previous day and must not go out as today's.
    lead = "" if day.get("stale") else " ".join(
        x for x in [day.get("leader") or "", day.get("leader_badge") or ""] if x
    )
    top = [l for l in matrix.get("lines") or [] if l.get("today", 0) > 0][:3]
    headline = "、".join(f"{l['line']}{l['today']}" for l in top) or "无涨停线"
    # 与页面 header 同一串文字：微信标题和正文标题下的引导语对得上。
    #
    # 但 Server酱 的 title 只收 32 个字符，超出部分直接砍掉：完整写法
    # 「Kenny's Horizon 2026-11-20 盘后洞察晚报」是 33 个字符，被砍掉的正好是
    # 「晚报」的「报」。日期改写成「11月20日」省 4 个字符，落在 29，产品名
    # 一个字不动，也不会因为哪天改了文案又悄悄超限——超了就在日志里喊一声。
    stamp = date
    _md = re.fullmatch(r"\d{4}-(\d{2})-(\d{2})", date or "")
    if _md:
        stamp = f"{int(_md.group(1))}月{int(_md.group(2))}日"
    title = f"Kenny's Horizon {stamp} 盘后洞察晚报"
    if len(title) > 32:
        print(f"warning: title {len(title)} chars > 32, Server酱 will cut it", file=sys.stderr)
    note = (
        f"（{kpi.get('emotion_phase') or ''} 涨停{kpi.get('limit_up')} 跌停{kpi.get('limit_down')}"
        f" 封板率{kpi.get('seal_rate_pct')}%"
        + (f"｜主线 {headline}" if top else "")
        + (f"｜总龙头 {lead}" if lead else "")
        + "）"
    )
    desp = "\n\n".join(
        part
        for part in [
            _read_markdown(summary, note, payload),
            # 页面上的数字板块：推文里此前只有研判，读者要跳出去才看得到盘面与矩阵。
            data_markdown(payload),
        ]
        if part
    )
    # dissent 空着不报错、也不占版面，事后只能靠日志判断是「模型认为一致」
    # 还是「模型根本没拿到那份复盘」。两个长度一起打，一眼能分清。
    _lb = payload.get("lianban") or {}
    print(
        f"read: third_party={len(_lb.get('ai_review') or '')} chars, "
        f"dissent={len(str(summary.get('dissent') or ''))} chars"
    )
    print(
        f"push: title={len(title)} chars / {len(title.encode('utf-8'))} bytes, "
        f"desp={len(desp)} chars"
    )
    ok = push_webhook(hook, title, desp, short=_card_short(summary, note))
    print(f"push: {'ok' if ok else 'failed'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
