from pathlib import Path

from flightwall.theme_file import write_theme_if_missing


def test_write_theme_if_missing_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "themes" / "flightwall.yaml"
    assert write_theme_if_missing(path) is True
    text = path.read_text(encoding="utf-8")
    assert text.startswith("flightwall:")
    assert "flightwall-night:" in text


def test_write_theme_if_missing_leaves_existing(tmp_path: Path) -> None:
    path = tmp_path / "themes" / "flightwall.yaml"
    path.parent.mkdir()
    path.write_text("user-owned theme\n", encoding="utf-8")
    assert write_theme_if_missing(path) is False
    assert path.read_text(encoding="utf-8") == "user-owned theme\n"
