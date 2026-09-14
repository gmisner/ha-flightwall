"""Keep or drop aircraft before ranking."""

from __future__ import annotations

import re
from typing import Any

from .flight import callsign_of

HELICOPTER_CODES = {
    "A109", "A139", "A169", "A189", "AS50", "AS65", "B06", "B407", "B429",
    "EC20", "EC30", "EC35", "EC45", "EC55", "EC75", "GAZL", "H47", "H60",
    "H64", "LYNX", "MI8", "MI24", "NH90", "R22", "R44", "R66", "S76",
    "TIGR", "UH1",
}

MILITARY_CODES = {
    "A10", "A400", "B1", "B2", "B52", "C130", "C17", "C2", "C5M", "E3CF",
    "E3TF", "E8", "EUFI", "F15", "F16", "F18H", "F18S", "F22", "F35",
    "HAWK", "HUNT", "KC2", "KC46", "MRF1", "P3", "P8", "RFAL", "T38",
    "TOR", "U2", "V22", "VF35",
}

_AIRLINE_CALLSIGN = re.compile(r"^[A-Z]{3}\d")


def _code(flight: dict[str, Any]) -> str:
    return str(flight.get("aircraft_code") or flight.get("t") or "").strip().upper()


def is_helicopter(flight: dict[str, Any]) -> bool:
    code = _code(flight)
    if code in HELICOPTER_CODES:
        return True
    model = str(flight.get("aircraft_model") or "").upper()
    return "HELI" in model or "HELICOPTER" in model


def is_military(flight: dict[str, Any]) -> bool:
    return _code(flight) in MILITARY_CODES


def is_airliner(flight: dict[str, Any]) -> bool:
    iata = str(flight.get("airline_iata") or "").strip()
    icao = str(flight.get("airline_icao") or "").strip()
    if len(iata) == 2 or len(icao) == 3:
        return True
    callsign = callsign_of(flight)
    return bool(_AIRLINE_CALLSIGN.match(callsign))


def _speed_kt(flight: dict[str, Any]) -> float | None:
    raw = flight.get("ground_speed")
    if raw is None:
        raw = flight.get("gs")
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def keep_flight(
    flight: dict[str, Any],
    *,
    airliners_only: bool = False,
    hide_helicopters: bool = False,
    hide_military: bool = False,
    min_speed_kt: float = 0,
) -> bool:
    if hide_helicopters and is_helicopter(flight):
        return False
    if hide_military and is_military(flight):
        return False
    if airliners_only and not is_airliner(flight):
        return False
    if min_speed_kt > 0:
        speed = _speed_kt(flight)
        if speed is not None and speed < min_speed_kt:
            return False
    return True


def filter_flights(
    flights: list[dict[str, Any]] | None,
    *,
    airliners_only: bool = False,
    hide_helicopters: bool = False,
    hide_military: bool = False,
    min_speed_kt: float = 0,
) -> list[dict[str, Any]]:
    if not flights:
        return []
    return [
        flight
        for flight in flights
        if keep_flight(
            flight,
            airliners_only=airliners_only,
            hide_helicopters=hide_helicopters,
            hide_military=hide_military,
            min_speed_kt=min_speed_kt,
        )
    ]
