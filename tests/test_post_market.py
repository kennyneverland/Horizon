"""晚报融资余额的端到端守卫：面板里那一行要能走到 model input 的 breadth 里。

2026-11-28 的 A7 把「融资余额11-18」这种带 as-of 日期的整标签匹配改成了前缀匹配
（``lianban_extra._row_by_prefix``），但 ``post_market.py`` 里真正把面板值搬进
payload 的两行——``build_model_input`` 的 ``:1288`` 取值与 ``:1488/:1489`` 落字段——
此前没有任何测试碰到过：全仓没有 test_post_market*，CI 装包也只装依赖、不执行这两行，
所以这一格静默变 None 时没有任何东西会红。

这里从 ``extra.panel`` 一路走到 ``build_model_input`` 的返回值，锁住那条链路；
断言只取关键字段，不做整份输出快照。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def post_market():
    # 模块自己会把 scripts/ 与仓库根插进 sys.path（文件头两行 insert），
    # 所以这里只按路径加载，不依赖调用方的 cwd。
    spec = importlib.util.spec_from_file_location(
        "_post_market_margin_guard", ROOT / "scripts" / "post_market.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _payload(panel_rows):
    """最小 payload：只给 build_model_input 需读到的那几块，其余留空。"""
    return {
        "kpi": {"date": "2026-11-28", "_status": "final"},
        "matrix": {"day": {}, "lines": [], "dates": ["11-28"]},
        "extra": {"panel": panel_rows},
    }


def test_margin_balance_reaches_model_input(post_market):
    """源站标签带 as-of 日期时，值与原样标签下的附注都要落到 breadth。"""
    out = post_market.build_model_input(
        _payload([{"label": "融资余额11-19", "value": "1.87万亿", "sub": "较前值+0.02"}])
    )
    assert out["breadth"]["margin_balance"] == "1.87万亿"
    assert out["breadth"]["margin_change"] == "较前值+0.02"


def test_margin_label_date_rollover_still_matches(post_market):
    """日期滚到第二天（11-19 → 11-20）仍然命中；整标签匹配会在这里丢行。"""
    out = post_market.build_model_input(
        _payload([{"label": "融资余额11-20", "value": "1.88万亿", "sub": "较前值+0.01"}])
    )
    assert out["breadth"]["margin_balance"] == "1.88万亿"


def test_margin_label_with_space_still_matches(post_market):
    """``_panel_map`` 会去掉标签里的空格，带空格的源标签不该因此取空。"""
    out = post_market.build_model_input(
        _payload([{"label": "融资余额 11-19", "value": "1.87万亿", "sub": ""}])
    )
    assert out["breadth"]["margin_balance"] == "1.87万亿"


def test_missing_margin_row_is_none_not_crash(post_market):
    """源站整行没给时不抛异常，两个字段留空——晚报其余部分照常出。"""
    out = post_market.build_model_input(
        _payload([{"label": "两市成交", "value": "1.9万亿", "sub": "较前值+1000亿"}])
    )
    assert out["breadth"]["margin_balance"] is None
    assert out["breadth"]["margin_change"] is None
