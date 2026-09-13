"""Airline mark URLs.

Kiwi is the default CDN, but it does not serve Southwest's mark. After a
trademark suit Kiwi replaced ``WN.png`` with its own logo, so that code
uses Google Flights instead.
"""

from __future__ import annotations

import hashlib

KIWI_LOGO_URL = "https://images.kiwi.com/airlines/128/{iata}.png"

# Heart mark. Kiwi's WN.png is the kiwi.com logo, not Southwest.
LOGO_URL_OVERRIDES = {
    "WN": "https://www.gstatic.com/flights/airline_logos/70px/WN.png",
}

# Kiwi brand mark served for WN (multiple CDN encodings), plus the generic aircraft.
UNUSABLE_LOGO_SHA256 = {
    "1fe23e6d0b1ae8e9a8b8102f7dde086e9e3dd4de6a82f5ee73fa4616fd820855",
    "1a04f072c8018a01eb8baa88d31524062c25c7a0b8e7d5d159be2c8ee557157b",
    "53545c0ed6a76040fb5afe0af343ff29feb7545fceae2caaa0680c711c95657b",
}


def normalize_iata(iata: str) -> str:
    return (iata or "").strip().upper()


def logo_url(iata: str) -> str:
    code = normalize_iata(iata)
    if not code:
        return ""
    return LOGO_URL_OVERRIDES.get(code, KIWI_LOGO_URL.format(iata=code))


def logo_cache_name(iata: str) -> str:
    """Keep Kiwi fallbacks from sticking around when an override exists."""
    code = normalize_iata(iata)
    if code in LOGO_URL_OVERRIDES:
        return f"{code}.override.png"
    return f"{code}.png"


def logo_bytes_unusable(data: bytes) -> bool:
    return hashlib.sha256(data).hexdigest() in UNUSABLE_LOGO_SHA256
