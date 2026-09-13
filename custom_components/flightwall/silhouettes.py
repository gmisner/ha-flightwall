"""Top-down aircraft shapes for the type row.

Shapes are fetched from AircraftShapesSVG (GPL-3) on first use and cached
under ``/local/flightwall/silhouettes/``. They are not bundled, and they
never replace the airline mark.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw

SHAPE_BASE = (
    "https://raw.githubusercontent.com/RexKramer1/AircraftShapesSVG/"
    "main/Shapes%20SVG/{name}"
)

# ICAO codes with no exact SVG, mapped to the closest published shape.
SHAPE_ALIASES = {
    "A319": "A320",
    "B732": "B737",
    "B736": "B737",
    "B778": "B779",
    "C56X": "C750",
    "C68A": "C750",
    "CL30": "GLF6",
    "CL35": "GLF6",
    "CL60": "GLF6",
    "DH8A": "DH8C",
    "DH8B": "DH8C",
    "E175": "E170",
    "E190": "E195",
    "E290": "E195",
    "E295": "E195",
    "GLF4": "GLF6",
    "GLF5": "GLF6",
    "H25B": "LJ35",
    "LJ45": "LJ35",
    "LJ60": "LJ35",
    "PC24": "PC12",
}

_COMMANDS = set("MmLlHhVvCcSsQqTtAaZz")
_PATH_D = re.compile(r"""\bd\s*=\s*(['"])(.*?)\1""", re.DOTALL)


def normalize_type(code: str | None) -> str:
    return (code or "").strip().upper()


def shape_code(code: str | None) -> str:
    key = normalize_type(code)
    if not key:
        return ""
    return SHAPE_ALIASES.get(key, key)


def silhouette_file_name(code: str | None) -> str:
    key = shape_code(code)
    if not key:
        return ""
    return f"{key}.svg"


def silhouette_url(code: str | None) -> str:
    name = silhouette_file_name(code)
    if not name:
        return ""
    return SHAPE_BASE.format(name=quote(name))


def fetch_silhouette_svg(code: str | None, timeout: float = 6) -> bytes | None:
    url = silhouette_url(code)
    if not url:
        return None
    try:
        request = Request(url, headers={"User-Agent": "FlightWall/1.12"})
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
    except OSError:
        return None
    if not data or b"<svg" not in data[:800].lower() and b"<svg" not in data.lower():
        return None
    return data


def load_silhouette_svg(code: str | None, sil_dir: Path | None) -> bytes | None:
    """Read a cached SVG, or fetch and cache it when ``sil_dir`` is set."""
    name = silhouette_file_name(code)
    if not name:
        return None
    path = sil_dir / name if sil_dir is not None else None
    if path is not None and path.is_file():
        try:
            data = path.read_bytes()
        except OSError:
            data = b""
        if data:
            return data
    if sil_dir is None:
        return None
    data = fetch_silhouette_svg(code)
    if not data:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    except OSError:
        pass
    return data


def rasterize_svg(
    svg: bytes | str,
    fill: tuple[int, int, int],
    size: int,
) -> Image.Image | None:
    """Stroke SVG paths into a square RGBA image that fills ``size``."""
    text = svg.decode("utf-8", errors="ignore") if isinstance(svg, bytes) else svg
    polylines = _svg_polylines(text)
    if not polylines:
        return None
    xs = [x for line in polylines for x, _y in line]
    ys = [y for line in polylines for _x, y in line]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    height = max_y - min_y
    if width <= 0 and height <= 0:
        return None
    pad = max(width, height) * 0.06 or 1
    width = max(width, 1e-6) + 2 * pad
    height = max(height, 1e-6) + 2 * pad
    scale = (size - 2) / max(width, height)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    stroke = max(2, size // 42)
    color = (*fill, 255)
    ox = (size - width * scale) / 2
    oy = (size - height * scale) / 2

    def tx(x: float, y: float) -> tuple[int, int]:
        return (
            int(round((x - min_x + pad) * scale + ox)),
            int(round((y - min_y + pad) * scale + oy)),
        )

    for line in polylines:
        points = [tx(x, y) for x, y in line]
        if len(points) < 2:
            continue
        draw.line(points, fill=color, width=stroke, joint="curve")
    return image


def _svg_polylines(text: str) -> list[list[tuple[float, float]]]:
    paths = _path_data(text)
    out: list[list[tuple[float, float]]] = []
    for data in paths:
        out.extend(_flatten_path(data))
    return [line for line in out if len(line) >= 2]


def _path_data(text: str) -> list[str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return [match.group(2) for match in _PATH_D.finditer(text)]
    found: list[str] = []
    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag != "path":
            continue
        data = elem.attrib.get("d")
        if data:
            found.append(data)
    if found:
        return found
    return [match.group(2) for match in _PATH_D.finditer(text)]


def _flatten_path(data: str) -> list[list[tuple[float, float]]]:
    tokens = _tokenize_path(data)
    x = y = 0.0
    start = (0.0, 0.0)
    prev_ctrl: tuple[float, float] | None = None
    prev_cmd = ""
    current: list[tuple[float, float]] = []
    lines: list[list[tuple[float, float]]] = []

    def flush() -> None:
        nonlocal current
        if len(current) >= 2:
            lines.append(current)
        current = []

    def append(px: float, py: float) -> None:
        if current and current[-1] == (px, py):
            return
        current.append((px, py))

    i = 0
    n = len(tokens)
    while i < n:
        token = tokens[i]
        if token in _COMMANDS:
            cmd = token
            i += 1
        elif prev_cmd:
            cmd = prev_cmd
            if cmd in "Mm":
                cmd = "l" if cmd == "m" else "L"
        else:
            i += 1
            continue

        relative = cmd.islower()
        kind = cmd.upper()

        if kind == "Z":
            append(*start)
            x, y = start
            prev_ctrl = None
            prev_cmd = cmd
            continue

        if kind == "M":
            flush()
            x, y, i = _read_pair(tokens, i, x, y, relative)
            start = (x, y)
            append(x, y)
            prev_ctrl = None
            prev_cmd = cmd
            while i < n and tokens[i] not in _COMMANDS:
                x, y, i = _read_pair(tokens, i, x, y, relative)
                append(x, y)
            continue

        if kind == "L":
            while i < n and tokens[i] not in _COMMANDS:
                x, y, i = _read_pair(tokens, i, x, y, relative)
                append(x, y)
                prev_ctrl = None
            prev_cmd = cmd
            continue

        if kind == "H":
            while i < n and tokens[i] not in _COMMANDS:
                value, i = _read_num(tokens, i)
                x = x + value if relative else value
                append(x, y)
                prev_ctrl = None
            prev_cmd = cmd
            continue

        if kind == "V":
            while i < n and tokens[i] not in _COMMANDS:
                value, i = _read_num(tokens, i)
                y = y + value if relative else value
                append(x, y)
                prev_ctrl = None
            prev_cmd = cmd
            continue

        if kind == "C":
            while i < n and tokens[i] not in _COMMANDS:
                x1, y1, i = _read_pair(tokens, i, x, y, relative)
                x2, y2, i = _read_pair(tokens, i, x, y, relative)
                nx, ny, i = _read_pair(tokens, i, x, y, relative)
                current.extend(_cubic((x, y), (x1, y1), (x2, y2), (nx, ny))[1:])
                x, y = nx, ny
                prev_ctrl = (x2, y2)
            prev_cmd = cmd
            continue

        if kind == "S":
            while i < n and tokens[i] not in _COMMANDS:
                if prev_cmd.upper() in {"C", "S"} and prev_ctrl is not None:
                    x1, y1 = 2 * x - prev_ctrl[0], 2 * y - prev_ctrl[1]
                else:
                    x1, y1 = x, y
                x2, y2, i = _read_pair(tokens, i, x, y, relative)
                nx, ny, i = _read_pair(tokens, i, x, y, relative)
                current.extend(_cubic((x, y), (x1, y1), (x2, y2), (nx, ny))[1:])
                x, y = nx, ny
                prev_ctrl = (x2, y2)
            prev_cmd = cmd
            continue

        if kind == "Q":
            while i < n and tokens[i] not in _COMMANDS:
                x1, y1, i = _read_pair(tokens, i, x, y, relative)
                nx, ny, i = _read_pair(tokens, i, x, y, relative)
                current.extend(_quad((x, y), (x1, y1), (nx, ny))[1:])
                x, y = nx, ny
                prev_ctrl = (x1, y1)
            prev_cmd = cmd
            continue

        if kind == "T":
            while i < n and tokens[i] not in _COMMANDS:
                if prev_cmd.upper() in {"Q", "T"} and prev_ctrl is not None:
                    x1, y1 = 2 * x - prev_ctrl[0], 2 * y - prev_ctrl[1]
                else:
                    x1, y1 = x, y
                nx, ny, i = _read_pair(tokens, i, x, y, relative)
                current.extend(_quad((x, y), (x1, y1), (nx, ny))[1:])
                x, y = nx, ny
                prev_ctrl = (x1, y1)
            prev_cmd = cmd
            continue

        if kind == "A":
            while i < n and tokens[i] not in _COMMANDS:
                _rx, i = _read_num(tokens, i)
                _ry, i = _read_num(tokens, i)
                _rot, i = _read_num(tokens, i)
                _large, i = _read_num(tokens, i)
                _sweep, i = _read_num(tokens, i)
                x, y, i = _read_pair(tokens, i, x, y, relative)
                append(x, y)
                prev_ctrl = None
            prev_cmd = cmd
            continue

        prev_cmd = cmd

    flush()
    return lines


def _tokenize_path(data: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    n = len(data)
    while i < n:
        char = data[i]
        if char in ", \t\r\n":
            i += 1
            continue
        if char in _COMMANDS:
            tokens.append(char)
            i += 1
            continue
        if char in "+-" or char.isdigit() or char == ".":
            start = i
            if char in "+-":
                i += 1
            dotted = False
            exp = False
            if i < n and data[i] == ".":
                dotted = True
                i += 1
            while i < n:
                nxt = data[i]
                if nxt.isdigit():
                    i += 1
                    continue
                if nxt == "." and not dotted and not exp:
                    dotted = True
                    i += 1
                    continue
                if nxt in "eE" and not exp:
                    exp = True
                    i += 1
                    if i < n and data[i] in "+-":
                        i += 1
                    continue
                break
            tokens.append(data[start:i])
            continue
        i += 1
    return tokens


def _read_num(tokens: list[str], index: int) -> tuple[float, int]:
    if index >= len(tokens) or tokens[index] in _COMMANDS:
        return 0.0, index
    try:
        return float(tokens[index]), index + 1
    except ValueError:
        return 0.0, index + 1


def _read_pair(
    tokens: list[str],
    index: int,
    x: float,
    y: float,
    relative: bool,
) -> tuple[float, float, int]:
    dx, index = _read_num(tokens, index)
    dy, index = _read_num(tokens, index)
    if relative:
        return x + dx, y + dy, index
    return dx, dy, index


def _cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 12,
) -> list[tuple[float, float]]:
    points = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        points.append(
            (
                u**3 * p0[0]
                + 3 * u**2 * t * p1[0]
                + 3 * u * t**2 * p2[0]
                + t**3 * p3[0],
                u**3 * p0[1]
                + 3 * u**2 * t * p1[1]
                + 3 * u * t**2 * p2[1]
                + t**3 * p3[1],
            )
        )
    return points


def _quad(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    steps: int = 10,
) -> list[tuple[float, float]]:
    points = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        points.append(
            (
                u**2 * p0[0] + 2 * u * t * p1[0] + t**2 * p2[0],
                u**2 * p0[1] + 2 * u * t * p1[1] + t**2 * p2[1],
            )
        )
    return points

