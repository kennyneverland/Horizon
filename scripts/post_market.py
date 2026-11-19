#!/usr/bin/env python3
"""Post-close brief: the mainline matrix, the screened names, and a written read.

The morning digest answers "what happened". This one answers "where did the money
go today, and is that direction still alive tomorrow" — a question the matrix
alone cannot answer, because a count says a line was bought and nothing about
whether it was bought for the third day running.

Three sources, all public and all read with the standard library:

  mainline.html   the 10-day matrix, the session's 情绪, and each line's driver
  opendata/       the site's own KPI block (limit-ups, seal rate, breadth)
  filter.html     the three screening templates' top five, with 60-day gain

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


def render_html(payload: Dict[str, Any], summary: str, page_url: str) -> str:
    """One self-contained page: no external CSS, no JS, readable inside WeChat."""
    kpi = payload.get("kpi") or {}
    matrix = payload.get("matrix") or {}
    day = matrix.get("day") or {}
    lines = matrix.get("lines") or []
    picks = payload.get("filter") or {}
    date = kpi.get("date") or ""

    rows = []
    for l in lines:
        # Two shapes matter after the close: lines that drew limit-ups today,
        # and lines that had them yesterday and lost them. A line dark for two
        # sessions is history, and the page is about tomorrow.
        if l["today"] == 0 and l["prev"] == 0:
            continue
        rows.append(
            "<tr>"
            f"<td class='mute'>{l['rank']}</td>"
            f"<td class='name'>{_esc(l['line'])}</td>"
            f"<td class='num'>{l['today']}<span class='prev'>/{l['prev']}</span></td>"
            f"<td class='num {_pct_class(str(l['delta1']))}'>{l['delta1']:+d}</td>"
            f"<td class='num {_pct_class(str(l['delta3']))}'>{l['delta3']:+d}</td>"
            f"<td class='num'>{l['streak']}</td>"
            f"<td class='{_state_class(l['state'])}'>{_esc(l['state'])}</td>"
            "</tr>"
        )

    pick_blocks = []
    for label, block in picks.items():
        body = []
        for r in block.get("rows", []):
            body.append(
                "<tr>"
                f"<td class='mute'>{_esc(r['rank'])}</td>"
                f"<td class='name'>{_esc(r['name'])}"
                f"<span class='code'>{_esc(r['code'])}</span>"
                f"<span class='sector'>{_esc(r['sector'])}</span></td>"
                f"<td class='num {_pct_class(r['gain60'])}'>{_esc(r['gain60'])}</td>"
                f"<td class='num {_pct_class(r['from_high60'])}'>{_esc(r['from_high60'])}</td>"
                "</tr>"
            )
        total = block.get("total")
        hint = f"共 {total} 只，免费可见前 5" if total else "前 5 只"
        pick_blocks.append(
            f"<div class='card'><div class='card-h'><b>{_esc(label)}</b>"
            f"<span class='mute'>{_esc(hint)}</span></div>"
            f"<div class='why'>{_esc(block.get('why', ''))}</div>"
            "<div class='scroll'><table><thead><tr>"
            "<th>#</th><th>个股 / 题材</th><th>60日涨幅</th><th>距高点</th>"
            "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div></div>"
        )

    drivers = ""
    if day.get("lines"):
        items = "".join(
            f"<li><b>{_esc(x['name'])}</b> <span class='num'>{x['count']}家</span>"
            f"<span class='drv'>{_esc(x['driver'])}</span>"
            f" <span class='ld'>{_esc(x['leader'])}</span></li>"
            for x in day["lines"]
        )
        drivers = f"<div class='card'><div class='card-h'><b>当日主线与驱动</b></div><ul class='drvlist'>{items}</ul></div>"

    summary_html = ""
    if summary:
        paras = "".join(f"<p>{_esc(p)}</p>" for p in summary.split("\n") if p.strip())
        summary_html = f"<section class='read'><h2>主线动向</h2>{paras}</section>"

    mood = kpi.get("emotion_phase") or ""
    degree = day.get("degree")
    mood_text = f"{mood} {degree}°" if degree is not None else mood

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>盘后总结 {_esc(date)}</title>
<style>
:root{{--bg:#f6f7f9;--fg:#1b1f27;--mute:#8a94a6;--line:#e3e6ec;--up:#d14343;--down:#2e9e5b;--hot:#e08a1e;--card:#fff}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}}
.wrap{{max-width:760px;margin:0 auto;padding:16px 14px 40px}}
header{{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:4px 0 14px}}
header h1{{font-size:20px;margin:0}}
.badge{{font-size:12px;padding:2px 8px;border-radius:10px;background:#eef1f6;color:var(--mute)}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px}}
.kpi{{background:var(--card);border-radius:10px;padding:10px 8px;text-align:center;border:1px solid var(--line)}}
.kpi b{{display:block;font-size:19px;line-height:1.3}}
.kpi span{{font-size:11px;color:var(--mute)}}
.read{{background:var(--card);border:1px solid var(--line);border-left:3px solid #3b6fd4;border-radius:10px;padding:14px 16px;margin-bottom:16px}}
.read h2{{font-size:15px;margin:0 0 8px;color:#3b6fd4}}
.read p{{margin:0 0 10px}}
.read p:last-child{{margin-bottom:0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:14px}}
.card-h{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px}}
.card-h span{{font-size:12px;color:var(--mute)}}
.why{{font-size:12px;color:var(--mute);margin-bottom:8px}}
.scroll{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}}
th{{text-align:right;font-weight:500;color:var(--mute);font-size:12px;padding:6px 8px;border-bottom:1px solid var(--line)}}
th:nth-child(-n+2),td:nth-child(-n+2){{text-align:left}}
td{{padding:6px 8px;border-bottom:1px solid #f0f2f5}}
tr:last-child td{{border-bottom:0}}
.name{{font-weight:600;max-width:200px;overflow:hidden;text-overflow:ellipsis}}
.code{{font-size:11px;color:var(--mute);margin-left:5px;font-weight:400}}
.sector{{font-size:11px;color:var(--mute);margin-left:6px;font-weight:400}}
.prev{{font-size:11px;color:var(--mute);font-weight:400}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.up{{color:var(--up)}}
.down{{color:var(--down)}}
.hot{{color:var(--hot);font-weight:600}}
.mute{{color:var(--mute)}}
.drvlist{{list-style:none;margin:0;padding:0}}
.drvlist li{{padding:7px 0;border-bottom:1px solid #f0f2f5}}
.drvlist li:last-child{{border-bottom:0}}
.drv{{color:var(--mute);font-size:13px;margin-left:4px}}
.ld{{font-size:12px;color:var(--hot);margin-left:6px;white-space:nowrap}}
footer{{font-size:11px;color:var(--mute);line-height:1.8;margin-top:20px;border-top:1px solid var(--line);padding-top:12px}}
footer a{{color:var(--mute)}}
@media(max-width:480px){{.kpis{{grid-template-columns:repeat(4,1fr)}}.kpi b{{font-size:16px}}.kpi span{{font-size:10px}}}}
</style></head><body><div class="wrap">
<header><h1>盘后总结 {_esc(date)}</h1><span class="badge">{_esc(mood_text)}</span></header>

{summary_html}

<section class="kpis">
<div class="kpi"><b>{_esc(kpi.get('limit_up'))}</b><span>涨停</span></div>
<div class="kpi"><b>{_esc(kpi.get('limit_down'))}</b><span>跌停</span></div>
<div class="kpi"><b>{_esc(kpi.get('lianban'))}</b><span>连板</span></div>
<div class="kpi"><b>{_esc(kpi.get('max_board'))}</b><span>最高板</span></div>
<div class="kpi"><b>{_esc(kpi.get('seal_rate_pct'))}%</b><span>封板率</span></div>
<div class="kpi"><b>{_esc(kpi.get('zhaban'))}</b><span>炸板</span></div>
<div class="kpi"><b>{_esc(kpi.get('adv'))}</b><span>上涨</span></div>
<div class="kpi"><b>{_esc(kpi.get('dec'))}</b><span>下跌</span></div>
</section>

<div class="card"><div class="card-h"><b>主线矩阵</b><span>近 10 个交易日涨停家数</span></div>
<div class="scroll"><table><thead><tr>
<th>#</th><th>产业线</th><th>今日/昨</th><th>日Δ</th><th>3日Δ</th><th>连</th><th>状态</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></div></div>

{drivers}

{''.join(pick_blocks)}

<footer>
数据来源：<a href="https://lianban.net/mainline.html">连板网 · 主线追踪</a>、
<a href="https://lianban.net/filter.html">一键筛选</a>、
<a href="https://lianban.net/days/{_esc(date)}.html">当日复盘</a>。
行情与题材数据版权归连板网，依 CC BY 4.0 署名引用。
本页由 Horizon 自动生成，涨停家数只说明资金当天在买什么，不构成任何投资建议。
</footer>
</div></body></html>"""


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


def collect() -> Dict[str, Any]:
    """Fetch the three public sources and parse them into one payload.

    Each source is allowed to fail on its own: a page that will not load costs
    its section, not the whole brief.
    """
    payload: Dict[str, Any] = {"matrix": {}, "kpi": {}, "filter": {}, "errors": []}
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
    parser.add_argument("--no-push", action="store_true", help="write the page, do not push")
    args = parser.parse_args(argv)

    payload = collect()
    for err in payload["errors"]:
        print(f"source failed: {err}", file=sys.stderr)
    matrix = payload["matrix"]
    kpi = payload["kpi"]
    date = args.date or kpi.get("date") or (matrix.get("dates") or [""])[0]
    if not date:
        print("no date from any source; aborting", file=sys.stderr)
        return 2
    payload["date"] = date

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
    title = f"盘后 {date[5:]} {kpi.get('emotion_phase') or ''} {headline}".strip()
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