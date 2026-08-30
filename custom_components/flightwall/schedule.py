"""Quiet-hours helper."""

from __future__ import annotations

from datetime import datetime, time


def parse_clock(value: str | None, fallback: str) -> time:
    raw = (value or fallback).strip()
    parts = raw.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError, IndexError):
        hour, minute = (22, 0) if fallback.startswith("22") else (7, 0)
    return time(hour % 24, minute % 60)


def in_quiet_hours(
    now: datetime,
    *,
    enabled: bool,
    start: str | None,
    end: str | None,
) -> bool:
    """True when the board should stay quiet.

    A window that wraps midnight (22:00–07:00) is the usual case. A window
    that does not wrap (01:00–05:00) is also supported. Equal start and end
    means no quiet period.
    """
    if not enabled:
        return False
    begin = parse_clock(start, "22:00:00")
    finish = parse_clock(end, "07:00:00")
    current = now.time().replace(second=0, microsecond=0)
    begin = begin.replace(second=0, microsecond=0)
    finish = finish.replace(second=0, microsecond=0)
    if begin == finish:
        return False
    if begin < finish:
        return begin <= current < finish
    return current >= begin or current < finish
