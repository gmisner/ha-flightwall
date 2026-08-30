from __future__ import annotations

from flightwall.tv import is_cast_source, should_refresh_board, should_select_cast


def test_cast_source_names() -> None:
    assert is_cast_source("Cast")
    assert is_cast_source("Chromecast")
    assert is_cast_source("Google Cast")
    assert not is_cast_source("Netflix")
    assert not is_cast_source("SmartCast Home")


def test_refresh_only_on_cast_or_unknown_source() -> None:
    assert should_refresh_board(source="Cast", showing_board=False)
    assert should_refresh_board(source="HDMI-1", showing_board=True)
    assert should_refresh_board(source="", showing_board=False)
    assert not should_refresh_board(source="Netflix", showing_board=False)
    assert not should_refresh_board(source="SmartCast Home", showing_board=False)
    assert not should_refresh_board(source="webOS Home", showing_board=False)


def test_select_cast_only_on_takeover() -> None:
    assert should_select_cast("tv_on")
    assert should_select_cast("armed")
    assert should_select_cast("recast")
    assert not should_select_cast("keep")
    assert not should_select_cast("flight")
