from __future__ import annotations

from pathlib import Path

from flightwall.silhouettes import (
    rasterize_svg,
    shape_code,
    silhouette_file_name,
    silhouette_url,
)

FIXTURE = Path(__file__).parent / "fixtures" / "silhouettes" / "B738.svg"


def test_shape_aliases_and_url() -> None:
    assert shape_code("b738") == "B738"
    assert shape_code("A319") == "A320"
    assert silhouette_file_name("A319") == "A320.svg"
    assert silhouette_url("B738").endswith("B738.svg")
    assert silhouette_url("") == ""


def test_rasterize_fixture_svg() -> None:
    image = rasterize_svg(FIXTURE.read_bytes(), (159, 184, 232), 80)
    assert image is not None
    assert image.size == (80, 80)
    assert image.mode == "RGBA"
    assert image.getchannel("A").getextrema()[1] > 0
