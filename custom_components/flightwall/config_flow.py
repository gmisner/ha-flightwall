"""Config flow for Flight Wall."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    CONF_BOARD_STYLE,
    CONF_DISPLAY_MODE,
    CONF_FLIGHTS_ENTITY,
    CONF_THEME,
    CONF_TV_ENABLED,
    CONF_TV_PLAYER,
    CONF_TV_POWER,
    CONF_UNITS,
    DEFAULT_DISPLAY_MODE,
    DEFAULT_FLIGHTS_ENTITY,
    DEFAULT_THEME,
    DEFAULT_UNITS,
    DISPLAY_IMAGE,
    DISPLAY_LIVE,
    DOMAIN,
    STYLE_AMBER,
    STYLE_LED,
    STYLE_PLAIN,
    UNIT_IMPERIAL,
    UNIT_METRIC,
)


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
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
                                "label": "Image (Cast-safe, Vizio / old Chromecast)",
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
                        ],
                        "mode": "dropdown",
                    }
                }
            ),
        }
    )


class FlightwallConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up Flight Wall."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                return self.async_create_entry(title="Flight Wall", data=_store(user_input))

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> FlightwallOptionsFlow:
        return FlightwallOptionsFlow(config_entry)


class FlightwallOptionsFlow(OptionsFlow):
    """Change sensor and TV entities later."""

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
                    self._config_entry, data=_store(user_input)
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(dict(self._config_entry.data)),
            errors=errors,
        )


def _store(user_input: dict[str, Any]) -> dict[str, Any]:
    data = dict(user_input)
    theme = data.get(CONF_THEME) or data.get(CONF_BOARD_STYLE, DEFAULT_THEME)
    data[CONF_THEME] = theme
    data[CONF_BOARD_STYLE] = theme
    return data


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if user_input.get(CONF_TV_ENABLED) and not user_input.get(CONF_TV_PLAYER):
        errors[CONF_TV_PLAYER] = "tv_player_required"
    return errors
