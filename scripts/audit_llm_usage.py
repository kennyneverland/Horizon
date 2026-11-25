#!/usr/bin/env python3
"""核验晚报四段研判有没有用上连板网新增的情绪与题材数据。

只读，不改任何生产文件。它做三件事：

1. 从当天晚报页面里抽出「盘后洞察」四段正文；
2. 从 qingxu.html / market.html 取当天站点算出的基准率，作为「应该被引用」的数字集合；
3. 对一遍，报引用率、四类误用、以及正文百分数的溯源率。

它回答不了「数据有没有喂进去」——那需要模型输入落盘。它只回答
「模型写出来的东西里，有多少痕迹能对上这批数据」。

用法：
    python audit_llm_usage.py --date 2026-11-26
    python audit_llm_usage.py --page pm.html --qx qx.html --mk mk.html
    python audit_llm_usage.py --date 2026-11-26 --no-breadth --json

依赖同目录的 lianban_extra.py（口径与生产完全一致，不重复实现解析）。
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from lianban_extra import parse_emotion, _theme_health, _narrow_transition
except Exception as exc:  # noqa: BLE001
    print(f"无法导入 lianban_extra：{exc}", file=sys.stderr)
    raise SystemExit(2)

UA = "Mozilla/5.0 (compatible; HorizonAudit/1.0)"
PAGE_URL = "https://kennyneverland.github.io/Horizon/post-market/{date}.html"
QX_URL = "https://lianban.net/qingxu.html"
MK_URL = "https://lianban.net/market.html"

# 每个新增字段的「上下文词」：光有数字不算引用，得配上这些词才算它真被用上。
FIELD_WORDS = {
    "relay_promotion": ("晋级", "连板率", "1进2", "首板", "接力"),
    "relay_by_phase": ("晋级", "连板率", "1进2", "冰点期", "高潮期"),
    "phase_duration": ("持续", "段", "平均", "天数"),
    "phase_transition": ("转移", "去向", "次日阶段", "修复", "概率"),
    "themes_health": ("上升期", "趋势", "占比", "健康", "底座"),
}

PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def fetch(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
    return body.decode("utf-8", "replace")


def read_local(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def strip_tags(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def sections(page: str) -> List[Tuple[str, str]]:
    """「盘后洞察」四段：``<div class='read'>`` 里的 h3/p 配对。"""
    m = re.search(r"<div class=['\"]read['\"]>(.*?)</div>", page, re.S)
    if not m:
        return []
    return [
        (strip_tags(h), strip_tags(p))
        for h, p in re.findall(r"<h3>(.*?)</h3>\s*<p>(.*?)</p>", m.group(1), re.S)
    ]


def page_phase(page: str) -> str:
    """盘面 KPI 里的「情绪周期」格，与转移矩阵行名同为「冰点期」这种写法。"""
    m = re.search(
        r"<span>\s*情绪周期\s*</span>\s*<b[^>]*>(.*?)</b>", page, re.S
    )
    return strip_tags(m.group(1)) if m else ""


def _num(text: Any) -> Optional[float]:
    m = re.search(r"-?\d+(?:\.\d+)?", str(text or ""))
    return float(m.group(0)) if m else None


def expected_values(emotion: Dict[str, Any], themes: Dict[str, Any]) -> Dict[str, List[float]]:
    """当天站点算出的基准率，按字段归组。"""
    exp: Dict[str, List[float]] = {}

    rates = [_num(r.get("rate")) for r in (emotion.get("relay_promotion") or [])]
    exp["relay_promotion"] = [x for x in rates if x is not None]

    by_phase: List[float] = []
    for row in emotion.get("relay_by_phase") or []:
        for key in ("next_1to2", "next_2to3"):
            v = _num(row.get(key))
            if v is not None:
                by_phase.append(v)
    exp["relay_by_phase"] = by_phase

    dur: List[float] = []
    for row in emotion.get("phase_duration") or []:
        for key in ("mean", "longest", "share"):
            v = _num(row.get(key))
            if v is not None:
                dur.append(v)
    exp["phase_duration"] = dur

    trans: List[float] = []
    tr = emotion.get("phase_transition") or {}
    if isinstance(tr.get("next"), dict):
        for v in tr["next"].values():
            n = _num(v)
            if n is not None:
                trans.append(n)
    exp["phase_transition"] = trans

    health: List[float] = []
    for key in ("strong", "weak"):
        for row in (themes or {}).get(key) or []:
            v = _num(row.get("uptrend_share"))
            if v is not None:
                health.append(v)
    exp["themes_health"] = health
    return exp


def find_refs(
    secs: List[Tuple[str, str]], exp: Dict[str, List[float]]
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for title, text in secs:
        pcts = {float(x) for x in PCT_RE.findall(text)}
        if not pcts:
            continue
        for field, values in exp.items():
            shared = pcts & set(values)
            if not shared:
                continue
            ctx = [w for w in FIELD_WORDS[field] if w in text]
            hits.append(
                {
                    "field": field,
                    "values": sorted(shared),
                    "section": title,
                    "context": ctx,
                    # 有数字没上下文，可能是巧合；两个都齐才算真引用。
                    "strong": bool(ctx),
                }
            )
    return hits


def find_misuse(
    secs: List[Tuple[str, str]],
    emotion: Dict[str, Any],
    themes: Dict[str, Any],
    phase: str,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    tr = (emotion.get("phase_transition") or {}).get("next") or {}
    dur = {r.get("phase"): r for r in (emotion.get("phase_duration") or [])}
    cur = dur.get(phase) or {}
    hist_days = {_num(cur.get("mean")), _num(cur.get("longest"))} - {None}

    for title, text in secs:
        # A. 把历史分布读成本轮已持续天数（站点连续天数本身算错，这条最易犯）
        for m in re.finditer(r"(?:已持续|连续第|连续)\s*([0-9]+|[一二三四五六七八九十])\s*天", text):
            raw = m.group(1)
            n = float(raw) if raw.isdigit() else float(
                "一二三四五六七八九十".index(raw) + 1
            )
            if n in hist_days:
                out.append(
                    {
                        "type": "历史分布当本轮天数",
                        "section": title,
                        "evidence": m.group(0),
                        "detail": f"{phase}历史均值{cur.get('mean')}／最长{cur.get('longest')}，不是本轮实际",
                    }
                )
                break

        # B. 趋势底座读成涨跌幅
        health_vals = {
            _num(r.get("uptrend_share"))
            for r in (themes.get("strong") or []) + (themes.get("weak") or [])
        } - {None}
        pcts = {float(x) for x in PCT_RE.findall(text)}
        if pcts & health_vals and re.search(r"涨|跌|升幅|降幅", text) and not re.search(
            r"上升期|占比|成员|趋势", text
        ):
            out.append(
                {
                    "type": "趋势底座当涨跌幅",
                    "section": title,
                    "evidence": sorted(pcts & health_vals),
                    "detail": "uptrend_share 是成员处于上升期的比例，不是板块涨跌幅",
                }
            )

        # C. 单阶段晋级率与全样本并排比高低
        all_rates = {_num(r.get("rate")) for r in (emotion.get("relay_promotion") or [])} - {None}
        phase_rates = set()
        for row in emotion.get("relay_by_phase") or []:
            for key in ("next_1to2", "next_2to3"):
                v = _num(row.get(key))
                if v is not None:
                    phase_rates.add(v)
        if (pcts & all_rates) and (pcts & phase_rates) and re.search(
            r"比|高于|低于|更容易|更大|更强|显著", text
        ):
            out.append(
                {
                    "type": "两套样本并排比",
                    "section": title,
                    "evidence": sorted((pcts & all_rates) | (pcts & phase_rates)),
                    "detail": "晋级率与按阶段分组的样本期不同，不能比高低",
                }
            )

        # D. 转移矩阵里的「·」被读成 0%
        dots = [k for k, v in tr.items() if str(v).strip() in {"·", "", "-"}]
        if dots and re.search(r"0(?:\.0)?%", text):
            for k in dots:
                if k in text:
                    out.append(
                        {
                            "type": "无样本读成 0%",
                            "section": title,
                            "evidence": f"{k} 0%",
                            "detail": "该去向样本不足，站点用「·」表示，不是 0%",
                        }
                    )
                    break
    return out


def audit(args: argparse.Namespace) -> Dict[str, Any]:
    page = read_local(args.page) if args.page else fetch(PAGE_URL.format(date=args.date))
    qx = read_local(args.qx) if args.qx else fetch(QX_URL)
    emotion = parse_emotion(qx)

    themes: Dict[str, Any] = {}
    if not args.no_breadth:
        try:
            mk = read_local(args.mk) if args.mk else fetch(MK_URL)
            themes = _theme_health(mk)
        except Exception as exc:  # noqa: BLE001 - 题材取不到不影响其余核验
            print(f"题材健康度未取到：{exc}", file=sys.stderr)

    phase = ((emotion.get("phase_transition") or {}).get("phase") or "").strip()
    if not phase:
        phase = page_phase(page) or (args.phase or "")
    # 生产侧已用 _narrow_transition 收成当日一行；这里对未收窄的整表做同样处理，
    # 口径才对得上，也才不会拿 36 个格子的数字去撞巧合。
    tr = emotion.get("phase_transition")
    if tr and "next" not in tr and phase:
        emotion["phase_transition"] = _narrow_transition(tr, phase)
    exp = expected_values(emotion, themes)
    secs = sections(page)
    hits = find_refs(secs, exp)
    misuse = find_misuse(secs, emotion, themes, phase)

    ref_fields = sorted({h["field"] for h in hits if h["strong"]})
    all_pcts = {float(x) for _, t in secs for x in PCT_RE.findall(t)}
    known = {v for vals in exp.values() for v in vals}
    traced = all_pcts & known

    return {
        "date": args.date,
        "page_bytes": len(page.encode("utf-8")),
        "sections": [{"h": h, "chars": len(t)} for h, t in secs],
        "phase": phase,
        "expected": {k: sorted(v) for k, v in exp.items()},
        "refs": hits,
        "ref_fields": ref_fields,
        "ref_rate": round(len(ref_fields) / max(len(exp), 1), 3),
        "misuse": misuse,
        "pct_total": len(all_pcts),
        "pct_traced": len(traced),
        "trace_rate": round(len(traced) / max(len(all_pcts), 1), 3),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="核验晚报是否用上连板网新增数据")
    ap.add_argument("--date", default="", help="晚报日期 YYYY-MM-DD")
    ap.add_argument("--page", help="本地晚报 HTML（不给则按 --date 拉线上）")
    ap.add_argument("--qx", help="本地 qingxu.html")
    ap.add_argument("--mk", help="本地 market.html")
    ap.add_argument("--phase", help="当日情绪阶段（页面取不到时手动给，如 冰点期）")
    ap.add_argument("--no-breadth", action="store_true", help="跳过题材健康度")
    ap.add_argument("--json", action="store_true", help="只输出 JSON")
    ap.add_argument("--csv", help="把一行结果追加到这个 CSV")
    args = ap.parse_args()
    if not args.page and not args.date:
        ap.error("需要 --date 或 --page")

    result = audit(args)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"日期 {result['date']}  页面 {result['page_bytes']} B  四段 {len(result['sections'])} 段")
        print(f"当日阶段：{result['phase'] or '（未取到）'}")
        print("应喂数字：" + "  ".join(
            f"{k}={len(v)}个" for k, v in result["expected"].items()
        ))
        strong = [h for h in result["refs"] if h["strong"]]
        print(f"\n引用：{len(strong)} 处（字段 {len(result['ref_fields'])}/{len(result['expected'])}）")
        for h in strong:
            print(f"  · {h['field']} {h['values']} @{h['section']}")
        weak = [h for h in result["refs"] if not h["strong"]]
        if weak:
            print(f"  另有 {len(weak)} 处只有数字、没有上下文词，按巧合处理")
        print(f"\n误用：{len(result['misuse'])} 处")
        for m in result["misuse"]:
            print(f"  · [{m['type']}] {m['evidence']} @{m['section']} — {m['detail']}")
        print(f"\n百分数溯源：{result['pct_traced']}/{result['pct_total']} = {result['trace_rate']:.0%}")
        if not strong:
            print("\n结论：四段里没有一处把新增数据当依据用。要么没喂进去，要么喂了没用——")
            print("      这两者现在分不开，需要模型输入落盘才能判定。")

    if args.csv:
        path = Path(args.csv)
        new = not path.exists()
        with path.open("a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["date", "page_bytes", "sections", "ref_fields", "ref_rate",
                            "misuse", "pct_traced", "pct_total", "trace_rate", "phase"])
            w.writerow([
                result["date"], result["page_bytes"], len(result["sections"]),
                "|".join(result["ref_fields"]), result["ref_rate"],
                len(result["misuse"]), result["pct_traced"], result["pct_total"],
                result["trace_rate"], result["phase"],
            ])
        print(f"\n已追加一行到 {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
