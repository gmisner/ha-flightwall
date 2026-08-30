"""Render a dot-matrix Flight Wall PNG for Chromecast Default Media Receiver."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = Path(__file__).parent / "fonts" / "Roboto-Bold.ttf"
CANVAS = (1920, 1080)
BG = (0, 0, 0)
WHITE = (255, 255, 255)
MUTED = (159, 184, 232)
GREEN = (53, 255, 122)
GREEN_DIM = (20, 70, 40)
LOGO_TILE = (214, 214, 214)
LOGO_URL = "https://images.kiwi.com/airlines/128/{iata}.png"


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


def _airline_logo(iata: str) -> Image.Image | None:
    code = _clean(iata).upper()
    if not code:
        return None
    try:
        with urlopen(LOGO_URL.format(iata=code), timeout=6) as response:
            logo = Image.open(BytesIO(response.read())).convert("RGBA")
    except OSError:
        return None
    # Pixelate to the LED tile, then scale back up.
    logo = logo.resize((32, 32), Image.Resampling.BILINEAR)
    return logo.resize((220, 220), Image.Resampling.NEAREST)


def _dot_matrix(image: Image.Image, cell: int = 4) -> Image.Image:
    """Scale through a coarse grid so the board reads as an LED panel."""
    small = image.resize(
        (image.width // cell, image.height // cell), Image.Resampling.BILINEAR
    )
    led = small.resize(image.size, Image.Resampling.NEAREST).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    for y in range(0, height, cell):
        draw.line((0, y, width, y), fill=(0, 0, 0, 110))
    for x in range(0, width, cell):
        draw.line((x, 0, x, height), fill=(0, 0, 0, 110))
    return Image.alpha_composite(led, overlay).convert("RGB")


def render_board_png(flight: dict[str, Any] | None, now: datetime | None = None) -> bytes:
    """Return PNG bytes for the current flight, or the empty-sky board."""
    now = now or datetime.now(UTC)
    image = Image.new("RGB", CANVAS, BG)
    draw = ImageDraw.Draw(image)
    callsign_font = _font(40)
    route_font = _font(168)
    body_font = _font(48)
    stats_font = _font(42)

    if not flight:
        draw.rectangle((120, 280, 520, 360), fill=WHITE)
        draw.text((120, 460), "WAITING FOR TRAFFIC", font=body_font, fill=MUTED)
        return _png_bytes(_dot_matrix(image))

    iata = _clean(flight.get("airline_iata"))
    logo = _airline_logo(iata)
    tile = (80, 280, 360, 560)
    draw.rounded_rectangle(tile, radius=8, fill=LOGO_TILE)
    if logo is not None:
        box = Image.new("RGBA", (280, 280), (*LOGO_TILE, 255))
        lx = (280 - logo.width) // 2
        ly = (280 - logo.height) // 2
        box.paste(logo, (lx, ly), logo)
        image.paste(box.convert("RGB"), (80, 280))

    left = 420 if logo is not None or iata else 120
    callsign = _clean(flight.get("callsign")) or _clean(
        flight.get("aircraft_registration"), "IN FLIGHT"
    )
    airline = _clean(flight.get("airline_short")) or _clean(flight.get("airline"))
    if len(airline) > 22:
        airline = airline[:21].rstrip()
    heading = f"{callsign} ({airline})" if airline else callsign
    origin = _clean(flight.get("airport_origin_code_iata"))
    dest = _clean(flight.get("airport_destination_code_iata"))
    route = f"{origin}-{dest}" if origin and dest else callsign
    model = _clean(flight.get("aircraft_model")) or _clean(flight.get("aircraft_code"))
    origin_city = _clean(flight.get("airport_origin_city"))
    dest_city = _clean(flight.get("airport_destination_city"))

    y = 80
    draw.text((left, y), heading.upper(), font=callsign_font, fill=MUTED)
    y = 150
    draw.text((left, y), route, font=route_font, fill=WHITE)
    y = 360
    if model:
        draw.text((left, y), model.upper(), font=body_font, fill=MUTED)
        y += 80

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
        y += 72
    else:
        draw.text((left, y), "IN FLIGHT", font=body_font, fill=WHITE)
        y += 72
    if arr > now_ts:
        city = f"{dest_city.upper()} " if dest_city else ""
        draw.text(
            (left, y),
            f"ARRIVING {city}IN {_ago(arr - now_ts)}",
            font=body_font,
            fill=WHITE,
        )
        y += 72
    else:
        draw.text((left, y), "EN ROUTE", font=body_font, fill=WHITE)
        y += 72

    stats = []
    if flight.get("altitude") is not None:
        stats.append(f"{int(flight['altitude']):,} FT".replace(",", "."))
    if flight.get("ground_speed") is not None:
        stats.append(f"{int(flight['ground_speed'])} KT")
    if flight.get("distance") is not None:
        stats.append(f"{float(flight['distance']):.1f} KM")
    if stats:
        draw.text((left, y), "  ·  ".join(stats), font=stats_font, fill=WHITE)
        y += 90

    if arr > dep > 0:
        progress = max(0, min(32, round(((now_ts - dep) / max(arr - dep, 1)) * 32)))
        gap = 8
        size = 28
        for i in range(32):
            x = left + i * (size + gap)
            color = GREEN if i < progress else GREEN_DIM
            draw.rounded_rectangle((x, y, x + size, y + size), radius=4, fill=color)

    return _png_bytes(_dot_matrix(image))


def _png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def write_board_png(path: Path, flight: dict[str, Any] | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_board_png(flight))
