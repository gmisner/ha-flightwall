from __future__ import annotations

from flightwall.filters import filter_flights, is_airliner, is_helicopter, is_military


AIRLINER = {
    "callsign": "AAL123",
    "airline_iata": "AA",
    "aircraft_code": "B738",
    "ground_speed": 280,
}

HELI = {
    "callsign": "N1HX",
    "aircraft_code": "EC35",
    "aircraft_model": "Eurocopter EC135",
    "ground_speed": 90,
}

FIGHTER = {
    "callsign": "RCH01",
    "aircraft_code": "F16",
    "ground_speed": 420,
}

GA = {
    "callsign": "N123AB",
    "aircraft_code": "C172",
    "ground_speed": 110,
}


def test_is_airliner_from_iata_or_callsign() -> None:
    assert is_airliner(AIRLINER)
    assert is_airliner({"callsign": "UAL7"})
    assert not is_airliner(GA)
    assert not is_airliner(HELI)


def test_helicopter_and_military_codes() -> None:
    assert is_helicopter(HELI)
    assert is_military(FIGHTER)
    assert not is_helicopter(AIRLINER)
    assert not is_military(AIRLINER)


def test_filter_airliners_only() -> None:
    kept = filter_flights([AIRLINER, HELI, GA], airliners_only=True)
    assert [f["callsign"] for f in kept] == ["AAL123"]


def test_filter_hide_helicopters_and_military() -> None:
    kept = filter_flights(
        [AIRLINER, HELI, FIGHTER],
        hide_helicopters=True,
        hide_military=True,
    )
    assert [f["callsign"] for f in kept] == ["AAL123"]


def test_filter_min_speed() -> None:
    slow = {**AIRLINER, "ground_speed": 40}
    kept = filter_flights([AIRLINER, slow], min_speed_kt=100)
    assert [f["callsign"] for f in kept] == ["AAL123"]
