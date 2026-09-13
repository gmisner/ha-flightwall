from __future__ import annotations

from flightwall.const import UNIT_IMPERIAL
from flightwall.radar import bearing_deg, destination, draw_radar, flight_latlon

HOME = (34.0, -118.4)


def test_flight_latlon_reads_fr24_and_adsb_keys() -> None:
    assert flight_latlon({"latitude": 34.1, "longitude": -118.3}) == (34.1, -118.3)
    assert flight_latlon({"lat": 34.1, "lon": -118.3}) == (34.1, -118.3)
    assert flight_latlon({"callsign": "AAL1"}) is None


def test_destination_and_bearing_round_trip() -> None:
    lat, lon = destination(HOME[0], HOME[1], 6.76, 45)
    assert 40 < bearing_deg(HOME[0], HOME[1], lat, lon) < 50


def test_draw_radar_is_square_and_visible() -> None:
    plane = destination(HOME[0], HOME[1], 6.76, 45)
    image = draw_radar(
        400,
        HOME,
        {"latitude": plane[0], "longitude": plane[1], "heading": 225},
        {
            "bg": (0, 0, 0),
            "ink": (255, 255, 255),
            "muted": (159, 184, 232),
            "bar": (53, 255, 122),
            "bar_dim": (20, 70, 40),
        },
        units=UNIT_IMPERIAL,
    )
    assert image is not None
    assert image.size == (400, 400)
    assert image.getchannel("A").getextrema()[1] > 0
