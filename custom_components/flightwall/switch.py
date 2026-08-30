"""Arm or disarm the television flight board."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_TV_ENABLED, DOMAIN
from .runtime import FlightwallRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: FlightwallRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FlightwallTvSwitch(runtime)])


class FlightwallTvSwitch(SwitchEntity, RestoreEntity):
    """On means turning the TV on shows the flight board."""

    _attr_name = "Flightwall TV"
    _attr_icon = "mdi:television"
    _attr_should_poll = False

    def __init__(self, runtime: FlightwallRuntime) -> None:
        self._runtime = runtime
        self._attr_suggested_object_id = "flightwall_tv"
        self._attr_unique_id = f"{runtime.entry.entry_id}_tv"
        self._attr_is_on = bool(runtime.entry.data.get(CONF_TV_ENABLED, False))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.entry.title,
            manufacturer="Flight Wall",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            self._attr_is_on = last.state == "on"
        await self._runtime.async_set_tv_enabled(bool(self._attr_is_on))

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._attr_is_on = True
        self.async_write_ha_state()
        await self._runtime.async_set_tv_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        self.async_write_ha_state()
        await self._runtime.async_set_tv_enabled(False)
