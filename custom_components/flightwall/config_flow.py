"""Config flow for Flight Wall."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    CONF_ADSB_URL,
    CONF_BOARD_STYLE,
    CONF_DISPLAY_MODE,
    CONF_FLIGHTS_ENTITY,
    CONF_MIN_ALTITUDE,
    CONF_QUIET_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_SHOW_LOGOS,
    CONF_THEME,
    CONF_TIME_FORMAT,
    CONF_TV_ENABLED,
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
    DISPLAY_IMAGE,
    DISPLAY_LIVE,
    DOMAIN,
    STYLE_AMBER,
    STYLE_LED,
    STYLE_NIGHT,
    STYLE_PLAIN,
    STYLE_SPLITFLAP,
    TIME_12H,
    TIME_24H,
    TIME_FOLLOW_UNITS,
    UNIT_IMPERIAL,
    UNIT_METRIC,
)


def _setup_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_FLIGHTS_ENTITY,
                default=defaults.get(CONF_FLIGHTS_ENTITY, DEFAULT_FLIGHTS_ENTITY),
            ): selector({"entity": {"domain": "sensor"}}),
            vol.Required(
                CONF_TV_ENABLED,
                default=defaults.get(CONF_TV_ENABLED, True),
            ): bool,
            vol.Optional(
                CONF_TV_POWER,
                description={"suggested_value": defaults.get(CONF_TV_POWER, "")},
            ): selector({"entity": {"domain": "media_player"}}),
            vol.Optional(
                CONF_TV_PLAYER,
                description={"suggested_value": defaults.get(CONF_TV_PLAYER, "")},
            ): selector({"entity": {"domain": "media_player"}}),
        }
    )


def _options_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_FLIGHTS_ENTITY,
                description={
                    "suggested_value": defaults.get(
                        CONF_FLIGHTS_ENTITY, DEFAULT_FLIGHTS_ENTITY
                    )
                },
            ): selector({"entity": {"domain": "sensor"}}),
            vol.Optional(
                CONF_ADSB_URL,
                description={"suggested_value": defaults.get(CONF_ADSB_URL, "")},
            ): selector({"text": {"type": "url"}}),
            vol.Required(
                CONF_TV_ENABLED,
                default=defaults.get(CONF_TV_ENABLED, True),
            ): bool,
            vol.Optional(
                CONF_TV_POWER,
                description={"suggested_value": defaults.get(CONF_TV_POWER, "")},
            ): selector({"entity": {"domain": "media_player"}}),
            vol.Optional(
                CONF_TV_PLAYER,
                description={"suggested_value": defaults.get(CONF_TV_PLAYER, "")},
            ): selector({"entity": {"domain": "media_player"}}),
            vol.Required(
                CONF_UNITS,
                default=defaults.get(CONF_UNITS, DEFAULT_UNITS),
            ): selector(
                {
                    "select": {
                        "options": [
                            {
                                "value": UNIT_IMPERIAL,
                                "label": "Imperial (ft, kt, mi)",
                            },
                            {
                                "value": UNIT_METRIC,
                                "label": "Metric (m, km/h, km)",
                            },
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
            vol.Required(
                CONF_DISPLAY_MODE,
                default=defaults.get(CONF_DISPLAY_MODE, DEFAULT_DISPLAY_MODE),
            ): selector(
                {
                    "select": {
                        "options": [
                            {
                                "value": DISPLAY_IMAGE,
                                "label": "Image (Cast-safe, older Chromecast / smart TV)",
                            },
                            {
                                "value": DISPLAY_LIVE,
                                "label": "Live dashboard (browser / HA Cast)",
                            },
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
            vol.Required(
                CONF_THEME,
                default=defaults.get(CONF_THEME)
                or defaults.get(CONF_BOARD_STYLE, DEFAULT_THEME),
            ): selector(
                {
                    "select": {
                        "options": [
                            {
                                "value": STYLE_LED,
                                "label": "LED night",
                            },
                            {
                                "value": STYLE_PLAIN,
                                "label": "Plain large type",
                            },
                            {
                                "value": STYLE_AMBER,
                                "label": "Amber departures",
                            },
                            {
                                "value": STYLE_SPLITFLAP,
                                "label": "Split-flap",
                            },
                            {
                                "value": STYLE_NIGHT,
                                "label": "Night dim",
                            },
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
            vol.Required(
                CONF_MIN_ALTITUDE,
                default=defaults.get(CONF_MIN_ALTITUDE, DEFAULT_MIN_ALTITUDE),
            ): selector(
                {
                    "number": {
                        "min": 0,
                        "max": 50000,
                        "step": 100,
                        "unit_of_measurement": "ft",
                        "mode": "box",
                    }
                }
            ),
            vol.Required(
                CONF_TIME_FORMAT,
                default=defaults.get(CONF_TIME_FORMAT, DEFAULT_TIME_FORMAT),
            ): selector(
                {
                    "select": {
                        "options": [
                            {
                                "value": TIME_FOLLOW_UNITS,
                                "label": "Follow units (12h imperial, 24h metric)",
                            },
                            {"value": TIME_12H, "label": "12-hour"},
                            {"value": TIME_24H, "label": "24-hour"},
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
            vol.Required(
                CONF_SHOW_LOGOS,
                default=defaults.get(CONF_SHOW_LOGOS, DEFAULT_SHOW_LOGOS),
            ): bool,
            vol.Required(
                CONF_QUIET_ENABLED,
                default=defaults.get(CONF_QUIET_ENABLED, DEFAULT_QUIET_ENABLED),
            ): bool,
            vol.Optional(
                CONF_QUIET_START,
                default=defaults.get(CONF_QUIET_START, DEFAULT_QUIET_START),
            ): selector({"time": {}}),
            vol.Optional(
                CONF_QUIET_END,
                default=defaults.get(CONF_QUIET_END, DEFAULT_QUIET_END),
            ): selector({"time": {}}),
        }
    )


class FlightwallConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up Flight Wall."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input, require_flights=True)
            if not errors:
                unique = (
                    f"{user_input.get(CONF_FLIGHTS_ENTITY)}|"
                    f"{user_input.get(CONF_TV_PLAYER) or 'no-tv'}"
                )
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                count = len(self._async_current_entries())
                title = "Flight Wall" if count == 0 else f"Flight Wall ({count + 1})"
                return self.async_create_entry(title=title, data=_store(user_input))

        return self.async_show_form(
            step_id="user",
            data_schema=_setup_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> FlightwallOptionsFlow:
        return FlightwallOptionsFlow(config_entry)


class FlightwallOptionsFlow(OptionsFlow):
    """Change entities and display options later."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=_store(user_input, self._config_entry.data)
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(dict(self._config_entry.data)),
            errors=errors,
        )


