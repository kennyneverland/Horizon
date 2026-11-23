"""Weight themes by how consistently the market traded them over ten days.

One day of limit-ups is a rotation; the same line showing up six days out of
ten is what the market is actually paying for. The snapshot lianban publishes
already carries ten trading days of per-line limit-up counts, so the ten-day
view needs no extra request — it is a read of the file the after-close brief
already refreshes.

The weight is deliberately a coarse ladder rather than a fitted score. A
reader can check it: "this line had limit-ups on 7 of the last 10 sessions"
is a statement about the tape, not a model output.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path("data/mainline_snapshot.json")

# lianban's own roll-up: an industry line -> the theme rows that belong to it.
LINE_MAP_PATH = Path("data/mainline_map.json")

# (min days present out of ten, bonus)
LADDER = ((6, 1.0), (4, 0.6), (2, 0.3))

# Rows that are not industry lines.
PSEUDO_LINES = ("未归类", "事件驱动", "当日涨停")

# A line the page marked as overheated within this many sessions is still
# falling back, so a story on it gets no lift: the point of the weight is to
# follow a line being accumulated, not one that just ran.
OVERHEAT_WINDOW = 2

# A-share pricing runs on expectation. A policy or a price change creates one;
# an order or a contract confirms one that has already been paid for. So the
# carrier gate still accepts 订单/中标/合同 as proof of a carrier, but they earn
# no weight here, and neither does a local-government plan.
SIGNAL_WEIGHT = 1.0

# The 中国股市 board has to stay distinguishable from 财经要闻: at least this
# share of its items must trace to an A-share theme, or the board is just a
# second finance page. Items that cannot are marked down, not dropped.
LANDING_FLOOR = 0.6
UNMATCHED_PENALTY = 0.3

_NATIONAL_BODY = re.compile(
    r"国务院|国常会|中共中央|中央经济工作会议|工信部|工业和信息化部|"
    r"国家发改委|发改委|国家数据局|国家能源局|财政部|科技部|国资委|"
    r"国家网信办|国家医保局|国家药监局|国家市场监管总局"
)
_INDUSTRY = re.compile(
    r"人工智能|AI|算力|芯片|半导体|集成电路|新能源|光伏|储能|锂电|机器人|"
    r"数据要素|6G|量子|低空|商业航天|生物制造|新材料|智能网联|自动驾驶|"
    r"新型基础设施|新型电网|国产替代"
)
# Market mechanics the exchange or the regulator changes: these move the tape
# before anything is delivered, which is the same expectation a policy carries.
_MARKET_RULE = re.compile(
    r"融资保证金|两融|融资融券|做市商|印花税|减持新规|注册制|转融通|"
    r"降准|降息|平准基金|汇金|国家队|IPO 节奏|再融资"
)
# Delivered rather than expected: an order, a contract or a local plan is the
# end of a story the market has already traded, so it earns no weight even when
# the line it touches is hot.
_CONFIRMATION = re.compile(
    r"中标|订单|合同|签约|框架协议|采购协议|政府补助|财政补贴|"
    r"地方政府|地方政策|省级|市级|区级"
)
_PRICE_HIKE = re.compile(
    r"涨价|提价|价格上调|上调.{0,6}(价格|报价|售价)|涨价函|缺货|断供|"
    r"供不应求|产能紧张|排产.{0,4}(满|提升|上调)"
)


def _read(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - no snapshot means no weighting
        return {}


def load_weights(path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Theme -> {days, total, weight} over the last ten trading sessions.

    ``days`` is how many of the ten sessions the line recorded a limit-up;
    ``total`` is the sum of those counts; ``weight`` is the ladder bonus the
    scorer adds. A line with no limit-up in ten sessions is absent from the
    map rather than present with a zero.
    """
    doc = _read(path or SNAPSHOT_PATH)
    dates: List[str] = list(doc.get("dates") or [])
    if not dates:
        return {}
    window = dates[:10]
    recent = dates[:OVERHEAT_WINDOW]
    overheat: Dict[str, List[str]] = doc.get("overheat") or {}
    out: Dict[str, Dict[str, Any]] = {}
    for line, counts in (doc.get("lines") or {}).items():
        if not line or line in PSEUDO_LINES or not isinstance(counts, dict):
            continue
        days = 0
        total = 0
        for day in window:
            try:
                n = int(counts.get(day) or 0)
            except (TypeError, ValueError):
                continue
            if n > 0:
                days += 1
                total += n
        if days == 0:
            continue
        weight = 0.0
        for need, bonus in LADDER:
            if days >= need:
                weight = bonus
                break
        hot = [day for day in (overheat.get(line) or []) if day in recent]
        out[line] = {
            "days": days,
            "total": total,
            "weight": weight,
            "overheat": bool(hot),
        }
    return out


