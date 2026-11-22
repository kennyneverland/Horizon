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
from urllib.parse import urlencode

try:  # httpx 由 workflow 装上；缺失时退回 urllib，不让整篇因为一个可选块崩掉
    import httpx
except ImportError:  # pragma: no cover - 只在依赖没装时走到
    httpx = None

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
# 当日主线卡: <div class="zxc"><div class="r1"><b>光刻机（胶）</b>
#   <span class="n mono zxn" data-m="zxm0" ...>涨停11家 ▾</span>
#   <span class="ld" data-stk="603030" data-nm="全筑股份">龙头 全筑股份<i class="mono">3连板</i></span>
#   </div><div class="rs">英伟达宣布…</div></div>
_ZXC_RE = re.compile(
    r'<div class="zxc"><div class="r1"><b>(.*?)</b>(.*?)</div><div class="rs">(.*?)</div>', re.S
)
# 逐只明细（点开「涨停11家 ▾」才显示的那块）:
#   <div id="zxm0" style="display:none"><div class="zmnote">…</div>
#   <div class="zmg"><i class="zmt">芯片 · 11家</i><div class="zms">
#   <span class="wc" data-stk="603030" data-nm="全筑股份"><b>全筑股份</b>
#   <em class="mono md">3连板</em><i class="wsub">光刻机</i></span>…</div></div></div>
_ZXM_RE = re.compile(
    r'<div id="(zxm\d+)"[^>]*>(.*?)(?=<div id="zxm|</div></div><div class="zmfoot"|$)', re.S
)
_ZMT_RE = re.compile(r'<i class="zmt">(.*?)</i>', re.S)
_ZMS_RE = re.compile(r'<div class="zms">(.*)', re.S)
_WC_RE = re.compile(
    r'<span class="wc" data-stk="(\d{6})" data-nm="([^"]*)">(.*?)</span>', re.S
)
# 板块行是 <div class="zr">，个股行多两个属性：<div class="zr" data-stk="688981"
# data-nm="中芯国际">。只匹配无属性写法会把个股流入/流出整块丢掉。
# 块末行的 </div> 会被切块边界吞掉，所以结束标签写成可选。
_ZR_RE = re.compile(
    r'<div class="zr"[^>]*><b>(.*?)</b><i class="[^"]*">(.*?)</i><em class="[^"]*">(.*?)</em>(?:</div>)?',
    re.S,
)


def _clean(raw: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)).strip()


def _prev_value(value: str, delta: str) -> str:
    """今日值 − 变化量 = 昨日值，单位只从今日值取。

    面板的 value 是 "28"、"5板"、"80%"，delta 是 "+5"、"+1板"、"+31.1点"：
    封板率的变化单位是「点」而今日值是「%」，所以单位不能跟着 delta 走。
    """
    vm = re.search(r"-?\d+(?:\.\d+)?", str(value or ""))
    dm = re.search(r"[-+]?\d+(?:\.\d+)?", str(delta or ""))
    if not vm or not dm:
        return ""
    prev = float(vm.group(0)) - float(dm.group(0))
    unit = re.sub(r"[-+]?\d+(?:\.\d+)?", "", str(value)).strip()
    num = str(int(prev)) if abs(prev - round(prev)) < 1e-9 else f"{prev:.1f}"
    return f"{num}{unit}"


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


DAY_URL = "https://lianban.net/days/{date}.html"

# 今日信号面：一条一个 .sgr，左边是彩色标签，右边是说明。说明在页面里就已经
# 被截断（以 … 结尾），抓下来就是读者看到的长度，没有更长的版本可取。
_SIG_RE = re.compile(
    r'<div class="sgr">\s*<i class="wchip[^"]*">(.*?)</i>\s*<em>(.*?)</em>',
    re.S,
)

