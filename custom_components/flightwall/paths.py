"""Locations for the board PNG. Keep it out of www/ (/local/)."""

from __future__ import annotations

from pathlib import Path

from .const import BOARD_PNG_NAME, DOMAIN


def private_board_png_path(config_dir: str | Path) -> Path:
    """Store the board where Home Assistant does not serve it anonymously."""
    return Path(config_dir) / DOMAIN / BOARD_PNG_NAME


def public_board_png_path(www_dir: str | Path) -> Path:
    """Legacy unauthenticated path from earlier releases."""
    return Path(www_dir) / BOARD_PNG_NAME


def camera_proxy_path(entity_id: str) -> str:
    """Authenticated camera still used by the dashboard and signed Cast URLs."""
    return f"/api/camera_proxy/{entity_id}"
