"""Selected-aircraft sensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
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
    async_add_entities([FlightwallFlightSensor(runtime)])


class FlightwallFlightSensor(SensorEntity):
    """Callsign of the aircraft with the highest elevation angle."""

    _attr_name = "Flightwall Flight"
    _attr_icon = "mdi:airplane"
    _attr_should_poll = False

    def __init__(self, runtime: FlightwallRuntime) -> None:
        self._runtime = runtime
        self._attr_suggested_object_id = "flightwall_flight"
        self._attr_unique_id = f"{runtime.entry.entry_id}_flight"
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
        self._attr_native_value = self._runtime.callsign
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "flight": self._runtime.flight,
            "next_flight": self._runtime.next_flight,
            "last_flight": self._runtime.last_flight,
            "board": self._runtime.board,
            "units": self._runtime.units,
            "theme": self._runtime.board_style,
            "display_mode": self._runtime.display_mode,
        }
