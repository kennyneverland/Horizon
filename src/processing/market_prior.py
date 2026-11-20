"""把「昨天谁真的被买了」挂到今天的票上。

早报的成员表来自 lianban 题材页，而那张表按三个月相对强度排序：一个题材
第一次出现时印出的五只票，和昨天有没有人买它们无关。2026-11-20 早报 63
只票里，只有 9 只在前一交易日的涨停池、晚报三类或龙虎榜上出现过——读者
看不出哪只是纸面成员，哪只是市场真在买的。

这个模块只做一件事：读前一交易日的涨停池、炸板池和龙虎榜，给每只票一句
不超过十个字的注脚。它不排序、不替换、不改变名单长度，读不到就什么都不加。
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional

from . import eastmoney

logger = logging.getLogger(__name__)

# 长假最多连着放八天，再加上周末，十天足够回退到上一个交易日。
LOOKBACK_DAYS = 10
SHANGHAI = timezone(timedelta(hours=8))

_TICKER_RE = re.compile(r"^(.*?)\s*[（(](\d{6})[)）]\s*$")


def _norm(text: Any) -> str:
    """东财的票名带空格（``红 宝 丽``），按名字匹配前先抹平。"""
    return re.sub(r"\s+", "", str(text or ""))


def member_name(member: Any) -> str:
    """``三佳科技（600520）`` → ``三佳科技``；没有代码的原样返回。"""
    raw = str(member or "").strip()
    match = _TICKER_RE.match(raw)
    return _norm(match.group(1)) if match else _norm(raw)


def _today() -> date:
    return datetime.now(SHANGHAI).date()


def _codes(doc: Dict[str, Any]) -> set[str]:
    return {str(row.get("c") or "") for row in doc.get("rows") or [] if row.get("c")}


def _session(day: date) -> Optional[tuple[date, Dict[str, Any], Dict[str, Any]]]:
    """最近一个真交易日，用涨停池自身比对出来。

    池子接口对非交易日不报错，而是回落到最近一个交易日：请求周六拿到的是
    周五的行，响应里的 ``qdate`` 只是服务器当天，都不能用来给数据贴日期。
    但同一个日期 D 与 D-1 的涨停名单相同，只可能是「D 没开市、两次都回落到
    同一个交易日」——两个真交易日不可能有完全一样的涨停名单。
    """
    probe = day - timedelta(days=1)
    for _ in range(LOOKBACK_DAYS):
        zt = _pool("ZT", probe)
        if not zt.get("rows"):
            probe -= timedelta(days=1)
            continue
        before = _pool("ZT", probe - timedelta(days=1))
        if _codes(zt) != _codes(before):
            zb = _pool("ZB", probe)
            return probe, zt, zb
        probe -= timedelta(days=1)
    return None


def _pool(topic: str, day: date, attempts: int = 2) -> Dict[str, Any]:
    """一次短读会让标注静默变少，所以行数不足总数时重试一次。"""
    doc: Dict[str, Any] = {}
    for attempt in range(attempts):
        doc = eastmoney.pool(topic, day.isoformat())
        rows = doc.get("rows") or []
        total = int(doc.get("count") or 0)
        if not total or len(rows) >= total:
            return doc
        if attempt + 1 < attempts:
            time.sleep(0.6)
    logger.warning(
        "Pool %s %s short read: %d/%s rows",
        topic,
        day.isoformat(),
        len(doc.get("rows") or []),
        doc.get("count"),
    )
    return doc


def _board_note(row: Dict[str, Any], prefix: str) -> str:
    """涨停票的注脚：连板优先，其次「N 天 M 板」，最后是首板。"""
    boards = int(row.get("boards") or 0)
    if boards >= 2:
        note = f"{prefix}{boards}连板"
        if boards >= 3:
            # 三连板以上不是低位机会，标注要自己说清楚。
            note += "·位置偏高"
        return note
    days = int(row.get("days") or 0)
    times = int(row.get("times") or 0)
    if times >= 2 and days:
        return f"{prefix}{days}天{times}板"
    return f"{prefix}涨停"


def _lhb_note(row: Dict[str, Any]) -> str:
    net = str(row.get("net") or "").strip()
    if not net:
        return ""
    side = "净买" if net.startswith("+") else "净卖" if net.startswith("-") else ""
    amount = net.lstrip("+-").replace(" ", "").strip()
    if not side or not amount:
        return ""
    return f"龙虎榜{side}{amount}"


@dataclass
class MarketPrior:
    """前一交易日的三份事实，按票名索引。"""

    date: str = ""
    # 周一运行时上一交易日是周五，说「昨」会错；间隔超过一天就写日期。
    prefix: str = "昨"
    limit_up: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    broken: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    lhb: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def available(self) -> bool:
        return bool(self.limit_up or self.broken or self.lhb)

    def note(self, member: Any) -> str:
        """一只票的注脚；没有事实就返回空串。"""
        name = member_name(member)
        if not name:
            return ""
        row = self.limit_up.get(name)
        if row:
            return _board_note(row, self.prefix)
        if name in self.broken:
            return f"{self.prefix}炸板"
        row = self.lhb.get(name)
        if row:
            return _lhb_note(row)
        return ""

    def notes_for(self, members: Iterable[Any]) -> Dict[str, str]:
        """``{成员原串: 注脚}``，只留命中的，供渲染层按原样查表。"""
        out: Dict[str, str] = {}
        for member in members:
            note = self.note(member)
            if note:
                out[str(member)] = note
        return out


def load(day: Optional[date] = None) -> MarketPrior:
    """读前一交易日的涨停、炸板与龙虎榜；任何一步失败都返回空表。"""
    try:
        found = _session(day or _today())
        if not found:
            logger.warning("Market prior: no session in the last %d days", LOOKBACK_DAYS)
            return MarketPrior()
        session, zt, zb = found
        gap = ((day or _today()) - session).days
        prior = MarketPrior(
            date=session.isoformat(),
            prefix="昨" if gap == 1 else f"{session.month}-{session.day}",
        )
        for row in zt.get("rows") or []:
            name = _norm(row.get("n"))
            if not name:
                continue
            stats = row.get("zttj") or {}
            prior.limit_up[name] = {
                "boards": row.get("lbc") or 0,
                "days": stats.get("days") or 0,
                "times": stats.get("ct") or 0,
                "industry": row.get("hybk") or "",
            }
        for row in zb.get("rows") or []:
            name = _norm(row.get("n"))
            if name:
                prior.broken[name] = {"boards": row.get("lbc") or 0}
        for row in (eastmoney.lhb(session.isoformat()).get("items") or []):
            name = _norm(row.get("name"))
            if name:
                prior.lhb[name] = {"net": row.get("net") or "", "reason": row.get("reason") or ""}
        logger.warning(
            "Market prior %s (%s): %d 涨停 %d 炸板 %d 龙虎榜",
            prior.date,
            prior.prefix,
            len(prior.limit_up),
            len(prior.broken),
            len(prior.lhb),
        )
        return prior
    except Exception as exc:  # noqa: BLE001 - 标注缺席不该让早报失败
        logger.warning("Market prior unavailable: %s", exc)
        return MarketPrior()


_STATE: Optional[MarketPrior] = None


def load_state() -> MarketPrior:
    """一次 run 只取一次。"""
    global _STATE
    if _STATE is None:
        _STATE = load()
    return _STATE


def reset_state() -> None:
    global _STATE
    _STATE = None
