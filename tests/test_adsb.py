from __future__ import annotations

from flightwall.adsb import flights_from_attributes, from_adsb, haversine_km


def test_haversine_zero() -> None:
    assert haversine_km(33.94, -118.41, 33.94, -118.41) == 0


def test_from_adsb_maps_tar1090() -> None:
    flight = from_adsb(
        {
            "hex": "a12345",
            "flight": "AAL123  ",
            "lat": 34.0,
            "lon": -118.4,
            "alt_baro": 4000,
            "gs": 250,
            "track": 90,
            "r": "N12345",
            "t": "B738",
        },
        33.94,
        -118.41,
    )
    assert flight is not None
    assert flight["callsign"] == "AAL123"
    assert flight["altitude"] == 4000
    assert flight["ground_speed"] == 250
    assert flight["heading"] == 90
    assert flight["aircraft_code"] == "B738"
    assert flight["distance"] > 0


def test_from_adsb_skips_no_position() -> None:
    assert from_adsb({"flight": "X", "alt_baro": 1000}, 0, 0) is None


def test_flights_from_fr24_passthrough() -> None:
    flights = [{"callsign": "AAL1", "altitude": 8000, "distance": 3, "airline_iata": "AA"}]
    assert flights_from_attributes({"flights": flights}, 0, 0) == flights


def test_flights_from_aircraft_attribute() -> None:
    mapped = flights_from_attributes(
        {
            "aircraft": [
                {"hex": "abc", "lat": 34.0, "lon": -118.4, "alt_baro": "ground"},
                {"hex": "def", "flight": "SWA1", "lat": 34.05, "lon": -118.4, "alt_baro": 3000},
            ]
        },
        33.94,
        -118.41,
    )
    assert [item["callsign"] for item in mapped] == ["abc", "SWA1"]
    assert mapped[0]["altitude"] == 0
