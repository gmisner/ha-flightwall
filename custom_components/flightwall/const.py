"""Constants for Flight Wall."""

from datetime import timedelta

DOMAIN = "flightwall"

CONF_FLIGHTS_ENTITY = "flights_entity"
CONF_TV_ENABLED = "tv_enabled"
CONF_TV_POWER = "tv_power"
CONF_TV_PLAYER = "tv_player"
CONF_UNITS = "units"
CONF_BOARD_STYLE = "board_style"
CONF_THEME = "theme"
CONF_DISPLAY_MODE = "display_mode"

UNIT_IMPERIAL = "imperial"
UNIT_METRIC = "metric"
DEFAULT_UNITS = UNIT_IMPERIAL

STYLE_LED = "led"
STYLE_PLAIN = "plain"
STYLE_AMBER = "amber"
STYLE_SPLITFLAP = "splitflap"
DEFAULT_BOARD_STYLE = STYLE_LED
DEFAULT_THEME = STYLE_LED

DISPLAY_IMAGE = "image"
DISPLAY_LIVE = "live"
DEFAULT_DISPLAY_MODE = DISPLAY_IMAGE

THEME_HA = {
    STYLE_LED: "flightwall",
    STYLE_PLAIN: "flightwall-plain",
    STYLE_AMBER: "flightwall-amber",
    STYLE_SPLITFLAP: "flightwall-splitflap",
}

MIN_ALTITUDE_FT = 500
INBOUND_DELAY_OFF = timedelta(minutes=2)
TV_POWER_ON_DELAY = timedelta(seconds=10)
TV_KEEPALIVE = timedelta(minutes=1)
TV_CAST_SOURCE = "Cast"
TV_CAST_SOURCES = frozenset({"cast", "chromecast", "google cast"})
TV_IDLE_SOURCES = frozenset(
    {
        "smartcast home",
        "smartcast",
        "home",
        "watchfree+",
        "watchfree",
        "watchfree+ home",
    }
)
TV_TAKEOVER_REASONS = frozenset({"tv_on", "armed"})
BOARD_PNG_NAME = "flightwall-board.png"

DASHBOARD_PATH = "flight-wall"
VIEW_PATH = "board"

DEFAULT_FLIGHTS_ENTITY = "sensor.flightradar24_flights_in_area"
