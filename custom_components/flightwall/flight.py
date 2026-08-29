"""Pick the most visible aircraft from a Flightradar24 flights list."""

from __future__ import annotations

from math import atan
from typing import Any


def pick_best_flight(
    flights: list[dict[str, Any]] | None,
    min_altitude_ft: float = 500,
) -> dict[str, Any] | None:
    """Return the flight with the highest elevation angle, or None."""
    if not flights:
        return None

    best: dict[str, Any] | None = None
    score = -1.0

    for flight in flights:
        if "altitude" not in flight or "distance" not in flight:
            continue
        try:
            altitude_ft = float(flight.get("altitude") or 0)
        except (TypeError, ValueError):
            continue
        if altitude_ft <= min_altitude_ft:
            continue
        try:
            distance_km = float(flight.get("distance") or 0)
        except (TypeError, ValueError):
            continue

        altitude_m = altitude_ft * 0.3048
        distance_m = max(distance_km * 1000, 50)
        elevation = atan(altitude_m / distance_m)
        if elevation > score:
            score = elevation
            best = flight

    return best


def callsign_of(flight: dict[str, Any] | None) -> str:
    """State string for the selected flight."""
    if not flight:
        return "none"
    callsign = flight.get("callsign")
    if callsign in (None, "", "None", "none", "null"):
        return "none"
    return str(callsign)
