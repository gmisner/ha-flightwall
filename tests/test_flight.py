from __future__ import annotations

from flightwall.flight import callsign_of, pick_best_flight, rank_flights


def test_rank_flights_prefers_higher_elevation() -> None:
    cruise = {"callsign": "CRUISE", "altitude": 38000, "distance": 20}
    approach = {"callsign": "APPR", "altitude": 2000, "distance": 1}
    ranked = rank_flights([cruise, approach])
    assert [f["callsign"] for f in ranked] == ["APPR", "CRUISE"]


def test_rank_flights_skips_ground_and_low_altitude() -> None:
    ground = {"callsign": "GND", "altitude": 80, "distance": 1}
    low = {"callsign": "LOW", "altitude": 500, "distance": 1}
    air = {"callsign": "AIR", "altitude": 1200, "distance": 2}
    assert [f["callsign"] for f in rank_flights([ground, low, air])] == ["AIR"]


def test_rank_flights_respects_min_altitude() -> None:
    flight = {"callsign": "MID", "altitude": 800, "distance": 2}
    assert rank_flights([flight], min_altitude_ft=500)[0]["callsign"] == "MID"
    assert rank_flights([flight], min_altitude_ft=900) == []


def test_rank_flights_skips_broken_rows() -> None:
    assert rank_flights([{"callsign": "NOALT", "distance": 1}]) == []
    assert rank_flights([{"callsign": "BAD", "altitude": "x", "distance": 1}]) == []
    assert pick_best_flight([]) is None
    assert pick_best_flight(None) is None


def test_callsign_of() -> None:
    assert callsign_of(None) == "none"
    assert callsign_of({"callsign": "AAL123"}) == "AAL123"
    assert callsign_of({"callsign": "None"}) == "none"
    assert callsign_of({"callsign": ""}) == "none"
