"""Overnight US tape from Sina Finance.

lianban's morning brief carried the same numbers, but only on trading days and
under a daily browse quota that already answers 429. Sina answers every day
with the last close, which is what a weekend digest needs: on a Saturday it
returns Friday's close, and on Monday it returns that same Friday close again,
because the US market does not trade over the weekend. The block therefore
needs no freshness gate — it only has to print which session the numbers
belong to.

The US ticker → A-share theme map is lianban's own, lifted from the five
sessions to 2026-11-20, so the labels stay the ones the reader already saw
rather than ones invented here.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SINA_URL = "https://hq.sinajs.cn/list="
TIMEOUT_SECONDS = 15.0
HEADERS = {
    "Referer": "https://finance.sina.com.cn",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    ),
}

INDICES = (
    ("费城半导体", "gb_sox"),
    ("纳指100", "gb_ndx"),
    ("纳斯达克", "gb_ixic"),
    ("道琼斯", "gb_dji"),
    ("标普500", "gb_inx"),
)

# (Sina code, label, A-share themes) — themes as lianban mapped them.
MOVERS = (
    ("gb_amd", "AMD", ("半导体", "国产芯片")),
    ("gb_smci", "超微电脑", ("英伟达概念", "液冷概念")),
    ("gb_crwv", "CoreWeave", ("东数西算", "液冷概念")),
    ("gb_vrt", "维谛VRT", ("液冷概念",)),
    ("gb_cohr", "相干COHR", ("CPO概念", "消费电子")),
    ("gb_crdo", "Credo", ("铜缆高速连接", "CPO概念")),
    ("gb_sndk", "闪迪", ("存储芯片",)),
    ("gb_asts", "ASTS", ("卫星互联网", "商业航天")),
    ("gb_ionq", "IonQ", ("量子科技",)),
    ("gb_achr", "Archer", ("低空经济",)),
    ("gb_joby", "Joby", ("低空经济",)),
    ("gb_wrd", "文远知行", ("无人驾驶",)),
    ("gb_pony", "小马智行", ("无人驾驶",)),
    ("gb_smr", "NuScale", ("核电",)),
    ("gb_fslr", "第一太阳能", ("光伏设备",)),
    ("gb_crcl", "Circle", ("数字货币", "跨境支付")),
    ("gb_avav", "AeroVironment", ("无人机", "军工")),
)

# lianban showed six, ordered by how far the stock moved.
MOVERS_SHOWN = 6

_LINE_RE = re.compile(r'var hq_str_(gb_\w+)="([^"]*)";')


def parse(text: str) -> Dict[str, Dict[str, Any]]:
    """``var hq_str_gb_amd="超威半导体,489.1900,-7.72,2026-11-20 09:16:27,..."``

    Field 0 is the Chinese name, 1 the last price, 2 the percent change and 3
    the Beijing timestamp of that print. An empty payload means Sina has no
    quote for the code, and the row is dropped.
    """
    rows: Dict[str, Dict[str, Any]] = {}
    for code, payload in _LINE_RE.findall(text):
        fields = payload.split(",")
        if len(fields) < 4 or not fields[1].strip():
            continue
        try:
            pct = float(fields[2])
        except ValueError:
            continue
        rows[code] = {
            "name": fields[0].strip(),
            "pct": pct,
            "stamp": fields[3].strip(),
        }
    return rows


def _close_date(stamp: str) -> str:
    """Beijing print time → the US session it belongs to, as ``11-19``.

    A US close lands at 04:00–05:00 Beijing the next morning, so any print
    before noon belongs to the previous US date. Anything after noon is a
    pre-market quote for the session that has not closed yet.
    """
    try:
        moment = datetime.strptime(stamp[:16], "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return ""
    if moment.hour < 12:
        moment -= timedelta(days=1)
    return f"{moment.month}-{moment.day:02d}"


CST = timezone(timedelta(hours=8))

# NYSE 的常规休市日按规则算，不维护年表：固定日期 + 第 n 个周几 + 复活节前的
# 周五。临时休市（国葬、飓风）不在其中，那时 _us_holiday 返回 None，块照原样
# 打印数据并标注交易日——查不到原因就不编一个。
_HOLIDAY_NAMES = {
    "new_year": {"zh": "元旦", "en": "New Year's Day"},
    "mlk": {"zh": "马丁·路德·金纪念日", "en": "Martin Luther King Jr. Day"},
    "presidents": {"zh": "总统日", "en": "Presidents' Day"},
    "good_friday": {"zh": "耶稣受难日", "en": "Good Friday"},
    "memorial": {"zh": "阵亡将士纪念日", "en": "Memorial Day"},
    "juneteenth": {"zh": "六月节", "en": "Juneteenth"},
    "independence": {"zh": "独立日", "en": "Independence Day"},
    "labor": {"zh": "劳动节", "en": "Labor Day"},
    "thanksgiving": {"zh": "感恩节", "en": "Thanksgiving Day"},
    "christmas": {"zh": "圣诞节", "en": "Christmas Day"},
}


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """某月第 n 个星期 weekday（0=周一）。"""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """某月最后一个星期 weekday。"""
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    last = nxt - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _easter(year: int) -> date:
    """Anonymous Gregorian algorithm。"""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _observed(day: date) -> date:
    """周六的假日提前到周五，周日的推后到周一。"""
    if day.weekday() == 5:
        return day - timedelta(days=1)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _holiday_table(year: int) -> Dict[date, str]:
    return {
        _observed(date(year, 1, 1)): "new_year",
        _nth_weekday(year, 1, 0, 3): "mlk",
        _nth_weekday(year, 2, 0, 3): "presidents",
        _easter(year) - timedelta(days=2): "good_friday",
        _last_weekday(year, 5, 0): "memorial",
        _observed(date(year, 6, 19)): "juneteenth",
        _observed(date(year, 7, 4)): "independence",
        _nth_weekday(year, 9, 0, 1): "labor",
        _nth_weekday(year, 11, 3, 4): "thanksgiving",
        _observed(date(year, 12, 25)): "christmas",
    }


def _us_holiday(day: date) -> Optional[Dict[str, str]]:
    """美东某日是常规休市日时返回节日名（中英各一份），否则 None。

    查前后三年：元旦落在周六时会提前到上一年的 12/31，那张表挂在前一年。
    """
    for year in (day.year - 1, day.year, day.year + 1):
        key = _holiday_table(year).get(day)
        if key:
            return _HOLIDAY_NAMES[key]
    return None


def last_night_holiday(today: date) -> Optional[Dict[str, str]]:
    """昨夜美股是不是因节日休市。

    今晨对应的美东日期就是北京日期减一天。周末不开市属于周期性安排，
    不在这条判断里——那种情况沿用原行为，打印数据并标注交易日。
    """
    day = today - timedelta(days=1)
    if day.weekday() >= 5:
        return None
    return _us_holiday(day)


async def fetch_overnight(url: str = SINA_URL) -> Optional[Dict[str, Any]]:
    """One GET per run; any failure returns None and the digest drops the block."""
    codes = [code for _, code in INDICES] + [code for code, _, _ in MOVERS]
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(url + ",".join(codes), headers=HEADERS)
            response.raise_for_status()
            rows = parse(response.content.decode("gbk", "replace"))
    except Exception as exc:  # noqa: BLE001 - the block is optional
        logger.warning("Overnight tape unavailable: %s", exc)
        return None

    indices: List[Dict[str, Any]] = [
        {"name": label, "pct": rows[code]["pct"]}
        for label, code in INDICES
        if code in rows
    ]
    if not indices:
        logger.warning("Overnight tape parsed empty; block skipped")
        return None

    movers: List[Dict[str, Any]] = []
    for code, label, themes in MOVERS:
        row = rows.get(code)
        if not row:
            continue
        movers.append({"ticker": label, "pct": row["pct"], "themes": list(themes)})
    movers.sort(key=lambda mover: abs(mover["pct"]), reverse=True)

    stamp = next((rows[code]["stamp"] for _, code in INDICES if code in rows), "")
    holiday = last_night_holiday(datetime.now(CST).date())
    brief = {
        "indices": indices,
        "movers": movers[:MOVERS_SHOWN],
        "close_date": _close_date(stamp),
        "stamp": stamp,
        "holiday": holiday,
    }
    logger.warning(
        "Overnight tape %s: %d indices, %d movers, stamp %s, holiday %s",
        brief["close_date"] or "(no date)",
        len(indices),
        len(brief["movers"]),
        stamp or "(none)",
        (holiday or {}).get("zh") or "(none)",
    )
    return brief
