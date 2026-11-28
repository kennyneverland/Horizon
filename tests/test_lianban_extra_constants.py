"""外盘常量守卫：函数可以删，它下面的模块常量不能跟着走。

2026-11-28 的 A1 提交把 parse_overseas 连同紧挨着的 18 行常量一起删了，
而 post_market.py 调用处有 try/except，NameError 被吞成 payload["errors"] 里一条，
晚报照常出、"外盘参考"整块静默消失。这个测试拦的就是这种"删函数带走常量"。
"""

from __future__ import annotations

import importlib.util
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
