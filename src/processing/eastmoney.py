"""Eastmoney as a second source for the evening brief's numbers.

The brief used to take every figure from one site. Most of those figures are
public trading facts with a canonical publisher, not that site's opinion, so
they can be read from Eastmoney instead — and the six breadth counts were
checked against the site's own numbers on 2026-11-19 and matched exactly
(limit-ups 23, limit-downs 68, broken boards 24, seal rate 48.9%, 连续板 5,
highest 3).

What is *not* here is deliberate: the ten-day line matrix, the three screening
templates and the sentiment degree are that site's own taxonomy and scoring,
and no third party publishes them. Swapping those would change the numbers,
not the source.

Every call is one GET with a timeout, and every failure raises: the caller
decides whether a missing block is worth failing over, and here it never is.
"""

from __future__ import annotations

import gzip
import json
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)
TIMEOUT = 20.0

POOL_URL = "https://push2ex.eastmoney.com/getTopic{topic}Pool"
POOL_UT = "7eea3edcaed734bea9cbfc24409ed989"
DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"

# 涨停池按首次封板时间排，跌停池按封单资金排，炸板池按首次封板时间排。
_POOL_SORT = {"ZT": "fbt:asc", "DT": "fund:asc", "ZB": "fbt:asc"}


def _get(url: str, timeout: float = TIMEOUT) -> str:
    request = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return body.decode("utf-8", "replace")


def _get_json(url: str, timeout: float = TIMEOUT) -> Dict[str, Any]:
    return json.loads(_get(url, timeout=timeout))


def _day(date: str) -> str:
    """``2026-11-19`` -> ``20261119``, the pool endpoints' date format."""
    return re.sub(r"[^0-9]", "", date)


def _iso(date: str) -> str:
    """``20261119`` or ``2026-11-19`` -> ``2026-11-19``."""
    digits = _day(date)
    if len(digits) != 8:
        return date
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


def pool(topic: str, date: str, page_size: int = 200) -> Dict[str, Any]:
    """``{"count": int, "rows": [...]}`` for ZT (涨停) / DT (跌停) / ZB (炸板)."""
    query = urllib.parse.urlencode(
        {
            "ut": POOL_UT,
            "dpt": "wz.ztzt",
            "Pageindex": 0,
            "pagesize": page_size,
            "sort": _POOL_SORT.get(topic, "fbt:asc"),
            "date": _day(date),
        }
    )
    doc = _get_json(f"{POOL_URL.format(topic=topic)}?{query}")
    data = doc.get("data") or {}
    if doc.get("rc") not in (0, None):
        raise ValueError(f"pool {topic}: rc={doc.get('rc')}")
    return {"count": int(data.get("tc") or 0), "rows": data.get("pool") or []}


def kpi(date: str) -> Dict[str, Any]:
    """The six breadth counts, computed the way the site computes them.

    Seal rate is limit-ups over limit-ups plus broken boards — the same ratio
    the site reports, which is why 2026-11-19 comes out at 48.9% on both sides.
    ``连板`` counts boards of two and up; ``最高板`` is the tallest board.
    """
    zt = pool("ZT", date)
    dt = pool("DT", date)
    zb = pool("ZB", date)
    boards = [int(row.get("lbc") or 0) for row in zt["rows"]]
    seal = None
    if zt["count"]:
        seal = round(zt["count"] / (zt["count"] + zb["count"]) * 100, 1)
    return {
        "source": "eastmoney",
        "date": _iso(date),
        "limit_up": zt["count"],
        "limit_down": dt["count"],
        "zhaban": zb["count"],
        "seal_rate_pct": seal,
        "lianban": sum(1 for n in boards if n >= 2),
        "max_board": max(boards) if boards else 0,
    }


def _report(name: str, params: Dict[str, Any], timeout: float = TIMEOUT) -> List[Dict[str, Any]]:
    query = urllib.parse.urlencode(
        dict(params, reportName=name, source="WEB", client="WEB", pageNumber=1)
    )
    doc = _get_json(f"{DATACENTER_URL}?{query}", timeout=timeout)
    result = doc.get("result") or {}
    if not result:
        return []
    return result.get("data") or []


def lhb(date: str, limit: int = 15) -> Dict[str, Any]:
    """龙虎榜：净买额前 N，带上榜原因与买一席位名称。

    The detail report lists one row per stock *per reason*, so a name flagged for
    two reasons arrives twice; dedupe by code before ranking, or the top fifteen
    would hold fewer than fifteen names. The seat name lives in a second report,
    fetched once for the whole day rather than once per stock.
    """
    rows = _report(
        "RPT_DAILYBILLBOARD_DETAILSNEW",
        {
            "columns": "ALL",
            "filter": f"(TRADE_DATE='{date}')",
            "sortColumns": "BILLBOARD_NET_AMT",
            "sortTypes": "-1",
            "pageSize": "500",
        },
    )
    seats: Dict[str, str] = {}
    for row in _report(
        "RPT_BILLBOARD_DAILYDETAILSBUY",
        {"columns": "ALL", "filter": f"(TRADE_DATE='{date}')", "pageSize": "2000"},
        timeout=25.0,
    ):
        code = str(row.get("SECURITY_CODE") or "")
        name = str(row.get("OPERATEDEPT_NAME") or "").strip()
        if code and name and code not in seats:
            seats[code] = name

    seen = set()
    items: List[Dict[str, Any]] = []
    for row in rows:
        code = str(row.get("SECURITY_CODE") or "")
        if not code or code in seen:
            continue
        seen.add(code)
        net = row.get("BILLBOARD_NET_AMT")
        items.append(
            {
                "name": str(row.get("SECURITY_NAME_ABBR") or ""),
                "code": code,
                "chg": _signed(row.get("CHANGE_RATE")),
                "net": _amount(net),
                "reason": str(row.get("EXPLANATION") or "").strip(),
                "seat": seats.get(code, ""),
            }
        )
        if len(items) >= limit:
            break
    return {"header": f"净买额前 {len(items)}", "items": items}


