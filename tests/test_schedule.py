from __future__ import annotations

from datetime import datetime

from flightwall.schedule import in_quiet_hours


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 8, 30, hour, minute)


def test_quiet_hours_disabled() -> None:
    assert not in_quiet_hours(
        _at(23), enabled=False, start="22:00:00", end="07:00:00"
    )


def test_quiet_hours_wrap_midnight() -> None:
    kwargs = {"enabled": True, "start": "22:00:00", "end": "07:00:00"}
    assert in_quiet_hours(_at(22), **kwargs)
    assert in_quiet_hours(_at(23, 30), **kwargs)
    assert in_quiet_hours(_at(3), **kwargs)
    assert not in_quiet_hours(_at(7), **kwargs)
    assert not in_quiet_hours(_at(12), **kwargs)
    assert not in_quiet_hours(_at(21, 59), **kwargs)


def test_quiet_hours_same_day_window() -> None:
    kwargs = {"enabled": True, "start": "01:00:00", "end": "05:00:00"}
    assert in_quiet_hours(_at(2), **kwargs)
    assert not in_quiet_hours(_at(0, 30), **kwargs)
    assert not in_quiet_hours(_at(5), **kwargs)
