"""外盘常量守卫：函数可以删，它下面的模块常量不能跟着走。

2026-11-28 的 A1 提交把 parse_overseas 连同紧挨着的 18 行常量一起删了，
而 post_market.py 调用处有 try/except，NameError 被吞成 payload["errors"] 里一条，
晚报照常出、"外盘参考"整块静默消失。这个测试拦的就是这种"删函数带走常量"。
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "_EM_ULIST", "_EM_KLINE", "_EM_ASIA", "_EM_ASIA_HIST", "_TWSE",
    "_SINA_HQ", "_SINA_US", "_SINA_FUT", "TWSE_ATTEMPTS", "TWSE_RETRY_SECONDS",
]


def _load():
    spec = importlib.util.spec_from_file_location("_lianban_extra_guard", ROOT / "scripts" / "lianban_extra.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_overseas_constants_present():
    mod = _load()
    missing = [name for name in REQUIRED if not hasattr(mod, name)]
    assert not missing, f"外盘常量丢失：{missing}"


def test_parse_overseas_is_gone():
    mod = _load()
    assert not hasattr(mod, "parse_overseas"), "parse_overseas 已无调用方，不该复活"


def test_fetch_overseas_does_not_raise_when_data_missing(monkeypatch):
    mod = _load()
    monkeypatch.setattr(mod, "_overseas_get", lambda *args, **kwargs: "")
    result = mod.fetch_overseas("")
    assert isinstance(result, list)


# 盘面 as-of 标签：源站把数据日期写进标签（融资余额11-18）。写死这个日期，
# 日更之后取值就空了——盘面少一行、margin_balance 变 None，不抛异常也不进
# payload["errors"]。下面三条拦的是这件事，外加一条拦"又写死回去"。


def test_row_by_prefix_keeps_dated_label():
    mod = _load()
    label, row = mod._row_by_prefix({"融资余额11-19": {"value": "1.9万亿", "sub": "较前值"}}, "融资余额")
    assert label == "融资余额11-19" and row["value"] == "1.9万亿"


def test_row_by_prefix_missing_is_empty():
    mod = _load()
    assert mod._row_by_prefix({}, "融资余额") == ("", {})


def test_panel_html_renders_dated_row():
    mod = _load()
    payload = {"extra": {"panel": [{"label": "融资余额11-19", "value": "1.9万亿", "sub": "较前值+0.3%"}]}}
    html = mod._panel_html(payload)
    assert "融资余额11-19" in html, "日期滚动后这一行不该整行消失，as-of 也不该被抹掉"
    assert "1.9万亿" in html


def test_no_hardcoded_asof_label():
    pattern = re.compile(r'["\']融资余额\d{1,2}-\d{1,2}["\']')
    code = (ROOT / "scripts" / "post_market.py").read_text(encoding="utf-8")
    body = re.sub(r'"""[\s\S]*?"""', "", code)  # 注释里举例不算
    assert not pattern.search(body), "取值标签又写死了 as-of 日期"