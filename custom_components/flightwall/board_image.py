"""Render a Flight Wall PNG for Chromecast Default Media Receiver."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont

from .board_copy import build_board
from .const import STYLE_AMBER, STYLE_LED, STYLE_SPLITFLAP, UNIT_IMPERIAL

FONT_PATH = Path(__file__).parent / "fonts" / "Roboto-Bold.ttf"
CANVAS = (3840, 2160)
SCALE = 2
CELL = 3
LOGO_URL = "https://images.kiwi.com/airlines/128/{iata}.png"
LOGO_TARGET = 220

PALETTES = {
    STYLE_LED: {
        "bg": (0, 0, 0),
        "ink": (255, 255, 255),
        "muted": (159, 184, 232),
        "bar": (53, 255, 122),
        "bar_dim": (20, 70, 40),
        "logo_tile": (214, 214, 214),
        "mark": (28, 44, 82),
        "grid": True,
    },
    "plain": {
        "bg": (0, 0, 0),
        "ink": (255, 255, 255),
        "muted": (159, 184, 232),
        "bar": (53, 255, 122),
        "bar_dim": (20, 70, 40),
        "logo_tile": (214, 214, 214),
        "mark": (28, 44, 82),
        "grid": False,
    },
    STYLE_AMBER: {
        "bg": (10, 8, 4),
        "ink": (255, 184, 74),
        "muted": (201, 137, 58),
        "bar": (255, 159, 26),
        "bar_dim": (70, 40, 10),
        "logo_tile": (48, 36, 16),
        "mark": (255, 184, 74),
        "grid": False,
    },
}

_LOGO_CACHE: dict[str, Image.Image | None] = {}


def _s(value: int) -> int:
    return value * SCALE


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_PATH), _s(size))
    except OSError:
        return ImageFont.load_default()


def _palette(style: str) -> dict[str, Any]:
    return PALETTES.get(style, PALETTES[STYLE_LED])


def _load_logo(iata: str) -> Image.Image | None:
    if not iata:
        return None
    if iata in _LOGO_CACHE:
        return _LOGO_CACHE[iata]
    try:
        with urlopen(LOGO_URL.format(iata=iata), timeout=6) as response:
            logo = Image.open(BytesIO(response.read())).convert("RGBA")
    except OSError:
        _LOGO_CACHE[iata] = None
        return None
    _LOGO_CACHE[iata] = logo
    return logo


def _airline_logo(iata: str, style: str) -> Image.Image | None:
    logo = _load_logo(iata)
    if logo is None:
        return None
    size = (_s(LOGO_TARGET), _s(LOGO_TARGET))
    resample = Image.Resampling.NEAREST if style == STYLE_LED else Image.Resampling.LANCZOS
    return logo.resize(size, resample)


def _generic_mark(size: int, fill: tuple[int, int, int]) -> Image.Image:
    """Simple top-down aircraft so every flight has the same logo column."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    scale = size / 100

    def pts(*pairs: tuple[float, float]) -> list[tuple[float, float]]:
        return [(x * scale, y * scale) for x, y in pairs]

    draw.polygon(
        pts(
            (50, 10),
            (55, 30),
            (55, 44),
            (90, 58),
            (90, 66),
            (55, 60),
            (55, 78),
            (68, 90),
            (68, 95),
            (50, 88),
            (32, 95),
            (32, 90),
            (45, 78),
            (45, 60),
            (10, 66),
            (10, 58),
            (45, 44),
            (45, 30),
        ),
        fill=(*fill, 255),
    )
    return image


def _dot_matrix(image: Image.Image, cell: int = CELL) -> Image.Image:
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


def _png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


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
    colors = _palette(style)
    board = build_board(
        flight,
        now=now,
        units=units,
        last_flight=last_flight,
        last_seen=last_seen,
        next_flight=next_flight,
    )
    if style == STYLE_SPLITFLAP:
        return _png_bytes(_draw_splitflap(board))

    image = Image.new("RGB", CANVAS, colors["bg"])
    draw = ImageDraw.Draw(image)
    callsign_font = _font(40)
    route_font = _font(168)
    clock_font = _font(180)
    body_font = _font(48)
    stats_font = _font(42)

    if not board.has_flight:
        _draw_empty(draw, board, colors, clock_font, body_font, stats_font)
    else:
        _draw_flight(
            image,
            draw,
            board,
            colors,
            style,
            callsign_font,
            route_font,
            body_font,
            stats_font,
        )

    if colors["grid"]:
        image = _dot_matrix(image)
    return _png_bytes(image)


def _draw_empty(
    draw: ImageDraw.ImageDraw,
    board: Any,
    colors: dict[str, Any],
    clock_font: ImageFont.ImageFont,
    body_font: ImageFont.ImageFont,
    stats_font: ImageFont.ImageFont,
) -> None:
    left = _s(120)
    draw.text((left, _s(80)), board.date, font=stats_font, fill=colors["muted"])
    draw.text((left, _s(180)), board.clock, font=clock_font, fill=colors["ink"])
    draw.text((left, _s(460)), "WAITING FOR TRAFFIC", font=body_font, fill=colors["muted"])
    if board.last_line:
        draw.text((left, _s(600)), board.last_label, font=stats_font, fill=colors["muted"])
        draw.text((left, _s(680)), board.last_line, font=body_font, fill=colors["ink"])
        if board.last_ago:
            draw.text((left, _s(760)), board.last_ago, font=body_font, fill=colors["ink"])


