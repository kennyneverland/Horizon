"""Main-business profiles for theme members, used by the re-rank pass.

lianban ranks a theme's members by three-month relative strength, so a theme's
leading names can be companies whose business has nothing to do with the theme:
景观设计 sitting in 算力租赁, 有线电视 in 国产芯片. A bare name gives the model
nothing to judge that on, so the re-rank pass is handed each member's main
business line.

Source is Eastmoney's F10 business breakdown: the latest report period's
revenue split by product. One GET per stock, cached for the run, and a failed
lookup leaves the name unannotated rather than dropping it.
"""

import asyncio
import gzip
import json
import logging
import re
import urllib.request
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

PROFILE_URL = (
    "https://emweb.securities.eastmoney.com/PC_HSF10/BusinessAnalysis/PageAjax?code={code}"
)
THS_URL = (
    "https://basic.10jqka.com.cn/fuyao/f10_stock_index/concept/v1/"
    "theme_key_points?subject={subject}"
)
# 同花顺市场号：沪市 17，深市 33。
THS_MARKET = {"6": "17", "0": "33", "3": "33"}
FETCH_TIMEOUT = 8.0
FETCH_CONCURRENCY = 3
# How many of a theme's members to annotate. Set to the full list the model
# sees: a name alone cannot tell 景观设计 from 算力租赁, and a partially
# annotated list would bias the pick toward whichever names carry a profile.
ANNOTATE_LIMIT = 120
# Only products above this revenue share are worth naming.
MIN_RATIO = 0.10
MAX_ITEMS = 3

_CODE_RE = re.compile(r"(\d{6})")
_MAIN_BIZ_RE = re.compile(
    r"[^。；]{0,60}(?:主要从事|核心业务为|主营业务为|专注于)[^。；]{0,140}。"
)
# F10 lines that carry no business information; a company reporting only
# "销售商品99.9%" tells the re-rank nothing, so the THS fallback is used.
_USELESS = ("销售商品", "其他", "主营业务", "商品销售")


def stock_code(member: str) -> Optional[str]:
    """Pull the six-digit code out of a member string, or None."""
    match = _CODE_RE.search(str(member or ""))
    return match.group(1) if match else None


def market_code(code: str) -> str:
    """Eastmoney's market prefix: SH for 6xx, SZ for 0xx/3xx, BJ otherwise."""
    if code.startswith("6"):
        return "SH" + code
    if code.startswith(("0", "3")):
        return "SZ" + code
    return "BJ" + code


def parse_profile(payload: Dict[str, object]) -> str:
    """Turn an F10 payload into '云计算66.8%、通信设备33.0%' or ''.

    Product-level lines are preferred; some companies only report by industry,
    which is coarser but still enough to tell 有线电视 from 光模块.
    """
    rows = payload.get("zygcfx") or []
    if not isinstance(rows, list) or not rows:
        return ""
    dated = [row for row in rows if isinstance(row, dict) and row.get("REPORT_DATE")]
    if not dated:
        return ""
    latest = max(str(row["REPORT_DATE"])[:10] for row in dated)
    for op_type in ("1", "2"):
        picked = [
            row
            for row in dated
            if str(row.get("REPORT_DATE"))[:10] == latest
            and str(row.get("MAINOP_TYPE")) == op_type
        ]
        if not picked:
            continue
        picked.sort(key=lambda row: -float(row.get("MBI_RATIO") or 0))
        parts = []
        for row in picked:
            ratio = float(row.get("MBI_RATIO") or 0)
            name = str(row.get("ITEM_NAME") or "").strip()
            if not name or ratio < MIN_RATIO:
                continue
            parts.append(f"{name}{ratio * 100:.1f}%")
            if len(parts) >= MAX_ITEMS:
                break
        if parts:
            if len(parts) == 1 and any(word in parts[0] for word in _USELESS):
                return ""
            return "、".join(parts)
    return ""


def parse_ths(payload: Dict[str, object]) -> str:
    """Pull the main-business sentence out of THS theme key points.

    Used only when the F10 breakdown says nothing useful. The key points are
    prose about what the company does, so a sentence anchored on 主要从事 /
    主营业务为 is the closest thing to a business line.
    """
    items = payload.get("data") or []
    if not isinstance(items, list):
        return ""
    text = " ".join(
        str(item.get("content") or "") for item in items if isinstance(item, dict)
    )
    match = _MAIN_BIZ_RE.search(text)
    if match:
        return match.group(0).strip()[:120]
    for item in items:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or "").strip()
        if len(content) >= 20:
            return content[:120]
    return ""


