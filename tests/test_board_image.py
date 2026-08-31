from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO

from PIL import Image

from flightwall.board_image import render_board_png
from flightwall.const import STYLE_LED, STYLE_SPLITFLAP, WAITING_CLOCK

from test_board_copy import FLIGHT


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
