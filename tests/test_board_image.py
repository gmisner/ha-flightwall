from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from PIL import Image

from flightwall.board_image import _LOGO_CACHE, _SIL_CACHE, render_board_png
from flightwall.const import STYLE_LED, STYLE_SPLITFLAP, WAITING_CLOCK

from test_board_copy import FLIGHT

SIL_DIR = Path(__file__).parent / "fixtures" / "silhouettes"


NOW = datetime.fromtimestamp(1_700_005_000, UTC)
SEEN = datetime.fromtimestamp(1_700_004_970, UTC)


def test_render_waiting_board_with_last_flight() -> None:
    raw = render_board_png(
        None,
        now=NOW,
        last_flight=FLIGHT,
        last_seen=SEEN,
        style=STYLE_LED,
    )
    image = Image.open(BytesIO(raw))
    assert image.size == (3840, 2160)
    assert image.mode == "RGB"


def test_render_waiting_splitflap_with_last_flight() -> None:
    raw = render_board_png(
        None,
        now=NOW,
        last_flight=FLIGHT,
        last_seen=SEEN,
        style=STYLE_SPLITFLAP,
    )
    image = Image.open(BytesIO(raw))
    assert image.size == (3840, 2160)


def test_render_waiting_clock_first() -> None:
    raw = render_board_png(
        None,
        now=NOW,
        last_flight=FLIGHT,
        last_seen=SEEN,
        style=STYLE_LED,
        waiting_layout=WAITING_CLOCK,
    )
    image = Image.open(BytesIO(raw))
    assert image.size == (3840, 2160)
    assert image.mode == "RGB"


def test_silhouette_sits_beside_type_not_in_logo_tile() -> None:
    _LOGO_CACHE.clear()
    _SIL_CACHE.clear()
    without = Image.open(
        BytesIO(render_board_png(FLIGHT, now=NOW, style=STYLE_LED, show_logos=False))
    )
    _SIL_CACHE.clear()
    with_sil = Image.open(
        BytesIO(
            render_board_png(
                FLIGHT,
                now=NOW,
                style=STYLE_LED,
                show_logos=False,
                sil_dir=SIL_DIR,
            )
        )
    )
    assert without.tobytes() != with_sil.tobytes()
    # Logo column (left of the type text) stays empty when marks are off.
    logo_tile = without.crop((160, 160, 680, 680))
    logo_with = with_sil.crop((160, 160, 680, 680))
    assert logo_tile.tobytes() == logo_with.tobytes()


def test_radar_does_not_replace_logo_tile() -> None:
    from flightwall.radar import destination

    home = (34.0, -118.4)
    lat, lon = destination(home[0], home[1], 6.76, 45)
    flight = {**FLIGHT, "latitude": lat, "longitude": lon}
    without = Image.open(BytesIO(render_board_png(flight, now=NOW, style=STYLE_LED)))
    with_radar = Image.open(
        BytesIO(render_board_png(flight, now=NOW, style=STYLE_LED, home=home))
    )
    assert without.tobytes() != with_radar.tobytes()
    logo_tile = without.crop((160, 160, 680, 680))
    logo_with = with_radar.crop((160, 160, 680, 680))
    assert logo_tile.tobytes() == logo_with.tobytes()


def test_show_radar_off_skips_radar() -> None:
    from flightwall.radar import destination

    home = (34.0, -118.4)
    lat, lon = destination(home[0], home[1], 6.76, 45)
    flight = {**FLIGHT, "latitude": lat, "longitude": lon}
    without = Image.open(BytesIO(render_board_png(flight, now=NOW, style=STYLE_LED)))
    hidden = Image.open(
        BytesIO(
            render_board_png(
                flight,
                now=NOW,
                style=STYLE_LED,
                home=home,
                show_radar=False,
            )
        )
    )
    shown = Image.open(
        BytesIO(render_board_png(flight, now=NOW, style=STYLE_LED, home=home))
    )
    assert hidden.tobytes() == without.tobytes()
    assert shown.tobytes() != hidden.tobytes()