class MemberProfiles:
    """Per-run cache of main-business strings, keyed by member string."""

    def __init__(
        self,
        *,
        timeout: float = FETCH_TIMEOUT,
        concurrency: int = FETCH_CONCURRENCY,
    ):
        self.timeout = timeout
        self.concurrency = max(concurrency, 1)
        self._cache: Dict[str, str] = {}

    def _fetch(self, code: str) -> str:
        """F10 breakdown first, THS key points only when that says nothing."""
        return self._fetch_f10(code) or self._fetch_ths(code)

    def _fetch_f10(self, code: str) -> str:
        request = urllib.request.Request(
            PROFILE_URL.format(code=market_code(code)),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                ),
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = response.read()
            # The endpoint gzips some responses regardless of what was asked
            # for, so the header is the only reliable signal.
            if response.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
        payload = json.loads(body.decode("utf-8", "replace"))
        # Under load it answers {"status": -1, "message": "股票代码不合法"} for
        # codes that are perfectly valid; treat it as a transient failure so the
        # caller retries instead of caching an empty profile.
        if isinstance(payload, dict) and payload.get("status") == -1:
            raise ValueError(str(payload.get("message") or "rejected"))
        return parse_profile(payload)

    def _fetch_ths(self, code: str) -> str:
        """THS theme key points, for names the F10 breakdown does not describe."""
        market = THS_MARKET.get(code[:1])
        if not market:
            return ""
        request = urllib.request.Request(
            THS_URL.format(subject=f"{market}-{code}"),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                ),
                "Referer": f"https://basic.10jqka.com.cn/{code}/concept.html",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        if isinstance(payload, dict) and payload.get("status_code") not in (0, None):
            raise ValueError("theme key points rejected")
        return parse_ths(payload)

    async def annotate(self, members: List[str]) -> Dict[str, str]:
        """Map member string -> '主营构成', for the ones that could be fetched."""
        targets = [m for m in members[:ANNOTATE_LIMIT] if stock_code(m)]
        missing = [m for m in targets if m not in self._cache]
        semaphore = asyncio.Semaphore(self.concurrency)

        async def run(member: str) -> None:
            code = stock_code(member)
            if not code:
                return
            async with semaphore:
                profile = ""
                # The endpoint intermittently answers with an empty body under
                # load (three of twenty on a first pass, all of them fine on a
                # retry), so a single attempt would silently thin the list.
                for attempt in range(3):
                    try:
                        profile = await asyncio.to_thread(self._fetch, code)
                        break
                    except Exception as exc:  # noqa: BLE001 - name still works alone
                        if attempt == 2:
                            logger.warning("Profile fetch failed for %s: %s", code, exc)
                        else:
                            await asyncio.sleep(0.4 * (attempt + 1))
                self._cache[member] = profile

        if missing:
            await asyncio.gather(*(run(member) for member in missing))
            hits = sum(1 for member in missing if self._cache.get(member))
            logger.warning(
                "Member profiles: %d/%d fetched for %d requested",
                hits,
                len(missing),
                len(targets),
            )
        return {member: self._cache[member] for member in targets if self._cache.get(member)}


# Business segments, in the order a theme's value chain usually reads. The
# re-rank pass uses these to keep five names from landing in one segment: five
# chip designers move together and give the reader one bet, not five.
SEGMENTS = (
    ("设计", ("芯片设计", "IC设计", "集成电路设计", "设计服务", "IP授权", "EDA",
              "GPU", "CPU", "SoC", "MCU", "存储芯片", "模拟芯片", "射频", "处理器")),
    ("制造", ("晶圆", "代工", "半导体设备", "光刻", "刻蚀", "薄膜", "硅片",
              "电子特气", "光刻胶", "抛光", "制造")),
    ("封测", ("封装", "测试", "封测", "Chiplet", "先进封装")),
    ("整机", ("服务器", "整机", "模组", "光模块", "交换机", "路由器", "终端设备")),
    ("材料", ("材料", "化学品", "靶材", "基板", "覆铜板", "PCB", "印制电路", "铜箔")),
    ("分销", ("分销", "代理", "贸易", "供应链", "批发")),
    ("租赁", ("租赁", "IDC", "数据中心", "机柜", "运营")),
    ("服务", ("软件", "系统集成", "解决方案", "运维", "云服务", "信息技术服务")),
)
# How many members the model sees. The page order is a three-month strength
# ranking, so its tail is rarely picked: on 2026-11-19 the median pick sat at
# position 31 of 120, which made most of the window dead weight.
SHORTLIST_LIMIT = 25
# One segment may supply at most this many of the five names.
MAX_PER_SEGMENT = 2

_RATIO_RE = re.compile(r"(\d+(?:\.\d+)?)%")


def business_strength(profile: str) -> float:
    """Largest revenue share of a *named* business, or 0.5 for prose ones.

    A prose profile from the THS fallback names the business but carries no
    share; treating it as zero would push those names to the back of the
    shortlist for lack of a number rather than for lack of fit.

    其他 is the residual bucket. Its share says the company is concentrated in
    something, not that the theme's business is what it does: a profile of
    「IDC租赁35.0%、其他65.0%」 must not outrank 「芯片设计61.0%」.
    """
    if not profile:
        return 0.0
    ratios = []
    for item in profile.split("、"):
        match = _RATIO_RE.search(item)
        if not match:
            continue
        label = item[: match.start()].strip()
        if label.startswith("其他") or label.startswith("其它"):
            continue
        ratios.append(float(match.group(1)))
    if ratios:
        return max(ratios) / 100.0
    # Nothing but residual lines: fall back to the largest share on record
    # rather than pretending the company has no business at all.
    ratios = [float(value) for value in _RATIO_RE.findall(profile)]
    if ratios:
        return max(ratios) / 100.0
    return 0.5


