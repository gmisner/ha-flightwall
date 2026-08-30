"""Map tar1090 / readsb aircraft lists into Flight Wall's flight dicts."""

from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import Any


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius * atan2(sqrt(a), sqrt(1 - a))


def _altitude_ft(aircraft: dict[str, Any]) -> float | None:
    raw = aircraft.get("alt_baro")
    if raw is None:
        raw = aircraft.get("alt_geom")
    if raw is None:
        raw = aircraft.get("altitude")
    if raw in (None, "ground"):
        return 0.0 if raw == "ground" else None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def from_adsb(
    aircraft: dict[str, Any],
    home_lat: float,
    home_lon: float,
) -> dict[str, Any] | None:
    """Return a Flightradar24-shaped dict, or None if it cannot be ranked."""
    try:
        lat = float(aircraft["lat"])
        lon = float(aircraft["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    altitude = _altitude_ft(aircraft)
    if altitude is None:
        return None
    callsign = str(aircraft.get("flight") or aircraft.get("callsign") or "").strip()
    if not callsign:
        callsign = str(aircraft.get("hex") or aircraft.get("r") or "").strip()
    speed = aircraft.get("gs")
    if speed is None:
        speed = aircraft.get("ground_speed")
    heading = aircraft.get("track")
    if heading is None:
        heading = aircraft.get("true_heading")
    if heading is None:
        heading = aircraft.get("heading")
    result: dict[str, Any] = {
        "callsign": callsign or "none",
        "altitude": altitude,
        "distance": haversine_km(home_lat, home_lon, lat, lon),
        "aircraft_registration": aircraft.get("r") or aircraft.get("aircraft_registration"),
        "aircraft_code": aircraft.get("t") or aircraft.get("aircraft_code"),
        "lat": lat,
        "lon": lon,
    }
    if speed is not None:
        try:
            result["ground_speed"] = float(speed)
        except (TypeError, ValueError):
            pass
    if heading is not None:
        try:
            result["heading"] = float(heading)
        except (TypeError, ValueError):
            pass
    return result


def flights_from_attributes(
    attributes: dict[str, Any] | None,
    home_lat: float,
    home_lon: float,
) -> list[dict[str, Any]]:
    if not attributes:
        return []
    raw = attributes.get("flights")
    if isinstance(raw, list) and raw:
        first = raw[0] if isinstance(raw[0], dict) else {}
        if isinstance(first, dict) and (
            "airport_origin_code_iata" in first
            or "airline_iata" in first
            or ("distance" in first and "altitude" in first and "hex" not in first)
        ):
            return [item for item in raw if isinstance(item, dict)]
        mapped = [
            flight
            for item in raw
            if isinstance(item, dict)
            and (flight := from_adsb(item, home_lat, home_lon))
        ]
        if mapped:
            return mapped
    aircraft = attributes.get("aircraft")
    if isinstance(aircraft, list):
        return [
            flight
            for item in aircraft
            if isinstance(item, dict)
            and (flight := from_adsb(item, home_lat, home_lon))
        ]
    return []
