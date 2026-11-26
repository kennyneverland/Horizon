#!/usr/bin/env python3
"""今日人气榜：同花顺 + 东方财富两源，按连板网公布的规则合并。

连板网的综合人气榜把同花顺、东方财富、开盘啦三份榜单合在一起，取前 10。
它的口径写在榜单页上：先按同时上榜的来源数排序，来源数相同时综合各榜名次；
每源取前 50 名，不直接相加原始热度。这里只取前两家——开盘啦的接口要完整
签名参数（2026-11-26 实测返回 1020 参数出错），公开入口取不到，不值得为它
引入一个随时会坏的依赖。

因此本榜与连板网那份**不是同一份数据**：少了开盘啦一列，第 10 名附近会不同。
页面上必须写明这一点，读者才不会被两个「人气榜」弄混。

历史落在一个文件里（data/renqi/history.jsonl），每天一行，用来算：
  · 连续上榜天数
  · 近 30 日上榜次数
  · 近 1 年上榜次数

只用标准库：它在 Actions job 里原样跑，不引额外依赖。
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date as _date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

THS_URL = (
    "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"
    "?stock_type=a&type=day&list_type=normal"
)
EM_URL = "https://emappdata.eastmoney.com/stockrank/getAllCurrentList"
EM_QUOTE_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"

# 连板网每源取前 50，这里跟着它，否则「上榜」的含义会和它不一样。
PER_SOURCE = 50
TOP_N = 10

HISTORY_PATH = Path("data/renqi/history.jsonl")

# 连续天数的判定：历史里缺一天就断。周末与假期本来就没有交易日，所以只有
# 相邻两条记录相隔超过 5 个日历日，才当成「那天没跑、连续记录已断」，不去猜
# 中间到底上没上榜。宁可少算一天，也不给一个查不到的连续天数。
MAX_GAP_DAYS = 5


def _get(url: str, data: Optional[bytes] = None, timeout: float = 25.0,
         headers: Optional[Dict[str, str]] = None, retries: int = 1) -> bytes:
    """一次 GET/POST；超时与连接类错误退避 1.5 秒再试一次，4xx 不重试。"""
    last: Optional[BaseException] = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(
            url, data=data, headers={"User-Agent": UA, **(headers or {})}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500:
                raise
            last = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
        if attempt < retries:
            time.sleep(1.5)
    assert last is not None
    raise last


def _pct(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    return f"{value:+.2f}%"


def fetch_ths() -> Dict[str, Dict[str, Any]]:
    """同花顺人气日榜：名次、名称、涨跌幅、两个概念、上榜标签。"""
    raw = _get(THS_URL, headers={"Referer": "https://eq.10jqka.com.cn/"})
    doc = json.loads(raw.decode("utf-8", "replace"))
    if doc.get("status_code") not in (0, None):
        raise ValueError(f"ths status_code={doc.get('status_code')}")
    out: Dict[str, Dict[str, Any]] = {}
    for item in ((doc.get("data") or {}).get("stock_list") or []):
        code = str(item.get("code") or "").strip()
        rank = item.get("order")
        if not code or not isinstance(rank, int):
            continue
        tag = item.get("tag") or {}
        out[code] = {
            "rank": rank,
            "name": str(item.get("name") or "").strip(),
            "pct": _pct(item.get("rise_and_fall")),
            "concepts": [str(x).strip() for x in (tag.get("concept_tag") or []) if str(x).strip()][:2],
            "tag": str(tag.get("popularity_tag") or "").strip(),
        }
    if not out:
        raise ValueError("ths returned no rows")
    return out


def fetch_em() -> Dict[str, Dict[str, Any]]:
    """东方财富人气榜：只有代码与名次，名称和涨跌幅要另取一次。"""
    payload = json.dumps({
        "appId": "appId01",
        "globalId": "786e4c21-70dc-435a-93bb-38",
        "marketType": "",
        "pageNo": 1,
        "pageSize": 100,
    }).encode()
    raw = _get(EM_URL, data=payload, headers={
        "Content-Type": "application/json",
        "Referer": "https://guba.eastmoney.com/",
    })
    doc = json.loads(raw.decode("utf-8", "replace"))
    out: Dict[str, Dict[str, Any]] = {}
    for item in (doc.get("data") or []):
        sc = str(item.get("sc") or "")
        rank = item.get("rk")
        if len(sc) < 8 or not isinstance(rank, int):
            continue
        out[sc[2:]] = {"rank": rank, "market": sc[:2]}
    if not out:
        raise ValueError("eastmoney returned no rows")
    return out


def em_quotes(em: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """补东财榜里那些不在同花顺榜上的票：名称与当日涨跌幅。"""
    codes = [c for c in em if em[c]["rank"] <= PER_SOURCE]
    if not codes:
        return {}
    secids = ",".join(
        ("0." if em[c]["market"] == "SZ" else "1.") + c for c in codes
    )
    raw = _get(f"{EM_QUOTE_URL}?secids={secids}&fields=f12,f14,f3&fltt=2")
    doc = json.loads(raw.decode("utf-8", "replace"))
    out: Dict[str, Dict[str, Any]] = {}
    for row in ((doc.get("data") or {}).get("diff") or []):
        code = str(row.get("f12") or "")
        if code:
            out[code] = {"name": str(row.get("f14") or ""), "pct": _pct(row.get("f3"))}
    return out


def merge(
    ths: Dict[str, Dict[str, Any]],
    em: Dict[str, Dict[str, Any]],
    quotes: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """两源合并。

    排序键就是连板网写的那条：来源数降序 → 平均名次升序。平均名次相同
    （两源同分只有一种可能：名次互换）时按同花顺名次、再按东财名次定序，
    与它页面上的展示顺序一致。
    """
    rows: List[Dict[str, Any]] = []
    for code in set(ths) | set(em):
        ths_rank = (ths.get(code) or {}).get("rank")
        em_rank = (em.get(code) or {}).get("rank")
        ranks = [r for r in (ths_rank, em_rank) if isinstance(r, int) and r <= PER_SOURCE]
        if not ranks:
            continue
        rows.append({
            "code": code,
            "name": (ths.get(code) or {}).get("name") or (quotes.get(code) or {}).get("name") or code,
            "pct": (ths.get(code) or {}).get("pct") or (quotes.get(code) or {}).get("pct") or "",
            "n": len(ranks),
            "mean": sum(ranks) / len(ranks),
            "ths": ths_rank if isinstance(ths_rank, int) and ths_rank <= PER_SOURCE else None,
            "em": em_rank if isinstance(em_rank, int) and em_rank <= PER_SOURCE else None,
            "concepts": (ths.get(code) or {}).get("concepts") or [],
            "tag": (ths.get(code) or {}).get("tag") or "",
        })
    rows.sort(key=lambda r: (-r["n"], r["mean"], r["ths"] or 999, r["em"] or 999, r["code"]))
    return rows


def load_history(path: Path = HISTORY_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    records: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except ValueError:
            continue
        if doc.get("date") and isinstance(doc.get("rows"), list):
            records.append(doc)
    records.sort(key=lambda d: str(d["date"]))
    return records


def save_history(records: Sequence[Dict[str, Any]], path: Path = HISTORY_PATH) -> None:
    """整份重写：一天一行，按日期升序。

    只替换当天那一行，其余原样保留，所以 git 上每天只多一行（重跑则改一行），
    不会因为重写把整份文件的每一行都标成改动。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in records
    )
    path.write_text(body + ("\n" if body else ""), encoding="utf-8")


