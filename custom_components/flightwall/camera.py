"""Still of the 4K board PNG so Lovelace can mirror the television."""

from __future__ import annotations

from typing import Any

from homeassistant.components.camera import Camera
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
    async_add_entities([FlightwallBoardCamera(runtime)])


class FlightwallBoardCamera(Camera):
    """Serves the current Flight Wall PNG."""

    _attr_name = "Flightwall Board"
    _attr_icon = "mdi:monitor-screenshot"
    _attr_content_type = "image/png"
    _attr_should_poll = False

    def __init__(self, runtime: FlightwallRuntime) -> None:
        super().__init__()
        self._runtime = runtime
        self._attr_suggested_object_id = "flightwall_board"
        self._attr_unique_id = f"{runtime.entry.entry_id}_board"
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
        self.schedule_update_ha_state()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        path = self._runtime.board_png_path
        if not path.is_file():
            try:
                await self._runtime._write_board_image()
            except OSError:
                return None
        try:
            return await self.hass.async_add_executor_job(path.read_bytes)
        except OSError:
            return None
