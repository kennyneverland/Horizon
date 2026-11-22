"""Asia-Pacific opening tape for the 08:00 digest.

The 08:00 Beijing run lands on the Tokyo and Seoul open: both exchanges ring in
at 09:00 local time, which is 08:00 in Beijing. This is the one block in the
digest that is same-day rather than overnight, so it has to be read live and it
has to prove that it is live.

Eastmoney is the source. Sina's ``b_NKY`` / ``b_KOSPI`` feeds are a fallback
only — the ``int_*`` codes are not used, because ``int_nikkei`` still carries a
44,946 print while the live Nikkei trades at 56,436.

A print whose session date is not today is not an opening quote: it is the
previous close, which is what a Saturday run, or a run before the bell, sees.
The block is dropped in that case rather than printing yesterday's close under
"today's open".
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


def _stamp_date(value: Any) -> str:
    """Unix seconds (Eastmoney ``f86``) → Beijing calendar date, or ``""``."""
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return ""
    if seconds <= 0:
        return ""
    return datetime.fromtimestamp(seconds, BEIJING).strftime("%Y-%m-%d")


def _row(label: str, last: float, pct: float) -> Dict[str, Any]:
    return {"name": label, "last": last, "pct": pct}


async def _from_eastmoney(
    client: httpx.AsyncClient, today: str
) -> List[Dict[str, Any]]:
    """``f2`` last, ``f3`` percent (scaled ×100), ``f14`` name, ``f86`` print time."""
    response = await client.get(
        EM_URL,
        params={
            "fields": "f2,f3,f12,f14,f86",
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
        if not row or _stamp_date(row.get("f86")) != today:
            continue
        try:
            last = float(row["f2"]) / 100
            pct = float(row["f3"]) / 100
        except (KeyError, TypeError, ValueError):
            continue
        if last <= 0:
            continue
        rows.append(_row(label, last, pct))
    return rows


async def _from_sina(
    client: httpx.AsyncClient, today: str
) -> List[Dict[str, Any]]:
    """``b_NKY`` / ``b_KOSPI``: field 1 last, 3 percent, 6 session date."""
    codes = ",".join(code for _, _, code in ASIA)
    response = await client.get(SINA_URL + codes, headers=SINA_HEADERS)
    response.raise_for_status()
    parsed = dict(_SINA_RE.findall(response.content.decode("gbk", "replace")))
    rows: List[Dict[str, Any]] = []
    for label, _, code in ASIA:
        parts = (parsed.get(code) or "").split(",")
        if len(parts) < 7 or parts[6].strip() != today:
            continue
        try:
            last = float(parts[1])
            pct = float(parts[3])
        except (TypeError, ValueError):
            continue
        if last <= 0:
            continue
        rows.append(_row(label, last, pct))
    return rows


async def fetch_asia_open(today: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Nikkei 225 and KOSPI for today's session, or ``None``.

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
                        " ".join(f"{row['name']} {row['pct']:+.2f}%" for row in rows),
                    )
                    return {"rows": rows, "source": source, "date": today}
            if attempt == 1:
                await asyncio.sleep(RETRY_SECONDS)
    logger.warning("Asia open tape unavailable for %s; block skipped", today)
    return None
