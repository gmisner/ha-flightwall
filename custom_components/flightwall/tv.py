"""Television source helpers.

Keepalive and flight updates only refresh while Cast is already showing the
board, or while the TV has not reported a source yet (set just woke). Any
named app — Netflix, HDMI, SmartCast Home, webOS Home — is left alone until
the set is turned off and on or Flight Wall is re-armed.
"""

from __future__ import annotations

from .const import TV_CAST_SOURCES, TV_TAKEOVER_REASONS

RECAST_REASON = "recast"
TAKEOVER_REASONS = frozenset({*TV_TAKEOVER_REASONS, RECAST_REASON})


def normalize_source(source: str | None) -> str:
    return str(source or "").strip().lower()


def is_cast_source(source: str | None) -> bool:
    return normalize_source(source) in TV_CAST_SOURCES


def should_refresh_board(*, source: str | None, showing_board: bool) -> bool:
    if showing_board or is_cast_source(source):
        return True
    return not normalize_source(source)


def should_select_cast(reason: str) -> bool:
    return reason in TAKEOVER_REASONS


def should_attempt_cast(
    *,
    reason: str,
    power_on: bool,
    player_state: str | None,
) -> bool:
    """False when keepalive would recast into a set that is already gone."""
    if reason == RECAST_REASON:
        return True
    if reason in TV_TAKEOVER_REASONS:
        return power_on or reason == "armed"
    if not power_on:
        return False
    state = str(player_state or "").strip().lower()
    return state not in {"", "off", "unavailable", "unknown"}
