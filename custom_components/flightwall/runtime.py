"""Shared runtime: flight ranking plus TV image Cast."""

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

from .adsb import flights_from_attributes
from .board_copy import build_board
from .board_image import write_board_png
from .const import (
    ADSB_POLL,
    BOARD_PNG_NAME,
    CONF_ADSB_URL,
    CONF_BOARD_STYLE,
    CONF_DISPLAY_MODE,
    CONF_FLIGHTS_ENTITY,
    CONF_MIN_ALTITUDE,
    CONF_QUIET_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_REFRESH_SECONDS,
    CONF_SHOW_LOGOS,
    CONF_THEME,
    CONF_TIME_FORMAT,
    CONF_TV_PLAYER,
    CONF_TV_POWER,
    CONF_UNITS,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_FLIGHTS_ENTITY,
    DEFAULT_MIN_ALTITUDE,
    DEFAULT_QUIET_ENABLED,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DEFAULT_SHOW_LOGOS,
    DEFAULT_THEME,
    DEFAULT_TIME_FORMAT,
    DEFAULT_UNITS,
    DISPLAY_LIVE,
    INBOUND_DELAY_OFF,
    THEME_HA,
    TV_CAST_SOURCE,
    TV_CAST_SOURCES,
    TV_POWER_ON_DELAY,
    VIEW_PATH,
    keepalive_interval,
)
from .dashboard import dashboard_path_for
from .flight import callsign_of, rank_flights
from .schedule import in_quiet_hours
from .tv import RECAST_REASON, TAKEOVER_REASONS, should_refresh_board, should_select_cast

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
        self._live_failed = False
        self.last_cast_reason: str | None = None
        self.last_cast_error: str | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._inbound_unsub: CALLBACK_TYPE | None = None
        self._cast_delay_unsub: CALLBACK_TYPE | None = None
        self._adsb_attributes: dict[str, Any] | None = None

    @property
    def flights_entity(self) -> str:
        return (self.entry.data.get(CONF_FLIGHTS_ENTITY) or "").strip() or (
            DEFAULT_FLIGHTS_ENTITY if not self.adsb_url else ""
        )

    @property
    def adsb_url(self) -> str:
        return (self.entry.data.get(CONF_ADSB_URL) or "").strip()

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
        return self.entry.data.get(CONF_THEME) or self.entry.data.get(
            CONF_BOARD_STYLE, DEFAULT_THEME
        )

    @property
    def display_mode(self) -> str:
        return self.entry.data.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE)

    @property
    def min_altitude_ft(self) -> float:
        try:
            return float(self.entry.data.get(CONF_MIN_ALTITUDE, DEFAULT_MIN_ALTITUDE))
        except (TypeError, ValueError):
            return float(DEFAULT_MIN_ALTITUDE)

    @property
    def time_format(self) -> str:
        return self.entry.data.get(CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT)

    @property
    def show_logos(self) -> bool:
        return bool(self.entry.data.get(CONF_SHOW_LOGOS, DEFAULT_SHOW_LOGOS))

    @property
    def refresh_seconds(self) -> int:
        return int(keepalive_interval(self.entry.data.get(CONF_REFRESH_SECONDS)).total_seconds())

    @property
    def quiet_enabled(self) -> bool:
        return bool(self.entry.data.get(CONF_QUIET_ENABLED, DEFAULT_QUIET_ENABLED))

    def _in_quiet_hours(self) -> bool:
        return in_quiet_hours(
            self._local_now(),
            enabled=self.quiet_enabled,
            start=self.entry.data.get(CONF_QUIET_START, DEFAULT_QUIET_START),
            end=self.entry.data.get(CONF_QUIET_END, DEFAULT_QUIET_END),
        )

    @property
    def ha_theme(self) -> str:
        return THEME_HA.get(self.board_style, THEME_HA[DEFAULT_THEME])

    @property
    def dashboard_path(self) -> str:
        return dashboard_path_for(self.hass, self.entry)

    @property
    def board(self) -> dict[str, Any]:
        return build_board(
            self.flight,
            now=self._local_now(),
            units=self.units,
            last_flight=self.last_flight if self.flight is None else None,
            last_seen=self.last_seen if self.flight is None else None,
            next_flight=self.next_flight,
            time_format=self.time_format,
            show_logos=self.show_logos,
        ).as_dict()

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
        if self.flights_entity:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, [self.flights_entity], self._source_changed
                )
            )
        if self.adsb_url:
            self._unsubs.append(
                async_track_time_interval(self.hass, self._poll_adsb, ADSB_POLL)
            )
            self.hass.add_job(self._poll_adsb(None))
        if self.tv_power:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, [self.tv_power], self._tv_power_changed
                )
            )
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._keepalive,
                keepalive_interval(self.entry.data.get(CONF_REFRESH_SECONDS)),
            )
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
        self._live_failed = False
        self.hass.add_job(self.async_cast(reason="tv_on", delay=True))

    @callback
    def _keepalive(self, _now: datetime) -> None:
        self._notify()
        self.hass.add_job(self.async_cast(reason="keep"))

    def _local_now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.hass.config.time_zone))
        except (KeyError, ValueError):
            return datetime.now().astimezone()

    async def _poll_adsb(self, _now: datetime | None) -> None:
        if not self.adsb_url:
            return
        try:
            from aiohttp import ClientTimeout
            from homeassistant.helpers.aiohttp_client import async_get_clientsession

            session = async_get_clientsession(self.hass)
            async with session.get(
                self.adsb_url, timeout=ClientTimeout(total=8)
            ) as response:
                data = await response.json(content_type=None)
        except Exception as err:  # noqa: BLE001 — poll must never raise
            _LOGGER.debug("ADS-B poll failed: %s", err)
            return
        if isinstance(data, dict):
            self._adsb_attributes = data
            previous = self.callsign
            self._refresh_flight()
            if self.callsign != previous:
                await self.async_cast(reason="flight")

    def _refresh_flight(self) -> None:
        attrs: dict[str, Any] | None = self._adsb_attributes
        if attrs is None and self.flights_entity:
            state = self.hass.states.get(self.flights_entity)
            if state is not None:
                attrs = dict(state.attributes)
        flights = flights_from_attributes(
            attrs,
            float(self.hass.config.latitude or 0),
            float(self.hass.config.longitude or 0),
        )

        ranked = rank_flights(flights, self.min_altitude_ft)
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
        if "default media receiver" in app:
            return True
        return self._player_showing_live()

    def _player_showing_live(self) -> bool:
        if not self.tv_player:
            return False
        player = self.hass.states.get(self.tv_player)
        if player is None:
            return False
        app = str(player.attributes.get("app_name") or "").lower()
        return "home assistant" in app or "lovelace" in app

    def _tv_showing_board(self) -> bool:
        """True when this set is already on Cast / our image."""
        if self._tv_source() in TV_CAST_SOURCES:
            return True
        return self._player_showing_board()

    def _should_refresh_board(self) -> bool:
        return should_refresh_board(
            source=self._tv_source(),
            showing_board=self._tv_showing_board(),
        )

    async def async_set_tv_enabled(self, enabled: bool) -> None:
        self.tv_enabled = enabled
        if enabled:
            await self.async_cast(reason="armed")

    def _board_path(self) -> Path:
        return Path(self.hass.config.path("www")) / BOARD_PNG_NAME

    def _board_url(self) -> str:
        base = get_url(self.hass, prefer_external=False, allow_internal=True)
        return f"{base.rstrip('/')}/local/{BOARD_PNG_NAME}?t={int(datetime.now().timestamp())}"

    async def _write_board_image(self) -> None:
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
            self.time_format,
            self.show_logos,
        )

    async def _select_cast_source(self, reason: str) -> None:
        if self.tv_power and should_select_cast(reason):
            await self.hass.services.async_call(
                "media_player",
                "select_source",
                {"entity_id": self.tv_power, "source": TV_CAST_SOURCE},
                blocking=False,
            )
            await asyncio.sleep(1.5)

    async def _play_board_image(self) -> None:
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

    async def _cast_live_view(self) -> None:
        await self.hass.services.async_call(
            "cast",
            "show_lovelace_view",
            {
                "entity_id": self.tv_player,
                "dashboard_path": self.dashboard_path,
                "view_path": VIEW_PATH,
            },
            blocking=False,
        )

    async def async_cast(self, reason: str, delay: bool = False) -> None:
        """Show the board on the Chromecast."""
        if not self.tv_player:
            return
        if reason != "recast" and not self.tv_enabled:
            return
        if reason != "armed" and not self._tv_is_on():
            return
        if reason != RECAST_REASON and self._in_quiet_hours():
            _LOGGER.debug("Skip Flight Wall cast (%s); quiet hours", reason)
            return
        if reason not in TAKEOVER_REASONS and not self._should_refresh_board():
            _LOGGER.debug("Skip Flight Wall cast (%s); TV is on another source", reason)
            return
        self.last_cast_reason = reason
        self.last_cast_error = None

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
            await self._write_board_image()
            await self._select_cast_source(reason)
            use_live = self.display_mode == DISPLAY_LIVE and not self._live_failed
            if use_live:
                if reason in {"keep", "flight"} and self._player_showing_live():
                    return
                await self._cast_live_view()
                if reason in TAKEOVER_REASONS:
                    await asyncio.sleep(8)
                    if not self._player_showing_live():
                        _LOGGER.warning(
                            "Live Home Assistant Cast did not connect on %s; "
                            "showing the board image instead",
                            self.tv_player,
                        )
                        self._live_failed = True
                        await self._play_board_image()
                return
            await self._play_board_image()
        except HomeAssistantError as err:
            self.last_cast_error = str(err)
            _LOGGER.warning("Cast to %s failed (%s): %s", self.tv_player, reason, err)
        except OSError as err:
            self.last_cast_error = str(err)
            _LOGGER.warning("Could not write Flight Wall image (%s): %s", reason, err)
