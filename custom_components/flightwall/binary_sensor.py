"""Inbound traffic binary sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .runtime import FlightwallRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: FlightwallRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FlightwallInboundSensor(runtime)])


class FlightwallInboundSensor(BinarySensorEntity):
    """On while any aircraft is in range, with a configurable off-delay."""

    _attr_name = "Flightwall Inbound"
    _attr_icon = "mdi:airplane-alert"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_should_poll = False

    def __init__(self, runtime: FlightwallRuntime) -> None:
        self._runtime = runtime
        self._attr_suggested_object_id = "flightwall_inbound"
        self._attr_unique_id = f"{runtime.entry.entry_id}_inbound"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.entry.title,
            manufacturer="Flight Wall",
        )
        self._unsub: Any = None

    async def async_added_to_hass(self) -> None:
        self._unsub = self._runtime.async_add_listener(self._handle_update)
        self._handle_update()

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_update(self) -> None:
        self._attr_is_on = self._runtime.inbound
        self.schedule_update_ha_state()
