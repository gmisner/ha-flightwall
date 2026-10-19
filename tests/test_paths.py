from pathlib import Path

from flightwall.paths import (
    camera_proxy_path,
    private_board_png_path,
    public_board_png_path,
)


def test_board_png_is_kept_out_of_www() -> None:
    path = private_board_png_path("/config")
    assert path == Path("/config/flightwall/flightwall-board.png")
    assert "www" not in path.parts


def test_legacy_public_board_png_is_the_www_file() -> None:
    assert public_board_png_path("/config/www") == Path(
        "/config/www/flightwall-board.png"
    )


def test_cast_uses_authenticated_camera_proxy() -> None:
    assert camera_proxy_path("camera.flightwall_board") == (
        "/api/camera_proxy/camera.flightwall_board"
    )
    assert "/local/" not in camera_proxy_path("camera.flightwall_board")
