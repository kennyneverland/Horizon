#!/usr/bin/env python3
"""The two things lianban only renders, and the one thing it publishes for agents.

主线强度 and 主力资金动向 exist only in the DOM of today.html — there is no JSON
for either — so they are read from a real browser. The day's review (KPI, themes,
and lianban's own write-up) is on the public MCP endpoint, which is the site's
stated machine route and needs no key.

Both halves are optional by construction: a browser that will not start, or an
MCP call that fails, costs its own section and nothing else.

    python scripts/lianban_extra.py --date 2026-11-19
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from typing import Any, Dict, List, Optional

TODAY_URL = "https://lianban.net/today.html"
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


def collect_extra(timeout_ms: int = 60000) -> Dict[str, Any]:
    """The browser half. Never raises: a failure is reported, not propagated."""
    try:
        page = render(timeout_ms)
    except Exception as exc:  # noqa: BLE001 - the page degrades, the run does not
        return {"error": f"{type(exc).__name__}: {exc}"}
    strength = parse_strength(page)
    flows = parse_flows(page)
    if not strength and not flows:
        return {"error": "rendered page had neither block"}
    return {"strength": strength, "flows": flows}


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
@media (max-width:360px){.zjg{grid-template-columns:1fr}}
"""


def _esc(value: Any) -> str:
    import html as _html

    return _html.escape(str(value if value is not None else ""))


def _pct_class(raw: str) -> str:
    text = str(raw or "").strip()
    return "up" if text.startswith("+") else ("down" if text.startswith("-") else "")


def _funds_html(payload: Dict[str, Any]) -> str:
    extra = payload.get("extra") or {}
    strength = extra.get("strength") or []
    flows = extra.get("flows") or {}
    out = []

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
