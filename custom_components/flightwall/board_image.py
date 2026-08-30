"""Render a Flight Wall PNG for Chromecast Default Media Receiver."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont

from .const import STYLE_LED, UNIT_IMPERIAL, UNIT_METRIC

FONT_PATH = Path(__file__).parent / "fonts" / "Roboto-Bold.ttf"
# 4K canvas so a 50"+ set is not stretching a 1080p LED grid.
CANVAS = (3840, 2160)
SCALE = 2
CELL = 3
BG = (0, 0, 0)
WHITE = (255, 255, 255)
MUTED = (159, 184, 232)
GREEN = (53, 255, 122)
GREEN_DIM = (20, 70, 40)
LOGO_TILE = (214, 214, 214)
LOGO_URL = "https://images.kiwi.com/airlines/128/{iata}.png"
LOGO_TARGET = 220
CARDINALS = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")

_LOGO_CACHE: dict[str, Image.Image | None] = {}


def _s(value: int) -> int:
    return value * SCALE


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_PATH), _s(size))
    except OSError:
        return ImageFont.load_default()


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value).strip() if value is not None else ""
    if text in {"", "None", "none", "null", "N/A"}:
        return fallback
    return text


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 1)].rstrip()


def _ago(seconds: int) -> str:
    seconds = max(int(seconds), 0)
    if seconds >= 3600:
        return f"{seconds // 3600}H {(seconds % 3600) // 60}M"
    return f"{seconds // 60}M"


def _heading_label(flight: dict[str, Any]) -> str:
    raw = flight.get("heading")
    if raw is None:
        raw = flight.get("track")
    try:
        degrees = float(raw)
    except (TypeError, ValueError):
        return ""
    return f"HDG {CARDINALS[int((degrees + 22.5) // 45) % 8]}"


def _route(flight: dict[str, Any]) -> str:
    origin = _clean(flight.get("airport_origin_code_iata"))
    dest = _clean(flight.get("airport_destination_code_iata"))
    if origin and dest:
        return f"{origin}-{dest}"
    return _clean(flight.get("callsign")) or _clean(
        flight.get("aircraft_registration"), "IN FLIGHT"
    )


def _cities(flight: dict[str, Any]) -> str:
    origin = _clip(_clean(flight.get("airport_origin_city")).upper(), 18)
    dest = _clip(_clean(flight.get("airport_destination_city")).upper(), 18)
    if origin and dest:
        return f"{origin}  TO  {dest}"
    return origin or dest


def _clock_text(now: datetime, units: str) -> str:
    if units == UNIT_METRIC:
        return now.strftime("%H:%M")
    hour = now.hour % 12 or 12
    return f"{hour}:{now.strftime('%M')} {now.strftime('%p')}".upper()


def _format_stats(flight: dict[str, Any], units: str) -> list[str]:
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
    return stats


def _load_logo(iata: str) -> Image.Image | None:
    code = _clean(iata).upper()
    if not code:
        return None
    if code in _LOGO_CACHE:
        return _LOGO_CACHE[code]
    try:
        with urlopen(LOGO_URL.format(iata=code), timeout=6) as response:
            logo = Image.open(BytesIO(response.read())).convert("RGBA")
    except OSError:
        _LOGO_CACHE[code] = None
        return None
    _LOGO_CACHE[code] = logo
    return logo


def _airline_logo(iata: str, style: str) -> Image.Image | None:
    logo = _load_logo(iata)
    if logo is None:
        return None
    size = (_s(LOGO_TARGET), _s(LOGO_TARGET))
    resample = Image.Resampling.NEAREST if style == STYLE_LED else Image.Resampling.LANCZOS
    return logo.resize(size, resample)


def _dot_matrix(image: Image.Image, cell: int = CELL) -> Image.Image:
    """Apply a fine LED grid without crushing the board to 480p."""
    small = image.resize(
        (image.width // cell, image.height // cell), Image.Resampling.BILINEAR
    )
    led = small.resize(image.size, Image.Resampling.NEAREST).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    line = (0, 0, 0, 80)
    for y in range(0, height, cell):
        draw.line((0, y, width, y), fill=line)
    for x in range(0, width, cell):
        draw.line((x, 0, x, height), fill=line)
    return Image.alpha_composite(led, overlay).convert("RGB")


def _finish(image: Image.Image, style: str) -> bytes:
    if style == STYLE_LED:
        image = _dot_matrix(image)
    return _png_bytes(image)


def render_board_png(
    flight: dict[str, Any] | None,
    now: datetime | None = None,
    units: str = UNIT_IMPERIAL,
    style: str = STYLE_LED,
    last_flight: dict[str, Any] | None = None,
    last_seen: datetime | None = None,
    next_flight: dict[str, Any] | None = None,
) -> bytes:
    """Return PNG bytes for the current flight, or the empty-sky board."""
    now = now or datetime.now(UTC)
    image = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(image)
    callsign_font = _font(40)
    route_font = _font(168)
    clock_font = _font(180)
    body_font = _font(48)
    stats_font = _font(42)

    if not flight:
        return _finish(
            _draw_empty(
                image,
                draw,
                now,
                units,
                last_flight,
                last_seen,
                clock_font,
                body_font,
                stats_font,
            ),
            style,
        )

    return _finish(
        _draw_flight(
            image,
            draw,
            flight,
            now,
            units,
            style,
            next_flight,
            callsign_font,
            route_font,
            body_font,
            stats_font,
        ),
        style,
    )


def _draw_empty(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    now: datetime,
    units: str,
    last_flight: dict[str, Any] | None,
    last_seen: datetime | None,
    clock_font: ImageFont.ImageFont,
    body_font: ImageFont.ImageFont,
    stats_font: ImageFont.ImageFont,
) -> Image.Image:
    left = _s(120)
    draw.text(
        (left, _s(80)),
        f"{now.strftime('%a')} {now.day} {now.strftime('%b')}".upper(),
        font=stats_font,
        fill=MUTED,
    )
    draw.text((left, _s(180)), _clock_text(now, units), font=clock_font, fill=WHITE)
    draw.text((left, _s(460)), "WAITING FOR TRAFFIC", font=body_font, fill=MUTED)

    if last_flight:
        callsign = _clean(last_flight.get("callsign")) or _clean(
            last_flight.get("aircraft_registration"), "LAST FLIGHT"
        )
        route = _route(last_flight)
        draw.text((left, _s(600)), "LAST OVERHEAD", font=stats_font, fill=MUTED)
        draw.text((left, _s(680)), f"{callsign}  {route}", font=body_font, fill=WHITE)
        if last_seen is not None:
            elapsed = int((now - last_seen).total_seconds())
            seen = "JUST NOW" if elapsed < 60 else f"{_ago(elapsed)} AGO"
            draw.text((left, _s(760)), seen, font=body_font, fill=WHITE)
    return image


def _draw_flight(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    flight: dict[str, Any],
    now: datetime,
    units: str,
    style: str,
    next_flight: dict[str, Any] | None,
    callsign_font: ImageFont.ImageFont,
    route_font: ImageFont.ImageFont,
    body_font: ImageFont.ImageFont,
    stats_font: ImageFont.ImageFont,
) -> Image.Image:
    iata = _clean(flight.get("airline_iata"))
    logo = _airline_logo(iata, style)
    draw.rounded_rectangle(
        (_s(80), _s(280), _s(360), _s(560)), radius=_s(8), fill=LOGO_TILE
    )
    if logo is not None:
        box = Image.new("RGBA", (_s(280), _s(280)), (*LOGO_TILE, 255))
        lx = (_s(280) - logo.width) // 2
        ly = (_s(280) - logo.height) // 2
        box.paste(logo, (lx, ly), logo)
        image.paste(box.convert("RGB"), (_s(80), _s(280)))

    left = _s(420) if logo is not None or iata else _s(120)
    callsign = _clean(flight.get("callsign")) or _clean(
        flight.get("aircraft_registration"), "IN FLIGHT"
    )
    airline = _clean(flight.get("airline_short")) or _clean(flight.get("airline"))
    if len(airline) > 22:
        airline = airline[:21].rstrip()
    heading = f"{callsign} ({airline})" if airline else callsign
    route = _route(flight)
    cities = _cities(flight)
    model = _clean(flight.get("aircraft_model")) or _clean(flight.get("aircraft_code"))
    registration = _clean(flight.get("aircraft_registration")).upper()
    direction = _heading_label(flight)
    origin_city = _clean(flight.get("airport_origin_city"))
    dest_city = _clean(flight.get("airport_destination_city"))

    y = _s(80)
    draw.text((left, y), heading.upper(), font=callsign_font, fill=MUTED)
    y = _s(150)
    draw.text((left, y), route, font=route_font, fill=WHITE)
    y = _s(340)
    if cities:
        draw.text((left, y), cities, font=stats_font, fill=MUTED)
        y = _s(420)

    detail_bits = [bit for bit in (model.upper() if model else "", registration, direction) if bit]
    if detail_bits:
        draw.text((left, y), "  ·  ".join(detail_bits), font=body_font, fill=MUTED)
        y += _s(80)

    now_ts = int(now.timestamp())
    dep = int(flight.get("time_real_departure") or 0) or int(
        flight.get("time_scheduled_departure") or 0
    )
    arr = int(flight.get("time_estimated_arrival") or 0) or int(
        flight.get("time_scheduled_arrival") or 0
    )
    if dep > 0 and now_ts > dep:
        city = f"{origin_city.upper()} " if origin_city else ""
        draw.text(
            (left, y),
            f"DEPARTED {city}{_ago(now_ts - dep)} AGO",
            font=body_font,
            fill=WHITE,
        )
        y += _s(72)
    else:
        draw.text((left, y), "IN FLIGHT", font=body_font, fill=WHITE)
        y += _s(72)
    if arr > now_ts:
        city = f"{dest_city.upper()} " if dest_city else ""
        draw.text(
            (left, y),
            f"ARRIVING {city}IN {_ago(arr - now_ts)}",
            font=body_font,
            fill=WHITE,
        )
        y += _s(72)
    else:
        draw.text((left, y), "EN ROUTE", font=body_font, fill=WHITE)
        y += _s(72)

    stats = _format_stats(flight, units)
    if stats:
        draw.text((left, y), "  ·  ".join(stats), font=stats_font, fill=WHITE)
        y += _s(90)

    if arr > dep > 0:
        progress = max(0, min(32, round(((now_ts - dep) / max(arr - dep, 1)) * 32)))
        gap = _s(8)
        size = _s(28)
        for i in range(32):
            x = left + i * (size + gap)
            color = GREEN if i < progress else GREEN_DIM
            draw.rounded_rectangle((x, y, x + size, y + size), radius=_s(4), fill=color)

    if next_flight:
        next_callsign = _clean(next_flight.get("callsign")) or _clean(
            next_flight.get("aircraft_registration")
        )
        next_route = _route(next_flight)
        if next_callsign:
            draw.text(
                (_s(120), _s(980)),
                f"NEXT  {next_callsign}  {next_route}",
                font=stats_font,
                fill=MUTED,
            )

    return image


def _png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def write_board_png(
    path: Path,
    flight: dict[str, Any] | None,
    units: str = UNIT_IMPERIAL,
    now: datetime | None = None,
    style: str = STYLE_LED,
    last_flight: dict[str, Any] | None = None,
    last_seen: datetime | None = None,
    next_flight: dict[str, Any] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        render_board_png(
            flight,
            now=now,
            units=units,
            style=style,
            last_flight=last_flight,
            last_seen=last_seen,
            next_flight=next_flight,
        )
    )