# ``.sgr`` 的 <em> 是列表里的省略版（结尾固定带「…」），全文在同页折叠的
# ``.topwarn`` 浮层里：<b> 是标题、<span> 是完整正文。默认 display:none，
# 但 page.content() 照样带出来，正则能读到。
_SIG_FULL_RE = re.compile(
    r'<div[^>]*class="topwarn[^"]*"[^>]*>\s*<b>(.*?)</b>\s*<span>(.*?)</span>',
    re.S,
)


def render_day(date: str, timeout_ms: int = 60000) -> str:
    """Load ``/days/<date>.html`` and return the settled DOM.

    The 今日信号面 block exists in no JSON feed — not in opendata, not in the
    MCP payload — and the page builds it after its fingerprint check, so a plain
    HTTP fetch returns the 6 KB shell with the block absent. Chromium is the
    only route to it.
    """
    from playwright.sync_api import sync_playwright  # imported late: optional

    url = DAY_URL.format(date=date)
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
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        # state="attached"：这一块在页面上是折叠的（元素存在但不可见），
        # 等 visible 会一直等到超时。
        page.wait_for_selector(".aisig .sgr", state="attached", timeout=timeout_ms)
        html = page.content()
        browser.close()
    return html


def parse_signals(page: str) -> List[Dict[str, str]]:
    """``[{chip, text}]`` — the signal rows in the order the page prints them.

    ``chip`` keeps its emoji: it is the colour coding the site uses (🔴 risk /
    🔵 setup / ❄️ defence) and the only thing separating the three rows at a
    glance.
    """
    out: List[Dict[str, str]] = []
    # 先取折叠浮层里的全文；取不到再退回列表里的省略版，至少不丢这一块。
    for chip, text in _SIG_FULL_RE.findall(page):
        name, body = _clean(chip), _clean(text)
        if name and body:
            out.append({"chip": name, "text": body})
    if out:
        return out
    for chip, text in _SIG_RE.findall(page):
        name, body = _clean(chip), _clean(text)
        if name and body:
            out.append({"chip": name, "text": body})
    return out


def parse_strength(page: str) -> List[Dict[str, Any]]:
    """``[{name, pct, bar}]`` — bar is the relative width the site draws, 0-100."""
    out = []
    for name, pct, bar in _STC_RE.findall(page):
        out.append({"name": _clean(name), "pct": _clean(pct), "bar": int(bar)})
    return out


def parse_flows(page: str) -> Dict[str, List[Dict[str, str]]]:
    """``{"板块流入": [{name, pct, amount}], ...}`` in the order the page prints.

    页面 #zjf 下有四个块：板块流入、板块流出、个股流入、个股流出，每块八行。
    四组都取，顺序照页面，不在这里截断。
    """
    start = page.find('id="zjf"')
    if start < 0:
        return {}
    block = page[start : start + 12000]
    # 按标题切段，而不是按 <div class="zc">…</div></div> 匹配：后者会把每块最后
    # 一行的 </div> 当成块结束符，末行永远读不到（实测每组 8 行只出 7 行）。
    heads = [
        (m.start(), _clean(m.group(1)))
        for m in re.finditer(r'<div class="zh">(.*?)</div>', block)
    ]
    out: Dict[str, List[Dict[str, str]]] = {}
    for idx, (pos, label) in enumerate(heads):
        if idx + 1 < len(heads):
            end = heads[idx + 1][0]
        else:
            tail = block[pos:]
            m = re.search(r"</div></div>", tail)
            end = pos + (m.end() if m else len(tail))
        seg = block[pos:end]
        rows = [
            {"name": _clean(n), "pct": _clean(p), "amount": _clean(a)}
            for n, p, a in _ZR_RE.findall(seg)
        ]
        if rows and label:
            out[label] = rows
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


