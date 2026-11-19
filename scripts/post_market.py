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
from lianban_extra import EXTRA_CSS, collect_extra, mcp_review, render_sections  # noqa: E402

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

【六段，各回答一个问题】
1. 盘面总结：今天是什么市（冰点／退潮／分歧／修复／主升，选一个并说明强度）。必须用"指数分化"和"宽度分位"各一条证据，并指出至少一处互相矛盾的信号——例如涨停高度集中在一条线，但成交额创 60 日新低、新低家数创新高。
2. 重点信号：给 2 到 3 个今天最值得记住的异常，每个都要带"相对于什么"（60 日分位、昨日值、或与其他指数/板块的背离）。这一段是替读者划重点，不要把所有指标都念一遍。
3. 盘面变动归因：钱从哪来、到哪去。用成交额相对 20 日均、各线 delta_1d、板块资金流判断今天是缩量撤退、存量搬家还是增量入场，并说清跌的是哪一类（小盘／双创／主板）。
4. 趋势展望：先给出连板网的基准率（next_day_base_rate），再明确说同意还是不同意、为什么；然后给两个"如果……则……；否则……"的观察点，必须明天能从同一份数据里读到。
5. 重点关注题材：1 到 2 条。说清为什么是它（连续天数、集中度、驱动、板块强弱），以及明天什么信号能确认或证伪。
6. 重点关注个股：从 candidates 的三个面板里选 2 到 3 只，写明它属于哪条题材、位置如何（60 日涨幅与距高点，意味着高位加速还是刚启动）。只描述特征，不做推荐。

【硬性禁止】
- 禁止罗列数字。数字只能作为比较出现："从 3 家到 11 家"可以，单独一句"涨停 11 家"不可以。
- 禁止把先后关系写成因果关系。"英伟达宣布合作"与"芯片涨停"同时出现，不等于前者驱动了后者。
- 禁止买卖建议、目标价、仓位、点位、任何荐股语气。
- 禁止"综上所述""值得关注""后市可期""静待方向选择"这类空话。
- 禁止复述页面上已有的表格。

