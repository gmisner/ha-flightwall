from __future__ import annotations

from datetime import timedelta

from flightwall.const import keepalive_interval
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


def test_keepalive_interval_clamps_and_defaults() -> None:
    assert keepalive_interval() == timedelta(seconds=20)
    assert keepalive_interval(15) == timedelta(seconds=15)
    assert keepalive_interval("45") == timedelta(seconds=45)
    assert keepalive_interval(1) == timedelta(seconds=5)
    assert keepalive_interval(999) == timedelta(seconds=300)
    assert keepalive_interval("nope") == timedelta(seconds=20)


def test_select_cast_only_on_takeover() -> None:
    assert should_select_cast("tv_on")
    assert should_select_cast("armed")
    assert should_select_cast("recast")
    assert not should_select_cast("keep")
    assert not should_select_cast("flight")