_EM_ULIST = "https://push2.eastmoney.com/api/qt/ulist.np/get"
_EM_KLINE = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
# 东财 ulist：f3 是涨跌幅×100，f12 是代码（不含市场号）
_EM_ASIA = (("恒指", "100.HSI"), ("恒科", "124.HSTECH"), ("日经", "100.N225"), ("韩国", "100.KS11"))
_SINA_HQ = "https://hq.sinajs.cn/list="
_SINA_US = (("道指", "gb_dji"), ("标普", "gb_inx"), ("纳综", "gb_ixic"))
# hf_ 是外盘期货连续：0 最新、7 昨收，涨跌幅自己算
_SINA_FUT = (("纳指期", "hf_NQ"), ("标普期", "hf_ES"))


def _overseas_get(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 20.0) -> str:
    """东财会掐掉 urllib 的默认指纹（RemoteDisconnected），httpx 才放行。

    workflow 里装了 httpx；万一环境里没有，退回 urllib 尽力取一次。取不到由
    调用方按「宁缺不错」处理，不让整篇因为一个可选块崩掉。
    """
    hdrs = headers or {"User-Agent": UA}
    if httpx is not None:
        with httpx.Client(timeout=timeout, headers=hdrs) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
    request = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        body = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return body.decode("utf-8", "replace")


def _pct(value: float) -> str:
    return f"{value:+.2f}%"


def _asia_on(date: str) -> List[Dict[str, Any]]:
    """按目标日期取亚太四个指数的收盘涨跌幅。

    重跑历史日期时实时接口对不上：那天早收盘了，ulist 返回的 f3 是空的，整组
    被过滤掉，页面上就只剩美股。这里改走 K 线，beg=end=当天，只取 f51（日期）
    与 f59（涨跌幅）。拿不到那天的就跳过，宁缺不错。
    """
    day = date.replace("-", "")
    items: List[Dict[str, Any]] = []
    for name, secid in _EM_ASIA:
        query = urlencode(
            {
                "secid": secid,
                "klt": 101,
                "fqt": 1,
                "beg": day,
                "end": day,
                "fields1": "f1,f2,f3",
                "fields2": "f51,f59",
            }
        )
        try:
            raw = _overseas_get(
                f"{_EM_KLINE}?{query}",
                headers={"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"},
            )
            klines = (json.loads(raw).get("data") or {}).get("klines") or []
        except Exception as exc:  # noqa: BLE001 - 少一个指数不该拖垮整块
            print(f"overseas({name}@{date}) failed: {exc}", file=sys.stderr)
            continue
        if not klines:
            continue
        parts = str(klines[-1]).split(",")
        if len(parts) < 2 or not parts[0].startswith(date):
            continue
        try:
            value = float(parts[1])
        except ValueError:
            continue
        items.append({"name": name, "pct": _pct(value), "up": value >= 0})
    return items


def fetch_overseas(date: str = "") -> List[Dict[str, Any]]:
    """外盘参考：亚太走东财，前夜美股与期指走新浪 hq。

    原先是解析连板网当天页面的 DOM（见 parse_overseas），但连板网报价更新滞后，
    晚报 21:40 出稿时可能还是下午的旧值；页面一改版整块还会直接丢失。东财与新浪
    都是稳定接口，也不占连板网的浏览配额。取不到就返回空，宁缺不错。

    传了 date（重跑历史某天）就按那天的收盘取亚太——实时接口在休市日拿不到
    数值；没传就取实时。美股与期指没有按日期的历史接口，始终是跑的时候的最新值。
    """
    groups: List[Dict[str, Any]] = []

    if date:
        try:
            items = _asia_on(date)
            if items:
                groups.append({"label": "亚太", "items": items})
        except Exception as exc:  # noqa: BLE001 - 少一块也不该拖垮整篇
            print(f"overseas(asia) failed: {exc}", file=sys.stderr)
        return groups + _us_overseas()

    try:
        secids = ",".join(code for _, code in _EM_ASIA)
        raw = _overseas_get(f"{_EM_ULIST}?fields=f2,f3,f12,f13,f14&secids={secids}")
        diff = (json.loads(raw).get("data") or {}).get("diff") or []
        by_code = {str(row.get("f12")): row for row in diff}
        items = []
        for name, code in _EM_ASIA:
            row = by_code.get(code.split(".", 1)[1])
            if not row or row.get("f3") in (None, "-", ""):
                continue
            value = float(row["f3"]) / 100
            items.append({"name": name, "pct": _pct(value), "up": value >= 0})
        if items:
            groups.append({"label": "亚太", "items": items})
    except Exception as exc:  # noqa: BLE001 - 少一块也不该拖垮整篇
        print(f"overseas(asia) failed: {exc}", file=sys.stderr)

    return groups + _us_overseas()