def _signed(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    return f"{value:+.2f}%"


def _amount(value: Any) -> str:
    """Yuan -> 亿 or 万, whichever the reader can hold in their head."""
    if not isinstance(value, (int, float)):
        return ""
    if abs(value) >= 100000000:
        return f"{value / 100000000:+.2f} 亿"
    return f"{value / 10000:+.0f} 万"


def sector_flow(limit: int = 5, descending: bool = True) -> List[Dict[str, Any]]:
    """行业板块主力净额。``descending`` 取净流入榜首，否则取净流出榜首。

    The listing endpoint caps a page at 100 rows and the market has ~500 sector
    rows, so the two ends are two requests rather than one page split in half.
    """
    query = urllib.parse.urlencode(
        {
            "pn": 1,
            "pz": 100,
            "po": 1 if descending else 0,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "fid": "f62",
            "fs": "m:90+t:2",
            "fields": "f12,f14,f3,f62,f184",
        }
    )
    doc = _get_json(f"{CLIST_URL}?{query}")
    rows = (doc.get("data") or {}).get("diff") or []
    out = []
    for row in rows[:limit]:
        net = row.get("f62")
        if not isinstance(net, (int, float)):
            continue
        out.append(
            {
                "name": str(row.get("f14") or ""),
                "pct": _signed(row.get("f3")),
                "amount": f"{net / 100000000:+.2f} 亿",
                "net_raw": net,
            }
        )
    return out


CONCEPT_FS = "m:90+t:3"


def concept_flow(page_size: int = 100, max_pages: int = 6) -> List[Dict[str, Any]]:
    """概念板块的当日涨跌幅与主力净额。

    连板网 ``#s-strength`` 既不公开算法，板块集合也和它自己的主线趋势对不上，
    主线强度改从这里取：涨跌幅与主力净额都是交易所行情口径，与 kpi、龙虎榜
    同一套接口。一页最多 100 行，概念板块有几百个，所以要翻页。
    """
    out: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        query = urllib.parse.urlencode(
            {
                "pn": page,
                "pz": page_size,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": CONCEPT_FS,
                "fields": "f12,f14,f3,f62",
            }
        )
        doc = _get_json(f"{CLIST_URL}?{query}")
        data = doc.get("data") or {}
        rows = data.get("diff") or []
        if not rows:
            break
        for row in rows:
            pct = row.get("f3")
            if not isinstance(pct, (int, float)):
                continue
            net = row.get("f62")
            out.append(
                {
                    "name": str(row.get("f14") or ""),
                    "pct": float(pct),
                    "net": float(net) if isinstance(net, (int, float)) else None,
                }
            )
        total = data.get("total") or 0
        if len(rows) < page_size or (total and len(out) >= total):
            break
    return out


def calendar(date: str) -> Dict[str, List[Dict[str, str]]]:
    """当日解禁与除权除息，拼成早报日历块需要的行。"""
    lift = _report(
        "RPT_LIFT_STAGE",
        {
            "columns": "ALL",
            "filter": f"(FREE_DATE='{date}')",
            "pageSize": "100",
            "sortColumns": "LIFT_MARKET_CAP",
            "sortTypes": "-1",
        },
    )
    exdiv = _report(
        "RPT_SHAREBONUS_DET",
        {"columns": "ALL", "filter": f"(EX_DIVIDEND_DATE='{date}')", "pageSize": "100"},
    )
    rows: List[Dict[str, str]] = []
    for row in lift:
        rows.append(
            {
                "code": str(row.get("SECURITY_CODE") or ""),
                "name": str(row.get("SECURITY_NAME_ABBR") or ""),
                "tag": "限售解禁",
                "note": _cap(row.get("LIFT_MARKET_CAP")),
            }
        )
    for row in exdiv:
        rows.append(
            {
                "code": str(row.get("SECURITY_CODE") or ""),
                "name": str(row.get("SECURITY_NAME_ABBR") or ""),
                "tag": "除权除息",
                "note": _bonus(row),
            }
        )
    return {"rows": rows}


def _cap(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    return f"解禁市值 {value / 10000:.1f} 亿"


def _bonus(row: Dict[str, Any]) -> str:
    cash = row.get("PRETAX_BONUS_RMB")
    if isinstance(cash, (int, float)) and cash:
        return f"每10股派 {cash:g} 元"
    return ""
