"""Shared runtime: flight ranking plus TV image Cast."""

from __future__ import annotations

import asyncio
import logging
import time
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
from homeassistant.helpers.storage import Store

from .adsb import flights_from_attributes
from .board_copy import build_board
from .board_image import write_board_png
from .const import (
    ADSB_POLL,
    BOARD_PNG_NAME,
    CONF_ADSB_URL,
    CONF_AIRLINERS_ONLY,
    CONF_AUTO_NIGHT,
    CONF_BOARD_STYLE,
    CONF_DISPLAY_MODE,
    CONF_FLIGHTS_ENTITY,
    CONF_HIDE_HELICOPTERS,
    CONF_HIDE_MILITARY,
    CONF_INBOUND_DELAY,
    CONF_MIN_ALTITUDE,
    CONF_MIN_SPEED,
    CONF_QUIET_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_REFRESH_SECONDS,
    CONF_SHOW_LOGOS,
    CONF_SHOW_PHOTO,
    CONF_SHOW_RADAR,
    CONF_SHOW_SILHOUETTE,
    CONF_THEME,
    CONF_TIME_FORMAT,
    CONF_TV_PLAYER,
    CONF_TV_POWER,
    CONF_UNITS,
    CONF_WAITING_LAYOUT,
    DEFAULT_AIRLINERS_ONLY,
    DEFAULT_AUTO_NIGHT,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_FLIGHTS_ENTITY,
    DEFAULT_HIDE_HELICOPTERS,
    DEFAULT_HIDE_MILITARY,
    DEFAULT_MIN_ALTITUDE,
    DEFAULT_MIN_SPEED,
    DEFAULT_QUIET_ENABLED,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DEFAULT_SHOW_LOGOS,
    DEFAULT_SHOW_PHOTO,
    DEFAULT_SHOW_RADAR,
    DEFAULT_SHOW_SILHOUETTE,
    DEFAULT_THEME,
    DEFAULT_TIME_FORMAT,
    DEFAULT_UNITS,
    DEFAULT_WAITING_LAYOUT,
    DISPLAY_LIVE,
    DOMAIN,
    inbound_delay,
    SKIP_SECONDS,
    THEME_HA,
    TV_CAST_SOURCES,
    TV_POWER_ON_DELAY,
    VIEW_PATH,
    keepalive_interval,
)
from .dashboard import dashboard_path_for
from .filters import filter_flights
from .flight import callsign_of, pick_display, rank_flights
from .persist import dump_state, load_state, merge_overhead
from .radar import flight_latlon, update_trail
from .schedule import effective_theme, in_quiet_hours
from .tv import (
    RECAST_REASON,
    TAKEOVER_REASONS,
    cast_source_name,
    should_attempt_cast,
    should_refresh_board,
    should_select_cast,
)

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
        self.overhead_today: list[dict[str, Any]] = []
        self.nearby_flights: list[dict[str, Any]] = []
        self.inbound = False
        self.tv_enabled = False
        self._live_failed = False
        self.last_cast_reason: str | None = None
        self.last_cast_error: str | None = None
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[CALLBACK_TYPE] = []
        self._inbound_unsub: CALLBACK_TYPE | None = None
        self._cast_delay_unsub: CALLBACK_TYPE | None = None
        self._save_unsub: CALLBACK_TYPE | None = None
        self._adsb_attributes: dict[str, Any] | None = None
        self._store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self._trail: list[tuple[float, float]] = []
        self._skipped: dict[str, float] = {}
        self._pinned: str | None = None
        self._write_lock = asyncio.Lock()

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
    def configured_style(self) -> str:
        return self.entry.data.get(CONF_THEME) or self.entry.data.get(
            CONF_BOARD_STYLE, DEFAULT_THEME
        )

    @property
    def board_style(self) -> str:
        return effective_theme(
            self.configured_style,
            auto_night=self.auto_night,
            sun_below=self._sun_below(),
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
    def show_radar(self) -> bool:
        return bool(self.entry.data.get(CONF_SHOW_RADAR, DEFAULT_SHOW_RADAR))

    @property
    def show_silhouette(self) -> bool:
        return bool(self.entry.data.get(CONF_SHOW_SILHOUETTE, DEFAULT_SHOW_SILHOUETTE))

    @property
    def show_photo(self) -> bool:
        return bool(self.entry.data.get(CONF_SHOW_PHOTO, DEFAULT_SHOW_PHOTO))

    @property
    def auto_night(self) -> bool:
        return bool(self.entry.data.get(CONF_AUTO_NIGHT, DEFAULT_AUTO_NIGHT))

    @property
    def airliners_only(self) -> bool:
        return bool(self.entry.data.get(CONF_AIRLINERS_ONLY, DEFAULT_AIRLINERS_ONLY))

    @property
    def hide_helicopters(self) -> bool:
        return bool(self.entry.data.get(CONF_HIDE_HELICOPTERS, DEFAULT_HIDE_HELICOPTERS))

    @property
    def hide_military(self) -> bool:
        return bool(self.entry.data.get(CONF_HIDE_MILITARY, DEFAULT_HIDE_MILITARY))

    @property
    def min_speed_kt(self) -> float:
        try:
            return float(self.entry.data.get(CONF_MIN_SPEED, DEFAULT_MIN_SPEED))
        except (TypeError, ValueError):
            return float(DEFAULT_MIN_SPEED)

    @property
    def pinned(self) -> str | None:
        return self._pinned

    @property
    def refresh_seconds(self) -> int:
        return int(keepalive_interval(self.entry.data.get(CONF_REFRESH_SECONDS)).total_seconds())

    @property
    def inbound_delay_seconds(self) -> int:
        return int(inbound_delay(self.entry.data.get(CONF_INBOUND_DELAY)).total_seconds())

    @property
    def waiting_layout(self) -> str:
        return self.entry.data.get(CONF_WAITING_LAYOUT, DEFAULT_WAITING_LAYOUT)

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
            waiting_layout=self.waiting_layout,
            overhead_today=self.overhead_today,
            nearby_flights=self.nearby_flights,
        ).as_dict()

    def async_add_listener(self, update: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(update)

        def _remove() -> None:
            if update in self._listeners:
                self._listeners.remove(update)

        return _remove

    @callback
    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    async def _async_restore(self) -> None:
        data = await self._store.async_load()
        last_flight, last_seen, overhead = load_state(data if isinstance(data, dict) else None)
        if last_flight:
            self.last_flight = last_flight
            self.last_seen = last_seen
        self.overhead_today = overhead
        self._prune_overhead()

    async def _async_save(self) -> None:
        await self._store.async_save(
            dump_state(self.last_flight, self.last_seen, self.overhead_today)
        )

    @callback
    def _save_now(self, _now: datetime | None = None) -> None:
        self._save_unsub = None
        self.hass.async_create_task(self._async_save())

    def _schedule_save(self) -> None:
        if self._save_unsub is not None:
            return
        self._save_unsub = async_call_later(self.hass, 2, self._save_now)

    async def async_setup(self) -> None:
        await self._async_restore()
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
        self._unsubs.append(
            async_track_state_change_event(self.hass, ["sun.sun"], self._sun_changed)
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
        if self._save_unsub:
            self._save_unsub()
            self._save_unsub = None
        await self._async_save()

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

    @callback
    def _sun_changed(self, _event: Event) -> None:
        if self.auto_night:
            self.hass.add_job(self.async_cast(reason="keep"))

    def _sun_below(self) -> bool:
        state = self.hass.states.get("sun.sun")
        return state is not None and state.state == "below_horizon"

    def _local_now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.hass.config.time_zone))
        except (KeyError, ValueError):
            return datetime.now().astimezone()

    def _prune_overhead(self) -> None:
        day = self._local_now().date().isoformat()
        pruned = [item for item in self.overhead_today if item.get("day") == day]
        if pruned != self.overhead_today:
            self.overhead_today = pruned
            self._schedule_save()

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
        flights = filter_flights(
            flights_from_attributes(
                attrs,
                float(self.hass.config.latitude or 0),
                float(self.hass.config.longitude or 0),
            ),
            airliners_only=self.airliners_only,
            hide_helicopters=self.hide_helicopters,
            hide_military=self.hide_military,
            min_speed_kt=self.min_speed_kt,
        )

        self._prune_overhead()
        now_m = time.monotonic()
        self._skipped = {
            callsign: expires
            for callsign, expires in self._skipped.items()
            if expires > now_m
        }
        ranked = rank_flights(flights, self.min_altitude_ft)
        selected, nxt, nearby = pick_display(
            ranked,
            skipped=set(self._skipped),
            pinned=self._pinned,
        )
        new_cs = callsign_of(selected)
        if new_cs != self.callsign:
            self._trail = []
        if selected is not None:
            selected = dict(selected)
            pair = flight_latlon(selected)
            if pair is not None:
                self._trail = update_trail(self._trail, pair[0], pair[1])
            if self._trail:
                selected["trail"] = list(self._trail)
            self.last_flight = dict(selected)
            self.last_seen = self._local_now()
            self.overhead_today = merge_overhead(
                self.overhead_today, selected, self.last_seen
            )
            self._schedule_save()
        else:
            self._trail = []
        self.flight = selected
        self.next_flight = nxt
        self.nearby_flights = nearby
        self.callsign = new_cs
        self._set_inbound(len(flights) > 0)
        self._notify()
        self.hass.add_job(self._write_board_image())

    @callback
    def _inbound_off(self, _now: datetime) -> None:
        self._inbound_unsub = None
        self.inbound = False
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

        self._inbound_unsub = async_call_later(
            self.hass,
            inbound_delay(self.entry.data.get(CONF_INBOUND_DELAY)).total_seconds(),
            self._inbound_off,
        )

    def _tv_is_on(self) -> bool:
        if not self.tv_power:
            return False
        state = self.hass.states.get(self.tv_power)
        return state is not None and state.state not in OFF_STATES

    def _player_state(self) -> str:
        if not self.tv_player:
            return ""
        state = self.hass.states.get(self.tv_player)
        if state is None:
            return ""
        return str(state.state or "").strip().lower()

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

    def _home_latlon(self) -> tuple[float, float] | None:
        try:
            lat = float(self.hass.config.latitude)
            lon = float(self.hass.config.longitude)
        except (TypeError, ValueError):
            return None
        if lat == 0 and lon == 0:
            return None
        return lat, lon

    def _board_path(self) -> Path:
        return Path(self.hass.config.path("www")) / BOARD_PNG_NAME

    @property
    def board_png_path(self) -> Path:
        return self._board_path()

    def _board_url(self) -> str:
        base = get_url(self.hass, prefer_external=False, allow_internal=True)
        return f"{base.rstrip('/')}/local/{BOARD_PNG_NAME}?t={int(datetime.now().timestamp())}"

    async def _write_board_image(self) -> None:
        async with self._write_lock:
            await self.hass.async_add_executor_job(self._render_board_png)
        self._notify()

    def _render_board_png(self) -> None:
        www = Path(self.hass.config.path("www", "flightwall"))
        write_board_png(
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
            self.waiting_layout,
            www / "logos",
            www / "silhouettes",
            self._home_latlon(),
            self.show_radar,
            show_silhouette=self.show_silhouette,
            photo_dir=www / "photos",
            show_photo=self.show_photo,
            overhead_today=self.overhead_today,
            nearby_flights=self.nearby_flights,
        )

    async def async_skip(self) -> None:
        if self.callsign != "none":
            self._skipped[self.callsign] = time.monotonic() + SKIP_SECONDS
            if self._pinned == self.callsign:
                self._pinned = None
        self._refresh_flight()
        await self.async_cast(reason="flight")

    async def async_pin(self) -> None:
        if self.callsign != "none":
            self._pinned = self.callsign
        self._notify()

    async def async_unpin(self) -> None:
        if self._pinned is None:
            return
        self._pinned = None
        self._refresh_flight()
        await self.async_cast(reason="flight")

    async def _select_cast_source(self, reason: str) -> None:
        if not self.tv_power or not should_select_cast(reason):
            return
        state = self.hass.states.get(self.tv_power)
        if state is None:
            return
        source = cast_source_name(state.attributes.get("source_list"))
        if source is None:
            _LOGGER.debug(
                "Skip select_source; %s has no Cast input", self.tv_power
            )
            return
        await self.hass.services.async_call(
            "media_player",
            "select_source",
            {"entity_id": self.tv_power, "source": source},
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
        self.last_cast_reason = reason
        self.last_cast_error = None

        if delay:
            if self._cast_delay_unsub:
                self._cast_delay_unsub()

            @callback
            def _go(_now: datetime) -> None:
                self._cast_delay_unsub = None
                self.hass.add_job(self.async_cast(reason="tv_on"))

            self._cast_delay_unsub = async_call_later(
                self.hass, TV_POWER_ON_DELAY.total_seconds(), _go
            )
            return

        try:
            await self._write_board_image()
        except OSError as err:
            self.last_cast_error = str(err)
            _LOGGER.warning("Could not write Flight Wall image (%s): %s", reason, err)
            return

        if not self.tv_player:
            return
        if reason != "recast" and not self.tv_enabled:
            return
        if reason != "armed" and not self._tv_is_on():
            return
        if not should_attempt_cast(
            reason=reason,
            power_on=self._tv_is_on(),
            player_state=self._player_state(),
        ):
            _LOGGER.debug("Skip Flight Wall cast (%s); TV or Cast is off", reason)
            return
        if reason != RECAST_REASON and self._in_quiet_hours():
            _LOGGER.debug("Skip Flight Wall cast (%s); quiet hours", reason)
            return
        if reason not in TAKEOVER_REASONS and not self._should_refresh_board():
            _LOGGER.debug("Skip Flight Wall cast (%s); TV is on another source", reason)
            return

        try:
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