【输出格式】
只输出一个 JSON 对象，不要 markdown 代码块，不要任何解释文字：
{{"headline": "一句话定性，不超过 18 字，必须是判断而不是描述",
 "sections": [
  {{"h": "盘面总结", "p": "70-110 字"}},
  {{"h": "重点信号", "p": "70-110 字"}},
  {{"h": "盘面变动归因", "p": "70-110 字"}},
  {{"h": "趋势展望", "p": "70-110 字"}},
  {{"h": "重点关注题材", "p": "70-110 字"}},
  {{"h": "重点关注个股", "p": "70-110 字"}}
 ],
 "dissent": "与连板网复盘的分歧，一句话；没有分歧就填空字符串，不要编"}}"""


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
            return {
                "headline": str(doc.get("headline") or "").strip(),
                "sections": sections,
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
        "max_tokens": 1600,
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


def _esc(value: Any) -> str:
    return _html.escape(str(value if value is not None else ""))


def _pct_class(raw: str) -> str:
    text = str(raw or "").strip()
    if text.startswith("+"):
        return "up"
    if text.startswith("-"):
        return "down"
    return ""


def _state_class(state: str) -> str:
    return {
        "扩散": "up",
        "新上榜": "up",
        "过热": "hot",
        "收缩": "down",
        "缺席": "mute",
    }.get(state, "mute")


_PAGE_CSS = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:#fff;color:#606c71;
  font:17px/1.75 "Open Sans","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
.page-header{color:#fff;text-align:center;background-color:#159957;
  background-image:linear-gradient(120deg,#155799,#159957);
  padding:38px 20px 32px;padding-top:calc(38px + env(safe-area-inset-top))}
.project-name{margin:0 0 8px;font-size:23px;font-weight:600;letter-spacing:.2px;line-height:1.3;word-break:keep-all}
.page-header .project-tagline{margin:0;font-size:14px;font-weight:400;color:rgba(255,255,255,.85);letter-spacing:.3px}
main{max-width:680px;margin:0 auto;padding:22px 18px calc(44px + env(safe-area-inset-bottom))}
main h2{margin:32px 0 12px;font-size:19px;font-weight:600;color:#159957;line-height:1.4}
main h2:first-child{margin-top:6px}
p{margin:0 0 1em}
.lede{margin:0 0 20px;color:#4c5866}
a{color:#1e6bb8;text-decoration:none}
.read{border-left:3px solid #159957;padding:2px 0 2px 14px}
.read p:last-child{margin-bottom:0}
.read .verdict{font-size:19px;line-height:1.5;font-weight:600;color:#22313f;margin:0 0 14px}
.read h3{margin:16px 0 6px;font-size:15px;font-weight:600;color:#159957;letter-spacing:.2px}
.read h3:first-of-type{margin-top:0}
.read .tag{margin-right:6px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#e9ebec;
  border:1px solid #e9ebec;border-radius:8px;overflow:hidden}
.stat{background:#fff;padding:12px 4px;text-align:center}
.stat b{display:block;font-size:20px;font-weight:600;color:#2b3440;line-height:1.25}
.stat span{font-size:11px;color:#8a94a6}
.lines{list-style:none;margin:0;padding:0}
.line{padding:13px 0;border-bottom:1px solid #eff0f1}
.line:last-child{border-bottom:0}
.line-h{display:flex;align-items:center;gap:8px}
.line-h b{font-size:17px;color:#2b3440;font-weight:600}
.line-n{margin-top:4px;font-size:13.5px;color:#8a94a6}
.line-n b{color:#2b3440;font-weight:600}
.tag{font-size:11px;line-height:1;padding:3px 7px;border-radius:9px;background:#f0f2f5;color:#8a94a6}
.tag.up{background:#fdecec;color:#d14343}
.tag.down{background:#eaf6ef;color:#2e9e5b}
.tag.hot{background:#fdf3e3;color:#c87a12}
.drv{list-style:none;margin:0;padding:0}
.drv li{padding:11px 0;border-bottom:1px solid #eff0f1}
.drv li:last-child{border-bottom:0}
.drv b{color:#2b3440;font-weight:600}
.drv .cnt{color:#d14343;font-weight:600;margin-left:6px}
.drv .why{display:block;margin-top:3px;font-size:13.5px;color:#8a94a6}
.drv .ld{display:inline-block;margin-top:5px;font-size:12px;color:#c87a12}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:13.5px}
th{font-weight:600;color:#8a94a6;font-size:11.5px;text-align:right;padding:7px 6px;
  border-bottom:1px solid #e9ebec;background:#fafbfc}
th:nth-child(-n+2){text-align:left}
td{padding:9px 6px;border-bottom:1px solid #eff0f1;vertical-align:top}
td.rk{color:#b3bcc9;font-variant-numeric:tabular-nums}
td.nm{overflow:hidden}
td.nm b{display:block;color:#2b3440;font-weight:600;font-size:14.5px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
td.nm .sub{display:block;font-size:11px;color:#8a94a6;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.num{text-align:right;font-variant-numeric:tabular-nums}
.up{color:#d14343}
.down{color:#2e9e5b}
.hot{color:#c87a12}
.mute{color:#8a94a6}
.hint{font-size:12px;color:#8a94a6;margin:0 0 8px}
footer{margin-top:34px;padding-top:16px;border-top:1px solid #eff0f1;
  font-size:12px;line-height:1.8;color:#98a2b3}
footer a{color:#98a2b3;text-decoration:underline}
@media (max-width:360px){body{font-size:16px}.project-name{font-size:22px}.stat b{font-size:18px}}
@media (prefers-color-scheme:dark){
  body{background:#14171c;color:#c3cad6}
  .stat{background:#14171c}.stat b,.line-h b,td.nm b,.drv b,.line-n b{color:#e6ebf2}
  th{background:#1a1f26;color:#8a94a6}
  .line,.drv li,td,footer,.stats{border-color:#252b33}
}
"""


