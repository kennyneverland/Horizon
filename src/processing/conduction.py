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
    r"人民币|亿元|国产|国产化|国产替代|工信部|发改委|证监会|国资委|"
    # A-share tape vocabulary: a story that names a board, a sector or a fund
    # is already quoted on the domestic market even when it names no issuer.
    # Measured on 2026-11-23: without these, "多只机器人ETF涨超3%" and
    # "黄金股ETF涨超3%" were dropped while the sector itself was moving.
    r"板块|概念股|ETF|指数|成分股|涨超|涨逾|异动|拉升|封板|连板|首板|"
    r"流通市值|主力资金|两融|融资余额"
)

# Chinese issuers whose supply chain is quoted in A shares even when the issuer
# itself is listed elsewhere (H shares, US ADRs, or not listed at all).
_CHINA_ENTITY = re.compile(
    r"腾讯|阿里|百度|字节|华为|小米|美团|京东|网易|拼多多|比亚迪|宁德时代|"
    r"中芯国际|浪潮信息|寒武纪|海光信息|北方华创|中微公司|长电科技|通富微电|"
    r"华天科技|晶方科技|沪电股份|深南电路|工业富联|中兴通讯|紫光股份|"
    r"神州数码|润泽科技|光环新网|英维克|中科曙光|科大讯飞|拓维信息"
)

# A national industry policy names the segment it is written for, so the
# document itself is the carrier: 国务院印发新能源汽车产业规划 reaches every
# listed maker without naming one.
_NATIONAL_POLICY = re.compile(
    r"(国务院|国常会|中共中央|工信部|工业和信息化部|国家发改委|发改委|国家数据局|"
    r"国家能源局|财政部|科技部|国资委|国家网信办|国家医保局|国家药监局)"
    r".{0,40}(规划|意见|方案|通知|办法|条例|行动计划|指导意见|若干措施|试点)"
)

# A metal price is the earnings input for the miners A shares list, so a quote
# alone is a carrier: 金价 moves 山东黄金 and 赤峰黄金 before any order is named.
_COMMODITY = re.compile(r"黄金|金价|贵金属|金矿|白银|银价")

# Domestic-only context: a Chinese market story without a named issuer still
# belongs to the A-share tape.
_DOMESTIC = re.compile(
    r"国内|我国|中国|中方|央行|交易所|银行间|财政部|商务部|沪深两市|"
    # 外媒报道中国的稿子标题与正文都是英文，只认中文会把它们全部误杀：
    # 2026-11-27 SCMP 的「China pushes brain-computer interface…」就是这样
    # 被判成落不到 A 股，而同一天中文源里的同一件事照常入榜。
    r"\bChina\b|\bChinese\b|\bBeijing\b|\bShanghai\b|\bShenzhen\b|"
    r"\bGuangdong\b|\bPBOC\b|\bNDRC\b|\bMIIT\b|\bCAC\b|\bCSRC\b",
    re.IGNORECASE,
)

# An industry segment A shares actually cover.
_SEGMENT = re.compile(
    r"封装|封测|晶圆|代工|光模块|光通信|HBM|高带宽内存|存储芯片|"
    r"PCB|覆铜板|液冷|温控|服务器|交换机|光刻|刻蚀|薄膜沉积|清洗设备|"
    r"探针台|靶材|电子特气|硅片|功率器件|模拟芯片|基板|测试厂|"
    r"算力|数据中心|IDC|机柜|连接器|先进制程|炼油|炼化|成品油|原油|"
    # New-energy segments: without these the ten-day weight could never fire on
    # 光伏 or 储能, which are lines the page tracks every session.
    r"光伏|电池片|组件|硅料|逆变器|储能|锂电|电解液|正极|负极|隔膜|风电|"
    # 医药这条线原先整条缺失：_SEGMENT 里全是制造环节，海外医疗新闻即使点名
    # 了 A 股有的题材（脑机接口、医疗器械都在 797 个题材目录里）也一律被判成
    # 落不到 A 股。2026-11-27 Neuralink 获 FDA 批准那条就是这样丢的标的。
    # 只补这四个词，不放开「临床」「药」这类泛词。
    r"脑机接口|医疗器械|创新药|生物医药"
)

# The hop that turns a foreign event into an A-share order: capacity, supply,
# price, customer. Without one the segment mention is only a shared noun.
_BRIDGE = re.compile(
    r"产能|供应|供货|订单|涨价|提价|断供|缺货|受限|减产|扩产|投产|建厂|兴建|"
    r"导入|验证|外溢|转单|上调|下调|报价|"
    # Policy-side supply changes: an export rule that squeezes a segment is a
    # bridge to the same segment in A shares, not a shared noun.
    r"限制|管制|禁令|制裁|关税|封锁|挤压|"
    # 医药的两跳桥不是产能与订单，是审批节点：获批、进入临床、拿到注册证，
    # 才是海外进展能落到国内同环节公司的那个动作。
    r"获批|批准|临床|上市许可|注册证|适应症"
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
    if (
        _STRONG.search(text)
        or _CHINA_ENTITY.search(text)
        or _DOMESTIC.search(text)
        or _COMMODITY.search(text)
        or _NATIONAL_POLICY.search(text)
    ):
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
