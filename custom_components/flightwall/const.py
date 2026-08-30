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
CONF_MIN_ALTITUDE = "min_altitude"
CONF_TIME_FORMAT = "time_format"
CONF_SHOW_LOGOS = "show_logos"
CONF_QUIET_ENABLED = "quiet_enabled"
CONF_QUIET_START = "quiet_start"
CONF_QUIET_END = "quiet_end"
CONF_ADSB_URL = "adsb_url"

ADSB_POLL = timedelta(seconds=10)

UNIT_IMPERIAL = "imperial"
UNIT_METRIC = "metric"
DEFAULT_UNITS = UNIT_IMPERIAL

STYLE_LED = "led"
STYLE_PLAIN = "plain"
STYLE_AMBER = "amber"
STYLE_SPLITFLAP = "splitflap"
STYLE_NIGHT = "night"
DEFAULT_BOARD_STYLE = STYLE_LED
DEFAULT_THEME = STYLE_LED

TIME_FOLLOW_UNITS = "follow_units"
TIME_12H = "12h"
TIME_24H = "24h"
DEFAULT_TIME_FORMAT = TIME_FOLLOW_UNITS
DEFAULT_MIN_ALTITUDE = 500
DEFAULT_SHOW_LOGOS = True
DEFAULT_QUIET_ENABLED = False
DEFAULT_QUIET_START = "22:00:00"
DEFAULT_QUIET_END = "07:00:00"

DISPLAY_IMAGE = "image"
DISPLAY_LIVE = "live"
DEFAULT_DISPLAY_MODE = DISPLAY_IMAGE

THEME_HA = {
    STYLE_LED: "flightwall",
    STYLE_PLAIN: "flightwall-plain",
    STYLE_AMBER: "flightwall-amber",
    STYLE_SPLITFLAP: "flightwall-splitflap",
    STYLE_NIGHT: "flightwall-night",
}

MIN_ALTITUDE_FT = 500
INBOUND_DELAY_OFF = timedelta(minutes=2)
TV_POWER_ON_DELAY = timedelta(seconds=10)
TV_KEEPALIVE = timedelta(minutes=1)
TV_CAST_SOURCE = "Cast"
TV_CAST_SOURCES = frozenset({"cast", "chromecast", "google cast"})
TV_TAKEOVER_REASONS = frozenset({"tv_on", "armed"})
SERVICE_RECAST = "recast"
BOARD_PNG_NAME = "flightwall-board.png"

DASHBOARD_PATH = "flight-wall"
VIEW_PATH = "board"

DEFAULT_FLIGHTS_ENTITY = "sensor.flightradar24_flights_in_area"
