"""休市判定的三态与原因措辞：判不出来不等于休市，没有原因不等于编一个。

两件事在这里分开测，因为它们混起来会出硬错误：

* ``session.opened`` 判的「今天开不开市」只认报价日期。它有三种结果——
  True 开市 / False 休市 / **None 判不出来**。把 None 当 False 用，交易日会被
  当成休市、晚间整份晚报不出；这个文件把三态各钉一条，顺带锁住「当天有开盘
  快照就不再问东财」这条缓存路径。
* ``market_calendar`` 只回答「为什么」。查不到原因就只说「休市」，不拿别的日子
  或别的市场的原因顶替——2026-11-23 日本勤劳感谢日那天，日经那格直接消失，
  读者分不清是休市还是取数断了，就是缺这层措辞。

所有用例都不碰网络：``_asked`` / ``_snapshot`` 全部被打桩或替换掉。
"""

from __future__ import annotations

import src.processing.market_calendar as calendar
import src.processing.session as session


# --- session.opened：三态 ---------------------------------------------------


def test_snapshot_hit_is_open_and_never_probes(tmp_path, monkeypatch):
    """当天落了开盘快照 → 直接 True，且不去问东财（晚报缓存命中的判据）。"""
    (tmp_path / "20261128.json").write_text("{}", encoding="utf-8")
    calls = []

    def probe(day, timeout):  # pragma: no cover - 被调到就说明缓存没生效
        calls.append(day)
        raise AssertionError("snapshot hit must not reach the pool endpoint")

    monkeypatch.setattr(session, "_asked", probe)
    assert session.opened("2026-11-28", store=tmp_path) is True
    assert calls == []


def test_pool_answering_the_same_day_is_open(tmp_path, monkeypatch):
    monkeypatch.setattr(session, "_asked", lambda day, timeout: "20261128")
    assert session.opened("2026-11-28", store=tmp_path) is True


def test_pool_answering_an_earlier_day_is_closed(tmp_path, monkeypatch):
    """涨停池回最近交易日 = 那天没开市，这是工作日休市唯一能认出来的路。"""
    monkeypatch.setattr(session, "_asked", lambda day, timeout: "20261127")
    assert session.opened("2026-11-28", store=tmp_path) is False


def test_probe_failure_is_unknown_not_closed(tmp_path, monkeypatch):
    """问不到（限流、改版、超时）是「判不出来」，不许当成休市。"""

    def boom(day, timeout):
        raise RuntimeError("429 too many requests")

    monkeypatch.setattr(session, "_asked", boom)
    assert session.opened("2026-11-28", store=tmp_path) is None


def test_empty_qdate_is_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(session, "_asked", lambda day, timeout: None)
    assert session.opened("2026-11-28", store=tmp_path) is None


def test_blank_day_is_unknown_without_a_request(tmp_path, monkeypatch):
    def probe(day, timeout):  # pragma: no cover
        raise AssertionError("a blank date must not trigger a request")

    monkeypatch.setattr(session, "_asked", probe)
    assert session.opened("  ", store=tmp_path) is None


# --- market_calendar：措辞 -------------------------------------------------


def test_reason_is_the_holiday_name_for_a_weekday_closure():
    assert calendar.reason("2027-01-01") == "元旦"


def test_reason_is_empty_for_a_weekend():
    """周末不在表里——那张表只收落在周一至周五的休市日。"""
    assert calendar.reason("2026-11-28") == ""


def test_cn_closed_line_names_the_holiday():
    assert calendar.cn_closed_line("2027-10-01") == "国内股市因国庆节休市"


def test_cn_closed_line_without_a_reason_says_only_closed():
    assert calendar.cn_closed_line("2026-11-28") == "国内股市今日休市"


def test_closed_line_for_market_with_empty_table_says_only_closed():
    """日、韩、港、台四张表先留空：不许编节日名。"""
    assert calendar.closed_line("日经225", "2027-01-01") == "日经225 今日休市"


def test_closed_line_without_a_market_says_only_closed():
    """认不出市场的名字不猜市场：猜错会把日本的原因安到韩国头上。"""
    assert calendar.closed_line("某个不存在的指数", "2027-01-01") == "某个不存在的指数 今日休市"


def test_market_of_translates_index_names():
    assert calendar.market_of("日经225") == "JP"
    assert calendar.market_of("恒生科技") == "HK"
    assert calendar.market_of("瞎写的名字") == ""


def test_known_is_diagnostic_only():
    assert calendar.known("2027-01-01") is True
    assert calendar.known("2026-11-28") is False


def test_describe_reads_as_a_log_line():
    assert calendar.describe("2027-01-01") == "2027-01-01 是 A股 的 元旦"
    assert calendar.describe("2026-11-28") is None
