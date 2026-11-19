#!/usr/bin/env python3
"""The blocks lianban only renders, and the one thing it publishes for agents.

主线强度、主力资金动向、盘面较前值与外盘参考 exist only in the DOM of today.html —
there is no JSON for any of them — so they are read from a real browser. The
day's review (KPI, themes, and lianban's own write-up) is on the public MCP
endpoint, which is the site's stated machine route and needs no key.

Both halves are optional by construction: a browser that will not start, or an
MCP call that fails, costs its own section and nothing else.

    python scripts/lianban_extra.py --date 2026-11-19
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import urllib.request
from typing import Any, Dict, List, Optional

TODAY_URL = "https://lianban.net/today.html"
MARKET_URL = "https://lianban.net/market.html"
MCP_URL = "https://lianban.net/mcp"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)

# #s-strength: <div class="stc"><div class="t"><span class="nm">芯片</span>
#   <span class="cg mono dn">-2.0%</span></div><div class="bar"><i style="width:100%"></i></div></div>
_STC_RE = re.compile(
    r'<div class="stc">.*?<span class="nm">(.*?)</span>.*?<span class="cg[^"]*">(.*?)</span>.*?'
    r'<div class="bar"><i style="width:(\d+)%"></i></div>',
    re.S,
)
# #zjf: <div class="zc"><div class="zh">板块流入</div>
#   <div class="zr"><b>融资融券</b><i class="up">+0.14%</i><em class="up">+44.34亿</em></div>...
_ZC_RE = re.compile(r'<div class="zc">(.*?)</div></div>', re.S)
# 外盘参考: <div class="ov-group"><span class="ov-label">亚太</span><div class="ov-items">
#   <details class="ov-item"><summary class="ov-main"><span class="ov-name" title="恒生指数">
#   <span aria-hidden="true">恒指</span>...</span><b class="ov-pct dn">-1.95%</b>
_OV_GROUP_RE = re.compile(
    r'<div class="ov-group"><span class="ov-label">(.*?)</span><div class="ov-items">(.*?)</div></div>',
    re.S,
)
_OV_ITEM_RE = re.compile(
    r'<span class="ov-name"[^>]*>.*?<span aria-hidden="true">(.*?)</span>.*?'
    r'<b class="ov-pct (up|dn)">(.*?)</b>',
    re.S,
)
# 盘面格子: <div class="c"><div class="l">涨停</div><div class="v mono">23</div>
#   <div class="ly">较前值 -18</div></div>   （“上涨/下跌”那格多一个 kpi-ad 类）
_PANEL_RE = re.compile(
    r'<div class="c(?: [^"]*)?"><div class="l"[^>]*>(.*?)</div>'
    r'<div class="v[^"]*"[^>]*>(.*?)</div>(?:<div class="ly"[^>]*>(.*?)</div>)?</div>',
    re.S,
)
# 分类指数条: <div class="idxc"><div class="n">上证</div><div class="v dn mono">-0.28%</div></div>
_IDXC_RE = re.compile(
    r'<div class="idxc"><div class="n">(.*?)</div><div class="v (up|dn)[^"]*">(.*?)</div></div>',
    re.S,
)
# 明日推演: 四个 .fst 格子 + 一段历史阶段分布
_FST_RE = re.compile(r'<div class="fst"><b>(.*?)</b><span>(.*?)</span></div>', re.S)
_FC_BASIS_RE = re.compile(r'<b>[^<]*明日推演</b><small>(.*?)</small>', re.S)
_FC_DIST_RE = re.compile(r'<span class="hl"[^>]*>(.*?)</span>', re.S)
# market.html 把 60 个交易日的宽度序列整段嵌在页面里，不需要浏览器
_MK_DATA_RE = re.compile(
    r'<script type="application/json" class="mk-data">(.*?)</script>', re.S
)
_ZH_RE = re.compile(r'<div class="zh">(.*?)</div>')
_ZR_RE = re.compile(
    r'<div class="zr"><b>(.*?)</b><i class="[^"]*">(.*?)</i><em class="[^"]*">(.*?)</em></div>',
    re.S,
)


def _clean(raw: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)).strip()


def render(timeout_ms: int = 60000) -> str:
    """Load today.html in Chromium and return the settled DOM.

    Images, fonts and media are aborted: the two blocks are text, and on a
    runner the difference between a four-second load and a twenty-second one
    is the difference between a job that finishes and one that does not.
    """
    from playwright.sync_api import sync_playwright  # imported late: optional

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1400, "height": 1200}, locale="zh-CN"
        )
        page = context.new_page()
        page.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ("image", "media", "font")
            else route.continue_(),
        )
        page.goto(TODAY_URL, wait_until="domcontentloaded", timeout=timeout_ms)
        # The page fills the two blocks after the fingerprint check clears.
        page.wait_for_selector("#s-strength .stc", timeout=timeout_ms)
        page.wait_for_selector("#zjf .zr", timeout=timeout_ms)
        html = page.content()
        browser.close()
    return html


def parse_strength(page: str) -> List[Dict[str, Any]]:
    """``[{name, pct, bar}]`` — bar is the relative width the site draws, 0-100."""
    out = []
    for name, pct, bar in _STC_RE.findall(page):
        out.append({"name": _clean(name), "pct": _clean(pct), "bar": int(bar)})
    return out


def parse_flows(page: str) -> Dict[str, List[Dict[str, str]]]:
    """``{"板块流入": [{name, pct, amount}], ...}`` in the order the page prints."""
    start = page.find('id="zjf"')
    if start < 0:
        return {}
    block = page[start : start + 12000]
    out: Dict[str, List[Dict[str, str]]] = {}
    for chunk in _ZC_RE.findall(block):
        head = _ZH_RE.search(chunk)
        if not head:
            continue
        rows = [
            {"name": _clean(n), "pct": _clean(p), "amount": _clean(a)}
            for n, p, a in _ZR_RE.findall(chunk)
        ]
        if rows:
            out[_clean(head.group(1))] = rows
    return out


def parse_overseas(page: str) -> List[Dict[str, Any]]:
    """``[{label, items: [{name, pct, up}]}]`` — 隔夜美股与亚太，按页面分组。"""
    out = []
    for label, body in _OV_GROUP_RE.findall(page):
        items = [
            {"name": _clean(n), "pct": _clean(p), "up": cls == "up"}
            for n, cls, p in _OV_ITEM_RE.findall(body)
        ]
        if items:
            out.append({"label": _clean(label), "items": items})
    return out


def parse_panel(page: str) -> List[Dict[str, str]]:
    """``[{label, value, sub}]`` for the KPI strip, in page order.

    The value is de-spaced ("3 板" -> "3板") because the page breaks the unit
    into its own <small>, and a phone wants the number and its unit together.
    """
    out = []
    for label, value, sub in _PANEL_RE.findall(page):
        label = _clean(label)
        if not label or label in {"速览"}:
            continue
        out.append(
            {
                "label": label,
                "value": re.sub(r"\s+", "", _clean(value)),
                "sub": _clean(sub),
            }
        )
    return out


def parse_indices(page: str) -> List[Dict[str, Any]]:
    """``[{name, pct, up}]`` — the six index chips in the header.

    These are the only numbers on the site that say how the *indices* moved, and
    the spread between them is the point: a day where 科创50 rises while 创业板
    falls is a different market from one where everything falls together.
    """
    return [
        {"name": _clean(name), "pct": _clean(pct), "up": cls == "up"}
        for name, cls, pct in _IDXC_RE.findall(page)
    ]


def parse_forecast(page: str) -> Dict[str, Any]:
    """The site's own next-day base rate: same phase, historically, what followed.

    Kept as a separate block rather than folded into the numbers: it is a
    frequency, not a prediction, and the model is asked to argue with it.
    """
    basis = _FC_BASIS_RE.search(page)
    items = [
        {"value": _clean(v), "label": _clean(l)} for v, l in _FST_RE.findall(page)
    ]
    dist = _FC_DIST_RE.search(page)
    if not items and not basis:
        return {}
    out: Dict[str, Any] = {"basis": _clean(basis.group(1)) if basis else ""}
    for item in items:
        label = item["label"]
        if "上涨占比" in label:
            out["up_share_next_day"] = item["value"]
        elif "均值" in label and "上证" in label:
            out["mean_next_day"] = item["value"]
        elif "最常见次日阶段" in label:
            out["common_next_phase"] = item["value"]
        elif "温差" in label:
            out["mean_degree_change"] = item["value"]
    if dist:
        out["next_phase_distribution"] = _clean(dist.group(1))
    return out


def _pct_rank(values: List[float], x: float) -> Optional[float]:
    """Where today sits inside the window, 0-100. Higher = higher value."""
    vals = [v for v in values if isinstance(v, (int, float))]
    if not vals or not isinstance(x, (int, float)):
        return None
    return round(sum(1 for v in vals if v <= x) / len(vals) * 100, 1)


def market_breadth(timeout: float = 30.0) -> Dict[str, Any]:
    """Sixty sessions of breadth, so today's numbers arrive with a distribution.

    ``up_ratio`` alone is a fact; ``up_ratio`` at the 2nd percentile of sixty
    sessions is a signal. That difference is the whole reason this block exists.
    """
    request = urllib.request.Request(
        MARKET_URL, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    page = body.decode("utf-8", "replace")
    hit = _MK_DATA_RE.search(page)
    if not hit:
        raise ValueError("market.html carries no mk-data block")
    rows = (json.loads(hit.group(1)) or {}).get("rows") or []
    if not rows:
        raise ValueError("mk-data block is empty")

    today = rows[-1]
    def series(key: str) -> List[float]:
        return [r.get(key) for r in rows if isinstance(r.get(key), (int, float))]

    amt = today.get("amt")
    amt20 = today.get("amt_ma20")
    recent = []
    for row in rows[-5:]:
        recent.append(
            {
                "date": str(row.get("date") or "")[5:],
                "up_ratio_pct": row.get("up_ratio"),
                "turnover_yi": row.get("amt"),
                "above_ma20_pct": row.get("above_ma20"),
                "new_low": row.get("nl"),
            }
        )
    return {
        "window_sessions": len(rows),
        "today": {
            "up_ratio_pct": today.get("up_ratio"),
            "turnover_yi": amt,
            "turnover_ma20_yi": amt20,
            "turnover_vs_ma20_pct": round((amt / amt20 - 1) * 100, 1) if amt and amt20 else None,
            "above_ma20_pct": today.get("above_ma20"),
            "above_ma50_pct": today.get("above_ma50"),
            "above_ma200_pct": today.get("above_ma200"),
            "new_high_63": today.get("nh"),
            "new_low_63": today.get("nl"),
            "new_high_250": today.get("nh250"),
            "new_low_250": today.get("nl250"),
            "stage2_pct": today.get("stage2"),
            "stage4_pct": today.get("stage4"),
        },
        # 0-100. For 新低 与 stage4（下跌阶段占比），越高越差——prompt 里说明。
        "pct_rank_60d": {
            "up_ratio": _pct_rank(series("up_ratio"), today.get("up_ratio")),
            "turnover": _pct_rank(series("amt"), amt),
            "above_ma20": _pct_rank(series("above_ma20"), today.get("above_ma20")),
            "new_low_63": _pct_rank(series("nl"), today.get("nl")),
            "stage4": _pct_rank(series("stage4"), today.get("stage4")),
        },
        "recent5": recent,
    }


def collect_extra(timeout_ms: int = 60000) -> Dict[str, Any]:
    """Everything the pages carry that is not in a JSON feed.

    Two independent halves: market.html is static and parsed over plain HTTP;
    today.html needs a browser. Either can fail alone — the caller degrades one
    section, not the whole brief.
    """
    out: Dict[str, Any] = {}
    try:
        out["breadth"] = market_breadth()
    except Exception as exc:  # noqa: BLE001
        out["breadth_error"] = f"{type(exc).__name__}: {exc}"
    try:
        page = render(timeout_ms)
    except Exception as exc:  # noqa: BLE001 - the page degrades, the run does not
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out
    strength = parse_strength(page)
    flows = parse_flows(page)
    panel = parse_panel(page)
    overseas = parse_overseas(page)
    if not strength and not flows:
        out["error"] = "rendered page had neither block"
        return out
    out.update(
        {
            "strength": strength,
            "flows": flows,
            "panel": panel,
            "overseas": overseas,
            "indices": parse_indices(page),
            "forecast": parse_forecast(page),
        }
    )
    return out


def _rpc(payload: Dict[str, Any], session: Optional[str] = None, timeout: float = 40.0):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session:
        headers["Mcp-Session-Id"] = session
    request = urllib.request.Request(
        MCP_URL, data=json.dumps(payload).encode("utf-8"), headers=headers
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        sid = response.headers.get("Mcp-Session-Id") or session
        raw = response.read().decode("utf-8", "replace")
    if not raw.strip():
        return {}, sid
    if raw.startswith(("event:", "data:")):
        for line in raw.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                break
    return json.loads(raw), sid


def mcp_review(date: str, timeout: float = 45.0) -> Dict[str, Any]:
    """The day's review from lianban's own MCP endpoint — the sanctioned route.

    Returns the site's themes and its own written review, so the page can show a
    second opinion next to ours. Anonymous access covers the recent sessions
    only; an older date returns an error and costs the section.
    """
    try:
        _, sid = _rpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "horizon", "version": "0.1"},
                },
            },
            timeout=timeout,
        )
        try:
            _rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid, timeout)
        except Exception:  # noqa: BLE001 - the server answers 202 with no body
            pass
        doc, _ = _rpc(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "get_daily_review", "arguments": {"date": date}},
            },
            sid,
            timeout,
        )
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}

    content = (doc.get("result") or {}).get("content") or []
    if not content:
        return {"error": (doc.get("error") or {}).get("message") or "empty MCP result"}
    try:
        body = json.loads(content[0].get("text") or "{}")
    except ValueError:
        return {"error": "MCP returned non-JSON text"}
    return {
        "status": body.get("status"),
        "status_label": body.get("status_label"),
        "updated_at": body.get("updated_at"),
        "themes": body.get("themes") or [],
        "ai_review": body.get("ai_review") or "",
        "page": body.get("page") or "",
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="lianban extras: strength, flows, MCP review")
    parser.add_argument("--date", default="")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    if not args.no_browser:
        extra = collect_extra()
        print(json.dumps(extra, ensure_ascii=False)[:800])
    if args.date:
        print(json.dumps(mcp_review(args.date), ensure_ascii=False)[:800])
    return 0


# ---------------------------------------------------------------------------
# Rendering. Kept here so post_market.py stays about the page it already had:
# it asks for two blocks of HTML and places them.

EXTRA_CSS = """
.stg{display:grid;grid-template-columns:repeat(2,1fr);gap:12px 16px}
.st-h{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-size:14px}
.st-h span{color:#2b3440;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.st-h b{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums}
.st-bar{height:4px;background:#eff0f1;border-radius:2px;margin-top:5px;overflow:hidden}
.st-bar i{display:block;height:100%;background:#159957;border-radius:2px}
.zjg{display:grid;grid-template-columns:repeat(2,1fr);gap:16px 18px}
.zc .zh{font-size:12px;color:#8a94a6;margin-bottom:2px}
.zr{display:flex;align-items:baseline;gap:6px;padding:5px 0;border-bottom:1px solid #f4f6f8;font-size:13px}
.zn{flex:1;min-width:0;color:#2b3440;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.zr b{font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap}
.zp{width:46px;text-align:right;font-size:11px;color:#98a2b3;font-variant-numeric:tabular-nums}
.quote{border-left:3px solid #d9dee7;padding:2px 0 2px 14px;color:#4c5866;font-size:15px}
.chg{font-size:12.5px;color:#8a94a6;margin:0 0 12px;line-height:1.9}
.chg b{font-weight:600}
.det{display:grid;grid-template-columns:repeat(2,1fr);gap:12px 16px}
.det .d span{display:block;font-size:12px;color:#8a94a6}
.det .d b{display:block;font-size:15.5px;color:#2b3440;font-weight:600;font-variant-numeric:tabular-nums}
.det .d i{display:block;font-style:normal;font-size:11.5px;color:#98a2b3}
.ovg{display:flex;flex-direction:column;gap:10px}
.ovr{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.ovl{width:100%;font-size:12px;color:#8a94a6}
.chip{display:inline-flex;align-items:baseline;gap:4px;padding:3px 8px;border:1px solid #e9ebec;border-radius:6px;font-size:12.5px}
.chip i{font-style:normal;color:#4c5866}
.chip b{font-weight:600;font-variant-numeric:tabular-nums}
@media (max-width:360px){.zjg{grid-template-columns:1fr}}
"""


def _esc(value: Any) -> str:
    import html as _html

    return _html.escape(str(value if value is not None else ""))


def _pct_class(raw: str) -> str:
    text = str(raw or "").strip()
    return "up" if text.startswith("+") else ("down" if text.startswith("-") else "")


def _panel_html(payload: Dict[str, Any]) -> str:
    """The strip above the fold: what moved versus yesterday, and the breadth
    numbers the KPI grid has no room for."""
    panel = {
        x["label"].replace(" ", ""): x for x in ((payload.get("extra") or {}).get("panel") or [])
    }
    if not panel:
        return ""

    changes = []
    for label in ("涨停", "跌停", "连板", "最高板", "封板率"):
        row = panel.get(label)
        if not row or not row["sub"].startswith("较前值"):
            continue
        delta = row["sub"].replace("较前值", "").strip()
        changes.append(f"{label} <b class='{_pct_class(delta)}'>{_esc(delta)}</b>")
    zb = panel.get("炸板")
    if zb and zb["sub"]:
        changes.append(f"炸板{_esc(zb['sub'])}")

    rows = []
    for label in ("昨涨停今表现", "情绪周期", "新高/新低63日", "两市成交", "融资余额11-18"):
        row = panel.get(label)
        if not row:
            continue
        rows.append(
            "<div class='d'>"
            f"<span>{_esc(label)}</span>"
            f"<b class='{_pct_class(row['value'])}'>{_esc(row['value'])}</b>"
            f"<i>{_esc(row['sub'])}</i></div>"
        )
    breadth = panel.get("上涨/下跌")
    if breadth:
        # 涨跌家数已经在上面那格里了，这里只补它带不动的两个比值。
        trin = re.search(r"TRIN\s*([0-9.]+)", breadth["sub"])
        red = re.search(r"红盘\s*([0-9]+%)", breadth["sub"])
        bits = [x for x in [red.group(1) if red else "", trin.group(1) if trin else ""] if x]
        if bits:
            rows.append(
                "<div class='d'><span>红盘 / TRIN</span>"
                f"<b>{_esc(' / '.join(bits))}</b><i>红盘占比 / 涨跌成交额比</i></div>"
            )

    html = ""
    if changes:
        html += f"<p class='chg'>较前值：{' · '.join(changes)}</p>"
    if rows:
        html += f"<div class='det'>{''.join(rows)}</div>"
    return html


def _funds_html(payload: Dict[str, Any]) -> str:
    extra = payload.get("extra") or {}
    strength = extra.get("strength") or []
    flows = extra.get("flows") or {}
    out = [_panel_html(payload)]

    if strength:
        chips = "".join(
            "<div class='st'>"
            f"<div class='st-h'><span>{_esc(x['name'])}</span>"
            f"<b class='{_pct_class(x['pct'])}'>{_esc(x['pct'])}</b></div>"
            f"<div class='st-bar'><i style='width:{max(2, min(100, int(x['bar'])))}%'></i></div>"
            "</div>"
            for x in strength
        )
        out.append(
            "<h2>主线强度</h2><p class='hint'>资金强度排名 · 条长=相对强度</p>"
            f"<div class='stg'>{chips}</div>"
        )

    if flows:
        cols = []
        for label, rows in flows.items():
            body = "".join(
                f"<div class='zr'><span class='zn'>{_esc(r['name'])}</span>"
                f"<b class='{_pct_class(r['amount'])}'>{_esc(r['amount'])}</b>"
                f"<span class='zp'>{_esc(r['pct'])}</span></div>"
                for r in rows[:5]
            )
            cols.append(f"<div class='zc'><div class='zh'>{_esc(label)}</div>{body}</div>")
        out.append(
            "<h2>主力资金动向</h2><p class='hint'>板块与个股主力净额 · 收盘定格</p>"
            f"<div class='zjg'>{''.join(cols)}</div>"
        )
    return "".join(out)


def _review_html(payload: Dict[str, Any]) -> str:
    doc = payload.get("lianban") or {}
    text = (doc.get("ai_review") or "").strip()
    if not text:
        return ""
    first = text.split("\n\n")[0].strip()
    if len(first) > 280:
        first = first[:280].rstrip() + "…"
    page = doc.get("page") or ""
    link = f"<a href='{_esc(page)}'>查看原文</a>" if page else ""
    return (
        "<h2>连板网复盘</h2>"
        f"<div class='quote'>{_esc(first)}</div>"
        f"<p class='hint'>连板网原文摘录，非本页判断{' · ' + link if link else ''}</p>"
        + _overseas_html(payload)
    )


def _overseas_html(payload: Dict[str, Any]) -> str:
    """隔夜美股与亚太：不解释今天，只交代明天开盘前的外部底色。"""
    groups = (payload.get("extra") or {}).get("overseas") or []
    if not groups:
        return ""
    rows = []
    for group in groups:
        chips = "".join(
            f"<span class='chip'><i>{_esc(x['name'])}</i>"
            f"<b class='{'up' if x['up'] else 'down'}'>{_esc(x['pct'])}</b></span>"
            for x in group["items"]
        )
        rows.append(f"<div class='ovr'><span class='ovl'>{_esc(group['label'])}</span>{chips}</div>")
    return (
        "<h2>外盘参考</h2><p class='hint'>隔夜美股与亚太收盘 · 报价时间见连板网明细</p>"
        f"<div class='ovg'>{''.join(rows)}</div>"
    )


def render_sections(payload: Dict[str, Any]) -> Dict[str, str]:
    """``{"funds": ..., "review": ...}`` — empty strings when a source is missing."""
    try:
        funds = _funds_html(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"funds render failed: {exc}", file=sys.stderr)
        funds = ""
    try:
        review = _review_html(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"review render failed: {exc}", file=sys.stderr)
        review = ""
    return {"funds": funds, "review": review}


if __name__ == "__main__":
    sys.exit(main())
