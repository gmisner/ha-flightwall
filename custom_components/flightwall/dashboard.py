"""Create the Cast-safe Flightwall Lovelace dashboard."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DASHBOARD_PATH, DOMAIN, THEME_HA, VIEW_PATH

DEFAULT_FLIGHT_ENTITY = "sensor.flightwall_flight"

_LOGGER = logging.getLogger(__name__)

BOARD_MARKDOWN = """{% set b = state_attr('__FLIGHT_ENTITY__','board') or {} %}
{% if b.has_flight %}
{% if b.logo_iata %}![](https://images.kiwi.com/airlines/128/{{ b.logo_iata }}.png){% endif %}

## {{ b.title }}

# {{ b.route }}

### {{ b.cities }}

{{ b.details }}

{{ b.departed }}

{{ b.arriving }}

{{ b.stats }}

{{ '█' * (b.progress | int(0)) }}{{ '░' * (32 - (b.progress | int(0))) }}

{{ b.next_line }}
{% else %}
### WAITING FOR TRAFFIC

{{ b.date }} {{ b.clock }}
{% if b.title %}
{% if b.logo_iata %}![](https://images.kiwi.com/airlines/128/{{ b.logo_iata }}.png){% endif %}

## {{ b.title }}

# {{ b.route }}

### {{ b.cities }}

{{ b.details }}

{{ b.departed }}

{{ b.arriving }}

{{ b.stats }}

{{ '█' * (b.progress | int(0)) }}{{ '░' * (32 - (b.progress | int(0))) }}

{{ b.next_line }}
{% endif %}
{% endif %}
"""


def dashboard_path_for(hass: HomeAssistant, entry: Any) -> str:
    """First config entry keeps /flight-wall; later ones get a suffix."""
    entries = sorted(
        hass.config_entries.async_entries(DOMAIN),
        key=lambda item: item.entry_id,
    )
    if not entries or entries[0].entry_id == entry.entry_id:
        return DASHBOARD_PATH
    return f"{DASHBOARD_PATH}-{entry.entry_id[:8].lower()}"


def flight_entity_for(hass: HomeAssistant, entry: Any) -> str:
    from homeassistant.helpers import entity_registry as er

    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}_flight"
    )
    return entity_id or DEFAULT_FLIGHT_ENTITY


def _dashboard_config(theme: str, flight_entity: str) -> dict[str, Any]:
    return {
        "title": "Flightwall",
        "views": [
            {
                "title": "Board",
                "path": VIEW_PATH,
                "theme": theme,
                "type": "masonry",
                "cards": [
                    {
                        "type": "markdown",
                        "content": BOARD_MARKDOWN.replace(
                            "__FLIGHT_ENTITY__", flight_entity
                        ),
                    }
                ],
            }
        ],
    }


def _lovelace_data(hass: HomeAssistant) -> Any:
    """Return the current LovelaceData object, if Lovelace is up."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        if LOVELACE_DATA in hass.data:
            return hass.data[LOVELACE_DATA]
    except ImportError:
        pass
    return hass.data.get("lovelace")


def _register_sidebar(hass: HomeAssistant, path: str) -> None:
    """Put Flightwall in the sidebar."""
    from homeassistant.components import frontend

    exists = False
    if hasattr(frontend, "async_panel_exists"):
        exists = frontend.async_panel_exists(hass, path)

    kwargs: dict[str, Any] = {
        "frontend_url_path": path,
        "require_admin": False,
        "sidebar_title": "Flightwall",
        "sidebar_icon": "mdi:airplane",
        "config": {"mode": "storage"},
    }
    if exists:
        kwargs["update"] = True

    frontend.async_register_built_in_panel(hass, "lovelace", **kwargs)


async def async_ensure_dashboard(
    hass: HomeAssistant,
    theme: str | None = None,
    path: str | None = None,
    flight_entity: str | None = None,
) -> None:
    """Create or refresh a Flightwall storage dashboard."""
    path = path or DASHBOARD_PATH
    flight_entity = flight_entity or DEFAULT_FLIGHT_ENTITY
    ll = _lovelace_data(hass)
    dashboards = getattr(ll, "dashboards", None) if ll is not None else None
    if ll is None or dashboards is None:
        _LOGGER.warning(
            "Lovelace is not ready; add a Flightwall dashboard under "
            "Settings → Dashboards, or reload Flight Wall after a restart"
        )
        return

    if path not in dashboards:
        try:
            from homeassistant.components.lovelace.dashboard import (
                DashboardsCollection,
                LovelaceStorage,
            )

            collection = DashboardsCollection(hass)
            await collection.async_load()
            if not any(item.get("url_path") == path for item in collection.async_items()):
                await collection.async_create_item(
                    {
                        "url_path": path,
                        "title": "Flightwall" if path == DASHBOARD_PATH else path,
                        "icon": "mdi:airplane",
                        "show_in_sidebar": True,
                        "require_admin": False,
                    }
                )
            item = next(
                item
                for item in collection.async_items()
                if item.get("url_path") == path
            )
            dashboards[path] = LovelaceStorage(hass, item)
        except (HomeAssistantError, ValueError, StopIteration, ImportError) as err:
            _LOGGER.warning("Could not create the %s dashboard: %s", path, err)
            return

    try:
        _register_sidebar(hass, path)
    except (ValueError, TypeError) as err:
        _LOGGER.debug("Sidebar panel already registered: %s", err)

    dash = dashboards[path]
    save = getattr(dash, "async_save", None)
    if save is None:
        return
    try:
        await save(_dashboard_config(theme or THEME_HA["led"], flight_entity))
    except HomeAssistantError as err:
        _LOGGER.warning("Could not save the Flightwall dashboard: %s", err)
        return

    _LOGGER.info("Flightwall dashboard is at /%s/%s", path, VIEW_PATH)


async def async_write_theme(hass: HomeAssistant) -> None:
    """Drop the dark theme into config/themes if that folder is used."""
    theme_dir = hass.config.path("themes")
    theme_path = hass.config.path("themes", "flightwall.yaml")

    def _write() -> None:
        from pathlib import Path

        Path(theme_dir).mkdir(parents=True, exist_ok=True)
        Path(theme_path).write_text(
            """flightwall:
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
""",
            encoding="utf-8",
        )

    try:
        await hass.async_add_executor_job(_write)
    except OSError as err:
        _LOGGER.debug("Could not write theme file: %s", err)
        return

    if hass.services.has_service("frontend", "reload_themes"):
        try:
            await hass.services.async_call("frontend", "reload_themes", blocking=False)
        except HomeAssistantError:
            _LOGGER.debug("frontend.reload_themes failed for %s", DOMAIN)
