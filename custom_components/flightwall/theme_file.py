"""Optional Lovelace theme. Never overwrite a file the user already has."""

from __future__ import annotations

from pathlib import Path

THEME_YAML = """flightwall:
  primary-color: "#7ea6ff"
  accent-color: "#35ff7a"
  primary-background-color: "#000000"
  secondary-background-color: "#000000"
  card-background-color: "#000000"
  primary-text-color: "#ffffff"
  secondary-text-color: "#9fb8e8"
  text-primary-color: "#ffffff"
  app-header-background-color: "#000000"
  app-header-text-color: "#ffffff"
  ha-card-background: "#000000"
  ha-card-border-width: 0px
  ha-card-border-radius: 0px
  ha-card-box-shadow: "none"
  lovelace-background: "#000000"

flightwall-plain:
  primary-color: "#7ea6ff"
  accent-color: "#35ff7a"
  primary-background-color: "#000000"
  secondary-background-color: "#000000"
  card-background-color: "#000000"
  primary-text-color: "#ffffff"
  secondary-text-color: "#9fb8e8"
  text-primary-color: "#ffffff"
  app-header-background-color: "#000000"
  app-header-text-color: "#ffffff"
  ha-card-background: "#000000"
  ha-card-border-width: 0px
  ha-card-border-radius: 0px
  ha-card-box-shadow: "none"
  lovelace-background: "#000000"

flightwall-amber:
  primary-color: "#ffb84a"
  accent-color: "#ff9f1a"
  primary-background-color: "#0a0804"
  secondary-background-color: "#0a0804"
  card-background-color: "#0a0804"
  primary-text-color: "#ffb84a"
  secondary-text-color: "#c9893a"
  text-primary-color: "#ffb84a"
  app-header-background-color: "#0a0804"
  app-header-text-color: "#ffb84a"
  ha-card-background: "#0a0804"
  ha-card-border-width: 0px
  ha-card-border-radius: 0px
  ha-card-box-shadow: "none"
  lovelace-background: "#0a0804"

flightwall-splitflap:
  primary-color: "#f4f3ef"
  accent-color: "#35ff7a"
  primary-background-color: "#08090b"
  secondary-background-color: "#08090b"
  card-background-color: "#08090b"
  primary-text-color: "#f4f3ef"
  secondary-text-color: "#8b9099"
  text-primary-color: "#f4f3ef"
  app-header-background-color: "#08090b"
  app-header-text-color: "#f4f3ef"
  ha-card-background: "#08090b"
  ha-card-border-width: 0px
  ha-card-border-radius: 0px
  ha-card-box-shadow: "none"
  lovelace-background: "#08090b"

flightwall-night:
  primary-color: "#8ca0be"
  accent-color: "#1e7850"
  primary-background-color: "#04060a"
  secondary-background-color: "#04060a"
  card-background-color: "#04060a"
  primary-text-color: "#8ca0be"
  secondary-text-color: "#465a78"
  text-primary-color: "#8ca0be"
  app-header-background-color: "#04060a"
  app-header-text-color: "#8ca0be"
  ha-card-background: "#04060a"
  ha-card-border-width: 0px
  ha-card-border-radius: 0px
  ha-card-box-shadow: "none"
  lovelace-background: "#04060a"
"""


def write_theme_if_missing(theme_path: Path) -> bool:
    """Write the bundled theme only when the destination does not exist."""
    if theme_path.is_file():
        return False
    theme_path.parent.mkdir(parents=True, exist_ok=True)
    theme_path.write_text(THEME_YAML, encoding="utf-8")
    return True
