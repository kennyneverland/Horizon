"""题材块的回看窗口：12 天、跳过周末、休市日直接不读档。

``next_day.load`` 的三条约束都在这里钉住，因为每一条失效都会变成读者能看见的错误：

* 窗口从 5 改到 12 是因为 2027 年春节：2/15 开市，节前最后交易日是 2/4，相隔 11 天。
  10 天只回到 2/5（休市首日，站点上没有可读的晚报）——窗口少了就是「节后第一天
  题材块空白」。
* 晚班只在周一到周五发布，周末那两天请求必然 404；跳过的不是一两次：春节那 11 天
  里有 4 天是周末，12 次请求降到 8 次。
* ``trading_day=False`` 是「今天本来就没开市」，不该去站点上翻别人的晚报——那会把
  上一交易日的判断印在一个从没开盘的日期下（2026-11-28 周六就发生过）。

用例把 ``_get`` 与 ``session.opened`` 都打桩，不碰网络。
"""

from __future__ import annotations

import types
from datetime import date as _date

import pytest

import src.processing.next_day as next_day


def _dates_from(urls):
    out = []
    for url in urls:
        out.append(url.rsplit("/", 1)[-1].removesuffix(".html"))
    return out


def test_lookback_is_twelve_days():
    assert next_day.LOOKBACK_DAYS == 12


def test_chinese_new_year_gap_reaches_the_last_session(monkeypatch):
    """2/15 往回第 11 天才到 2/4；窗口正好 12，gap 记的是日历天数。"""
    asked = []

    def fake_get(url, timeout=20.0):
        day = _dates_from([url])[0]
        asked.append(day)
        if day == "2027-02-04":
            return '<script id="next-day-brief">{"mainline": []}</script>'
        raise RuntimeError("404")

    monkeypatch.setattr(next_day, "_get", fake_get)
    monkeypatch.setattr(next_day._session, "opened", lambda day: True)

    doc = next_day.load("2027-02-15")
    assert doc is not None
    assert doc["_source_date"] == "2027-02-04"
    assert doc["_gap_days"] == 11


def test_weekends_are_skipped_not_requested(monkeypatch):
    """12 天窗口里只该发出 8 次请求：2/14、2/13、2/7、2/6 是周末。"""
    asked = []

    def fake_get(url, timeout=20.0):
        asked.append(_dates_from([url])[0])
        raise RuntimeError("404")

    monkeypatch.setattr(next_day, "_get", fake_get)
    monkeypatch.setattr(next_day._session, "opened", lambda day: True)

    assert next_day.load("2027-02-15") is None
    assert asked == [
        "2027-02-12",
        "2027-02-11",
        "2027-02-10",
        "2027-02-09",
        "2027-02-08",
        "2027-02-05",
        "2027-02-04",
        "2027-02-03",
    ]
    assert not [d for d in asked if _date.fromisoformat(d).weekday() >= 5]


def test_closed_weekday_reads_nothing(monkeypatch):
    """2027-01-01 周五、表里有「元旦」：判出休市后一个请求都不发。"""
    called = []
    monkeypatch.setattr(next_day, "_get", lambda *a, **k: called.append(1) or "")
    monkeypatch.setattr(next_day, "_session", types.SimpleNamespace(opened=lambda day: False))

    assert next_day.load("2027-01-01") is None
    assert called == []


def test_weekend_does_not_even_probe_the_pool(monkeypatch):
    """周末由星期几就能判出，不必再问一次东财。"""
    probed = []

    def opened(day):
        probed.append(day)
        return True

    monkeypatch.setattr(next_day, "_session", types.SimpleNamespace(opened=opened))
    monkeypatch.setattr(
        next_day, "_get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no request"))
    )

    assert next_day.load("2027-02-14") is None
    assert probed == []


def test_explicit_trading_day_false_short_circuits(monkeypatch):
    """调用方已经知道今天没开市时，连日历都不查。"""
    monkeypatch.setattr(
        next_day, "_session", types.SimpleNamespace(opened=lambda day: pytest.fail("no probe"))
    )
    monkeypatch.setattr(
        next_day, "_get", lambda *a, **k: pytest.fail("no request")
    )
    assert next_day.load("2027-02-15", trading_day=False) is None