def segment_of(profile: str) -> str:
    """Which link of the value chain the business sits in, or ''."""
    text = profile or ""
    for segment, words in SEGMENTS:
        if any(word in text for word in words):
            return segment
    return ""


def rank_candidates(
    members: List[str], profiles: Dict[str, str], limit: int = SHORTLIST_LIMIT
) -> List[str]:
    """Shortlist before the model: biggest business first, page order breaks ties.

    Members whose main business is a large share of revenue are the ones a
    theme story can actually move; names sitting in the theme for liquidity
    stay in the tail. Nothing is dropped from the member list itself, only from
    what this pass shows the model.
    """
    scored = []
    for index, member in enumerate(members):
        strength = business_strength(profiles.get(member, ""))
        scored.append((-strength, index, member))
    scored.sort()
    return [member for _, _, member in scored[:limit]]


def diversify(
    picks: List[str],
    profiles: Dict[str, str],
    limit: int = 5,
    max_per_segment: int = MAX_PER_SEGMENT,
    pool: Optional[List[str]] = None,
    label: str = "",
) -> List[str]:
    """Cap how many picks share one value-chain segment.

    Five names from one segment rise and fall together, which is one bet with
    five tickers. Capping a list of five can only re-order it, so the cap is
    inert without alternates: the first version deferred the surplus and then
    filled the line with it again, five in and the same five out.

    The alternates are the theme's other annotated members, strongest business
    first. That is the order the shortlist is built in, so the replacements are
    the names the model could have picked, not arbitrary page-order tail.
    """
    if len(picks) <= 1:
        return picks[:limit]
    if pool is None:
        # sorted() is stable, so equal strengths keep the page order.
        alternates = sorted(
            (name for name in profiles if name not in picks),
            key=lambda name: -business_strength(profiles.get(name, "")),
        )
    else:
        alternates = [name for name in pool if name not in picks]
    segment_by_name = {
        name: segment_of(profiles.get(name, "")) for name in list(picks) + alternates
    }
    known = {segment for segment in segment_by_name.values() if segment}
    if len(known) <= 1:
        # The theme's own members sit in one link of the chain, so there is
        # nothing to diversify into and the model's order stands.
        logger.warning("Rank diversity: single-segment, fallback")
        return picks[:limit]
    kept: List[str] = []
    counts: Dict[str, int] = {}
    deferred: List[str] = []
    for pick in picks:
        segment = segment_by_name.get(pick, "")
        if segment and counts.get(segment, 0) >= max_per_segment:
            deferred.append(pick)
            continue
        kept.append(pick)
        if segment:
            counts[segment] = counts.get(segment, 0) + 1
    # Alternates with a known segment first: a name whose business line could
    # not be read cannot be shown to help the mix, so it only fills after them.
    ordered = [name for name in alternates if segment_by_name.get(name)]
    ordered += [name for name in alternates if not segment_by_name.get(name)]
    for pick in ordered + deferred:
        if len(kept) >= limit:
            break
        if pick in kept:
            continue
        segment = segment_by_name.get(pick, "")
        if segment and counts.get(segment, 0) >= max_per_segment:
            continue
        kept.append(pick)
        if segment:
            counts[segment] = counts.get(segment, 0) + 1
    # A short line is worse than a repeated segment: fill from whatever is
    # left rather than returning four names.
    for pick in list(picks) + ordered + deferred:
        if len(kept) >= limit:
            break
        if pick not in kept:
            kept.append(pick)
    final = kept[:limit]
    # What the cap actually did, and the weakest business fit that survived.
    # Both numbers are needed to read the run: 替换 0 means this pass did
    # nothing and any improvement came from the shortlist alone.
    tally: Dict[str, int] = {}
    for name in final:
        segment = segment_by_name.get(name, "")
        if segment:
            tally[segment] = tally.get(segment, 0) + 1
    logger.warning(
        "Rank diversity%s: %s | 替换 %d 只 | 主营min %.2f",
        f" {label}" if label else "",
        "/".join(f"{segment}{count}" for segment, count in sorted(tally.items()))
        or "none",
        sum(1 for name in final if name not in picks),
        min(
            (business_strength(profiles.get(name, "")) for name in final),
            default=0.0,
        ),
    )
    return final


def render_listing(members: List[str], profiles: Dict[str, str], limit: int) -> str:
    """The candidate list handed to the re-rank model, with business attached."""
    parts = []
    for member in members[:limit]:
        profile = profiles.get(member)
        parts.append(f"{member}｜{profile}" if profile else str(member))
    return "；".join(parts)