def render_html(payload: Dict[str, Any], read: Any, page_url: str) -> str:
    """One self-contained page wearing the daily digest's clothes.

    The morning page is a Jekyll Cayman document: a blue-to-green banner, green
    section headings, one white column. The evening brief keeps that, and then
    pays for it on a phone — the matrix is a list rather than a seven-column
    table, because at 430pt a table either shrinks the type or scrolls sideways,
    and both lose the comparison it exists to make.
    """
    kpi = payload.get("kpi") or {}
    matrix = payload.get("matrix") or {}
    day = matrix.get("day") or {}
    lines = matrix.get("lines") or []
    picks = payload.get("filter") or {}
    extra = render_sections(payload)
    date = kpi.get("date") or ""

    line_rows = []
    for l in lines:
        # Two shapes matter after the close: lines that drew limit-ups today,
        # and lines that had them yesterday and lost them. A line dark for two
        # sessions is history, and the page is about tomorrow.
        if l["today"] == 0 and l["prev"] == 0:
            continue
        line_rows.append(
            "<li class='line'>"
            f"<div class='line-h'><b>{_esc(l['line'])}</b>"
            f"<span class='tag {_state_class(l['state'])}'>{_esc(l['state'])}</span></div>"
            f"<div class='line-n'>今日 <b>{l['today']}</b> 家 · 昨日 {l['prev']} 家 · "
            f"日Δ <span class='{_pct_class(str(l['delta1']))}'>{l['delta1']:+d}</span> · "
            f"3日Δ <span class='{_pct_class(str(l['delta3']))}'>{l['delta3']:+d}</span> · "
            f"连续 {l['streak']} 天</div></li>"
        )

    stats = [
        (kpi.get("limit_up"), "涨停"),
        (kpi.get("limit_down"), "跌停"),
        (kpi.get("lianban"), "连板"),
        (kpi.get("max_board"), "最高板"),
        (f"{kpi.get('seal_rate_pct')}%", "封板率"),
        (kpi.get("zhaban"), "炸板"),
        (kpi.get("adv"), "上涨"),
        (kpi.get("dec"), "下跌"),
    ]
    stat_html = "".join(
        f"<div class='stat'><b>{_esc(v)}</b><span>{_esc(k)}</span></div>" for v, k in stats
    )

    pick_blocks = []
    for label, block in picks.items():
        body = []
        for r in block.get("rows", []):
            sub = " · ".join(x for x in [r.get("code") or "", r.get("sector") or ""] if x)
            body.append(
                "<tr>"
                f"<td class='rk'>{_esc(r['rank'])}</td>"
                f"<td class='nm'><b>{_esc(r['name'])}</b>"
                f"<span class='sub'>{_esc(sub)}</span></td>"
                f"<td class='num {_pct_class(r['gain60'])}'>{_esc(r['gain60'])}</td>"
                f"<td class='num {_pct_class(r['from_high60'])}'>{_esc(r['from_high60'])}</td>"
                "</tr>"
            )
        total = block.get("total")
        hint = f"共 {total} 只，免费可见前 5" if total else "前 5 只"
        why = block.get("why") or ""
        pick_blocks.append(
            f"<h2>{_esc(label)}</h2>"
            f"<p class='hint'>{_esc(hint)}{('｜' + _esc(why)) if why else ''}</p>"
            "<table><colgroup><col style='width:26px'><col>"
            "<col style='width:74px'><col style='width:64px'></colgroup>"
            "<thead><tr><th>#</th><th>个股 / 题材</th><th>60日涨幅</th><th>距高点</th></tr></thead>"
            "<tbody>" + "".join(body) + "</tbody></table>"
        )

    drivers = ""
    if day.get("lines"):
        items = "".join(
            f"<li><b>{_esc(x['name'])}</b><span class='cnt'>{x['count']} 家</span>"
            f"<span class='why'>{_esc(x['driver'])}</span>"
            f"<span class='ld'>龙头 {_esc(x['leader'])}</span></li>"
            for x in day["lines"]
        )
        drivers = f"<h2>当日主线与驱动</h2><ul class='drv'>{items}</ul>"

    # The model returns verdicts, not prose blocks: a headline that states the
    # call, six sections that each defend one, and an explicit dissent against
    # the site's own review. The headings come from the model's own answers, so
    # the page shows its reasoning structure rather than a wall of text.
    if isinstance(read, str):
        read = {"headline": "", "sections": [{"h": "", "p": p} for p in read.split("\n") if p.strip()]}
    read = read or {}
    summary_html = ""
    if read.get("sections"):
        parts = []
        if read.get("headline"):
            parts.append(f"<p class='verdict'>{_esc(read['headline'])}</p>")
        for sec in read["sections"]:
            if sec.get("h"):
                parts.append(f"<h3>{_esc(sec['h'])}</h3>")
            parts.append(f"<p>{_esc(sec['p'])}</p>")
        dis = read.get("dissent")
        if isinstance(dis, dict):
            text = str(dis.get("disagree") or dis.get("agree") or "").strip()
        else:
            text = str(dis or "").strip()
        if text:
            parts.append(f"<h3>与连板网复盘的分歧</h3><p>{_esc(text)}</p>")
        summary_html = f"<h2>盘后洞察</h2><div class='read'>{''.join(parts)}</div>"

    top = [l for l in lines if l.get("today", 0) > 0]
    if top:
        lede = (
            f"涨停 {kpi.get('limit_up')} 家、封板率 {kpi.get('seal_rate_pct')}%，"
            f"{kpi.get('emotion_phase') or ''}；最强的是{top[0]['line']}，{top[0]['today']} 家涨停。"
        )
    else:
        lede = (
            f"涨停 {kpi.get('limit_up')} 家、封板率 {kpi.get('seal_rate_pct')}%，"
            f"{kpi.get('emotion_phase') or ''}；今天没有产业线录得涨停。"
        )

    # The model's headline already states the call; printing the script's lede
    # above it would say the same thing twice in the first screenful.
    lede_html = "" if summary_html else f'<p class="lede">{_esc(lede)}</p>'

    mood = kpi.get("emotion_phase") or ""
    degree = day.get("degree")
    mood_text = f"{mood} {degree}°" if degree is not None else mood

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Kenny's Horizon {_esc(date)} 盘后洞察晚报 | Kenny's Horizon</title>
<meta name="description" content="{_esc(lede)}">
<meta property="og:title" content="Horizon 盘后洞察晚报：{_esc(date)}">
<meta property="og:description" content="{_esc(lede)}">
<meta property="og:url" content="{_esc(page_url)}">
<meta name="theme-color" content="#157878">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<style>{_PAGE_CSS}{EXTRA_CSS}</style></head><body>
<header class="page-header">
<h1 class="project-name">Kenny's Horizon {_esc(date)} 盘后洞察晚报</h1>
<h2 class="project-tagline">盘面总结 · 重点信号 · 变动归因 · 趋势展望</h2>
</header>
<main>
{lede_html}
{summary_html}
<h2>盘面</h2>
<div class="stats">{stat_html}</div>
{extra['funds']}
<h2>主线矩阵</h2>
<ul class="lines">{''.join(line_rows)}</ul>
{drivers}
{''.join(pick_blocks)}
{extra['review']}
<footer>
数据来源：<a href="https://lianban.net/mainline.html">连板网 · 主线追踪</a>、
<a href="https://lianban.net/filter.html">一键筛选</a>、
<a href="https://lianban.net/today.html">当日复盘</a>。
行情与题材数据版权归连板网，依 CC BY 4.0 署名引用。<br>
本页由 Horizon 自动生成，涨停家数只说明资金当天在买什么，不构成任何投资建议。
</footer>
</main></body></html>"""


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
