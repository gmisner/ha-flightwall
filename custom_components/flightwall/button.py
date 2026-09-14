"""Skip or pin the aircraft currently on the board."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    async_add_entities(
        [
            FlightwallActionButton(
                runtime,
                key="skip",
                name="Flightwall Skip",
                icon="mdi:skip-next",
                press=runtime.async_skip,
            ),
            FlightwallActionButton(
                runtime,
                key="pin",
                name="Flightwall Pin",
                icon="mdi:pin",
                press=runtime.async_pin,
            ),
            FlightwallActionButton(
                runtime,
                key="unpin",
                name="Flightwall Unpin",
                icon="mdi:pin-off",
                press=runtime.async_unpin,
            ),
        ]
    )


class FlightwallActionButton(ButtonEntity):
    """One-shot board action."""

    _attr_should_poll = False

    def __init__(
        self,
        runtime: FlightwallRuntime,
        *,
        key: str,
        name: str,
        icon: str,
        press: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        self._runtime = runtime
        self._press = press
        self._attr_name = name
        self._attr_icon = icon
        self._attr_suggested_object_id = f"flightwall_{key}"
        self._attr_unique_id = f"{runtime.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name=runtime.entry.title,
            manufacturer="Flight Wall",
        )

    async def async_press(self) -> None:
        await self._press()
