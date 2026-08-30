"""Render README TV-theme previews without Home Assistant."""

from __future__ import annotations

import sys
import types
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "custom_components" / "flightwall"
pkg = types.ModuleType("flightwall")
pkg.__path__ = [str(PKG)]
pkg.__package__ = "flightwall"
sys.modules["flightwall"] = pkg

from flightwall.board_image import render_board_png  # noqa: E402
from flightwall.const import (  # noqa: E402
    STYLE_AMBER,
    STYLE_LED,
    STYLE_NIGHT,
    STYLE_PLAIN,
    STYLE_SPLITFLAP,
)

FLIGHT = {
    "callsign": "AAL123",
    "airline_short": "American",
    "airline_iata": "",
    "aircraft_model": "Boeing 737-800",
    "aircraft_registration": "N12345",
    "altitude": 8000,
    "ground_speed": 280,
    "distance": 4.2,
    "heading": 225,
    "airport_origin_code_iata": "LAX",
    "airport_destination_code_iata": "JFK",
    "airport_origin_city": "Los Angeles",
    "airport_destination_city": "New York",
    "time_real_departure": 1_700_000_000,
    "time_estimated_arrival": 1_700_010_000,
}

NOW = datetime.fromtimestamp(1_700_005_000, UTC)
OUT = ROOT / "docs" / "images"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for style, name in (
        (STYLE_LED, "tv-led.png"),
        (STYLE_PLAIN, "tv-plain.png"),
        (STYLE_AMBER, "tv-amber.png"),
        (STYLE_NIGHT, "tv-night.png"),
        (STYLE_SPLITFLAP, "tv-splitflap.png"),
    ):
        raw = render_board_png(FLIGHT, now=NOW, style=style, show_logos=True)
        image = Image.open(BytesIO(raw)).convert("RGB")
        image = image.resize((1280, 720), Image.Resampling.LANCZOS)
        dest = OUT / name
        image.save(dest, "PNG", optimize=True)
        print(dest, dest.stat().st_size)


if __name__ == "__main__":
    main()