def test_show_silhouette_off_skips_shape() -> None:
    _SIL_CACHE.clear()
    without = Image.open(
        BytesIO(
            render_board_png(
                FLIGHT,
                now=NOW,
                style=STYLE_LED,
                show_logos=False,
                show_silhouette=False,
            )
        )
    )
    hidden = Image.open(
        BytesIO(
            render_board_png(
                FLIGHT,
                now=NOW,
                style=STYLE_LED,
                show_logos=False,
                sil_dir=SIL_DIR,
                show_silhouette=False,
            )
        )
    )
    shown = Image.open(
        BytesIO(
            render_board_png(
                FLIGHT,
                now=NOW,
                style=STYLE_LED,
                show_logos=False,
                sil_dir=SIL_DIR,
            )
        )
    )
    assert hidden.tobytes() == without.tobytes()
    assert shown.tobytes() != hidden.tobytes()


def test_waiting_today_and_live_nearby_change_pixels() -> None:
    empty = Image.open(BytesIO(render_board_png(None, now=NOW, style=STYLE_LED)))
    today = Image.open(
        BytesIO(
            render_board_png(
                None,
                now=NOW,
                style=STYLE_LED,
                overhead_today=[{"callsign": "AAL123", "route": "LAX-JFK"}],
            )
        )
    )
    assert today.tobytes() != empty.tobytes()
    live = Image.open(BytesIO(render_board_png(FLIGHT, now=NOW, style=STYLE_LED)))
    also = Image.open(
        BytesIO(
            render_board_png(
                FLIGHT,
                now=NOW,
                style=STYLE_LED,
                nearby_flights=[{**FLIGHT, "callsign": "UAL7", "distance": 8.0}],
            )
        )
    )
    assert also.tobytes() != live.tobytes()


def _last_changed_row(a: Image.Image, b: Image.Image) -> int:
    for y in range(a.height - 1, -1, -1):
        if a.crop((0, y, a.width, y + 1)).tobytes() != b.crop((0, y, a.width, y + 1)).tobytes():
            return y
    return -1


def test_nearby_and_today_stay_above_bottom_edge() -> None:
    live = Image.open(BytesIO(render_board_png(FLIGHT, now=NOW, style=STYLE_LED)))
    also = Image.open(
        BytesIO(
            render_board_png(
                FLIGHT,
                now=NOW,
                style=STYLE_LED,
                nearby_flights=[{**FLIGHT, "callsign": "UAL7", "distance": 8.0}],
            )
        )
    )
    last = _last_changed_row(live, also)
    assert last > 1600
    assert last < 2160 - 24

    waiting = Image.open(
        BytesIO(
            render_board_png(
                None,
                now=NOW,
                last_flight=FLIGHT,
                last_seen=SEEN,
                style=STYLE_LED,
            )
        )
    )
    today = Image.open(
        BytesIO(
            render_board_png(
                None,
                now=NOW,
                last_flight=FLIGHT,
                last_seen=SEEN,
                style=STYLE_LED,
                overhead_today=[{"callsign": "UAL7", "route": "SFO-EWR"}],
            )
        )
    )
    last = _last_changed_row(waiting, today)
    assert last > 1600
    assert last < 2160 - 24


def _first_changed_col(a: Image.Image, b: Image.Image, y: int) -> int:
    for x in range(a.width):
        if a.getpixel((x, y)) != b.getpixel((x, y)):
            return x
    return -1


def _last_changed_col(a: Image.Image, b: Image.Image, y: int) -> int:
    for x in range(a.width - 1, -1, -1):
        if a.getpixel((x, y)) != b.getpixel((x, y)):
            return x
    return -1


def test_nearby_footer_is_centered() -> None:
    live = Image.open(BytesIO(render_board_png(FLIGHT, now=NOW, style=STYLE_LED)))
    also = Image.open(
        BytesIO(
            render_board_png(
                FLIGHT,
                now=NOW,
                style=STYLE_LED,
                nearby_flights=[{**FLIGHT, "callsign": "UAL7", "distance": 8.0}],
            )
        )
    )
    y = _last_changed_row(live, also)
    left = _first_changed_col(live, also, y)
    right = _last_changed_col(live, also, y)
    assert left > 400
    assert abs((left + right) / 2 - 1920) < 240
