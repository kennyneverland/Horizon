"""今天开不开市：早报里「今天要关注什么」得先答这一问。

2026-11-28 是周六，早报照样印了一整块「今日建议关注题材」——内容是 11-27 晚报
的判断，读起来却是今天的。数据没错，是没人问过今天开不开市。

判据不靠日历，靠报价日期：东财涨停池对非交易日不报错，回最近交易日的池子，
只在 ``data.qdate`` 里写明是哪天的。qdate 不等于请求日，就是那天没开市。同一条
规则 ``opening._pool`` 已经用过一次，所以这里不重复取数——开盘块当天落了快照，
就说明池子答的是当天；只有快照缺席（开盘任务失败、或今天本来就没开市）才问一次。

工作日休市（元旦、国庆）只有这条路能认出来：星期几判断不到它们。
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 与 opening.EM_ZT_URL / EM_UT / EM_HEADERS 同一个接口、同一套参数：换一处不换
# 另一处，两边就会对「今天有没有池子」给出不同答案。
POOL_URL = "https://push2ex.eastmoney.com/getTopicZTPool"
EM_UT = "7eea3edcaed734bea9cbfc24409ed989"
EM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; HorizonDigest/1.0; "
        "+https://github.com/kennyneverland/Horizon)"
    ),
    "Referer": "https://quote.eastmoney.com/",
}
# opening.STORE 写的就是这个目录；这里不 import opening，是为了让本模块在没装
# httpx 的环境里也能单独跑（测试、脚本）。
DEFAULT_STORE = Path("data/opening")


def _compact(day: str) -> str:
    return str(day or "").replace("-", "").strip()


def _snapshot(day: str, store: Path) -> bool:
    """开盘块当天落了快照，就是它已经拿到当天的池子。"""
    try:
        return (Path(store) / f"{_compact(day)}.json").is_file()
    except OSError:
        return False


def _asked(day: str, timeout: float) -> Optional[str]:
    """问一次东财：池子答的是哪一天。``None`` 表示没问出结果。"""
    params = urllib.parse.urlencode(
        {
            "ut": EM_UT,
            "dpt": "wz.ztzt",
            "Pageindex": "0",
            "pagesize": "1",
            "sort": "fbt:asc",
            "date": _compact(day),
        }
    )
    request = urllib.request.Request(
        f"{POOL_URL}?{params}", headers=EM_HEADERS
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            import gzip

            raw = gzip.decompress(raw)
    data = json.loads(raw.decode("utf-8", "replace")).get("data") or {}
    if not isinstance(data, dict):
        return None
    return str(data.get("qdate") or "").strip() or None


def opened(day: str, store: Optional[Path] = None, timeout: float = 8.0) -> Optional[bool]:
    """那天开市了吗。True 开市 / False 休市 / None 判不出来。

    ``None`` 只在两种情况下出现：快照缺席且东财没答上来（网络、限流、改版）。
    调用方按「判不出来」处理，不要把它当成休市——那是两件事。
    """
    if not _compact(day):
        return None
    if _snapshot(day, store or DEFAULT_STORE):
        return True
    try:
        answered = _asked(day, timeout)
    except Exception as exc:  # noqa: BLE001 - 问不到就不下结论
        logger.info("session probe %s failed (%s)", day, exc)
        return None
    if not answered:
        return None
    if answered == _compact(day):
        return True
    logger.info("session probe %s: pool answered %s", day, answered)
    return False