def _as_date(value: Any) -> Optional[_date]:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def stats_for(code: str, day: str, history: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """连续天数、近 30 日次数、近 1 年次数（三项都含今天）。"""
    today = _as_date(day)
    if today is None:
        return {"streak": 1, "d30": 1, "d365": 1}
    past = [r for r in history if (_as_date(r.get("date")) or today) < today]
    past.sort(key=lambda r: str(r["date"]), reverse=True)

    streak = 1
    prev_day = today
    for record in past:
        when = _as_date(record.get("date"))
        if when is None:
            break
        if (prev_day - when).days > MAX_GAP_DAYS:
            break
        codes = {str(x.get("code") or "") for x in record.get("rows") or []}
        if code not in codes:
            break
        streak += 1
        prev_day = when

    def count(days: int) -> int:
        edge = today - timedelta(days=days)
        hits = 1  # 今天在榜
        for record in past:
            when = _as_date(record.get("date"))
            if when is None or when < edge:
                continue
            if code in {str(x.get("code") or "") for x in record.get("rows") or []}:
                hits += 1
        return hits

    return {"streak": streak, "d30": count(30), "d365": count(365)}


def collect(day: str = "", path: Path = HISTORY_PATH, top: int = TOP_N,
            write: bool = True) -> Dict[str, Any]:
    """取两源、合并、算历史统计、落盘当天一行。任何一路失败都只是少一列。"""
    day = day or datetime.now().strftime("%Y-%m-%d")
    errors: List[str] = []
    ths: Dict[str, Dict[str, Any]] = {}
    em: Dict[str, Dict[str, Any]] = {}

    try:
        ths = fetch_ths()
    except Exception as exc:  # noqa: BLE001 - 少一源仍可出榜
        errors.append(f"ths: {type(exc).__name__}: {exc}")
    try:
        em = fetch_em()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"eastmoney: {type(exc).__name__}: {exc}")

    if not ths and not em:
        for line in errors:
            print(f"renqi source failed: {line}", file=sys.stderr)
        return {"date": day, "rows": [], "errors": errors}

    quotes: Dict[str, Dict[str, Any]] = {}
    if em:
        try:
            quotes = em_quotes(em)
        except Exception as exc:  # noqa: BLE001 - 名称取不到就用代码顶上
            errors.append(f"eastmoney quotes: {type(exc).__name__}: {exc}")

    rows = merge(ths, em, quotes)[:top]
    history = [r for r in load_history(path) if str(r.get("date")) != day]
    for i, row in enumerate(rows, 1):
        row["rank"] = i
        row.update(stats_for(row["code"], day, history))

    record = {
        "date": day,
        "sources": [name for name, ok in (("ths", ths), ("em", em)) if ok],
        "rows": [
            {k: r[k] for k in ("rank", "code", "name", "pct", "n", "ths", "em", "concepts", "tag")}
            for r in rows
        ],
    }
    try:
        if write:
            save_history(list(history) + [record], path)
    except Exception as exc:  # noqa: BLE001 - 落盘失败不该让晚报失败
        errors.append(f"history write: {type(exc).__name__}: {exc}")
        for line in errors[-1:]:
            print(f"renqi: {line}", file=sys.stderr)

    for line in errors:
        print(f"renqi source failed: {line}", file=sys.stderr)
    print(f"renqi: {len(rows)} 只 · 来源 {'+'.join(record['sources']) or '无'} · "
          f"历史 {len(history) + 1} 天 · {day}", file=sys.stderr)
    return {"date": day, "rows": rows, "sources": record["sources"], "errors": errors}


