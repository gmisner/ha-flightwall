"""Create the Cast-safe Flightwall Lovelace dashboard."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DASHBOARD_PATH, DOMAIN

_LOGGER = logging.getLogger(__name__)

BOARD_MARKDOWN = """{% set f = state_attr('sensor.flightwall_flight','flight') %}
{% if f %}
{% macro clean(v, fb) %}{% set s = v | string | trim %}{{ fb if s in ['', 'None', 'none', 'null', 'N/A'] else s }}{% endmacro %}
{% set org = clean(f.airport_origin_code_iata, '') | trim %}
{% set dst = clean(f.airport_destination_code_iata, '') | trim %}
{% set orgc = clean(f.airport_origin_city, '') | trim %}
{% set dstc = clean(f.airport_destination_city, '') | trim %}
{% set iata = clean(f.airline_iata, '') | trim %}
{% set airline = clean(f.airline_short, '') | trim %}
{% set airlinel = clean(f.airline, '') | trim %}
{% set model = clean(f.aircraft_model, '') | trim %}
{% set code = clean(f.aircraft_code, '') | trim %}
{% set cs = clean(f.callsign, '') | trim %}
{% set reg = clean(f.aircraft_registration, '') | trim %}
{% set dep = (f.time_real_departure | default(0) | int(0)) or (f.time_scheduled_departure | default(0) | int(0)) %}
{% set arr = (f.time_estimated_arrival | default(0) | int(0)) or (f.time_scheduled_arrival | default(0) | int(0)) %}
{% set nw = as_timestamp(now()) | int %}
{% set d = nw - dep %}
{% set a = arr - nw %}
{% set prog = ([[(((nw - dep) / ([arr - dep, 1] | max)) * 32) | round(0) | int, 0] | max, 32] | min) if (arr > dep and dep > 0) else 0 %}
{% set alraw = airline if airline else airlinel %}
{% set al = alraw | truncate(22, true, '') | trim %}
![](https://images.kiwi.com/airlines/128/{{ iata | upper if iata else 'non-existing' }}.png)

## {{ cs if cs else reg }}{% if al %} ({{ al }}){% endif %}

# {% if org and dst %}{{ org }}-{{ dst }}{% elif reg %}{{ reg }}{% else %}IN FLIGHT{% endif %}

### {{ model if model else code }}

{% if dep > 0 and d > 0 %}DEPARTED {% if orgc %}{{ orgc }} {% endif %}{% if d >= 3600 %}{{ d // 3600 }}H {{ (d % 3600) // 60 }}M{% else %}{{ d // 60 }}M{% endif %} AGO{% else %}IN FLIGHT{% endif %}

{% if a > 0 %}ARRIVING {% if dstc %}{{ dstc }} {% endif %}IN {% if a >= 3600 %}{{ a // 3600 }}H {{ (a % 3600) // 60 }}M{% else %}{{ a // 60 }}M{% endif %}{% else %}EN ROUTE{% endif %}

{% if f.altitude is defined %}{{ "{:,}".format(f.altitude | int) | replace(",", ".") }} FT{% if f.ground_speed is defined %} · {{ f.ground_speed | int }} KT{% endif %}{% if f.distance is defined %} · {{ f.distance | round(1) }} KM{% endif %}{% endif %}

{{ '█' * prog }}{{ '░' * (32 - prog) }}
{% else %}

# —

## WAITING FOR TRAFFIC
{% endif %}
"""

DASHBOARD_CONFIG: dict[str, Any] = {
    "title": "Flightwall",
    "views": [
        {
            "title": "Board",
            "path": "board",
            "theme": "flightwall",
            "type": "masonry",
            "cards": [{"type": "markdown", "content": BOARD_MARKDOWN}],
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


def _register_sidebar(hass: HomeAssistant) -> None:
    """Put Flightwall in the sidebar."""
    from homeassistant.components import frontend

    exists = False
    if hasattr(frontend, "async_panel_exists"):
        exists = frontend.async_panel_exists(hass, DASHBOARD_PATH)

    kwargs: dict[str, Any] = {
        "frontend_url_path": DASHBOARD_PATH,
        "require_admin": False,
        "sidebar_title": "Flightwall",
        "sidebar_icon": "mdi:airplane",
        "config": {"mode": "storage"},
    }
    if exists:
        kwargs["update"] = True

    frontend.async_register_built_in_panel(hass, "lovelace", **kwargs)


async def async_ensure_dashboard(hass: HomeAssistant) -> None:
    """Create or refresh the flight-wall storage dashboard."""
    ll = _lovelace_data(hass)
    dashboards = getattr(ll, "dashboards", None) if ll is not None else None
    if ll is None or dashboards is None:
        _LOGGER.warning(
            "Lovelace is not ready; add a Flightwall dashboard under "
            "Settings → Dashboards, or reload Flight Wall after a restart"
        )
        return

    if DASHBOARD_PATH not in dashboards:
        try:
            from homeassistant.components.lovelace.dashboard import (
                DashboardsCollection,
                LovelaceStorage,
            )

            collection = DashboardsCollection(hass)
            await collection.async_load()
            if not any(
                item.get("url_path") == DASHBOARD_PATH
                for item in collection.async_items()
            ):
                await collection.async_create_item(
                    {
                        "url_path": DASHBOARD_PATH,
                        "title": "Flightwall",
                        "icon": "mdi:airplane",
                        "show_in_sidebar": True,
                        "require_admin": False,
                    }
                )
            item = next(
                item
                for item in collection.async_items()
                if item.get("url_path") == DASHBOARD_PATH
            )
            dashboards[DASHBOARD_PATH] = LovelaceStorage(hass, item)
        except (HomeAssistantError, ValueError, StopIteration, ImportError) as err:
            _LOGGER.warning("Could not create the %s dashboard: %s", DASHBOARD_PATH, err)
            return

    try:
        _register_sidebar(hass)
    except (ValueError, TypeError) as err:
        _LOGGER.debug("Sidebar panel already registered: %s", err)

    dash = dashboards[DASHBOARD_PATH]
    save = getattr(dash, "async_save", None)
    if save is None:
        return
    try:
        await save(DASHBOARD_CONFIG)
    except HomeAssistantError as err:
        _LOGGER.warning("Could not save the Flightwall dashboard: %s", err)
        return

    _LOGGER.info("Flightwall dashboard is at /%s/%s", DASHBOARD_PATH, "board")


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
