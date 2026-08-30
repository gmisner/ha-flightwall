"""Shared runtime: flight ranking plus guest-room TV image Cast."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.network import get_url

from .board_image import write_board_png
from .const import (
    BOARD_PNG_NAME,
    CONF_BOARD_STYLE,
    CONF_FLIGHTS_ENTITY,
    CONF_TV_PLAYER,
    CONF_TV_POWER,
    CONF_UNITS,
    DEFAULT_BOARD_STYLE,
    DEFAULT_FLIGHTS_ENTITY,
    DEFAULT_UNITS,
    INBOUND_DELAY_OFF,
    MIN_ALTITUDE_FT,
    TV_CAST_SOURCE,
    TV_CAST_SOURCES,
    TV_IDLE_SOURCES,
    TV_KEEPALIVE,
    TV_POWER_ON_DELAY,
    TV_TAKEOVER_REASONS,
)
from .flight import callsign_of, rank_flights

_LOGGER = logging.getLogger(__name__)

OFF_STATES = {"off", "unavailable", "unknown", None}


class FlightwallRuntime:
    """Holds selected-flight state and casts the board while the TV is on."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.callsign = "none"
        self.flight: dict[str, Any] | None = None
        self.next_flight: dict[str, Any] | None = None
        self.last_flight: dict[str, Any] | None = None
        self.last_seen: datetime | None = None
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

    @property
    def units(self) -> str:
        return self.entry.data.get(CONF_UNITS, DEFAULT_UNITS)

    @property
    def board_style(self) -> str:
        return self.entry.data.get(CONF_BOARD_STYLE, DEFAULT_BOARD_STYLE)

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
            self.hass.add_job(self.async_cast(reason="flight"))

    @callback
    def _tv_power_changed(self, event: Event) -> None:
        new = event.data.get("new_state")
        if new is None or new.state in OFF_STATES:
            return
        self.hass.add_job(self.async_cast(reason="tv_on", delay=True))

    @callback
    def _keepalive(self, _now: datetime) -> None:
        self.hass.add_job(self.async_cast(reason="keep"))

    def _local_now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.hass.config.time_zone))
        except (KeyError, ValueError):
            return datetime.now().astimezone()

    def _refresh_flight(self) -> None:
        state = self.hass.states.get(self.flights_entity)
        flights = []
        if state is not None:
            raw = state.attributes.get("flights") or []
            if isinstance(raw, list):
                flights = [f for f in raw if isinstance(f, dict)]

        ranked = rank_flights(flights, MIN_ALTITUDE_FT)
        selected = ranked[0] if ranked else None
        nxt = ranked[1] if len(ranked) > 1 else None
        if selected is not None:
            self.last_flight = dict(selected)
            self.last_seen = self._local_now()
        self.flight = selected
        self.next_flight = nxt
        self.callsign = callsign_of(selected)
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

    def _tv_source(self) -> str:
        if not self.tv_power:
            return ""
        state = self.hass.states.get(self.tv_power)
        if state is None:
            return ""
        return str(state.attributes.get("source") or "").strip().lower()

    def _player_showing_board(self) -> bool:
        if not self.tv_player:
            return False
        player = self.hass.states.get(self.tv_player)
        if player is None or player.state not in {"playing", "paused"}:
            return False
        content = str(player.attributes.get("media_content_id") or "")
        if BOARD_PNG_NAME in content:
            return True
        app = str(player.attributes.get("app_name") or "").lower()
        return "default media receiver" in app

    def _tv_showing_board(self) -> bool:
        """True when this set is already on Cast / our image."""
        if self._tv_source() in TV_CAST_SOURCES:
            return True
        return self._player_showing_board()

    def _tv_is_other_app(self) -> bool:
        """True when someone picked Netflix, HDMI, or another real app."""
        source = self._tv_source()
        if not source or source in TV_CAST_SOURCES or source in TV_IDLE_SOURCES:
            return False
        return True

    def _should_refresh_board(self) -> bool:
        if self._tv_showing_board():
            return True
        if self._tv_is_other_app():
            return False
        return self._tv_source() in TV_IDLE_SOURCES

    async def async_set_tv_enabled(self, enabled: bool) -> None:
        self.tv_enabled = enabled
        if enabled:
            await self.async_cast(reason="armed")

    def _board_path(self) -> Path:
        return Path(self.hass.config.path("www")) / BOARD_PNG_NAME

    def _board_url(self) -> str:
        base = get_url(self.hass, prefer_external=False, allow_internal=True)
        return f"{base.rstrip('/')}/local/{BOARD_PNG_NAME}?t={int(datetime.now().timestamp())}"

    async def async_cast(self, reason: str, delay: bool = False) -> None:
        """Show the board image on the guest-room Chromecast."""
        if not self.tv_enabled or not self.tv_player:
            return
        if reason != "armed" and not self._tv_is_on():
            return
        if reason not in TV_TAKEOVER_REASONS and not self._should_refresh_board():
            _LOGGER.debug("Skip Flight Wall cast (%s); TV is on another source", reason)
            return

        if delay:
            if self._cast_delay_unsub:
                self._cast_delay_unsub()

            def _go(_now: datetime) -> None:
                self._cast_delay_unsub = None
                self.hass.add_job(self.async_cast(reason="tv_on"))

            self._cast_delay_unsub = async_call_later(
                self.hass, TV_POWER_ON_DELAY.total_seconds(), _go
            )
            return

        try:
            await self.hass.async_add_executor_job(
                write_board_png,
                self._board_path(),
                self.flight,
                self.units,
                self._local_now(),
                self.board_style,
                self.last_flight if self.flight is None else None,
                self.last_seen if self.flight is None else None,
                self.next_flight,
            )
            if self.tv_power and (
                reason in TV_TAKEOVER_REASONS or self._tv_source() in TV_IDLE_SOURCES
            ):
                await self.hass.services.async_call(
                    "media_player",
                    "select_source",
                    {"entity_id": self.tv_power, "source": TV_CAST_SOURCE},
                    blocking=False,
                )
                await asyncio.sleep(1.5)
            await self.hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": self.tv_player,
                    "media_content_id": self._board_url(),
                    "media_content_type": "image/png",
                },
                blocking=False,
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Cast to %s failed (%s): %s", self.tv_player, reason, err)
        except OSError as err:
            _LOGGER.warning("Could not write Flight Wall image (%s): %s", reason, err)
