"""休市：判定归各取数模块，原因归这一张表。

早报的亚太开盘块和晚报的外盘参考各自都有一层旁证——报价日期。港股 09:30
没开盘、日本勤劳感谢日、台交所台风假，这些从报价日期上一眼就能看出来，所以
「今天开不开市」不需要日历。日历能给的是另一件事：**为什么**。

两件事分开，是因为它们的可靠性不同：

* 判定错了会印出上一交易日的数，那是硬错误，所以只认报价日期，不认日历；
* 原因错了只是措辞不对，所以查得到就写节日名，查不到就只说「休市」，不编。
  ``scripts/lianban_extra.py`` 的美股休市说明早就是这么做的：临时休市（国葬、
  飓风）不在表里，那里也只说「昨夜美股休市」，不给原因。

表只收「落在周一到周五」的休市日：周末本来就不开市，没有原因可写。中国 A 股
另有一层——调休上班的周六周日（如 2027-02-14）证券账户照常休市，那是周末，
同样不进表。

中国 A 股的日期取自国务院办公厅《关于2027年部分节假日安排的通知》
（国办发明电〔2026〕10 号，2026-11-05 发布）。通知给的是放假区间，表里只留
其中落在工作日的那些，所以 2 月 6 日、7 日（周六、周日）不在表内，2 月 5 日、
8 日到 12 日在。每年 11 月通知发布后补一次，改的是数据不是代码。

日本、韩国、香港、台湾四张表先留空：那四地的公众假期各自由当地政府公布，没有
一份能覆盖全部的统一源，逐条录入容易错。空表的实际效果是「今日休市」而不带
节日名——比编一个节日名好，等官方公布后再逐地补。
"""

from __future__ import annotations

from typing import Dict, Optional

# 市场代码 → 中文名。日报里出现的是「日经225」「恒生指数」这类指数名，
# 不是市场名，所以这里只用于日志和兜底文案。
MARKET_NAMES = {
    "CN": "A股",
    "JP": "日本",
    "KR": "韩国",
    "HK": "香港",
    "TW": "台湾",
}

# 2027 年 A 股工作日休市日。放假区间见文件头注释，这里只留工作日：
#   元旦   1/1（周五）
#   春节   2/5（周五）、2/8—2/12（周一至周五）
#   清明   4/5（周一）
#   劳动节 5/3—5/5（周一至周三）
#   端午   6/9（周三）
#   中秋   9/15（周三）
#   国庆   10/1（周五）、10/4—10/7（周一至周四）
_CN_2027: Dict[str, str] = {
    "2027-01-01": "元旦",
    "2027-02-05": "春节",
    "2027-02-08": "春节",
    "2027-02-09": "春节",
    "2027-02-10": "春节",
    "2027-02-11": "春节",
    "2027-02-12": "春节",
    "2027-04-05": "清明节",
    "2027-05-03": "劳动节",
    "2027-05-04": "劳动节",
    "2027-05-05": "劳动节",
    "2027-06-09": "端午节",
    "2027-09-15": "中秋节",
    "2027-10-01": "国庆节",
    "2027-10-04": "国庆节",
    "2027-10-05": "国庆节",
    "2027-10-06": "国庆节",
    "2027-10-07": "国庆节",
}

# 四个亚太市场先留空表。补的时候只加「落在周一到周五」的日期，
# 键写 ``YYYY-MM-DD``、值写当地公布的名字（中文），不需要改任何代码。
_MARKETS: Dict[str, Dict[str, str]] = {
    "CN": _CN_2027,
    "JP": {},
    "KR": {},
    "HK": {},
    "TW": {},
}


# 早报与晚报印的是指数名，不是市场名。休市时拿到的是「日经225」这样的名字，
# 要查原因得先知道它属于哪个市场。这张表就是那一层翻译。
INDEX_MARKETS: Dict[str, str] = {
    "日经225": "JP",
    "韩国KOSPI": "KR",
    "恒生指数": "HK",
    "恒生科技": "HK",
    "台湾加权": "TW",
    # 晚报的 K 线口径用的是短名，同一个市场两种写法都要认。
    "日经": "JP",
    "韩国": "KR",
    "恒指": "HK",
    "恒科": "HK",
    "台湾": "TW",
}


def _day(value: object) -> str:
    """``2027-01-01`` / ``20270101`` / ``2027-01-01 15:00`` → ``2027-01-01``。"""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return str(value or "")[:10]


def reason(day: object, market: str = "CN") -> str:
    """那天那个市场为什么不开市；查不到返回空串。

    空串是正常结果，不是错误：周末、临时休市、还没补进表里的年份都会走到这里。
    调用方拿到空串时只说「休市」，不要拿别的日子或别的市场的原因顶替。
    """
    key = _day(day)
    if not key:
        return ""
    return str((_MARKETS.get(str(market or "CN").upper()) or {}).get(key) or "")


def market_of(index_name: object, default: str = "") -> str:
    """「日经225」→ ``JP``；认不出就返回 ``default``。

    认不出时不猜一个市场：那会把日本的原因安到韩国头上。
    """
    return INDEX_MARKETS.get(str(index_name or "").strip(), default)


def closed_line(name: str, day: object, market: str = "") -> str:
    """「日经225 因勤劳感谢日休市」；查不到原因时「日经225 今日休市」。

    ``name`` 是读者认得的那个名字（指数名或市场名），不是市场代码；``market``
    省略时按指数名推。推不出来、或那天表里没有记录，就只说「休市」。
    """
    label = str(name or "").strip()
    code = str(market or "").upper() or market_of(label)
    if not code:
        return f"{label} 今日休市" if label else "今日休市"
    why = reason(day, code)
    if why:
        return f"{label} 因{why}休市" if label else f"因{why}休市"
    return f"{label} 今日休市" if label else "今日休市"


def cn_closed_line(day: object) -> str:
    """「国内股市因国庆节休市」；查不到原因时「国内股市今日休市」。

    这句用在国内休市的显眼位置：早报正文前的一行提示、晚报诗句原来的位置。
    两种情况下读者最想知道的就是「今天为什么没有盘」。
    """
    why = reason(day, "CN")
    return f"国内股市因{why}休市" if why else "国内股市今日休市"


def known(day: object, market: str = "CN") -> bool:
    """那天是不是表里记着的休市日。

    只用于诊断日志：判定开不开市仍然只认报价日期，这个函数回答不了那个问题。
    """
    return bool(reason(day, market))


def markets_with_table() -> Dict[str, int]:
    """``{"CN": 17, "JP": 0, ...}`` — 每张表收了多少天，给日志用。"""
    return {key: len(value) for key, value in _MARKETS.items()}


def describe(day: object, market: str = "CN") -> Optional[str]:
    """``2027-01-01 是 A股 的 元旦`` — 排查时一眼能看清表里有没有这天。"""
    why = reason(day, market)
    if not why:
        return None
    name = MARKET_NAMES.get(str(market or "CN").upper(), str(market))
    return f"{_day(day)} 是 {name} 的 {why}"
