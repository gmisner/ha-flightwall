"""Constants for Flight Wall."""

from datetime import timedelta

DOMAIN = "flightwall"

CONF_FLIGHTS_ENTITY = "flights_entity"
CONF_TV_ENABLED = "tv_enabled"
CONF_TV_POWER = "tv_power"
CONF_TV_PLAYER = "tv_player"

MIN_ALTITUDE_FT = 500
INBOUND_DELAY_OFF = timedelta(minutes=2)
TV_POWER_ON_DELAY = timedelta(seconds=10)
TV_KEEPALIVE = timedelta(minutes=3)

DASHBOARD_PATH = "flight-wall"
VIEW_PATH = "board"

DEFAULT_FLIGHTS_ENTITY = "sensor.flightradar24_flights_in_area"
