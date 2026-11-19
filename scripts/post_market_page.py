#!/usr/bin/env python3
"""The evening brief's page: one self-contained document, worn by a phone.

Split out of post_market.py because the page and the data have different
failure modes and different readers: this half is only HTML, and every number
in it arrives already computed. The one exception is the model's watch list,
which is text the model wrote — it is rendered as written, never recomputed.

    from post_market_page import render_html
"""

from __future__ import annotations

import html as _html
import re
from typing import Any, Dict, List

from lianban_extra import EXTRA_CSS, render_sections


def _esc(value: Any) -> str:
    return _html.escape(str(value if value is not None else ""))


def _pct_class(raw: str) -> str:
    text = str(raw or "").strip()
    if text.startswith("+"):
        return "up"
    if text.startswith("-"):
        return "down"
    return ""


def _state_class(state: str) -> str:
    return {
        "扩散": "up",
        "新上榜": "up",
        "过热": "hot",
        "收缩": "down",
        "缺席": "mute",
    }.get(state, "mute")


_PAGE_CSS = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:#fff;color:#606c71;
  font:17px/1.75 "Open Sans","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
.page-header{color:#fdf1e0;text-align:center;background-color:#7a3b1e;
  background-image:linear-gradient(120deg,#5b2c14,#a85a24);
  padding:38px 20px 32px;padding-top:calc(38px + env(safe-area-inset-top))}
.project-name{margin:0 0 8px;font-size:23px;font-weight:600;letter-spacing:.2px;line-height:1.3;word-break:keep-all}
.page-header .project-tagline{margin:0;font-size:14px;font-weight:400;color:rgba(253,241,224,.85);letter-spacing:.3px}
main{max-width:680px;margin:0 auto;padding:22px 18px calc(44px + env(safe-area-inset-bottom))}
main h2{margin:32px 0 12px;font-size:19px;font-weight:600;color:#a1521a;line-height:1.4}
main h2:first-child{margin-top:6px}
p{margin:0 0 1em}
.lede{margin:0 0 20px;color:#4c5866}
a{color:#a1521a;text-decoration:none}
.read{border-left:3px solid #c97a33;padding:2px 0 2px 14px}
.read p:last-child{margin-bottom:0}
.read .verdict{font-size:19px;line-height:1.5;font-weight:600;color:#22313f;margin:0 0 14px}
.read h3{margin:16px 0 6px;font-size:15px;font-weight:600;color:#a1521a;letter-spacing:.2px}
.read h3:first-of-type{margin-top:0}
.read .tag{margin-right:6px}
.wl{margin:0 0 18px}
.wl-h{display:flex;align-items:baseline;gap:8px;margin:16px 0 4px}
.wl-h:first-child{margin-top:2px}
.wl-h b{font-size:16px;color:#22313f;font-weight:600}
.wl-h .tag{flex:none}
.wl-g{margin:0 0 8px;font-size:13px;color:#8a94a6;line-height:1.6}
.wl-u{list-style:none;margin:0 0 4px;padding:0}
.wl-u li{padding:9px 0;border-bottom:1px dashed #eff0f1}
.wl-u li:last-child{border-bottom:0}
.wl-u .nm{font-size:15.5px;color:#2b3440;font-weight:600}
.wl-u .tag{margin-left:8px}
.wl-n{display:block;margin-top:3px;font-size:13.5px;color:#8a94a6;line-height:1.65}
.tc{margin:0 0 4px}
.tc .wl-u li{padding:10px 0}
.focus h3{margin:14px 0 3px;font-size:16px;font-weight:600;color:#22313f;line-height:1.4}
.focus h3 .tag{margin-left:8px;vertical-align:1px}
.focus .wl{margin:0 0 12px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#e9ebec;
  border:1px solid #e9ebec;border-radius:8px;overflow:hidden}
.stat{background:#fff;padding:12px 4px;text-align:center}
.stat b{display:block;font-size:20px;font-weight:600;color:#2b3440;line-height:1.25}
.stat span{font-size:11px;color:#8a94a6}
.lines{list-style:none;margin:0;padding:0}
.line{padding:13px 0;border-bottom:1px solid #eff0f1}
.line:last-child{border-bottom:0}
.line-h{display:flex;align-items:center;gap:8px}
.line-h b{font-size:17px;color:#2b3440;font-weight:600}
.line-n{margin-top:4px;font-size:13.5px;color:#8a94a6}
.line-n b{color:#2b3440;font-weight:600}
.tag{font-size:11px;line-height:1;padding:3px 7px;border-radius:9px;background:#f0f2f5;color:#8a94a6}
.tag.up{background:#fdecec;color:#d14343}
.tag.down{background:#eaf6ef;color:#2e9e5b}
.tag.hot{background:#fdf3e3;color:#c87a12}
.tag.lhb{background:#eef1fd;color:#4257b2}
.drv{list-style:none;margin:0;padding:0}
.drv li{padding:11px 0;border-bottom:1px solid #eff0f1}
.drv li:last-child{border-bottom:0}
.drv b{color:#2b3440;font-weight:600}
.drv .cnt{color:#d14343;font-weight:600;margin-left:6px}
.drv .why{display:block;margin-top:3px;font-size:13.5px;color:#8a94a6}
.drv .ld{display:inline-block;margin-top:5px;font-size:12px;color:#c87a12}
table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:13.5px}
th{font-weight:600;color:#8a94a6;font-size:11.5px;text-align:right;padding:7px 6px;
  border-bottom:1px solid #e9ebec;background:#fafbfc}
th:nth-child(-n+2){text-align:left}
td{padding:9px 6px;border-bottom:1px solid #eff0f1;vertical-align:top}
td.rk{color:#b3bcc9;font-variant-numeric:tabular-nums}
td.nm{overflow:hidden}
td.nm b{display:block;color:#2b3440;font-weight:600;font-size:14.5px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
td.nm .sub{display:block;font-size:11px;color:#8a94a6;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.num{text-align:right;font-variant-numeric:tabular-nums}
.up{color:#d14343}
.down{color:#2e9e5b}
.hot{color:#c87a12}
.mute{color:#8a94a6}
.hint{font-size:12px;color:#8a94a6;margin:0 0 8px}
footer{margin-top:34px;padding-top:16px;border-top:1px solid #eff0f1;
  font-size:12px;line-height:1.8;color:#98a2b3}
footer a{color:#98a2b3;text-decoration:underline}
@media (max-width:360px){body{font-size:16px}.project-name{font-size:22px}.stat b{font-size:18px}}
@media (prefers-color-scheme:dark){main h2,.read h3{color:#e8a765}.read .verdict{color:#f2e6d8}a{color:#e8a765}
  body{background:#14171c;color:#c3cad6}
  .stat{background:#14171c}.stat b,.line-h b,td.nm b,.drv b,.line-n b{color:#e6ebf2}
  th{background:#1a1f26;color:#8a94a6}
  .line,.drv li,td,footer,.stats{border-color:#252b33}
  .wl-h b,.wl-u .nm,.focus h3{color:#e6ebf2}
  .wl-u li{border-color:#252b33}
}
"""


def _theme_meta(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """题材 → 当日涨停家数与龙头，用脚本里的数给题材组做注脚。

    The model names the theme; the count and the leader are the page's own
    numbers, so they are attached here rather than asked for in the prompt —
    a model that paraphrases them is a model that can get them wrong.
    """
    out = {}
    for line in ((payload.get("matrix") or {}).get("day") or {}).get("lines") or []:
        name = line.get("name") or ""
        if name:
            out[name] = {"count": line.get("count"), "leader": line.get("leader") or ""}
    return out


def _loose(text: str) -> str:
    return re.sub(r"[（）()·\s]", "", str(text or ""))


def _watch_html(watch: List[Dict[str, Any]], meta: Dict[str, Dict[str, Any]]) -> str:
    """个股段：每个题材一组，组内是该题材里值得盯的几只。

    A flat list of names loses the one thing a reader needs after the close —
    which theme each name belongs to — so the theme is the heading and the names
    sit under it. Each row carries the board height and the role in one line,
    because on a phone two lines per name is already a lot.
    """
    loose = {_loose(k): v for k, v in meta.items()}
    groups = []
    for item in watch:
        info = meta.get(item["theme"]) or loose.get(_loose(item["theme"])) or {}
        chip = (
            f"<span class='tag'>{info['count']} 家涨停</span>" if info.get("count") else ""
        )
        lead = f"龙头 {info['leader']}" if info.get("leader") else ""
        rows = []
        for st in item.get("stocks") or []:
            tag = f"<span class='tag'>{_esc(st['tag'])}</span>" if st.get("tag") else ""
            note = f"<span class='wl-n'>{_esc(st['note'])}</span>" if st.get("note") else ""
            rows.append(f"<li><span class='nm'>{_esc(st['name'])}</span>{tag}{note}</li>")
        note = " · ".join(x for x in [lead, item.get("signal") or ""] if x)
        signal = f"<div class='wl-g'>{_esc(note)}</div>" if note else ""
        groups.append(
            f"<div class='wl'><div class='wl-h'><b>{_esc(item['theme'])}</b>{chip}</div>"
            f"{signal}<ul class='wl-u'>{''.join(rows)}</ul></div>"
        )
    return "<h3>重点关注个股</h3>" + "".join(groups)


def _lhb_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """龙虎榜个股 → 净额与当日涨跌，用来在活跃块里标注来源。

    The model already knows the name; the page supplies the number, for the same
    reason it supplies the 60-day position — a figure the model retypes is a
    figure it can get wrong.
    """
    out: Dict[str, Dict[str, str]] = {}
    for x in (payload.get("lhb") or {}).get("items") or []:
        out[(x.get("name") or "").replace(" ", "")] = {
            "net": x.get("net") or "",
            "chg": x.get("chg") or "",
        }
    return out


_FOCUS_ORDER = ("蓄势", "主线", "活跃")

# Each bucket answers a different question, so each gets its own one-line frame
# rather than a shared caption: 蓄势 is about position, 主线 about continuity,
# 活跃 about whether one day becomes two.
_FOCUS_DESC = {
    "蓄势": "还没动、结构就绪：票池是连板网「优选蓄势」，题材取该票所属板块，位置由面板回填",
    "主线": "已经在走、且有连续性：题材与个股来自当日题材明细，看的是明日能否延续",
    "活跃": "今天刚动、持续性未验证：新上榜或单日放量，看的是明日能否接力",
}


def _focus_html(
    focus: Dict[str, Any],
    meta: Dict[str, Dict[str, Any]],
    pos: Dict[str, Dict[str, Any]],
    lhb: Dict[str, Dict[str, str]],
) -> str:
    """明日关注分三类，每类是一组「题材 → 该题材的重点个股」。

    The old page answered "what to watch tomorrow" with one flat list plus a
    separate candidate block, which forced the reader to work out which names
    were already moving and which were not. Splitting by bucket does that work
    once, on the page: 蓄势 names have no limit-up behind them yet, 主线 names
    are riding a line that has already run, 活跃 names moved today and have to
    prove it again tomorrow.
    """
    loose_meta = {_loose(k): v for k, v in meta.items()}
    blocks = []
    for bucket in _FOCUS_ORDER:
        items = focus.get(bucket) or []
        if not items:
            continue
        groups = []
        for item in items:
            theme = str(item.get("theme") or "")
            info = meta.get(theme) or loose_meta.get(_loose(theme)) or {}
            # 蓄势的题材是票自己的板块，不是当日涨停线，不挂涨停家数
            chip = (
                f"<span class='tag'>{info['count']} 家涨停</span>"
                if bucket != "蓄势" and info.get("count")
                else ""
            )
            rows = []
            for st in item.get("stocks") or []:
                key = (st.get("name") or "").replace(" ", "")
                hit = pos.get(key) or {}
                bits = []
                if hit.get("gain60"):
                    bits.append(f"60日 {hit['gain60']}")
                if hit.get("from_high"):
                    bits.append(f"距高点 {hit['from_high']}")
                if st.get("note"):
                    bits.append(st["note"])
                tag = f"<span class='tag'>{_esc(st['tag'])}</span>" if st.get("tag") else ""
                # 活跃块里凡是能在龙虎榜上查到的，标出净额——"今天为什么动"
                # 的最直接证据，比模型转述一句席位说明可靠
                board = lhb.get(key) or {}
                if bucket == "活跃" and board.get("net"):
                    # 模型已经把来源写进 tag 时只补净额，否则连来源一起补——
                    # 净额是这一行最有信息量的数字，不该因为措辞不同就丢掉
                    if "龙虎榜" in (st.get("tag") or ""):
                        tag += f"<span class='tag lhb'>{_esc(board['net'])}</span>"
                    else:
                        tag += f"<span class='tag lhb'>龙虎榜 {_esc(board['net'])}</span>"
                note = f"<span class='wl-n'>{_esc(' · '.join(bits))}</span>" if bits else ""
                rows.append(f"<li><span class='nm'>{_esc(st['name'])}</span>{tag}{note}</li>")
            if not rows:
                continue
            signal = item.get("signal") or ""
            sig = f"<div class='wl-g'>{_esc(signal)}</div>" if signal else ""
            groups.append(
                f"<div class='wl'><h3>{_esc(theme)}{chip}</h3>{sig}"
                f"<ul class='wl-u'>{''.join(rows)}</ul></div>"
            )
        if not groups:
            continue
        blocks.append(
            f"<h2>明日关注 · {bucket}</h2>"
            f"<div class='wl-g'>{_FOCUS_DESC[bucket]}</div>"
            f"<div class='focus'>{''.join(groups)}</div>"
        )
    return "".join(blocks)


def _lhb_html(payload: Dict[str, Any]) -> str:
    """龙虎榜净买额前 15，每只票后面挂它倒查出来的题材。

    The board is the one place a name appears with no theme attached: the site
    explains why a stock was disclosed (a 7% move, a 20% turnover), never what it
    trades as. The index answers that, so the table prints the theme beside the
    number and the reader no longer has to look it up elsewhere.

    A stock the index does not carry says so, rather than borrowing a
    neighbour's theme.
    """
    items = (payload.get("lhb") or {}).get("items") or []
    if not items:
        return ""
    concepts = payload.get("concepts") or {}
    rows = []
    for x in items[:15]:
        hit = concepts.get(x.get("code") or "") or {}
        themes = list(hit.get("themes") or [])
        labels = [t for t in themes[:3]]
        if not labels:
            labels = [c.get("name") for c in (hit.get("concepts") or [])[:2] if c.get("name")]
        label = " / ".join(labels) or "题材未收录"
        sub = " · ".join(v for v in [x.get("code") or "", label] if v)
        net = x.get("net") or ""
        rows.append(
            "<tr>"
            f"<td class='nm'><b>{_esc(x.get('name'))}</b>"
            f"<span class='sub'>{_esc(sub)}</span></td>"
            f"<td class='num {_pct_class(x.get('chg'))}'>{_esc(x.get('chg'))}</td>"
            f"<td class='num {'down' if '-' in net else ('up' if net else '')}'>{_esc(net)}</td>"
            "</tr>"
        )
    return (
        "<h2>龙虎榜 · 题材归属</h2>"
        "<p class='hint'>净买额前 15；题材由本地题材索引倒查，"
        "与当日题材同名即归位，未收录的票照实标出</p>"
        "<table><colgroup><col><col style='width:66px'><col style='width:78px'></colgroup>"
        "<thead><tr><th>个股 / 所属题材</th><th>涨跌</th><th>净额</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
    )


def _filter_pos(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """个股 → 它出现在哪张筛选面板、位置多少。

    Only the fifteen names in the three free panels have a 60-day position, so a
    name the model picked from elsewhere comes back empty and the row prints no
    numbers rather than an estimate.
    """
    out: Dict[str, Dict[str, Any]] = {}
    concepts = payload.get("concepts") or {}
    for label, block in (payload.get("filter") or {}).items():
        for row in block.get("rows") or []:
            hit = concepts.get(row.get("code") or "") or {}
            out[row["name"].replace(" ", "")] = {
                "panel": label,
                "sector": row.get("sector") or "",
                "themes": hit.get("themes") or [],
                "gain60": row.get("gain60"),
                "from_high": row.get("from_high60"),
            }
    return out


def _tomorrow_html(items: List[Dict[str, Any]], pos: Dict[str, Dict[str, Any]]) -> str:
    """明日候选：还没涨、但结构就绪的那几只。

    Kept for replies written before the three-bucket contract; the current
    prompt returns ``focus`` instead.

    The position is filled in from the screening panel, not from the model: a
    number the model retypes is a number it can get wrong, and this block is
    about position more than anything else. The model supplies the theme and the
    reason; the panel supplies the 60-day gain and the distance from the high.
    """
    rows = []
    for item in items:
        key = (item.get("name") or "").replace(" ", "")
        hit = pos.get(key) or {}
        # The panel knows every name's sector; the model only knows the ones it
        # bothered to look up. So a missing or "未归类" theme falls back to the
        # sector rather than printing a label that says nothing.
        theme = item.get("theme") or ""
        if not theme or "未归类" in theme:
            theme = hit.get("sector") or ""
        tags = ""
        if theme:
            tags += f"<span class='tag'>{_esc(theme)}</span>"
        if hit.get("panel") and hit["panel"] != "优选蓄势":
            tags += f"<span class='tag'>{_esc(hit['panel'])}</span>"
        bits = []
        if hit.get("gain60"):
            bits.append(f"60日 {hit['gain60']}")
        if hit.get("from_high"):
            bits.append(f"距高点 {hit['from_high']}")
        if item.get("note"):
            bits.append(item["note"])
        note = f"<span class='wl-n'>{_esc(' · '.join(bits))}</span>" if bits else ""
        rows.append(f"<li><span class='nm'>{_esc(item.get('name'))}</span>{tags}{note}</li>")
    return (
        "<h3>明日候选（优选蓄势）</h3>"
        "<div class='wl-g'>取自连板网「优选蓄势」：当日未涨停、结构就绪；标签是该票的题材归属，位置由页面数据回填</div>"
        f"<div class='tc'><ul class='wl-u'>{''.join(rows)}</ul></div>"
    )


def render_html(payload: Dict[str, Any], read: Any, page_url: str) -> str:
    """One self-contained page wearing the daily digest's clothes.

    The morning page is a Jekyll Cayman document: a blue-to-green banner, green
    section headings, one white column. The evening brief keeps that, and then
    pays for it on a phone — the matrix is a list rather than a seven-column
    table, because at 430pt a table either shrinks the type or scrolls sideways,
    and both lose the comparison it exists to make.
    """
    kpi = payload.get("kpi") or {}
    matrix = payload.get("matrix") or {}
    day = matrix.get("day") or {}
    lines = matrix.get("lines") or []
    picks = payload.get("filter") or {}
    concepts = payload.get("concepts") or {}
    extra = render_sections(payload)
    date = kpi.get("date") or ""

    line_rows = []
    for l in lines:
        # Two shapes matter after the close: lines that drew limit-ups today,
        # and lines that had them yesterday and lost them. A line dark for two
        # sessions is history, and the page is about tomorrow.
        if l["today"] == 0 and l["prev"] == 0:
            continue
        line_rows.append(
            "<li class='line'>"
            f"<div class='line-h'><b>{_esc(l['line'])}</b>"
            f"<span class='tag {_state_class(l['state'])}'>{_esc(l['state'])}</span></div>"
            f"<div class='line-n'>今日 <b>{l['today']}</b> 家 · 昨日 {l['prev']} 家 · "
            f"日Δ <span class='{_pct_class(str(l['delta1']))}'>{l['delta1']:+d}</span> · "
            f"3日Δ <span class='{_pct_class(str(l['delta3']))}'>{l['delta3']:+d}</span> · "
            f"连续 {l['streak']} 天</div></li>"
        )

    stats = [
        (kpi.get("limit_up"), "涨停"),
        (kpi.get("limit_down"), "跌停"),
        (kpi.get("lianban"), "连板"),
        (kpi.get("max_board"), "最高板"),
        (f"{kpi.get('seal_rate_pct')}%", "封板率"),
        (kpi.get("zhaban"), "炸板"),
        (kpi.get("adv"), "上涨"),
        (kpi.get("dec"), "下跌"),
    ]
    stat_html = "".join(
        f"<div class='stat'><b>{_esc(v)}</b><span>{_esc(k)}</span></div>" for v, k in stats
    )

    pick_blocks = []
    for label, block in picks.items():
        body = []
        for r in block.get("rows", []):
            # 面板的 sector 是连板网口径，索引的 themes 是同花顺口径；两个都印，
            # 因为它们经常不是同一个名字（厨房小家电 / 家用电器），读者要的是覆盖面。
            idx = (concepts.get(r.get("code") or "") or {}).get("themes") or []
            idx_themes = [t for t in idx[:2] if t != (r.get("sector") or "")]
            sub = " · ".join(
                x
                for x in [r.get("code") or "", r.get("sector") or "", "/".join(idx_themes)]
                if x
            )
            body.append(
                "<tr>"
                f"<td class='rk'>{_esc(r['rank'])}</td>"
                f"<td class='nm'><b>{_esc(r['name'])}</b>"
                f"<span class='sub'>{_esc(sub)}</span></td>"
                f"<td class='num {_pct_class(r['gain60'])}'>{_esc(r['gain60'])}</td>"
                f"<td class='num {_pct_class(r['from_high60'])}'>{_esc(r['from_high60'])}</td>"
                "</tr>"
            )
        total = block.get("total")
        hint = f"共 {total} 只，免费可见前 5" if total else "前 5 只"
        why = block.get("why") or ""
        pick_blocks.append(
            f"<h2>{_esc(label)}</h2>"
            f"<p class='hint'>{_esc(hint)}{('｜' + _esc(why)) if why else ''}</p>"
            "<table><colgroup><col style='width:26px'><col>"
            "<col style='width:74px'><col style='width:64px'></colgroup>"
            "<thead><tr><th>#</th><th>个股 / 题材</th><th>60日涨幅</th><th>距高点</th></tr></thead>"
            "<tbody>" + "".join(body) + "</tbody></table>"
        )

    drivers = ""
    if day.get("lines"):
        items = "".join(
            f"<li><b>{_esc(x['name'])}</b><span class='cnt'>{x['count']} 家</span>"
            f"<span class='why'>{_esc(x['driver'])}</span>"
            f"<span class='ld'>龙头 {_esc(x['leader'])}</span></li>"
            for x in day["lines"]
        )
        drivers = f"<h2>当日主线与驱动</h2><ul class='drv'>{items}</ul>"

    # The model returns verdicts, not prose blocks: a headline that states the
    # call, four sections that each defend one, three buckets of names to watch,
    # and an explicit dissent against the site's own review.
    if isinstance(read, str):
        read = {"headline": "", "sections": [{"h": "", "p": p} for p in read.split("\n") if p.strip()]}
    read = read or {}
    summary_html = ""
    if read.get("sections"):
        parts = []
        if read.get("headline"):
            parts.append(f"<p class='verdict'>{_esc(read['headline'])}</p>")
        sections = list(read["sections"])
        watch = read.get("watchlist") or []
        # 模型偶尔仍按老契约把「重点关注个股」写成第六段；有结构化名单时以名单为准
        if watch and sections and "个股" in (sections[-1].get("h") or ""):
            sections = sections[:-1]
        for sec in sections:
            if sec.get("h"):
                parts.append(f"<h3>{_esc(sec['h'])}</h3>")
            parts.append(f"<p>{_esc(sec['p'])}</p>")
        focus = read.get("focus") or {}
        if focus:
            parts.append(
                _focus_html(
                    focus, _theme_meta(payload), _filter_pos(payload), _lhb_map(payload)
                )
            )
        elif watch:
            # Replies written before the three-bucket contract still render.
            parts.append(_watch_html(watch, _theme_meta(payload)))
            if read.get("tomorrow_candidates"):
                parts.append(
                    _tomorrow_html(read["tomorrow_candidates"], _filter_pos(payload))
                )
        dis = read.get("dissent")
        if isinstance(dis, dict):
            text = str(dis.get("disagree") or dis.get("agree") or "").strip()
        else:
            text = str(dis or "").strip()
        if text:
            parts.append(f"<h3>与连板网复盘的分歧</h3><p>{_esc(text)}</p>")
        summary_html = f"<h2>盘后洞察</h2><div class='read'>{''.join(parts)}</div>"

    top = [l for l in lines if l.get("today", 0) > 0]
    if top:
        lede = (
            f"涨停 {kpi.get('limit_up')} 家、封板率 {kpi.get('seal_rate_pct')}%，"
            f"{kpi.get('emotion_phase') or ''}；最强的是{top[0]['line']}，{top[0]['today']} 家涨停。"
        )
    else:
        lede = (
            f"涨停 {kpi.get('limit_up')} 家、封板率 {kpi.get('seal_rate_pct')}%，"
            f"{kpi.get('emotion_phase') or ''}；今天没有产业线录得涨停。"
        )

    # The model's headline already states the call; printing the script's lede
    # above it would say the same thing twice in the first screenful.
    lede_html = "" if summary_html else f'<p class="lede">{_esc(lede)}</p>'

    mood = kpi.get("emotion_phase") or ""
    degree = day.get("degree")
    mood_text = f"{mood} {degree}°" if degree is not None else mood

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Kenny's Horizon {_esc(date)} 盘后洞察晚报 | Kenny's Horizon</title>
<meta name="description" content="{_esc(lede)}">
<meta property="og:title" content="Horizon 盘后洞察晚报：{_esc(date)}">
<meta property="og:description" content="{_esc(lede)}">
<meta property="og:url" content="{_esc(page_url)}">
<meta name="theme-color" content="#7a3b1e">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<style>{_PAGE_CSS}{EXTRA_CSS}</style></head><body>
<header class="page-header">
<h1 class="project-name">Kenny's Horizon {_esc(date)} 盘后洞察晚报</h1>
<h2 class="project-tagline">盘面总结 · 重点信号 · 变动归因 · 趋势展望 · 蓄势 / 主线 / 活跃</h2>
</header>
<main>
{lede_html}
{summary_html}
<h2>盘面</h2>
<div class="stats">{stat_html}</div>
{extra['funds']}
<h2>主线矩阵</h2>
<ul class="lines">{''.join(line_rows)}</ul>
{drivers}
{''.join(pick_blocks)}
{_lhb_html(payload)}
{extra['review']}
<footer>
数据来源：<a href="https://lianban.net/mainline.html">连板网 · 主线追踪</a>、
<a href="https://lianban.net/filter.html">一键筛选</a>、
<a href="https://lianban.net/today.html">当日复盘</a>、
<a href="https://lianban.net/lhb.html">龙虎榜</a>。
行情与题材数据版权归连板网，依 CC BY 4.0 署名引用。<br>
本页由 Horizon 自动生成，涨停家数只说明资金当天在买什么，不构成任何投资建议。
</footer>
</main></body></html>"""