def _store(
    user_input: dict[str, Any], existing: dict[str, Any] | None = None
) -> dict[str, Any]:
    data = {
        CONF_UNITS: DEFAULT_UNITS,
        CONF_DISPLAY_MODE: DEFAULT_DISPLAY_MODE,
        CONF_THEME: DEFAULT_THEME,
        CONF_BOARD_STYLE: DEFAULT_THEME,
        CONF_MIN_ALTITUDE: DEFAULT_MIN_ALTITUDE,
        CONF_TIME_FORMAT: DEFAULT_TIME_FORMAT,
        CONF_SHOW_LOGOS: DEFAULT_SHOW_LOGOS,
        CONF_QUIET_ENABLED: DEFAULT_QUIET_ENABLED,
        CONF_QUIET_START: DEFAULT_QUIET_START,
        CONF_QUIET_END: DEFAULT_QUIET_END,
        CONF_ADSB_URL: "",
    }
    if existing:
        data.update(existing)
    data.update(user_input)
    theme = data.get(CONF_THEME) or data.get(CONF_BOARD_STYLE, DEFAULT_THEME)
    data[CONF_THEME] = theme
    data[CONF_BOARD_STYLE] = theme
    return data


def _validate(
    user_input: dict[str, Any], require_flights: bool = False
) -> dict[str, str]:
    errors: dict[str, str] = {}
    if user_input.get(CONF_TV_ENABLED) and not user_input.get(CONF_TV_PLAYER):
        errors[CONF_TV_PLAYER] = "tv_player_required"
    if require_flights and not user_input.get(CONF_FLIGHTS_ENTITY):
        errors[CONF_FLIGHTS_ENTITY] = "source_required"
    elif not require_flights and not user_input.get(CONF_FLIGHTS_ENTITY) and not user_input.get(
        CONF_ADSB_URL
    ):
        errors[CONF_FLIGHTS_ENTITY] = "source_required"
    return errors