def load_line_map(path: Optional[Path] = None) -> Dict[str, List[str]]:
    """Theme row -> the industry lines it rolls up into.

    The snapshot counts limit-ups per industry line (算力, 芯片, PCB), while the
    theme index answers in theme rows (算力概念, 存储芯片, 印制电路板). Without
    this map only the handful of lines whose name is also a theme row would
    ever weigh anything: four of sixteen, measured on the 2026-11-18 snapshot.
    A row that belongs to two lines keeps both and is weighted by the stronger.
    """
    doc = _read(path or LINE_MAP_PATH)
    out: Dict[str, List[str]] = {}
    for line, themes in (doc.get("lines") or {}).items():
        if not line or not isinstance(themes, list):
            continue
        for theme in themes:
            name = str(theme or "").strip()
            if name:
                out.setdefault(name, []).append(str(line))
    return out


def lines_for(
    themes: List[str], line_map: Dict[str, List[str]]
) -> List[str]:
    """The industry lines a story's theme rows roll up into."""
    out: List[str] = []
    for theme in themes or []:
        for line in line_map.get(theme) or ([theme] if theme else []):
            if line not in out:
                out.append(line)
    return out


def bonus_for(
    themes: List[str],
    weights: Dict[str, Dict[str, Any]],
    line_map: Optional[Dict[str, List[str]]] = None,
) -> float:
    """The largest ladder bonus among a story's lines.

    Each theme row is resolved to its industry line first, so 存储芯片 is
    weighed as 芯片 and 算力租赁 as 算力. Taking the max rather than the sum
    stops a story that touches three persistent lines from running away with
    the score.
    """
    best = 0.0
    for line in lines_for(themes, line_map or {}):
        hit = weights.get(line) or {}
        if hit.get("overheat"):
            continue
        weight = float(hit.get("weight") or 0.0)
        if weight > best:
            best = weight
    return best


def overheated_lines(
    themes: List[str],
    weights: Dict[str, Dict[str, Any]],
    line_map: Optional[Dict[str, List[str]]] = None,
) -> List[str]:
    """The story's lines the page flagged as overheated in the last sessions."""
    out: List[str] = []
    for line in lines_for(themes, line_map or {}):
        hit = weights.get(line) or {}
        if hit.get("overheat") and line not in out:
            out.append(line)
    return out


def signal_bonus(text: str) -> Tuple[float, str]:
    """The lift a story earns from what kind of news it is.

    Three kinds create an expectation before it is delivered: a national
    industry policy, a market rule the exchange or regulator changes, and a
    price move along the chain. Measured on the 2026-11-23 pool: 融资保证金
    比例下调 and AI 服务器涨价 45% both moved the tape with no order signed,
    while 订单/中标/合同 and 地方规划 only confirmed what was already bought.
    """
    body = text or ""
    if _NATIONAL_BODY.search(body) and _INDUSTRY.search(body):
        return SIGNAL_WEIGHT, "国家级产业政策"
    if _MARKET_RULE.search(body):
        return SIGNAL_WEIGHT, "市场制度"
    if _PRICE_HIKE.search(body):
        return SIGNAL_WEIGHT, "产业链涨价"
    return 0.0, ""


def is_confirmation(text: str) -> bool:
    """True for news that confirms an expectation rather than creating one."""
    return bool(_CONFIRMATION.search(text or ""))


def describe(weights: Dict[str, Dict[str, Any]], limit: int = 8) -> str:
    """One line for the run log: the persistent lines, strongest first."""
    rows = sorted(weights.items(), key=lambda x: (-x[1]["days"], -x[1]["total"]))
    shown = [
        f"{name}({hit['days']}/10{'·过热' if hit.get('overheat') else ''})"
        for name, hit in rows[:limit]
        if hit["weight"] > 0
    ]
    return "、".join(shown)