def _us_overseas() -> List[Dict[str, Any]]:
    """前夜美股与期指：新浪 hq 的实时值。

    新浪没有按日期查历史的接口，所以这一组始终是跑的时候的最新报价；重跑
    历史某天时，亚太按那天收盘取，美股仍是当下值，两者时点不同。
    """
    try:
        codes = [c for _, c in _SINA_US] + [c for _, c in _SINA_FUT]
        raw = _overseas_get(
            _SINA_HQ + ",".join(codes),
            headers={"Referer": "https://finance.sina.com.cn", "User-Agent": UA},
        )
        rows = dict(re.findall(r'var hq_str_(\w+)="([^"]*)";', raw))
        items = []
        for name, code in _SINA_US:
            parts = (rows.get(code) or "").split(",")
            if len(parts) < 3 or not parts[2]:
                continue
            value = float(parts[2])
            items.append({"name": name, "pct": _pct(value), "up": value >= 0})
        for name, code in _SINA_FUT:
            parts = (rows.get(code) or "").split(",")
            if len(parts) < 8:
                continue
            try:
                last, prev = float(parts[0]), float(parts[7])
            except ValueError:
                continue
            if prev <= 0:
                continue
            value = (last / prev - 1) * 100
            items.append({"name": name, "pct": _pct(value), "up": value >= 0})
        if items:
            return [{"label": "美股", "items": items}]
    except Exception as exc:  # noqa: BLE001
        print(f"overseas(us) failed: {exc}", file=sys.stderr)
    return []


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


def parse_themes(page: str) -> List[Dict[str, Any]]:
    """Each of the day's mainlines with the names that actually hit the limit.

    The card row (``.zxc``) carries the theme, its limit-up count, the driver and
    the leader. Some cards also link a hidden detail panel (``#zxmN``) that lists
    every stock behind the count, with its board height and the site's own
    sub-theme tag — that panel is the only place a theme and its stocks appear
    together, so it is what lets the brief name a theme's names instead of
    guessing them from a sector label.

    A card without a panel is not an error: the site only expands themes whose
    count is a merge of sub-themes. ``exact`` says which case this is, and the
    caller keeps the difference visible rather than filling the gap.
    """
    panels: Dict[str, Dict[str, Any]] = {}
    for pid, body in _ZXM_RE.findall(page):
        head = _ZMT_RE.search(body)
        label = _clean(head.group(1)) if head else ""
        group = label.split("·")[0].strip() if label else ""
        zms = _ZMS_RE.search(body)
        members = []
        if zms:
            for code, name, inner in _WC_RE.findall(zms.group(1)):
                board = re.search(r'<em class="[^"]*">(.*?)</em>', inner)
                sub = re.search(r'<i class="wsub">(.*?)</i>', inner)
                members.append(
                    {
                        "code": code,
                        "name": _clean(name),
                        "board": _clean(board.group(1)) if board else "",
                        "sub": _clean(sub.group(1)) if sub else "",
                    }
                )
        panels[pid] = {"group": group, "members": members}

    out = []
    for theme, mid, driver in _ZXC_RE.findall(page):
        theme = _clean(theme)
        if not theme:
            continue
        count = re.search(r"涨停(\d+)家", _clean(mid))
        link = re.search(r'data-m="(zxm\d+)"', mid)
        leader = re.search(r'data-stk="(\d{6})"\s+data-nm="([^"]+)"', mid)
        badge = re.search(r'<i class="mono">(.*?)</i>', mid)
        panel = panels.get(link.group(1)) if link else None
        out.append(
            {
                "theme": theme,
                "limit_up": int(count.group(1)) if count else None,
                "driver": _clean(driver),
                "leader": (
                    {"code": leader.group(1), "name": _clean(leader.group(2))} if leader else None
                ),
                "leader_board": _clean(badge.group(1)) if badge else "",
                "group": (panel or {}).get("group", ""),
                "exact": bool(panel and panel["members"]),
                "members": (panel or {}).get("members", []),
            }
        )
    return out


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


