from datetime import UTC, date, datetime

import pytest

from vowen.modules.rituals.schedule import local_slot, slot_days
from vowen.modules.rituals.schemas import Schedule


@pytest.mark.parametrize(
    ("zone", "day", "hour", "minute", "expected"),
    [
        ("Europe/Madrid", date(2026, 3, 29), 2, 30, datetime(2026, 3, 29, 1, 30, tzinfo=UTC)),
        ("Europe/Madrid", date(2026, 10, 25), 2, 30, datetime(2026, 10, 25, 0, 30, tzinfo=UTC)),
        (
            "Australia/Lord_Howe",
            date(2026, 10, 4),
            2,
            15,
            datetime(2026, 10, 3, 15, 45, tzinfo=UTC),
        ),
    ],
)
def test_dst_gap_shift_and_first_fold(zone, day, hour, minute, expected):
    assert local_slot(day, hour, minute, zone) == expected


def test_once_daily_and_weekdays():
    days = [date(2026, 10, 15), date(2026, 10, 16), date(2026, 10, 17)]
    base = dict(timezone="UTC", hour=9, minute=30, start_date=days[0], window_hours=24)
    assert list(slot_days(Schedule(kind="daily", **base), days[0], days[-1])) == days
    assert list(slot_days(Schedule(kind="once", **base), days[0], days[-1])) == days[:1]
    assert (
        list(slot_days(Schedule(kind="weekly", weekdays=[4], **base), days[0], days[-1]))
        == days[1:2]
    )
    with pytest.raises(ValueError):
        Schedule(kind="daily", **dict(base, timezone="invalid"))
    with pytest.raises(ValueError):
        Schedule(kind="weekly", **base)
