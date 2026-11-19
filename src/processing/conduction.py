"""Whether a story can reach an A-share carrier at all.

The theme index matches on wording, so a story that says 算力 or 数据中心
matches those themes whether or not anything in it can reach an A-share
company. On 2026-11-19 four Anthropic IPO stories carried seven theme lines
and twenty-five member slots without naming a single A-share issuer, and six
of those seven lines fell that day.

One question per story: can the subject be traced, in at most two hops, to an
A-share segment? A story that cannot is left without themes rather than
pointed at the closest-sounding list.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# A named issuer, a market mechanic, or China-only policy vocabulary. Any one
# of these means the story already has a domestic carrier on the page.
_STRONG = re.compile(
    r"A股|沪深|沪市|深市|创业板|科创板|北交所|沪股通|深股通|北向资金|"
    r"中标|订单|合同|公告|定增|回购|涨停|跌停|龙虎榜|"
    r"人民币|亿元|国产|国产化|国产替代|工信部|发改委|证监会|国资委"
)

# Chinese issuers whose supply chain is quoted in A shares even when the issuer
# itself is listed elsewhere (H shares, US ADRs, or not listed at all).
_CHINA_ENTITY = re.compile(
    r"腾讯|阿里|百度|字节|华为|小米|美团|京东|网易|拼多多|比亚迪|宁德时代|"
    r"中芯国际|浪潮信息|寒武纪|海光信息|北方华创|中微公司|长电科技|通富微电|"
    r"华天科技|晶方科技|沪电股份|深南电路|工业富联|中兴通讯|紫光股份|"
    r"神州数码|润泽科技|光环新网|英维克|中科曙光|科大讯飞|拓维信息"
)

# Domestic-only context: a Chinese market story without a named issuer still
# belongs to the A-share tape.
_DOMESTIC = re.compile(
    r"国内|我国|中国市场|中国客户|中国厂商|中方|央行|交易所|银行间|财政部|商务部|沪深两市"
)

# An industry segment A shares actually cover.
_SEGMENT = re.compile(
    r"封装|封测|晶圆|代工|光模块|光通信|HBM|高带宽内存|存储芯片|"
    r"PCB|覆铜板|液冷|温控|服务器|交换机|光刻|刻蚀|薄膜沉积|清洗设备|"
    r"探针台|靶材|电子特气|硅片|功率器件|模拟芯片|基板|测试厂|"
    r"算力|数据中心|IDC|机柜|连接器|先进制程|炼油|炼化|成品油|原油"
)

# The hop that turns a foreign event into an A-share order: capacity, supply,
# price, customer. Without one the segment mention is only a shared noun.
_BRIDGE = re.compile(
    r"产能|供应|供货|订单|涨价|提价|断供|缺货|受限|减产|扩产|投产|建厂|兴建|"
    r"导入|验证|外溢|转单"
)


def conduction_filter(
    themes: list[dict[str, Any]], text: str, item_id: str = ""
) -> list[dict[str, Any]]:
    """Drop themes the story cannot trace to an A-share carrier.

    A named issuer, a China-market mechanic or a domestic context is a direct
    carrier. A segment plus a bridging clause is a two-hop carrier: kept, but
    marked so the digest can show it rests on a link rather than a name.
    Anything else is a wording match and is dropped.
    """
    if not themes:
        return themes
    if _STRONG.search(text) or _CHINA_ENTITY.search(text) or _DOMESTIC.search(text):
        return themes
    if _SEGMENT.search(text) and _BRIDGE.search(text):
        for theme in themes:
            theme["conduction"] = "环节映射"
        return themes
    logger.warning(
        "Conduction gate dropped %s | %s | %s",
        "、".join(str(theme.get("name") or "") for theme in themes),
        item_id,
        " ".join(text.split())[:40],
    )
    return []


def direction_note(theme: dict[str, Any]) -> str:
    """The parenthetical after a theme's name: its reason, plus the link marker.

    A theme kept on a two-hop link says so where the reader already looks for
    the reason, so the line does not stack a second bracket after the first.
    """
    reason = str(theme.get("direction_reason") or "").strip()
    link = "环节映射" if theme.get("conduction") else ""
    if reason and link:
        return f"{reason}；{link}"
    return reason or link
