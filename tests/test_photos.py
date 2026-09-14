from __future__ import annotations

from flightwall.photos import photo_cache_name, photo_url


def test_photo_url_prefers_medium() -> None:
    flight = {
        "aircraft_photo_small": "https://example.com/s.jpg",
        "aircraft_photo_medium": "https://example.com/m.jpg",
        "aircraft_registration": "N12345",
    }
    assert photo_url(flight) == "https://example.com/m.jpg"
    assert photo_cache_name(flight) == "N12345.jpg"


def test_photo_url_empty_without_http() -> None:
    assert photo_url({"aircraft_photo_medium": "local.jpg"}) == ""
    assert photo_cache_name({"callsign": "AAL1"}) == "AAL1.jpg"
    assert photo_cache_name(None) == ""
