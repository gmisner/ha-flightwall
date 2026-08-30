"""Render a high-contrast Flight Wall PNG for Chromecast Default Media Receiver."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = Path(__file__).parent / "fonts" / "Roboto-Bold.ttf"
CANVAS = (1920, 1080)
BG = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 200, 0)
MUTED = (200, 200, 200)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except OSError:
        return ImageFont.load_default()


def _clean(value: Any, fallback: str = "") -> str:
    text = str(value).strip() if value is not None else ""
    if text in {"", "None", "none", "null", "N/A"}:
        return fallback
    return text


def _ago(seconds: int) -> str:
    if seconds >= 3600:
        return f"{seconds // 3600}H {(seconds % 3600) // 60}M"
    return f"{seconds // 60}M"


def render_board_png(flight: dict[str, Any] | None, now: datetime | None = None) -> bytes:
    """Return PNG bytes for the current flight, or the empty-sky board."""
    now = now or datetime.now(UTC)
    image = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(image)
    title = _font(72)
    huge = _font(180)
    mid = _font(56)
    small = _font(40)
    draw.rectangle((0, 0, CANVAS[0], 16), fill=YELLOW)

    if not flight:
        draw.text((80, 120), "FLIGHT WALL", font=title, fill=YELLOW)
        draw.text((80, 280), "WAITING", font=huge, fill=WHITE)
        draw.text((80, 500), "FOR TRAFFIC", font=huge, fill=WHITE)
        draw.text((80, 780), "No aircraft overhead", font=mid, fill=MUTED)
        draw.text((80, 980), "FLIGHT WALL", font=small, fill=MUTED)
        return _png_bytes(image)

    callsign = _clean(flight.get("callsign"), "IN FLIGHT")
    airline = _clean(flight.get("airline_short")) or _clean(flight.get("airline"))
    origin = _clean(flight.get("airport_origin_code_iata"))
    dest = _clean(flight.get("airport_destination_code_iata"))
    origin_city = _clean(flight.get("airport_origin_city"))
    dest_city = _clean(flight.get("airport_destination_city"))
    model = _clean(flight.get("aircraft_model")) or _clean(flight.get("aircraft_code"))
    heading = f"{callsign}  {airline}".strip()
    route = f"{origin}-{dest}" if origin and dest else callsign

    draw.text((80, 70), heading, font=title, fill=YELLOW)
    draw.text((80, 200), route, font=huge, fill=WHITE)
    if model:
        draw.text((80, 430), model, font=mid, fill=MUTED)

    cities = []
    if origin_city:
        cities.append(f"FROM {origin_city.upper()}")
    if dest_city:
        cities.append(f"TO {dest_city.upper()}")
    if cities:
        draw.text((80, 520), "  ·  ".join(cities), font=mid, fill=WHITE)

    now_ts = int(now.timestamp())
    dep = int(flight.get("time_real_departure") or 0) or int(
        flight.get("time_scheduled_departure") or 0
    )
    arr = int(flight.get("time_estimated_arrival") or 0) or int(
        flight.get("time_scheduled_arrival") or 0
    )
    timeline = []
    if dep > 0 and now_ts > dep:
        city = f"{origin_city} " if origin_city else ""
        timeline.append(f"DEPARTED {city}{_ago(now_ts - dep)} AGO")
    if arr > now_ts:
        city = f"{dest_city} " if dest_city else ""
        timeline.append(f"ARRIVING {city}IN {_ago(arr - now_ts)}")
    if timeline:
        draw.text((80, 620), "  ·  ".join(timeline), font=mid, fill=MUTED)

    stats = []
    if flight.get("altitude") is not None:
        stats.append(f"{int(flight['altitude']):,} FT".replace(",", "."))
    if flight.get("ground_speed") is not None:
        stats.append(f"{int(flight['ground_speed'])} KT")
    if flight.get("distance") is not None:
        stats.append(f"{float(flight['distance']):.1f} KM")
    if stats:
        draw.text((80, 720), "  ·  ".join(stats), font=mid, fill=WHITE)

    if arr > dep > 0:
        progress = max(0, min(32, round(((now_ts - dep) / max(arr - dep, 1)) * 32)))
        draw.text((80, 840), ("█" * progress) + ("░" * (32 - progress)), font=mid, fill=YELLOW)

    draw.text((80, 980), "FLIGHT WALL", font=small, fill=MUTED)
    return _png_bytes(image)


def _png_bytes(image: Image.Image) -> bytes:
    from io import BytesIO

    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def write_board_png(path: Path, flight: dict[str, Any] | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_board_png(flight))
