from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flightwall.aircraft_types import type_name
from flightwall.const import inbound_delay, keepalive_interval
from flightwall.persist import dump_state, load_state, merge_overhead
from flightwall.tv import (
    is_cast_source,
    should_attempt_cast,
    should_refresh_board,
    should_select_cast,
)


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


def test_inbound_delay_clamps_and_defaults() -> None:
    assert inbound_delay() == timedelta(seconds=120)
    assert inbound_delay(30) == timedelta(seconds=30)
    assert inbound_delay(1) == timedelta(seconds=15)
    assert inbound_delay(9999) == timedelta(seconds=600)


def test_select_cast_only_on_takeover() -> None:
    assert should_select_cast("tv_on")
    assert should_select_cast("armed")
    assert should_select_cast("recast")
    assert not should_select_cast("keep")
    assert not should_select_cast("flight")


def test_skip_keepalive_when_player_is_dead() -> None:
    assert not should_attempt_cast(reason="keep", power_on=True, player_state="off")
    assert not should_attempt_cast(reason="keep", power_on=True, player_state="unavailable")
    assert not should_attempt_cast(reason="flight", power_on=False, player_state="playing")
    assert should_attempt_cast(reason="keep", power_on=True, player_state="playing")
    assert should_attempt_cast(reason="tv_on", power_on=True, player_state="off")
    assert should_attempt_cast(reason="recast", power_on=False, player_state="off")


def test_icao_type_names() -> None:
    assert type_name("B738") == "Boeing 737-800"
    assert type_name("B738", "Boeing 737-800") == "Boeing 737-800"
    assert type_name("ZZZZ") == "ZZZZ"
    assert type_name(None, "Cessna 172") == "Cessna 172"


def test_overhead_history_persists_and_resets_by_day() -> None:
    now = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
    later = datetime(2026, 8, 31, 12, 5, tzinfo=UTC)
    next_day = datetime(2026, 9, 1, 8, 0, tzinfo=UTC)
    flight = {"callsign": "AAL123", "airport_origin_code_iata": "LAX", "airport_destination_code_iata": "JFK"}
    other = {"callsign": "UAL1", "airport_origin_code_iata": "SFO", "airport_destination_code_iata": "EWR"}
    history = merge_overhead([], flight, now)
    history = merge_overhead(history, flight, later)
    assert len(history) == 1
    assert history[0]["callsign"] == "AAL123"
    history = merge_overhead(history, other, later)
    assert [item["callsign"] for item in history] == ["AAL123", "UAL1"]
    history = merge_overhead(history, other, next_day)
    assert [item["callsign"] for item in history] == ["UAL1"]
    data = dump_state(flight, now, history)
    loaded_flight, loaded_seen, loaded_hist = load_state(data)
    assert loaded_flight["callsign"] == "AAL123"
    assert loaded_seen == now
    assert loaded_hist[0]["callsign"] == "UAL1"
