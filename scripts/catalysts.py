#!/usr/bin/env python3
"""当日政策类快讯：晚报「今日催化」块的数据源。

晚报 18:30 出，盘中的政策消息（国常会、部委发布、地方方案）往往是当天涨跌最
直接的线索，但盘面数据里没有它——成交额只说明钱进来了，不说明为什么进来。

这个模块只做三件事：取当日 09:15–15:05 的快讯、按政策词表筛、把能在正文里
对上板块名的消息挂上当日涨幅。它不做因果判断：时间与数据并排，判断留给读者。
一条消息进了「今日催化」不等于它造成了那波涨跌，页面措辞也不许这么写。

    from catalysts import collect, render_html, push_lines
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Sequence

FEED_URL = "https://zhibo.sina.com.cn/api/zhibo/feed"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
TIMEOUT = 20.0
PAGE_SIZE = 100
# 今天实测：从 22:00 往回翻到 07:00 约 18 页。留到 26 页，覆盖长假后消息密集日。
MAX_PAGES = 26
WINDOW_START = "09:15"
WINDOW_END = "15:05"
MAX_ITEMS = 8
MAX_BOARD_ITEMS = 5

# 只认这几类：中央与部委发文、地方产业方案、货币与财政工具。
POLICY = re.compile(
    r"国务院|国常会|中办|国办|中共中央|中央|发改委|工信部|财政部|央行|人民银行|"
    r"证监会|金融监管总局|能源局|商务部|科技部|国资委|统计局|税务总局|海关总署|"
    r"网信办|药监局|民航局|邮政局|住建部|生态环境部|农业农村部|"
    r"印发|出台|征求意见|试点|规划|指导意见|实施意见|行动方案|若干措施|"
    r"降准|降息|专项债|补贴|税收|关税|出口管制"
)
# 公司公告里也常出现「政策」「规划」，那是公司自己的事，不是催化。
COMPANY = re.compile(
    r"公告称|公告，|公告显示|收到|签订|中标|拟以|拟向|回购|增持|减持|"
    r"业绩预告|业绩快报|投资者关系|互动平台|辅导|IPO|首次公开发行|上市申请"
)
# 反腐、党建、人事：是新闻，不是盘面催化。
NOISE = re.compile(
    r"纪律审查|监察调查|双开|开除党籍|党建|学习贯彻|党组|巡视|任免|"
    r"简历|逝世|讣告|纪念|座谈|行业标准|持牌|牌照|业务据点"
)
# 境外主体的表态不是 A 股催化：印度央行、欧洲央行、外资机构的评论都归这里。
FOREIGN = re.compile(
    r"^(印度|欧洲|美国|日本|韩国|英国|德国|法国|俄罗斯|越南|泰国|印尼|"
    r"印度尼西亚|巴西|土耳其|加拿大|澳大利亚|乌克兰|巴拉圭|塞尔维亚|"
    r"墨西哥|阿根廷|沙特|伊朗|以色列|埃及|南非|新加坡|马来西亚|菲律宾)|"
    r"^(美联储|欧洲央行|日本央行)|^[A-Za-z]"
)
# 每日例行操作：中间价报价、公开市场逆回购与净投放／净回笼。它们每个交易日都发，
# 是流动性管理而不是政策催化；强度接口取不到时它们会顶到块首，把真消息挤下去。
# 只滤例行操作——「降准」「降息」这类真政策不在此列。
ROUTINE = re.compile(
    r"兑美元中间价|人民币汇率中间价|"
    r"公开市场.{0,12}(?:净投放|净回笼|逆回购)|"
    r"开展\s*[\d,.]+\s*亿元.{0,8}(?:逆回购|中期借贷便利|MLF)"
)
# 这几条是当天最硬的定调，排最前。
TOP = re.compile(r"国常会|国务院常务会议|政治局会议|中央经济工作会议")
OFFICIAL = re.compile(
    r"国务院|国常会|中办|国办|中共中央|发改委|工信部|财政部|央行|人民银行|"
    r"证监会|金融监管总局|能源局|商务部|科技部|国资委|药监局|住建部"
)

_CACHE: Dict[str, Dict[str, Any]] = {}


def _get(url: str, timeout: float = TIMEOUT) -> Dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return json.loads(body.decode("utf-8", "replace"))


def _rows(url: str) -> List[Dict[str, Any]]:
    doc = _get(url)
    return (
        ((doc.get("result") or {}).get("data") or {}).get("feed") or {}
    ).get("list") or []


def _text(item: Dict[str, Any]) -> str:
    raw = str(item.get("rich_text") or item.get("text") or "")
    raw = re.sub(r"<[^>]+>", "", raw)
    return re.sub(r"\s+", " ", raw).strip()


def _fetch(stamp: str, pages: int = MAX_PAGES) -> List[Dict[str, str]]:
    """从最新往回翻，翻到当日 09:15 之前就停。"""
    out: List[Dict[str, str]] = []
    for page in range(1, pages + 1):
        query = urllib.parse.urlencode(
            {
                "page": page,
                "page_size": PAGE_SIZE,
                "zhibo_id": 152,
                "tag_id": 0,
                "dire": "f",
                "dpc": 1,
            }
        )
        rows = _rows(f"{FEED_URL}?{query}")
        if not rows:
            # 新浪这个接口偶发空页（约每十页一次），不是真的到底了：等一下再要一次。
            time.sleep(1.2)
            rows = _rows(f"{FEED_URL}?{query}")
        if not rows:
            break
        oldest = ""
        for row in rows:
            when = str(row.get("create_time") or "")
            oldest = when or oldest
            if not when.startswith(stamp):
                continue
            clock = when[11:16]
            if WINDOW_START <= clock <= WINDOW_END:
                out.append({"time": clock, "text": _text(row)})
        if oldest and oldest[11:16] < WINDOW_START:
            break
        time.sleep(0.3)
    return out


def _keep(text: str) -> bool:
    if len(text) < 12 or not POLICY.search(text):
        return False
    # 公司自己的公告：带官方机构名的留下（「工信部…公司…」），纯公告丢掉。
    if TOP.search(text):
        return True
    if ROUTINE.search(text):
        return False
    if NOISE.search(text) or COMPANY.search(text) or FOREIGN.search(text):
        return False
    return True


def _boards(text: str, strength: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
    """正文里直接出现板块名的才算对上——不做同义扩展，宁可少挂也不硬套。"""
    hits = []
    for row in strength or []:
        name = str(row.get("name") or "").strip()
        if len(name) < 2 or name not in text:
            continue
        hits.append({"name": name, "pct": str(row.get("pct") or "")})
    return hits[:3]


def collect(
    date: str,
    strength: Optional[Sequence[Dict[str, Any]]] = None,
    max_pages: int = MAX_PAGES,
) -> Dict[str, Any]:
    """``date`` 形如 ``2026-11-27``；取不到就返回空 items，调用方整块不印。"""
    stamp = str(date or "")[:10]
    if len(stamp) != 10:
        return {"date": stamp, "items": [], "errors": ["bad date"]}
    if stamp in _CACHE:
        return _CACHE[stamp]
    try:
        rows = _fetch(stamp, max_pages)
    except Exception as exc:  # noqa: BLE001 - 源不通只是少一块
        print(f"catalysts: feed failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return {"date": stamp, "items": [], "errors": [f"{type(exc).__name__}: {exc}"]}

    seen = set()
    items: List[Dict[str, Any]] = []
    for row in rows:
        text = row["text"]
        if not _keep(text):
            continue
        key = re.sub(r"[^\w\u4e00-\u9fff]", "", text)[:24]
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "time": row["time"],
                "text": text,
                "boards": _boards(text, strength or []),
                "official": bool(OFFICIAL.search(text)),
            }
        )

    # 排序按「这条消息有多硬」，不按时间：翻页是从最新往回，按时间取会把上午的
    # 定调全丢掉（11-27 的国常会在 12:22，晚于它的都是部门例会）。
    def score(item: Dict[str, Any]) -> int:
        if TOP.search(item["text"]):
            return 0
        if item["official"]:
            return 1
        if item["boards"]:
            return 2
        return 3

    def when(item: Dict[str, Any]) -> str:
        return item["time"]

    top = sorted([x for x in items if score(x) == 0], key=when)[:3]
    linked = sorted(
        [x for x in items if x["boards"] and x not in top], key=when
    )[:MAX_BOARD_ITEMS]
    rest = sorted(
        [x for x in items if x not in top and x not in linked],
        key=lambda x: (score(x), x["time"]),
    )
    picked = (top + linked + rest)[:MAX_ITEMS]
    picked.sort(key=when)
    doc = {"date": stamp, "items": picked, "errors": [], "scanned": len(rows)}
    _CACHE[stamp] = doc
    print(
        f"catalysts: {len(picked)} 条（扫描 {len(rows)} 条，命中板块 {len(linked)} 条）",
        file=sys.stderr,
    )
    return doc


def _esc(value: Any) -> str:
    return (
        str(value if value is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def render_html(doc: Optional[Dict[str, Any]]) -> str:
    """页面块。用 .drv 的现成样式，不新增 CSS。"""
    items = (doc or {}).get("items") or []
    if not items:
        return ""
    rows = []
    for item in items:
        bits = [
            f"{b['name']} <span class='cnt'>{_esc(b['pct'])}</span>"
            for b in item.get("boards") or []
        ]
        tail = f"<span class='ld'>{' · '.join(bits)}</span>" if bits else ""
        text = item["text"]
        if len(text) > 150:
            text = text[:150] + "…"
        rows.append(f"<li><b>{_esc(item['time'])}</b> {_esc(text)}{tail}</li>")
    return (
        "<h2>今日催化</h2>"
        "<p class='hint'>当日 09:15–15:05 的政策与产业消息，按发布时间排列；"
        "正文点到板块名的，附该板块当日涨幅</p>"
        f"<ul class='drv'>{''.join(rows)}</ul>"
    )


def push_lines(doc: Optional[Dict[str, Any]], limit: int = 5) -> List[str]:
    """推送版：只给时间与要点，板块涨幅跟在后面。"""
    items = (doc or {}).get("items") or []
    if not items:
        return []
    out = []
    for item in items[:limit]:
        bits = " · ".join(
            f"{b['name']} {b['pct']}" for b in item.get("boards") or []
        )
        line = f"- **{item['time']}** {item['text'][:90]}"
        if bits:
            line += f"（{bits}）"
        out.append(line)
    return out
