from __future__ import annotations

import hashlib
from io import BytesIO

from PIL import Image

from flightwall import board_image
from flightwall.board_image import _load_logo
from flightwall.logos import (
    KIWI_LOGO_URL,
    logo_bytes_unusable,
    logo_cache_name,
    logo_url,
)


def _png_bytes(color: tuple[int, int, int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGBA", (8, 8), color).save(buf, format="PNG")
    return buf.getvalue()


def test_logo_url_overrides_southwest() -> None:
    assert logo_url("WN") == "https://www.gstatic.com/flights/airline_logos/70px/WN.png"
    assert logo_url(" wn ") == logo_url("WN")
    assert "kiwi.com" not in logo_url("WN")
    assert logo_url("AA") == KIWI_LOGO_URL.format(iata="AA")
    assert logo_url("") == ""
    assert logo_cache_name("WN") == "WN.override.png"
    assert logo_cache_name("AA") == "AA.png"


def test_known_kiwi_placeholders_are_unusable() -> None:
    assert not logo_bytes_unusable(b"southwest-heart")


def test_load_logo_refetches_cached_kiwi_placeholder(tmp_path, monkeypatch) -> None:
    board_image._LOGO_CACHE.clear()
    cached = _png_bytes((0, 199, 180, 255))
    (tmp_path / "WN.png").write_bytes(cached)
    (tmp_path / "WN.override.png").write_bytes(cached)
    monkeypatch.setattr(
        "flightwall.logos.UNUSABLE_LOGO_SHA256",
        {hashlib.sha256(cached).hexdigest()},
    )
    fetched = _png_bytes((204, 36, 45, 255))

    class _Response:
        def read(self) -> bytes:
            return fetched

        def __enter__(self) -> _Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(board_image, "urlopen", lambda *args, **kwargs: _Response())
    logo = _load_logo("WN", tmp_path)
    assert logo is not None
    assert logo.getpixel((0, 0))[:3] == (204, 36, 45)
    assert (tmp_path / "WN.override.png").read_bytes() == fetched
    assert (tmp_path / "WN.png").read_bytes() == cached
    board_image._LOGO_CACHE.clear()