def _draw_flight(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    board: Any,
    colors: dict[str, Any],
    style: str,
    callsign_font: ImageFont.ImageFont,
    route_font: ImageFont.ImageFont,
    body_font: ImageFont.ImageFont,
    stats_font: ImageFont.ImageFont,
) -> None:
    tile = colors["logo_tile"]
    size = _s(260)
    origin = (_s(80), _s(80))
    logo = _airline_logo(board.logo_iata, style)
    if logo is None:
        logo = _generic_mark(int(size * 0.72), colors["mark"])
    draw.rounded_rectangle(
        (origin[0], origin[1], origin[0] + size, origin[1] + size),
        radius=_s(8),
        fill=tile,
    )
    box = Image.new("RGBA", (size, size), (*tile, 255))
    lx = (size - logo.width) // 2
    ly = (size - logo.height) // 2
    box.paste(logo, (lx, ly), logo)
    image.paste(box.convert("RGB"), origin)
    left = origin[0] + size + _s(80)
    y = _s(80)
    draw.text((left, y), board.title, font=callsign_font, fill=colors["muted"])
    y = _s(150)
    draw.text((left, y), board.route, font=route_font, fill=colors["ink"])
    y = _s(360)
    if board.cities:
        draw.text((left, y), board.cities, font=stats_font, fill=colors["muted"])
        y = _s(420)
    if board.details:
        draw.text((left, y), board.details, font=body_font, fill=colors["muted"])
        y += _s(80)
    draw.text((left, y), board.departed, font=body_font, fill=colors["ink"])
    y += _s(72)
    draw.text((left, y), board.arriving, font=body_font, fill=colors["ink"])
    y += _s(72)
    if board.stats:
        draw.text((left, y), board.stats, font=stats_font, fill=colors["ink"])
        y += _s(90)
    gap = _s(8)
    size = _s(28)
    for i in range(32):
        x = left + i * (size + gap)
        color = colors["bar"] if i < board.progress else colors["bar_dim"]
        draw.rounded_rectangle((x, y, x + size, y + size), radius=_s(4), fill=color)
    if board.next_line:
        draw.text((_s(120), _s(980)), board.next_line, font=stats_font, fill=colors["muted"])


FLAP_COLS = 16
FLAP_BG = (8, 9, 11)
FLAP_FACE = (26, 28, 33)
FLAP_FACE_TOP = (34, 37, 43)
FLAP_INK = (244, 243, 239)
FLAP_LABEL = (139, 144, 153)
FLAP_SEAM = (0, 0, 0)
FLAP_LIT = (53, 255, 122)
FLAP_LIT_DIM = (20, 40, 28)


def _draw_splitflap(board: Any) -> Image.Image:
    """Static mechanical departure board. No logo — a flap board cannot show one."""
    image = Image.new("RGB", CANVAS, FLAP_BG)
    draw = ImageDraw.Draw(image)
    cell_h = _s(84)
    cell_w = _s(56)
    gap = _s(6)
    label_w = _s(220)
    rows = list(board.flap_rows)
    line_h = cell_h + gap
    board_h = line_h * (len(rows) + 1)
    board_w = label_w + _s(24) + FLAP_COLS * cell_w + (FLAP_COLS - 1) * gap
    left = (CANVAS[0] - board_w) // 2
    top = (CANVAS[1] - board_h) // 2
    label_font = _font(22)
    char_font = _font(36)

    def flap_cell(x: int, y: int, char: str, lit: bool = False) -> None:
        face = FLAP_LIT if lit else FLAP_FACE
        top_face = (70, 200, 110) if lit else FLAP_FACE_TOP
        draw.rounded_rectangle((x, y, x + cell_w, y + cell_h), radius=_s(4), fill=face)
        draw.rectangle((x, y, x + cell_w, y + cell_h // 2), fill=top_face)
        mid = y + cell_h // 2
        draw.line((x + 2, mid, x + cell_w - 2, mid), fill=FLAP_SEAM, width=2)
        if char and char != " ":
            bbox = draw.textbbox((0, 0), char, font=char_font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(
                (x + (cell_w - tw) // 2 - bbox[0], y + (cell_h - th) // 2 - bbox[1]),
                char,
                font=char_font,
                fill=FLAP_INK,
            )

    y = top
    for label, value in rows:
        name = label.upper()
        bbox = draw.textbbox((0, 0), name, font=label_font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (left + label_w - tw, y + (cell_h - _s(22)) // 2),
            name,
            font=label_font,
            fill=FLAP_LABEL,
        )
        text = (value or "").upper()[:FLAP_COLS].ljust(FLAP_COLS)
        x = left + label_w + _s(24)
        for char in text:
            flap_cell(x, y, char)
            x += cell_w + gap
        y += line_h

    draw.text(
        (left, y + (cell_h - _s(22)) // 2),
        "PROGRESS",
        font=label_font,
        fill=FLAP_LABEL,
    )
    filled = max(0, min(FLAP_COLS, round(board.progress * FLAP_COLS / 32)))
    x = left + label_w + _s(24)
    for i in range(FLAP_COLS):
        flap_cell(x, y, "", lit=i < filled)
        x += cell_w + gap
    return image


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
