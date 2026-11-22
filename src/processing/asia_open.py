"""Asia-Pacific opening prints for the 08:00 digest.

The 08:00 Beijing run lands on the Tokyo and Seoul open: both exchanges ring in
at 09:00 local time, which is 08:00 in Beijing. This block therefore carries
the *opening* print, not the latest one — by the time the digest reaches this
line the indexes have been trading for ten to forty minutes, and a "当日开盘"
row showing a 09:30 level would be a different number from what its own label
promises.

Eastmoney is the source: ``f46`` is the day's open and ``f60`` the previous
close, so the percent is the open measured against yesterday's close. Sina's
``b_NKY`` / ``b_KOSPI`` feeds are the fallback (field 8 open, field 9 previous
close) — not the ``int_*`` codes, which still carry a 44,946 Nikkei print while
the live index trades at 56,436.

Two gates keep the row honest:

* The session date must be today. A Saturday run, or a run before the bell,
  sees the previous session's close, and printing that under "today's open"
  would be wrong.
* If the opening print is missing but a live one exists, the row falls back to
  the live print and the label carries the time it was read (``日经225（08:23
  取数）``), so the reader can tell the two apart.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

BEIJING = timezone(timedelta(hours=8))
TIMEOUT_SECONDS = 12.0

EM_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"
# (label, Eastmoney secid, Sina fallback code)
ASIA = (
    ("日经225", "100.N225", "b_NKY"),
    ("韩国KOSPI", "100.KS11", "b_KOSPI"),
)
SINA_URL = "https://hq.sinajs.cn/list="

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)
EM_HEADERS = {"User-Agent": UA, "Referer": "https://quote.eastmoney.com/"}
SINA_HEADERS = {"User-Agent": UA, "Referer": "https://finance.sina.com.cn"}

_SINA_RE = re.compile(r'var hq_str_(\w+)="([^"]*)";')

# The run starts at 08:00 and reaches this block after the AI passes, so the
# bell has usually rung; one wait covers the case where it has not.
RETRY_SECONDS = 15.0


def _today_beijing() -> str:
    return datetime.now(BEIJING).strftime("%Y-%m-%d")


def _stamp(value: Any) -> str:
    """Unix seconds → Beijing ``YYYY-MM-DD HH:MM``, or ``""``."""
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return ""
    if seconds <= 0:
        return ""
    return datetime.fromtimestamp(seconds, BEIJING).strftime("%Y-%m-%d %H:%M")


def _num(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _scaled(value: Any, decimals: Optional[int] = None) -> Optional[float]:
    """Eastmoney ships integers scaled by the instrument's decimal places;
    Sina ships the real number. ``decimals=None`` means "already real"."""
    number = _num(value)
    if number is None:
        return None
    return number if decimals is None else number / (10**decimals)


def _quote(
    open_raw: Any,
    prev_raw: Any,
    last_raw: Any,
    pct_raw: Any,
    decimals: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Open print if there is one, otherwise the live print.

    ``price`` is what the row prints; ``mode`` says which of the two it is, so
    the caller can attach a read time only to the fallback.
    """
    open_price = _scaled(open_raw, decimals)
    prev = _scaled(prev_raw, decimals)
    if open_price and prev and open_price > 0 and prev > 0:
        return {"price": open_price, "pct": (open_price / prev - 1) * 100, "mode": "open"}
    last = _scaled(last_raw, decimals)
    pct = _scaled(pct_raw, decimals)
    if last and last > 0:
        return {"price": last, "pct": pct if pct is not None else 0.0, "mode": "last"}
    return None


def _row(label: str, quote: Dict[str, Any], clock: str) -> Dict[str, Any]:
    """``last`` keeps its name so the renderer needs no change; it is the price
    this row prints, which is the opening print whenever one exists."""
    name = label
    if quote["mode"] == "last" and clock:
        name = f"{label}（{clock} 取数）"
    return {"name": name, "last": quote["price"], "pct": quote["pct"], "mode": quote["mode"]}


async def _from_eastmoney(
    client: httpx.AsyncClient, today: str
) -> List[Dict[str, Any]]:
    """``f46`` open, ``f60`` previous close, ``f2`` last, ``f170`` percent."""
    response = await client.get(
        EM_URL,
        params={
            "fields": "f2,f12,f46,f60,f86,f170",
            "secids": ",".join(secid for _, secid, _ in ASIA),
        },
        headers=EM_HEADERS,
    )
    response.raise_for_status()
    payload = json.loads(response.text)
    diff = (payload.get("data") or {}).get("diff") or []
    if isinstance(diff, dict):  # some endpoints key the rows by index
        diff = list(diff.values())
    by_code = {str(row.get("f12")): row for row in diff if isinstance(row, dict)}
    rows: List[Dict[str, Any]] = []
    for label, secid, _ in ASIA:
        row = by_code.get(secid.split(".", 1)[1])
        if not row:
            continue
        stamp = _stamp(row.get("f86"))
        if not stamp.startswith(today):
            continue
        quote = _quote(
            row.get("f46"), row.get("f60"), row.get("f2"), row.get("f170"), decimals=2
        )
        if not quote:
            continue
        rows.append(_row(label, quote, stamp[11:]))
    return rows


async def _from_sina(
    client: httpx.AsyncClient, today: str
) -> List[Dict[str, Any]]:
    """``b_NKY`` / ``b_KOSPI``: 1 last, 3 percent, 6 date, 7 clock, 8 open, 9 prev."""
    codes = ",".join(code for _, _, code in ASIA)
    response = await client.get(SINA_URL + codes, headers=SINA_HEADERS)
    response.raise_for_status()
    parsed = dict(_SINA_RE.findall(response.content.decode("gbk", "replace")))
    rows: List[Dict[str, Any]] = []
    for label, _, code in ASIA:
        parts = (parsed.get(code) or "").split(",")
        if len(parts) < 12 or parts[6].strip() != today:
            continue
        quote = _quote(parts[8], parts[9], parts[1], parts[3])
        if not quote:
            continue
        rows.append(_row(label, quote, (parts[7] or "")[:5]))
    return rows


async def fetch_asia_open(today: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Nikkei 225 and KOSPI opening prints for today's session, or ``None``.

    Eastmoney first, Sina second. A source that answers with a print dated
    before today is treated as not having opened yet, not as a quote.
    """
    today = today or _today_beijing()
    async with httpx.AsyncClient(
        timeout=TIMEOUT_SECONDS, follow_redirects=True
    ) as client:
        for attempt in (1, 2):
            for source, fetch in (("eastmoney", _from_eastmoney), ("sina", _from_sina)):
                try:
                    rows = await fetch(client, today)
                except Exception as exc:  # noqa: BLE001 - the block is optional
                    logger.warning("Asia open via %s failed: %s", source, exc)
                    continue
                if rows:
                    logger.warning(
                        "Asia open %s via %s: %s",
                        today,
                        source,
                        " ".join(
                            f"{row['name']} {row['last']:,.2f} {row['pct']:+.2f}%"
                            for row in rows
                        ),
                    )
                    return {"rows": rows, "source": source, "date": today}
            if attempt == 1:
                await asyncio.sleep(RETRY_SECONDS)
    logger.warning("Asia open tape unavailable for %s; block skipped", today)
    return None
