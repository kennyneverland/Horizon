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

SUMMARY_PROMPT = """你是 A 股盘后复盘分析师。根据下面这份当日盘面数据，写一段主线动向研判。

判断规则（连板网口径）：
- {rule}
- 涨停家数只说明资金今天在买什么，不能证明某条新闻驱动了它。不要把"某条消息"写成"某条线涨停的原因"。
- 情绪冰点期意味着整体资金弱，此时单条线的小数量也可能已是全市场最强。

写作要求：
- 输出 3 段，每段 2-3 句，总字数不超过 420 字。
- 第一段：今天的主线是谁。用连续天数和家数变化说明它够不够"主线"资格。
- 第二段：退潮的是谁。昨天强今天弱的，判断是分歧还是结束，给出依据。
- 第三段：明天看什么。给可验证的观察点（比如某条线能否连续第 4 天领先），不要给买卖建议、不要喊点位。
- 不要罗列数字，页面上已经有表；只写判断和依据。
- 直接输出正文，不要标题、不要 markdown 标记。"""


def _compact(payload: Dict[str, Any]) -> str:
    """The numbers, flattened into the shortest text that still carries them."""
    kpi = payload.get("kpi") or {}
    matrix = payload.get("matrix") or {}
    day = matrix.get("day") or {}
    lines = matrix.get("lines") or []
    picks = payload.get("filter") or {}

    out = [
        f"日期 {kpi.get('date')}，情绪 {kpi.get('emotion_phase')}。",
        f"涨停 {kpi.get('limit_up')} 家、跌停 {kpi.get('limit_down')} 家、"
        f"连板 {kpi.get('lianban')} 家、最高 {kpi.get('max_board')} 板、"
        f"封板率 {kpi.get('seal_rate_pct')}%、炸板 {kpi.get('zhaban')} 家，"
        f"上涨 {kpi.get('adv')} 家 / 下跌 {kpi.get('dec')} 家。",
    ]
    if day:
        out.append(
            f"总龙头 {day.get('leader') or '-'} {day.get('leader_badge') or ''}".strip()
        )
    top = [l for l in lines if l.get("today", 0) > 0][:6]
    if top:
        out.append("产业线（今日/昨日/连续天数/状态）：")
        for l in top:
            out.append(
                f"  {l['line']} {l['today']}/{l['prev']}/连{l['streak']}天/{l['state']}"
            )
    if day.get("lines"):
        out.append("当日主线与驱动：")
        for item in day["lines"]:
            out.append(f"  {item['name']} {item['count']}家 · {item['driver']}")
    for label, block in picks.items():
        names = "、".join(
            f"{r['name']}({r['sector']} 60日{r['gain60']} 距高{r['from_high60']})"
            for r in block.get("rows", [])
        )
        if names:
            out.append(f"{label}（共{block.get('total')}只，前5）：{names}")
    return "\n".join(out)


def llm_summary(payload: Dict[str, Any], conf: Dict[str, Any], timeout: float = 120.0) -> str:
    """Ask the model for the written read. A failure returns "" and costs the page only that block."""
    key_env = conf.get("api_key_env") or "DASHSCOPE_API_KEY"
    api_key = os.environ.get(key_env, "").strip()
    if not api_key:
        print(f"no {key_env}; skipping the written read", file=sys.stderr)
        return ""
    url = str(conf.get("base_url") or "").rstrip("/") + "/chat/completions"
    body = {
        "model": conf.get("model") or "qwen3.8-flash",
        "messages": [
            {"role": "system", "content": SUMMARY_PROMPT.format(rule=ROTATION_RULE)},
            {"role": "user", "content": _compact(payload)},
        ],
        "temperature": 0.3,
        "max_tokens": 900,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            doc = json.loads(response.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        print(f"written read failed: {exc}", file=sys.stderr)
        return ""
    try:
        text = doc["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("written read: unexpected response shape", file=sys.stderr)
        return ""
    return str(text or "").strip()


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


def render_html(payload: Dict[str, Any], summary: str, page_url: str) -> str:
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

    summary_html = ""
    if summary:
        paras = "".join(f"<p>{_esc(p)}</p>" for p in summary.split("\n") if p.strip())
        summary_html = f"<h2>今日主线研判</h2><div class='read'>{paras}</div>"

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

    mood = kpi.get("emotion_phase") or ""
    degree = day.get("degree")
    mood_text = f"{mood} {degree}°" if degree is not None else mood

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Kenny's Horizon {_esc(date)} 晚报 | Kenny's Horizon 每日精选新闻速递</title>
<meta name="description" content="{_esc(lede)}">
<meta property="og:title" content="Horizon 晚报：{_esc(date)}">
<meta property="og:description" content="{_esc(lede)}">
<meta property="og:url" content="{_esc(page_url)}">
<meta name="theme-color" content="#157878">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<style>{_PAGE_CSS}{EXTRA_CSS}</style></head><body>
<header class="page-header">
<h1 class="project-name">Kenny's Horizon {_esc(date)} 晚报</h1>
<h2 class="project-tagline">Kenny's Horizon 每日精选新闻速递</h2>
</header>
<main>
<p class="lede">{_esc(lede)}</p>
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


def _short_read(summary: str, limit: int = 220) -> str:
    flat = " ".join(summary.split())
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

    summary = ""
    if not args.no_llm:
        summary = llm_summary(payload, _load_ai_conf(Path(args.config)))

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
    title = f"Horizon 晚报 {date[5:]} {kpi.get('emotion_phase') or ''} {headline}".strip()
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
