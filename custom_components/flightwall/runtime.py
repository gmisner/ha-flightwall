"""Shared runtime: flight ranking plus guest-room TV Cast."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import (
    CONF_FLIGHTS_ENTITY,
    CONF_TV_PLAYER,
    CONF_TV_POWER,
    DASHBOARD_PATH,
    DEFAULT_FLIGHTS_ENTITY,
    INBOUND_DELAY_OFF,
    MIN_ALTITUDE_FT,
    TV_KEEPALIVE,
    TV_POWER_ON_DELAY,
    VIEW_PATH,
)
from .flight import callsign_of, pick_best_flight

_LOGGER = logging.getLogger(__name__)

OFF_STATES = {"off", "unavailable", "unknown", None}


class FlightwallRuntime:
    """Holds selected-flight state and casts the board while the TV is on."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.callsign = "none"
        self.flight: dict[str, Any] | None = None
        self.inbound = False
        self.tv_enabled = False
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._inbound_unsub: CALLBACK_TYPE | None = None
        self._cast_delay_unsub: CALLBACK_TYPE | None = None

    @property
    def flights_entity(self) -> str:
        return self.entry.data.get(CONF_FLIGHTS_ENTITY, DEFAULT_FLIGHTS_ENTITY)

    @property
    def tv_power(self) -> str:
        return (self.entry.data.get(CONF_TV_POWER) or "").strip()

    @property
    def tv_player(self) -> str:
        return (self.entry.data.get(CONF_TV_PLAYER) or "").strip()

    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)

        def _remove() -> None:
            if update in self._listeners:
                self._listeners.remove(update)

        return _remove

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def async_setup(self) -> None:
        self._refresh_flight()
        self._unsubs.append(
            async_track_state_change_event(
                self.hass, [self.flights_entity], self._source_changed
            )
        )
        if self.tv_power:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, [self.tv_power], self._tv_power_changed
                )
            )
        self._unsubs.append(
            async_track_time_interval(self.hass, self._keepalive, TV_KEEPALIVE)
        )

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._inbound_unsub:
            self._inbound_unsub()
            self._inbound_unsub = None
        if self._cast_delay_unsub:
            self._cast_delay_unsub()
            self._cast_delay_unsub = None

    @callback
    def _source_changed(self, _event: Event) -> None:
        previous = self.callsign
        self._refresh_flight()
        if self.callsign != previous:
            self.hass.async_create_task(self.async_cast(reason="flight"))

    @callback
    def _tv_power_changed(self, event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or new.state in OFF_STATES:
            return
        self.hass.async_create_task(self.async_cast(reason="tv_on", delay=True))

    @callback
    def _keepalive(self, _now: datetime) -> None:
        self.hass.async_create_task(self.async_cast(reason="keep"))

    def _refresh_flight(self) -> None:
        state = self.hass.states.get(self.flights_entity)
        flights = []
        if state is not None:
            raw = state.attributes.get("flights") or []
            if isinstance(raw, list):
                flights = [f for f in raw if isinstance(f, dict)]

        self.flight = pick_best_flight(flights, MIN_ALTITUDE_FT)
        self.callsign = callsign_of(self.flight)
        self._set_inbound(len(flights) > 0)
        self._notify()

    def _set_inbound(self, present: bool) -> None:
        if present:
            if self._inbound_unsub:
                self._inbound_unsub()
                self._inbound_unsub = None
            self.inbound = True
            return
        if not self.inbound or self._inbound_unsub is not None:
            return

        def _clear(_now: datetime) -> None:
            self._inbound_unsub = None
            self.inbound = False
            self._notify()

        self._inbound_unsub = async_call_later(
            self.hass, INBOUND_DELAY_OFF.total_seconds(), _clear
        )

    def _tv_is_on(self) -> bool:
        if not self.tv_power:
            return False
        state = self.hass.states.get(self.tv_power)
        return state is not None and state.state not in OFF_STATES

    async def async_set_tv_enabled(self, enabled: bool) -> None:
        self.tv_enabled = enabled
        if enabled:
            await self.async_cast(reason="armed")

    async def async_cast(self, reason: str, delay: bool = False) -> None:
        """Cast the board if the guest-room path is armed and the TV is on."""
        if not self.tv_enabled or not self.tv_player:
            return
        if reason != "armed" and not self._tv_is_on():
            return

        if delay:
            if self._cast_delay_unsub:
                self._cast_delay_unsub()

            def _go(_now: datetime) -> None:
                self._cast_delay_unsub = None
                self.hass.async_create_task(self.async_cast(reason="tv_on"))

            self._cast_delay_unsub = async_call_later(
                self.hass, TV_POWER_ON_DELAY.total_seconds(), _go
            )
            return

        try:
            await self.hass.services.async_call(
                "cast",
                "show_lovelace_view",
                {
                    "entity_id": self.tv_player,
                    "dashboard_path": DASHBOARD_PATH,
                    "view_path": VIEW_PATH,
                },
                blocking=False,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Cast to %s failed (%s): %s", self.tv_player, reason, err)
