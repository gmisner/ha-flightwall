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
CONF_REFRESH_SECONDS = "refresh_seconds"
CONF_INBOUND_DELAY = "inbound_delay"
CONF_WAITING_LAYOUT = "waiting_layout"

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
DEFAULT_REFRESH_SECONDS = 20
MIN_REFRESH_SECONDS = 5
MAX_REFRESH_SECONDS = 300
DEFAULT_INBOUND_DELAY = 120
MIN_INBOUND_DELAY = 15
MAX_INBOUND_DELAY = 600
WAITING_LAST = "last_flight"
WAITING_CLOCK = "clock"
DEFAULT_WAITING_LAYOUT = WAITING_LAST

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
INBOUND_DELAY_OFF = timedelta(seconds=DEFAULT_INBOUND_DELAY)
TV_POWER_ON_DELAY = timedelta(seconds=10)
TV_KEEPALIVE = timedelta(seconds=DEFAULT_REFRESH_SECONDS)


def keepalive_interval(seconds: object = None) -> timedelta:
    """Clamp the image refresh to a usable Cast interval."""
    return timedelta(seconds=_clamp_seconds(
        seconds, DEFAULT_REFRESH_SECONDS, MIN_REFRESH_SECONDS, MAX_REFRESH_SECONDS
    ))


def inbound_delay(seconds: object = None) -> timedelta:
    """Clamp the inbound off-delay."""
    return timedelta(seconds=_clamp_seconds(
        seconds, DEFAULT_INBOUND_DELAY, MIN_INBOUND_DELAY, MAX_INBOUND_DELAY
    ))


def _clamp_seconds(
    seconds: object,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float, str)):
        value = default
    else:
        try:
            value = int(round(float(seconds)))
        except (TypeError, ValueError):
            value = default
    return max(minimum, min(maximum, value))


TV_CAST_SOURCE = "Cast"
TV_CAST_SOURCES = frozenset({"cast", "chromecast", "google cast"})
TV_TAKEOVER_REASONS = frozenset({"tv_on", "armed"})
SERVICE_RECAST = "recast"
BOARD_PNG_NAME = "flightwall-board.png"

DASHBOARD_PATH = "flight-wall"
VIEW_PATH = "board"

DEFAULT_FLIGHTS_ENTITY = "sensor.flightradar24_flights_in_area"