def push_lines(doc: Dict[str, Any], limit: int = TOP_N) -> List[str]:
    """微信推送用的紧凑版：名次、名称、涨跌幅、连续与累计。"""
    rows = (doc or {}).get("rows") or []
    if not rows:
        return []
    out = ["*自建 · 同花顺 + 东方财富；与连板网综合榜口径不同（少开盘啦一列）*"]
    for r in rows[:limit]:
        bits = [r.get("pct") or ""]
        if r.get("streak"):
            bits.append(f"连续{r['streak']}天")
        if r.get("d30"):
            bits.append(f"30日{r['d30']}次")
        if r.get("d365"):
            bits.append(f"1年{r['d365']}次")
        tail = " · ".join(x for x in bits if x)
        out.append(f"{r.get('rank')}. **{r.get('name')}** {r.get('code')}" + (f" {tail}" if tail else ""))
    return out


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="今日人气榜：两源合并 + 历史统计")
    parser.add_argument("--date", default="")
    parser.add_argument("--history", default=str(HISTORY_PATH))
    parser.add_argument("--top", type=int, default=TOP_N)
    parser.add_argument("--json", action="store_true", help="打印完整 JSON")
    parser.add_argument("--no-write", action="store_true", help="只算不落盘")
    args = parser.parse_args(argv)

    doc = collect(args.date, Path(args.history), args.top, write=not args.no_write)

    if args.json:
        print(json.dumps(doc, ensure_ascii=False, indent=1))
    else:
        print(f"{doc.get('date')} 今日人气榜（{'+'.join(doc.get('sources') or []) or '无来源'}）")
        for r in doc.get("rows") or []:
            print(f"{r['rank']:>2} {r['name']:<6} {r['code']}  {r.get('pct') or '':>8}  "
                  f"连续{r.get('streak', 0)}天 30日{r.get('d30', 0)}次 1年{r.get('d365', 0)}次  "
                  f"同花顺{r.get('ths') or '-'} 东财{r.get('em') or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