def collect_extra(timeout_ms: int = 60000, date: str = "") -> Dict[str, Any]:
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
    overseas = fetch_overseas(date)
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
            "theme_members": parse_themes(page),
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


# 判断「这份复盘是不是这一天的」，四层证据缺一不可。写在这里而不是调用处，
# 是因为 mcp_review 是唯一入口：页面、推送、模型输入三条路都从它拿数据。
_DAY_PAT = re.compile(r"/days/(\d{4}-\d{2}-\d{2})\.html")
_COUNT_PAT = {
    "adv": re.compile(r"上涨\s*(\d+)\s*家"),
    "dec": re.compile(r"下跌\s*(\d+)\s*家"),
    "limit_down": re.compile(r"跌停\s*(\d+)\s*家"),
}


def _check_day(body: Dict[str, Any], date: str) -> Dict[str, Any]:
    """Verify that this review really belongs to ``date``.

    The date cannot be taken from the request: the endpoint answers with the
    latest session when ``date`` is omitted, and a date outside the anonymous
    window comes back as an empty object rather than an error. Either path can
    hand yesterday's write-up to a model that is asked to disagree with it, so
    every layer below has to agree with the requested day on its own.

    L1 ``kpi.date``      the session the server itself labels the numbers with
    L2 ``page``/``source``  the ``/days/YYYY-MM-DD.html`` the text came from
    L3 ``updated_at``    the write-up must have been produced that same day
    L4 ``status``        only ``final`` is settled; anything else may still move
    L5 the counts in the text against the same response's ``kpi``
    """
    kpi = body.get("kpi") or {}
    text = str(body.get("ai_review") or "")
    kpi_date = str(kpi.get("date") or "").strip()
    page = str(body.get("page") or "") or str(body.get("source") or "")
    updated = str(body.get("updated_at") or "").strip()
    status = str(body.get("status") or "").strip()
    link = _DAY_PAT.search(page)
    page_date = link.group(1) if link else ""

    reasons: List[str] = []
    if not kpi_date:
        reasons.append("kpi.date 为空")
    elif kpi_date != date:
        reasons.append(f"kpi.date={kpi_date}")
    if not page_date:
        reasons.append("page 无日期")
    elif page_date != date:
        reasons.append(f"page={page_date}")
    if not updated:
        reasons.append("updated_at 为空")
    elif not updated.startswith(date):
        reasons.append(f"updated_at={updated}")
    if status != "final":
        reasons.append(f"status={status or '空'}")

    # 前四层看的是元数据，这一层看正文本身：把正文里自报的涨跌家数跟同一份
    # 响应的 kpi 对一遍。元数据被改成今天、正文却还是昨天的，只有这里能抓到。
    matched, conflicts = 0, []
    for key, pat in _COUNT_PAT.items():
        hit = pat.search(text)
        want = kpi.get(key)
        if not hit or want is None:
            continue
        matched += 1
        if int(hit.group(1)) != int(want):
            conflicts.append(f"{key} 正文{hit.group(1)}≠kpi{want}")
    reasons.extend(conflicts)

    return {
        "requested": date,
        "kpi_date": kpi_date,
        "page_date": page_date,
        "updated_at": updated,
        "status": status,
        "text_counts_matched": matched,
        "text_counts_conflict": bool(conflicts),
        "ok": not reasons,
        "reasons": reasons,
    }


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
    review = {
        "status": body.get("status"),
        "status_label": body.get("status_label"),
        "updated_at": body.get("updated_at"),
        "themes": body.get("themes") or [],
        "ai_review": body.get("ai_review") or "",
        "page": body.get("page") or "",
    }
    check = _check_day(body, date)
    review["date_check"] = check
    review["date_verified"] = check["ok"]
    if not check["ok"]:
        # 校验不过就整块丢掉：模型拿不到这一天的复盘，就不会去跟错的日子对比；
        # 页面和推送也因为这个字段为空而不渲染那一段。原始长度留在 date_check 里，
        # 跑完看日志就知道是「没取到」还是「取到了但不是当天」。
        review["rejected"] = {
            "ai_review_chars": len(review["ai_review"]),
            "themes": len(review["themes"]),
        }
        review["ai_review"] = ""
        review["themes"] = []
    return review


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
.stg{display:grid;grid-template-columns:repeat(2,1fr);gap:9px 16px}
.st-h{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-size:14px}
.st-h span{color:#2b3440;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.st-h b{font-size:13px;font-weight:600;font-variant-numeric:tabular-nums}
.zjg{display:grid;grid-template-columns:repeat(2,1fr);gap:16px 18px}
.zc .zh{font-size:12px;color:#8a94a6;margin-bottom:2px}
.zr{display:flex;align-items:baseline;gap:6px;padding:5px 0;border-bottom:1px solid #f4f6f8;font-size:13px}
.zn{flex:1;min-width:0;color:#2b3440;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.zr b{font-weight:600;font-variant-numeric:tabular-nums;white-space:nowrap}
.zp{width:46px;text-align:right;font-size:11px;color:#98a2b3;font-variant-numeric:tabular-nums}
.quote{border-left:3px solid #d9dee7;padding:2px 0 2px 14px;color:#4c5866;font-size:15px}
.sgs{display:flex;flex-direction:column;gap:8px;margin:0 0 6px}
.sg{display:flex;flex-direction:column;gap:6px;align-items:flex-start;padding:10px 12px;background:#f7f8fa;border-radius:8px}
.sgc{flex:0 0 auto;font-size:12.5px;line-height:1.6;padding:1px 8px;border-radius:10px;background:#eceff3;color:#2b3440;white-space:nowrap}
.sgt{width:100%;font-size:13.5px;line-height:1.7;color:#4c5866}
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
        prev = _prev_value(row["value"], delta)
        tail = f"（昨 {_esc(prev)}）" if prev else ""
        changes.append(f"{label} <b class='{_pct_class(delta)}'>{_esc(delta)}</b>{tail}")
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
        html += f"<p class='chg'>较昨日：{' · '.join(changes)}</p>"
    if rows:
        html += f"<div class='det'>{''.join(rows)}</div>"
    return html


def _strength_sorted(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """主线强度：按涨跌幅从高到低排。

    这块有两条数据源：东财概念板块（strength_em）和连板网强度榜（strength），
    各自的原始顺序不同，统一在这里按涨跌幅重排，页面与推送才读同一份次序。
    不再画条长：排序已经表达了强弱，数字已经表达了幅度，条长只是把同一件事
    再编码一遍，读者还得先学一遍刻度才能读。
    """
    parsed: List[tuple] = []
    for r in rows or []:
        raw = str(r.get("pct") or "")
        raw = raw.replace("%", "").replace("+", "").replace("−", "-").strip()
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        parsed.append((value, r))
    if not parsed:
        return []
    parsed.sort(key=lambda p: -p[0])
    return [dict(r) for _, r in parsed]


def _strength_html(payload: Dict[str, Any]) -> str:
    """主线强度：单独成块，跟在「主线追踪」后面，不掺进资金面板。"""
    # 东财那份由 post_market 算好后挂在 strength_em 上，页面与推送共用；没跑到
    # 那一步（单测、或接口没通）才回退连板网抓下来的强度榜。
    extra = payload.get("extra") or {}
    strength = extra.get("strength_em")
    if strength is None:
        strength = extra.get("strength") or []
    strength = _strength_sorted(strength)
    if not strength:
        return ""
    chips = "".join(
        "<div class='st'>"
        f"<div class='st-h'><span>{_esc(x['name'])}</span>"
        f"<b class='{_pct_class(x['pct'])}'>{_esc(x['pct'])}</b></div>"
        "</div>"
        for x in strength
    )
    return (
        "<h2>主线强度</h2><p class='hint'>板块今日涨跌幅，从上到下由强到弱</p>"
        f"<div class='stg'>{chips}</div>"
    )


def _flows_html(payload: Dict[str, Any]) -> str:
    """主力资金：四组板块与个股净额，收盘定格。"""
    flows = (payload.get("extra") or {}).get("flows") or {}
    if not flows:
        return ""
    cols = []
    for label, rows in flows.items():
        body = "".join(
            f"<div class='zr'><span class='zn'>{_esc(r['name'])}</span>"
            f"<b class='{_pct_class(r['amount'])}'>{_esc(r['amount'])}</b>"
            f"<span class='zp'>{_esc(r['pct'])}</span></div>"
            for r in rows
        )
        cols.append(f"<div class='zc'><div class='zh'>{_esc(label)}</div>{body}</div>")
    return (
        "<h2>主力资金动向</h2><p class='hint'>板块与个股主力净额 · 收盘定格</p>"
        f"<div class='zjg'>{''.join(cols)}</div>"
    )


def _funds_html(payload: Dict[str, Any]) -> str:
    extra = payload.get("extra") or {}
    strength = extra.get("strength") or []
    flows = extra.get("flows") or {}
    out = [_panel_html(payload)]

    strength = _strength_sorted(strength)
    if strength:
        chips = "".join(
            "<div class='st'>"
            f"<div class='st-h'><span>{_esc(x['name'])}</span>"
            f"<b class='{_pct_class(x['pct'])}'>{_esc(x['pct'])}</b></div>"
            "</div>"
            for x in strength
        )
        out.append(
            "<h2>主线强度</h2><p class='hint'>板块今日涨跌幅，从上到下由强到弱</p>"
            f"<div class='stg'>{chips}</div>"
        )

    if flows:
        cols = []
        for label, rows in flows.items():
            body = "".join(
                f"<div class='zr'><span class='zn'>{_esc(r['name'])}</span>"
                f"<b class='{_pct_class(r['amount'])}'>{_esc(r['amount'])}</b>"
                f"<span class='zp'>{_esc(r['pct'])}</span></div>"
                for r in rows
            )
            cols.append(f"<div class='zc'><div class='zh'>{_esc(label)}</div>{body}</div>")
        out.append(
            "<h2>主力资金动向</h2><p class='hint'>板块与个股主力净额 · 收盘定格</p>"
            f"<div class='zjg'>{''.join(cols)}</div>"
        )
    return "".join(out)


_BRAND_RE = re.compile(r"连板网|lianban\.net", re.IGNORECASE)


def _scrub(text: Any) -> str:
    """页面上不出现来源站名：抓来的正文与标签统一换成「第三方信源」。"""
    return _BRAND_RE.sub("第三方信源", str(text if text is not None else ""))


def _signals_html(payload: Dict[str, Any]) -> str:
    """今日信号面：连板网按历史形态自动触发的状态提示。

    每条都是「形态 + 历史统计」，不是本页判断，也不指向个股，所以整块放在
    复盘正文下面，标注来源。
    """
    rows = ((payload.get("extra") or {}).get("signals")) or []
    if not rows:
        return ""
    items = "".join(
        f"<div class='sg'><span class='sgc'>{_esc(_scrub(r.get('chip')))}</span>"
        f"<span class='sgt'>{_esc(_scrub(r.get('text')))}</span></div>"
        for r in rows
        if r.get("chip") and r.get("text")
    )
    if not items:
        return ""
    return (
        "<h2>今日信号面</h2>"
        f"<div class='sgs'>{items}</div>"
    )


def _review_html(payload: Dict[str, Any]) -> str:
    """复盘正文一块，信号面与外盘由 render_sections 单独给出。

    页面顺序是盘面 → 外盘 → 信号面 → 研判 → 第三方复盘 → 对比 → 明细数据，
    几块来自不同抓取，拼在一起就再也拆不开，所以这里只出正文，位置交给页面
    决定。标题与推文的「第三方复盘」统一叫法，不在这里另起一个名字。
    """
    doc = payload.get("lianban") or {}
    text = (doc.get("ai_review") or "").strip()
    if not text:
        return ""
    # 全文照登：复盘固定两段，砍掉第二段「重点游资」等于把席位分析整段丢掉。
    # 600 字上限只是防哪天原文突然变长，目前最长 520 字，等于不截。
    body = text.strip()
    if len(body) > 600:
        body = body[:600].rstrip() + "…"
    # .quote 没有 white-space，段落间的空行会被 HTML 折成空格，两段会连成一坨，
    # 所以换行要显式转成 <br>。
    body_html = _esc(body).replace("\n\n", "<br><br>").replace("\n", "<br>")
    return (
        "<h2>第三方复盘</h2>"
        f"<div class='quote'>{body_html}</div>"
    )


def _overseas_html(payload: Dict[str, Any]) -> str:
    """隔夜美股与亚太：不解释今天，只交代明天开盘前的外部底色。"""
    groups = (payload.get("extra") or {}).get("overseas") or []
    if not groups:
        return ""
    # 读者先关心今天亚洲怎么走（当日），再看昨夜美股（前夜），所以亚太排前面，
    # 标签也把时点写明，免得把隔夜的跌幅当成今天亚太的。
    _ORDER = (("亚太", "当日亚太"), ("美股", "前夜美股"))

    def _key(group: Dict[str, Any]) -> int:
        label = str(group.get("label") or "").split(" · ")[0]
        for i, (word, _) in enumerate(_ORDER):
            if word in label:
                return i
        return len(_ORDER)

    rows = []
    for group in sorted(groups, key=_key):
        label = str(group.get("label") or "").split(" · ")[0]
        for word, shown in _ORDER:
            if word in label:
                label = shown
                break
        chips = "".join(
            f"<span class='chip'><i>{_esc(x['name'])}</i>"
            f"<b class='{'up' if x['up'] else 'down'}'>{_esc(x['pct'])}</b></span>"
            for x in group["items"]
        )
        rows.append(f"<div class='ovr'><span class='ovl'>{_esc(label)}</span>{chips}</div>")
    return (
        "<h2>外盘参考</h2><p class='hint'>当日亚太与前夜美股</p>"
        f"<div class='ovg'>{''.join(rows)}</div>"
    )


def render_sections(payload: Dict[str, Any]) -> Dict[str, str]:
    """``{"funds", "review", "signals", "overseas"}`` — empty when a source is missing."""
    try:
        panel = _panel_html(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"panel render failed: {exc}", file=sys.stderr)
        panel = ""
    try:
        strength = _strength_html(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"strength render failed: {exc}", file=sys.stderr)
        strength = ""
    try:
        flows = _flows_html(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"flows render failed: {exc}", file=sys.stderr)
        flows = ""
    try:
        review = _review_html(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"review render failed: {exc}", file=sys.stderr)
        review = ""
    try:
        signals = _signals_html(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"signals render failed: {exc}", file=sys.stderr)
        signals = ""
    try:
        overseas = _overseas_html(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"overseas render failed: {exc}", file=sys.stderr)
        overseas = ""
    return {
        "panel": panel,
        "strength": strength,
        "flows": flows,
        "review": review,
        "signals": signals,
        "overseas": overseas,
    }


if __name__ == "__main__":
    sys.exit(main())
