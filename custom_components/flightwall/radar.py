"""North-up radar disc: house at the centre, aircraft on range rings."""

from __future__ import annotations

from math import asin, atan2, cos, degrees, radians, sin
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .adsb import haversine_km
from .const import UNIT_METRIC

KM_PER_MI = 1.609344
RINGS_MI = (2.5, 5.0, 10.0)
RINGS_KM = (4.0, 8.0, 16.0)


def flight_latlon(flight: dict[str, Any] | None) -> tuple[float, float] | None:
    if not flight:
        return None
    lat = flight.get("latitude", flight.get("lat"))
    lon = flight.get("longitude", flight.get("lon"))
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


def flight_heading(flight: dict[str, Any] | None) -> float | None:
    if not flight:
        return None
    raw = flight.get("heading")
    if raw is None:
        raw = flight.get("track")
    try:
        return float(raw) % 360
    except (TypeError, ValueError):
        return None


def flight_trail(flight: dict[str, Any] | None) -> list[tuple[float, float]]:
    if not flight:
        return []
    raw = flight.get("trail")
    if not isinstance(raw, list):
        return []
    points: list[tuple[float, float]] = []
    for item in raw:
        pair = None
        if isinstance(item, dict):
            pair = flight_latlon(item)
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            try:
                pair = (float(item[0]), float(item[1]))
            except (TypeError, ValueError):
                pair = None
        if pair is not None:
            points.append(pair)
    return points


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlon = radians(lon2 - lon1)
    phi1, phi2 = radians(lat1), radians(lat2)
    x = sin(dlon) * cos(phi2)
    y = cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(dlon)
    return (degrees(atan2(x, y)) + 360) % 360


def destination(lat: float, lon: float, km: float, bearing: float) -> tuple[float, float]:
    """Point ``km`` from ``(lat, lon)`` along ``bearing`` degrees."""
    ang = km / 6371.0
    brng = radians(bearing)
    phi1 = radians(lat)
    lam1 = radians(lon)
    sin_phi2 = sin(phi1) * cos(ang) + cos(phi1) * sin(ang) * cos(brng)
    phi2 = asin(max(-1.0, min(1.0, sin_phi2)))
    lam2 = lam1 + atan2(
        sin(brng) * sin(ang) * cos(phi1),
        cos(ang) - sin(phi1) * sin(phi2),
    )
    return degrees(phi2), (degrees(lam2) + 540) % 360 - 180


def _polar(cx: int, cy: int, radius: float, bearing: float) -> tuple[int, int]:
    rad = radians(bearing)
    return (
        int(round(cx + radius * sin(rad))),
        int(round(cy - radius * cos(rad))),
    )


def _plane(draw: ImageDraw.ImageDraw, x: int, y: int, heading: float, size: int, fill: tuple[int, int, int]) -> None:
    nose = _polar(x, y, size, heading)
    left = _polar(x, y, int(size * 0.7), heading - 140)
    tail = _polar(x, y, int(size * 0.45), heading + 180)
    right = _polar(x, y, int(size * 0.7), heading + 140)
    draw.polygon([nose, left, tail, right], fill=fill)


def _house(draw: ImageDraw.ImageDraw, x: int, y: int, size: int, fill: tuple[int, int, int]) -> None:
    body = size
    roof = int(size * 0.7)
    draw.rectangle((x - body // 2, y - body // 6, x + body // 2, y + body // 2), fill=fill)
    draw.polygon(
        (
            (x - body // 2 - 2, y - body // 6),
            (x, y - body // 6 - roof),
            (x + body // 2 + 2, y - body // 6),
        ),
        fill=fill,
    )


def draw_radar(
    size: int,
    home: tuple[float, float],
    flight: dict[str, Any],
    colors: dict[str, Any],
    units: str = "imperial",
    font: ImageFont.ImageFont | None = None,
) -> Image.Image | None:
    """Return a square RGBA radar, or None if the aircraft has no position."""
    plane = flight_latlon(flight)
    if plane is None:
        return None
    home_lat, home_lon = home
    ac_lat, ac_lon = plane
    distance_km = haversine_km(home_lat, home_lon, ac_lat, ac_lon)
    bearing = bearing_deg(home_lat, home_lon, ac_lat, ac_lon)
    heading = flight_heading(flight)
    metric = units == UNIT_METRIC
    rings = RINGS_KM if metric else tuple(r * KM_PER_MI for r in RINGS_MI)
    labels = [f"{r:g} KM" if metric else f"{r:g} MI" for r in (RINGS_KM if metric else RINGS_MI)]
    reach_km = max(rings[-1], distance_km * 1.15 if distance_km else rings[-1])

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    cx = cy = size // 2
    pad = max(8, size // 18)
    max_r = cx - pad
    ring_color = colors["muted"]
    ink = colors["ink"]
    accent = colors["bar"]
    dim = colors["bar_dim"]
    bg = colors["bg"]
    face = (*bg, 230)
    draw.ellipse((cx - max_r, cy - max_r, cx + max_r, cy + max_r), fill=face)

    label_bearings = (75, 90, 105)
    for km, label, angle in zip(rings, labels, label_bearings, strict=True):
        radius = max_r * (km / reach_km)
        if radius < 8 or radius > max_r:
            continue
        box = (cx - radius, cy - radius, cx + radius, cy + radius)
        draw.ellipse(box, outline=(*ring_color, 90), width=max(2, size // 220))
        if font is not None:
            tx, ty = _polar(cx, cy, radius, angle)
            box = draw.textbbox((0, 0), label, font=font)
            draw.text(
                (tx + 8, ty - (box[3] - box[1]) // 2),
                label,
                font=font,
                fill=(*ring_color, 170),
            )

    draw.ellipse(
        (cx - max_r, cy - max_r, cx + max_r, cy + max_r),
        outline=(*ring_color, 180),
        width=max(3, size // 160),
    )
    draw.line((cx, cy - max_r, cx, cy + max_r), fill=(*ring_color, 50), width=2)
    draw.line((cx - max_r, cy, cx + max_r, cy), fill=(*ring_color, 50), width=2)
    if font is not None:
        nb = draw.textbbox((0, 0), "N", font=font)
        draw.text((cx - (nb[2] - nb[0]) // 2, cy - max_r + 8), "N", font=font, fill=ink)

    trail = flight_trail(flight)
    if len(trail) >= 2:
        pts = [
            _polar(cx, cy, max_r * (haversine_km(home_lat, home_lon, lat, lon) / reach_km), bearing_deg(home_lat, home_lon, lat, lon))
            for lat, lon in trail
        ]
        draw.line(pts, fill=(*accent, 120), width=max(3, size // 180), joint="curve")

    plane_r = max_r * min(distance_km / reach_km, 0.98)
    px, py = _polar(cx, cy, plane_r, bearing)
    draw.line((cx, cy, px, py), fill=(*dim, 180), width=max(2, size // 200))
    _house(draw, cx, cy, max(10, size // 28), ink)
    _plane(draw, px, py, heading if heading is not None else bearing, max(16, size // 16), accent)
    return image
