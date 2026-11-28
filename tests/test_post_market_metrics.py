"""晚报推送摘要里的数字：与 kpi 同源、缺字段时不印 "None"。

``_kpi_lines`` 是推送卡片正文的第一屏——读者拿到的第一批数字就是它。它有两处
容易出错的写法：``kpi['limit_up']`` 用了下标却靠 ``kpi.get(...) is not None``
守卫（守卫写对才不崩），以及任一字段缺席时那一项必须**整项消失**而不是印
``None``。这个文件锁的就是这两点，不测整段卡片的排版。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def post_market():
    spec = importlib.util.spec_from_file_location(
        "_post_market_metrics_guard", ROOT / "scripts" / "post_market.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _payload(kpi, panel=None):
    return {"kpi": kpi, "extra": {"panel": panel or []}}


def test_first_line_carries_the_kpi_numbers(post_market):
    out = post_market._kpi_lines(
        _payload(
            {
                "limit_up": 62,
                "limit_down": 5,
                "seal_rate_pct": 78.0,
                "zhaban": 12,
                "lianban": 18,
                "max_board": 5,
                "adv": 3100,
                "dec": 1800,
            }
        )
    )
    first = out[0]
    assert "涨停 **62**" in first
    assert "跌停 **5**" in first
    assert "封板率 **78.0%**" in first
    assert "炸板 12" in first
    assert "连板 18" in first
    assert "最高 5 板" in first
    assert "上涨 3100 / 下跌 1800" in out[1]


def test_missing_fields_are_dropped_not_printed_as_none(post_market):
    out = post_market._kpi_lines(_payload({"limit_up": 62}))
    joined = "\n".join(out)
    assert "涨停 **62**" in joined
    assert "None" not in joined
    # 跌停 / 封板率 / 炸板 / 连板 / 最高板全缺，第一行只剩涨停一项。
    assert out[0] == "涨停 **62**"


def test_turnover_comes_from_the_panel_row(post_market):
    out = post_market._kpi_lines(
        _payload(
            {"limit_up": 1, "adv": 1, "dec": 1},
            panel=[{"label": "两市成交", "value": "1.9万亿", "sub": "较前值+1000亿"}],
        )
    )
    second = [line for line in out if "两市成交" in line]
    assert second and "两市成交 1.9万亿" in second[0]


def test_delta_row_carries_the_previous_close(post_market):
    """「较前值 +0.02」后面跟的昨收是减出来的，不是另取一份数据。"""
    out = post_market._kpi_lines(
        _payload(
            {"limit_up": 62},
            panel=[{"label": "涨停", "value": "62", "sub": "较前值+8"}],
        )
    )
    joined = "\n".join(out)
    assert "涨停 +8" in joined
    assert "（昨 54）" in joined
