"""Shared board text for the PNG renderer and the live Lovelace view."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from .const import UNIT_METRIC

CARDINALS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")


def clean(value: Any, fallback: str = "") -> str:
    text = str(value).strip() if value is not None else ""
    if text in {"", "None", "none", "null", "N/A"}:
        return fallback
    return text


def clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 1)].rstrip()


def ago(seconds: int) -> str:
    seconds = max(int(seconds), 0)
    if seconds >= 3600:
        return f"{seconds // 3600}H {(seconds % 3600) // 60}M"
    return f"{seconds // 60}M"


def heading_label(flight: dict[str, Any]) -> str:
    raw = flight.get("heading")
    if raw is None:
        raw = flight.get("track")
    try:
        degrees = float(raw)
    except (TypeError, ValueError):
        return ""
    return f"HDG {CARDINALS[int((degrees + 22.5) // 45) % 8]}"


def route_of(flight: dict[str, Any]) -> str:
    origin = clean(flight.get("airport_origin_code_iata"))
    dest = clean(flight.get("airport_destination_code_iata"))
    if origin and dest:
        return f"{origin}-{dest}"
    return clean(flight.get("callsign")) or clean(
        flight.get("aircraft_registration"), "IN FLIGHT"
    )


def cities_of(flight: dict[str, Any]) -> str:
    origin = clip(clean(flight.get("airport_origin_city")).upper(), 18)
    dest = clip(clean(flight.get("airport_destination_city")).upper(), 18)
    if origin and dest:
        return f"{origin}  TO  {dest}"
    return origin or dest


def clock_text(now: datetime, units: str) -> str:
    if units == UNIT_METRIC:
        return now.strftime("%H:%M")
    hour = now.hour % 12 or 12
    return f"{hour}:{now.strftime('%M')} {now.strftime('%p')}".upper()


def format_stats(flight: dict[str, Any], units: str) -> str:
    metric = units == UNIT_METRIC
    stats: list[str] = []
    if flight.get("altitude") is not None:
        altitude_ft = float(flight["altitude"])
        if metric:
            stats.append(f"{int(round(altitude_ft * 0.3048)):,} M")
        else:
            stats.append(f"{int(altitude_ft):,} FT")
    if flight.get("ground_speed") is not None:
        speed_kt = float(flight["ground_speed"])
        if metric:
            stats.append(f"{int(round(speed_kt * 1.852))} KM/H")
        else:
            stats.append(f"{int(speed_kt)} KT")
    if flight.get("distance") is not None:
        distance_km = float(flight["distance"])
        if metric:
            stats.append(f"{distance_km:.1f} KM")
        else:
            stats.append(f"{distance_km * 0.621371:.1f} MI")
    return "  ·  ".join(stats)


def progress_of(flight: dict[str, Any], now: datetime) -> int:
    now_ts = int(now.timestamp())
    dep = int(flight.get("time_real_departure") or 0) or int(
        flight.get("time_scheduled_departure") or 0
    )
    arr = int(flight.get("time_estimated_arrival") or 0) or int(
        flight.get("time_scheduled_arrival") or 0
    )
    if arr > dep > 0:
        return max(0, min(32, round(((now_ts - dep) / max(arr - dep, 1)) * 32)))
    return 0


@dataclass
class BoardCopy:
    has_flight: bool
    title: str
    route: str
    cities: str
    details: str
    departed: str
    arriving: str
    stats: str
    progress: int
    next_line: str
    date: str
    clock: str
    last_label: str
    last_line: str
    last_ago: str
    logo_iata: str
    flap_rows: list[tuple[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_board(
    flight: dict[str, Any] | None,
    now: datetime | None = None,
    units: str = "imperial",
    last_flight: dict[str, Any] | None = None,
    last_seen: datetime | None = None,
    next_flight: dict[str, Any] | None = None,
) -> BoardCopy:
    now = now or datetime.now(UTC)
    date = f"{now.strftime('%a')} {now.day} {now.strftime('%b')}".upper()
    if not flight:
        last_line = ""
        last_ago = ""
        if last_flight:
            callsign = clean(last_flight.get("callsign")) or clean(
                last_flight.get("aircraft_registration"), "LAST FLIGHT"
            )
            route = route_of(last_flight)
            last_line = callsign if callsign == route else f"{callsign}  {route}"
            if last_seen is not None:
                elapsed = int((now - last_seen).total_seconds())
                last_ago = "JUST NOW" if elapsed < 60 else f"{ago(elapsed)} AGO"
        return BoardCopy(
            has_flight=False,
            title="",
            route="",
            cities="",
            details="",
            departed="",
            arriving="",
            stats="",
            progress=0,
            next_line="",
            date=date,
            clock=clock_text(now, units),
            last_label="LAST OVERHEAD" if last_line else "",
            last_line=last_line,
            last_ago=last_ago,
            logo_iata="",
            flap_rows=[
                ("STATUS", "WAITING"),
                ("TIME", clock_text(now, units)),
                ("DATE", date),
                ("LAST", last_line),
                ("SEEN", last_ago),
            ],
        )

    callsign = clean(flight.get("callsign")) or clean(
        flight.get("aircraft_registration"), "IN FLIGHT"
    )
    airline = clean(flight.get("airline_short")) or clean(flight.get("airline"))
    if len(airline) > 22:
        airline = airline[:21].rstrip()
    title = f"{callsign} ({airline})" if airline else callsign
    model = clean(flight.get("aircraft_model")) or clean(flight.get("aircraft_code"))
    registration = clean(flight.get("aircraft_registration")).upper()
    direction = heading_label(flight)
    details = "  ·  ".join(
        bit for bit in (model.upper() if model else "", registration, direction) if bit
    )
    origin_city = clean(flight.get("airport_origin_city"))
    dest_city = clean(flight.get("airport_destination_city"))
    now_ts = int(now.timestamp())
    dep = int(flight.get("time_real_departure") or 0) or int(
        flight.get("time_scheduled_departure") or 0
    )
    arr = int(flight.get("time_estimated_arrival") or 0) or int(
        flight.get("time_scheduled_arrival") or 0
    )
    if dep > 0 and now_ts > dep:
        city = f"{origin_city.upper()} " if origin_city else ""
        departed = f"DEPARTED {city}{ago(now_ts - dep)} AGO"
    else:
        departed = "IN FLIGHT"
    if arr > now_ts:
        city = f"{dest_city.upper()} " if dest_city else ""
        arriving = f"ARRIVING {city}IN {ago(arr - now_ts)}"
    else:
        arriving = "EN ROUTE"

    next_line = ""
    if next_flight:
        next_callsign = clean(next_flight.get("callsign")) or clean(
            next_flight.get("aircraft_registration")
        )
        if next_callsign:
            route = route_of(next_flight)
            next_line = (
                f"NEXT  {next_callsign}"
                if next_callsign == route
                else f"NEXT  {next_callsign}  {route}"
            )

    stats = format_stats(flight, units)
    stat_parts = [part.strip() for part in stats.split("  ·  ") if part.strip()]
    estimated = arriving
    if " IN " in arriving:
        estimated = arriving[arriving.rfind(" IN ") + 1 :].strip()
    dest = dest_city or clean(flight.get("airport_destination_code_iata"))

    return BoardCopy(
        has_flight=True,
        title=title.upper(),
        route=route_of(flight),
        cities=cities_of(flight),
        details=details,
        departed=departed,
        arriving=arriving,
        stats=stats,
        progress=progress_of(flight, now),
        next_line=next_line,
        date=date,
        clock=clock_text(now, units),
        last_label="",
        last_line="",
        last_ago="",
        logo_iata=clean(flight.get("airline_iata")).upper(),
        flap_rows=[
            ("FLIGHT", callsign),
            ("AIRCRAFT", model),
            ("AIRLINE", airline),
            ("TO", dest),
            ("ESTIMATED", estimated),
            ("ALTITUDE", stat_parts[0] if stat_parts else ""),
            ("AIRSPEED", stat_parts[1] if len(stat_parts) > 1 else ""),
        ],
    )
