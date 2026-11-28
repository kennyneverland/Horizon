"""连板网日历的三态：没取到，不等于那天没有事件。

早报的题材靠「前一日 09:00 之后的三星事件」触发 Google News 检索。这条链路原先
只有两态：页面取到但没有三星 → `[]`；页面取不到 → 也是 `[]`。两者在日志里共用
一句「日历无昨日事件（YYYY-MM-DD），跳过注入」，于是「连板网没连上」被讲成
「昨天没有数据落地」——读日志的人不会再去查，那天的题材就静默地少了，而三处
画面全都正常。

三态在这里各钉一条，全部不碰网络：

* `fetch_calendar` 取不到返回 `None`，取到就返回页面（哪怕页面上一个三星都没有）；
* `archive_exists` 分出「次日没有存档」与「存档在」；
* `calendar_note` 三种情形给三句不同的话，只有「确实没取到」才用 yellow。
"""

from __future__ import annotations

import asyncio

import pytest

import src.processing.lianban_calendar as calendar


class _Response:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:  # pragma: no cover - 只需要存在
        return None


class _Client:
    """最小 httpx 替身：要么给页面，要么在 get 里抛。"""

    def __init__(self, text: str = "", exc: Exception | None = None) -> None:
        self._text = text
        self._exc = exc

    async def get(self, url, headers=None):  # noqa: ANN001, ANN201 - 签名对齐调用方
        if self._exc is not None:
            raise self._exc
        return _Response(self._text)


def test_fetch_calendar_returns_the_page():
    page = asyncio.run(calendar.fetch_calendar(_Client(text="<html>cald</html>")))
    assert page == "<html>cald</html>"


def test_fetch_calendar_failure_is_none_not_empty_string():
    """取不到必须是 None：空串会让下游把它当成「取到了、但一个字都没有」。"""
    page = asyncio.run(calendar.fetch_calendar(_Client(exc=RuntimeError("429 too many"))))
    assert page is None


def test_fetch_calendar_failure_is_logged_with_the_reason(caplog):
    with caplog.at_level("WARNING", logger="src.processing.lianban_calendar"):
        asyncio.run(calendar.fetch_calendar(_Client(exc=TimeoutError("timed out"))))
    assert "日历取不到" in caplog.text
    assert "timed out" in caplog.text


def test_fetch_events_duplicate_stays_deleted():
    """`fetch_events` 是同一件事的重复实现，零调用；不许再长回来。"""
    assert not hasattr(calendar, "fetch_events")


def test_archive_exists_separates_missing_from_present(tmp_path):
    assert calendar.archive_exists("2026-11-27", root=tmp_path) is False
    (tmp_path / "2026-11-27.json").write_text("{}", encoding="utf-8")
    assert calendar.archive_exists("2026-11-27", root=tmp_path) is True


def test_note_when_events_were_found():
    level, text = calendar.calendar_note("2026-11-27", 3, page_ok=True, archived=False)
    assert level == "dim"
    assert "3 条" in text


def test_note_confirmed_empty_when_the_page_was_read():
    """页面取到了、昨日没有三星：这是确定的「没有」，不该报警。"""
    level, text = calendar.calendar_note("2026-11-27", 0, page_ok=True, archived=False)
    assert level == "dim"
    assert "无 2026-11-27 三星事件" in text


def test_note_confirmed_empty_when_only_the_archive_was_read():
    """页面取不到，但昨日存档在：仍属确定结论。"""
    level, text = calendar.calendar_note("2026-11-27", 0, page_ok=False, archived=True)
    assert level == "dim"
    assert "无 2026-11-27 三星事件" in text


def test_note_unknown_when_nothing_was_fetched_or_archived():
    """页面取不到、存档也没有：只能说「这次没取到」，不许说「没有事件」。"""
    level, text = calendar.calendar_note("2026-11-27", 0, page_ok=False, archived=False)
    assert level == "yellow"
    assert "取不到" in text
    assert "不能据此判断" in text
    assert "无 2026-11-27 三星事件" not in text


def test_the_three_notes_are_three_different_sentences():
    """验收条件本身：三种造数下的日志三句不同。"""
    texts = {
        calendar.calendar_note("2026-11-27", 2, page_ok=True, archived=False)[1],
        calendar.calendar_note("2026-11-27", 0, page_ok=True, archived=False)[1],
        calendar.calendar_note("2026-11-27", 0, page_ok=False, archived=False)[1],
    }
    assert len(texts) == 3