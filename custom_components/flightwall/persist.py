"""Serialize last-overhead and today's traffic for Home Assistant storage."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .flight import callsign_of

OVERHEAD_LIMIT = 12


def overhead_entry(flight: dict[str, Any], now: datetime) -> dict[str, Any]:
    airline = str(flight.get("airline_short") or flight.get("airline") or "").strip()
    origin = str(flight.get("airport_origin_code_iata") or "").strip()
    dest = str(flight.get("airport_destination_code_iata") or "").strip()
    route = f"{origin}-{dest}" if origin and dest else callsign_of(flight)
    return {
        "callsign": callsign_of(flight),
        "route": route,
        "airline": airline,
        "seen": now.isoformat(),
        "day": now.date().isoformat(),
    }


def merge_overhead(
    history: list[dict[str, Any]] | None,
    flight: dict[str, Any],
    now: datetime,
    limit: int = OVERHEAD_LIMIT,
) -> list[dict[str, Any]]:
    day = now.date().isoformat()
    kept = [item for item in (history or []) if item.get("day") == day]
    callsign = callsign_of(flight)
    if callsign == "none":
        return kept
    entry = overhead_entry(flight, now)
    if kept and kept[-1].get("callsign") == callsign:
        kept[-1] = entry
        return kept
    kept.append(entry)
    return kept[-limit:]


def dump_state(
    last_flight: dict[str, Any] | None,
    last_seen: datetime | None,
    overhead: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "last_flight": last_flight,
        "last_seen": last_seen.isoformat() if last_seen else None,
        "overhead": overhead,
    }


def load_state(
    data: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, datetime | None, list[dict[str, Any]]]:
    if not data:
        return None, None, []
    last_flight = data.get("last_flight")
    if not isinstance(last_flight, dict):
        last_flight = None
    last_seen = None
    raw_seen = data.get("last_seen")
    if isinstance(raw_seen, str) and raw_seen:
        try:
            last_seen = datetime.fromisoformat(raw_seen)
        except ValueError:
            last_seen = None
    overhead = data.get("overhead")
    if not isinstance(overhead, list):
        overhead = []
    return last_flight, last_seen, [item for item in overhead if isinstance(item, dict)]
