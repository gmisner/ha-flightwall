"""Shared board text for the PNG renderer and the live Lovelace view."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from .const import TIME_12H, TIME_24H, TIME_FOLLOW_UNITS, UNIT_METRIC

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


def clock_text(
    now: datetime,
    units: str,
    time_format: str = TIME_FOLLOW_UNITS,
) -> str:
    use_24 = time_format == TIME_24H or (
        time_format != TIME_12H and units == UNIT_METRIC
    )
    if use_24:
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
    show_logos: bool
    flap_rows: list[tuple[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _airline_name(flight: dict[str, Any]) -> str:
    airline = clean(flight.get("airline_short")) or clean(flight.get("airline"))
    if len(airline) > 22:
        return airline[:21].rstrip()
    return airline


def _callsign(flight: dict[str, Any], fallback: str = "IN FLIGHT") -> str:
    return clean(flight.get("callsign")) or clean(
        flight.get("aircraft_registration"), fallback
    )


def describe_flight(
    flight: dict[str, Any],
    now: datetime,
    units: str,
    *,
    next_flight: dict[str, Any] | None = None,
    show_logos: bool = True,
) -> dict[str, Any]:
    """Shared title, route, cities, and times for the live and last-overhead boards."""
    callsign = _callsign(flight)
    airline = _airline_name(flight)
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
        next_callsign = _callsign(next_flight, "")
        if next_callsign:
            nxt_route = route_of(next_flight)
            next_line = (
                f"NEXT  {next_callsign}"
                if next_callsign == nxt_route
                else f"NEXT  {next_callsign}  {nxt_route}"
            )

    stats = format_stats(flight, units)
    stat_parts = [part.strip() for part in stats.split("  ·  ") if part.strip()]
    estimated = arriving
    if " IN " in arriving:
        estimated = arriving[arriving.rfind(" IN ") + 1 :].strip()
    dest = dest_city or clean(flight.get("airport_destination_code_iata"))
    route = route_of(flight)
    return {
        "callsign": callsign,
        "airline": airline,
        "title": f"{callsign} ({airline})".upper() if airline else callsign.upper(),
        "route": route,
        "cities": cities_of(flight),
        "details": details,
        "departed": departed,
        "arriving": arriving,
        "stats": stats,
        "progress": progress_of(flight, now),
        "next_line": next_line,
        "logo_iata": clean(flight.get("airline_iata")).upper() if show_logos else "",
        "model": model,
        "dest": dest,
        "estimated": estimated,
        "stat_parts": stat_parts,
        "origin_city": origin_city,
        "dest_city": dest_city,
    }


def build_board(
    flight: dict[str, Any] | None,
    now: datetime | None = None,
    units: str = "imperial",
    last_flight: dict[str, Any] | None = None,
    last_seen: datetime | None = None,
    next_flight: dict[str, Any] | None = None,
    time_format: str = TIME_FOLLOW_UNITS,
    show_logos: bool = True,
) -> BoardCopy:
    now = now or datetime.now(UTC)
    date = f"{now.strftime('%a')} {now.day} {now.strftime('%b')}".upper()
    clock = clock_text(now, units, time_format)
    if not flight:
        last_line = ""
        last_ago = ""
        last_label = ""
        shown: dict[str, Any] = {}
        if last_flight:
            shown = describe_flight(
                last_flight, now, units, show_logos=show_logos
            )
            last_line = (
                shown["callsign"]
                if shown["callsign"] == shown["route"]
                else f"{shown['callsign']}  {shown['route']}"
            )
            last_label = "LAST OVERHEAD"
            if last_seen is not None:
                elapsed = int((now - last_seen).total_seconds())
                last_ago = "JUST NOW" if elapsed < 60 else f"{ago(elapsed)} AGO"
            shown["next_line"] = (
                f"{last_label}  {last_ago}".strip() if last_ago else last_label
            )
        origin = clip(clean(shown.get("origin_city")).upper(), 16)
        dest = clip(clean(shown.get("dest_city")).upper(), 16)
        flap_rows = (
            [
                ("STATUS", "WAITING"),
                ("FLIGHT", shown.get("callsign", "")),
                ("AIRLINE", shown.get("airline", "")),
                ("ROUTE", shown.get("route", "")),
                ("FROM", origin),
                ("TO", dest),
                ("AIRCRAFT", shown.get("model", "")),
                ("SEEN", last_ago),
            ]
            if last_flight
            else [
                ("STATUS", "WAITING"),
                ("TIME", clock),
                ("DATE", date),
            ]
        )
        return BoardCopy(
            has_flight=False,
            title=shown.get("title", ""),
            route=shown.get("route", ""),
            cities=shown.get("cities", ""),
            details=shown.get("details", ""),
            departed=shown.get("departed", ""),
            arriving=shown.get("arriving", ""),
            stats=shown.get("stats", ""),
            progress=int(shown.get("progress") or 0),
            next_line=shown.get("next_line", ""),
            date=date,
            clock=clock,
            last_label=last_label,
            last_line=last_line,
            last_ago=last_ago,
            logo_iata=shown.get("logo_iata", ""),
            show_logos=bool(last_flight) and show_logos,
            flap_rows=flap_rows,
        )

    shown = describe_flight(
        flight,
        now,
        units,
        next_flight=next_flight,
        show_logos=show_logos,
    )
    return BoardCopy(
        has_flight=True,
        title=shown["title"],
        route=shown["route"],
        cities=shown["cities"],
        details=shown["details"],
        departed=shown["departed"],
        arriving=shown["arriving"],
        stats=shown["stats"],
        progress=shown["progress"],
        next_line=shown["next_line"],
        date=date,
        clock=clock,
        last_label="",
        last_line="",
        last_ago="",
        logo_iata=shown["logo_iata"],
        show_logos=show_logos,
        flap_rows=[
            ("FLIGHT", shown["callsign"]),
            ("AIRCRAFT", shown["model"]),
            ("AIRLINE", shown["airline"]),
            ("TO", shown["dest"]),
            ("ESTIMATED", shown["estimated"]),
            ("ALTITUDE", shown["stat_parts"][0] if shown["stat_parts"] else ""),
            ("AIRSPEED", shown["stat_parts"][1] if len(shown["stat_parts"]) > 1 else ""),
        ],
    )
