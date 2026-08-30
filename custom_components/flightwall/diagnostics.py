"""Diagnostics for a Flight Wall config entry."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .runtime import FlightwallRuntime


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    runtime: FlightwallRuntime | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is None:
        return {"error": "runtime_not_loaded"}

    power = hass.states.get(runtime.tv_power) if runtime.tv_power else None
    player = hass.states.get(runtime.tv_player) if runtime.tv_player else None
    return {
        "flights_entity": runtime.flights_entity,
        "adsb_url": bool(runtime.adsb_url),
        "units": runtime.units,
        "theme": runtime.board_style,
        "display_mode": runtime.display_mode,
        "refresh_seconds": runtime.refresh_seconds,
        "tv_enabled": runtime.tv_enabled,
        "tv_power": runtime.tv_power,
        "tv_player": runtime.tv_player,
        "tv_on": runtime._tv_is_on(),
        "tv_source": runtime._tv_source(),
        "player_state": player.state if player else None,
        "player_app": (
            str(player.attributes.get("app_name") or "") if player else None
        ),
        "showing_board": runtime._tv_showing_board(),
        "callsign": runtime.callsign,
        "inbound": runtime.inbound,
        "live_failed": runtime._live_failed,
        "last_cast_reason": runtime.last_cast_reason,
        "last_cast_error": runtime.last_cast_error,
        "power_state": power.state if power else None,
    }
