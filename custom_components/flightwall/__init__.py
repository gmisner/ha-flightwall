"""Flight Wall integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import Event, HomeAssistant, ServiceCall

from .const import DOMAIN, SERVICE_RECAST
from .dashboard import (
    async_ensure_dashboard,
    async_write_theme,
    dashboard_path_for,
    flight_entity_for,
)
from .runtime import FlightwallRuntime
from .www_files import async_install_www
from .tv import RECAST_REASON

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Flight Wall from a config entry."""
    runtime = FlightwallRuntime(hass, entry)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = runtime
    entry.runtime_data = runtime

    await runtime.async_setup()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    try:
        await _async_setup_dashboard(hass, runtime)
    except Exception:
        _LOGGER.exception("Flight Wall dashboard setup failed; TV path still loads")
    if not hass.is_running:

        async def _started(_event: Event) -> None:
            await _async_setup_dashboard(hass, runtime)

        entry.async_on_unload(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _started)
        )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _async_register_services(hass)
    return True


async def _async_setup_dashboard(hass: HomeAssistant, runtime: FlightwallRuntime) -> None:
    await async_install_www(hass)
    await async_write_theme(hass)
    await async_ensure_dashboard(
        hass,
        runtime.ha_theme,
        path=dashboard_path_for(hass, runtime.entry),
        flight_entity=flight_entity_for(hass, runtime.entry),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    runtime: FlightwallRuntime | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if runtime is not None:
        await runtime.async_unload()
    if not hass.data.get(DOMAIN) and hass.services.has_service(DOMAIN, SERVICE_RECAST):
        hass.services.async_remove(DOMAIN, SERVICE_RECAST)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_RECAST):
        return

    async def _recast(_call: ServiceCall) -> None:
        for runtime in hass.data.get(DOMAIN, {}).values():
            if isinstance(runtime, FlightwallRuntime):
                await runtime.async_cast(reason=RECAST_REASON)

    hass.services.async_register(DOMAIN, SERVICE_RECAST, _recast)
