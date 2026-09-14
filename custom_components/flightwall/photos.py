"""Optional FR24 aircraft photo for the board."""

from __future__ import annotations

from typing import Any

from .board_copy import clean


def photo_url(flight: dict[str, Any] | None) -> str:
    if not flight:
        return ""
    for key in (
        "aircraft_photo_medium",
        "aircraft_photo_small",
        "aircraft_photo_large",
    ):
        raw = str(flight.get(key) or "").strip()
        if raw.startswith("http"):
            return raw
    return ""


def photo_cache_name(flight: dict[str, Any] | None) -> str:
    if not flight:
        return ""
    key = clean(flight.get("aircraft_registration")).upper() or clean(
        flight.get("callsign")
    ).upper()
    if not key:
        return ""
    return f"{key}.jpg"
