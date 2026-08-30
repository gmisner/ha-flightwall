from __future__ import annotations

from datetime import UTC, datetime

from flightwall.board_copy import build_board, clock_text, format_stats, progress_of
from flightwall.const import TIME_12H, TIME_24H, UNIT_IMPERIAL, UNIT_METRIC


FLIGHT = {
    "callsign": "AAL123",
    "airline_short": "American",
    "airline_iata": "AA",
    "aircraft_model": "Boeing 737-800",
    "aircraft_registration": "N12345",
    "altitude": 8000,
    "ground_speed": 280,
    "distance": 4.2,
    "heading": 225,
    "airport_origin_code_iata": "LAX",
    "airport_destination_code_iata": "JFK",
    "airport_origin_city": "Los Angeles",
    "airport_destination_city": "New York",
    "time_real_departure": 1_700_000_000,
    "time_estimated_arrival": 1_700_010_000,
}


def test_format_stats_imperial_and_metric() -> None:
    imperial = format_stats(FLIGHT, UNIT_IMPERIAL)
    metric = format_stats(FLIGHT, UNIT_METRIC)
    assert "8,000 FT" in imperial
    assert "280 KT" in imperial
    assert "MI" in imperial
    assert "M" in metric
    assert "KM/H" in metric
    assert "KM" in metric


def test_clock_follows_units() -> None:
    noon = datetime(2026, 8, 30, 13, 5, tzinfo=UTC)
    assert clock_text(noon, UNIT_METRIC) == "13:05"
    assert clock_text(noon, UNIT_IMPERIAL) == "1:05 PM"
    assert clock_text(noon, UNIT_IMPERIAL, TIME_24H) == "13:05"
    assert clock_text(noon, UNIT_METRIC, TIME_12H) == "1:05 PM"


def test_progress_is_zero_without_times() -> None:
    now = datetime.fromtimestamp(1_700_005_000, UTC)
    assert progress_of({}, now) == 0
    assert 0 < progress_of(FLIGHT, now) < 32


def test_build_board_has_route_and_logo() -> None:
    now = datetime.fromtimestamp(1_700_005_000, UTC)
    board = build_board(FLIGHT, now=now, units=UNIT_IMPERIAL)
    assert board.has_flight
    assert board.route == "LAX-JFK"
    assert "LOS ANGELES" in board.cities
    assert board.logo_iata == "AA"
    assert board.title.startswith("AAL123")
    assert any(label == "FLIGHT" and value == "AAL123" for label, value in board.flap_rows)
    hidden = build_board(FLIGHT, now=now, show_logos=False)
    assert hidden.logo_iata == ""
    assert hidden.show_logos is False


def test_empty_sky_shows_last_flight() -> None:
    now = datetime.fromtimestamp(1_700_005_000, UTC)
    seen = datetime.fromtimestamp(1_700_004_970, UTC)
    board = build_board(
        None,
        now=now,
        last_flight=FLIGHT,
        last_seen=seen,
    )
    assert not board.has_flight
    assert "AAL123" in board.last_line
    assert board.last_ago == "JUST NOW"
    assert board.clock
    assert board.route == "LAX-JFK"
    assert "LOS ANGELES" in board.cities
    assert "NEW YORK" in board.cities
    assert "AMERICAN" in board.title
    assert "BOEING" in board.details
    assert board.logo_iata == "AA"
    assert board.show_logos is True
    assert "LAST OVERHEAD" in board.next_line
    assert 0 < board.progress < 32
    labels = {label: value for label, value in board.flap_rows}
    assert labels["STATUS"] == "WAITING"
    assert labels["AIRLINE"] == "American"
    assert labels["FROM"] == "LOS ANGELES"
    assert labels["TO"] == "NEW YORK"
    hidden = build_board(None, now=now, last_flight=FLIGHT, show_logos=False)
    assert hidden.logo_iata == ""
    assert hidden.show_logos is False
    empty = build_board(None, now=now)
    assert empty.title == ""
    assert empty.route == ""
    assert empty.show_logos is False
    assert [label for label, _ in empty.flap_rows] == ["STATUS", "TIME", "DATE"]
