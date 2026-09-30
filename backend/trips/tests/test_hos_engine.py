from datetime import datetime, timedelta

import pytest
from trips.services.hos_engine import simulate_trip
from trips.services.validator import validate_timeline


def parse_iso(value):
    if value.endswith("24:00:00"):
        return datetime.fromisoformat(
            value.replace("24:00:00", "00:00:00")
        ) + timedelta(days=1)
    return datetime.fromisoformat(value)


def make_leg(distance_miles, duration_hours, start=(0.0, 0.0), end=(1.0, 1.0)):
    return {
        "distance_miles": distance_miles,
        "duration_hours": duration_hours,
        "geometry": [start, end],
    }


def test_short_trip_has_single_day_and_no_10_hour_rest():
    route = [
        make_leg(120, 2.0),
        make_leg(80, 1.5),
    ]

    timeline = simulate_trip(
        legs=route,
        start_datetime=datetime(2026, 10, 1, 8, 0),
        current_cycle_used_hours=0,
    )

    assert len(timeline) > 0
    assert validate_timeline(timeline) is True
    assert sum(seg["miles"] for seg in timeline if seg["status"] == "D") >= 180
    assert not any(seg["status"] == "SB" for seg in timeline)


def test_medium_trip_respects_drive_and_break_limits():
    route = [
        make_leg(350, 6.0),
        make_leg(250, 4.0),
    ]

    timeline = simulate_trip(
        legs=route,
        start_datetime=datetime(2026, 10, 1, 8, 0),
        current_cycle_used_hours=10,
    )

    assert validate_timeline(timeline) is True
    assert any(
        seg["status"] == "OFF" and (seg["end"] - seg["start"]).total_seconds() >= 1800
        for seg in timeline
    )
    assert any(seg["status"] == "D" for seg in timeline)


def test_cycle_70_starts_with_34_hour_restart():
    route = [make_leg(50, 1.0)]

    timeline = simulate_trip(
        legs=route,
        start_datetime=datetime(2026, 10, 1, 8, 0),
        current_cycle_used_hours=70,
    )

    assert timeline[0]["status"] == "OFF"
    assert validate_timeline(timeline) is True


def test_john_doe_fixture_totals_match():
    fixture = [
        {
            "status": "OFF",
            "start": "2026-10-01T00:00:00",
            "end": "2026-10-01T06:00:00",
            "miles": 0,
        },
        {
            "status": "ON",
            "start": "2026-10-01T06:00:00",
            "end": "2026-10-01T07:30:00",
            "miles": 0,
        },
        {
            "status": "D",
            "start": "2026-10-01T07:30:00",
            "end": "2026-10-01T09:00:00",
            "miles": 0,
        },
        {
            "status": "ON",
            "start": "2026-10-01T09:00:00",
            "end": "2026-10-01T09:30:00",
            "miles": 0,
        },
        {
            "status": "D",
            "start": "2026-10-01T09:30:00",
            "end": "2026-10-01T12:00:00",
            "miles": 0,
        },
        {
            "status": "OFF",
            "start": "2026-10-01T12:00:00",
            "end": "2026-10-01T13:00:00",
            "miles": 0,
        },
        {
            "status": "D",
            "start": "2026-10-01T13:00:00",
            "end": "2026-10-01T15:00:00",
            "miles": 0,
        },
        {
            "status": "ON",
            "start": "2026-10-01T15:00:00",
            "end": "2026-10-01T15:30:00",
            "miles": 0,
        },
        {
            "status": "D",
            "start": "2026-10-01T15:30:00",
            "end": "2026-10-01T16:00:00",
            "miles": 0,
        },
        {
            "status": "SB",
            "start": "2026-10-01T16:00:00",
            "end": "2026-10-01T17:45:00",
            "miles": 0,
        },
        {
            "status": "D",
            "start": "2026-10-01T17:45:00",
            "end": "2026-10-01T19:00:00",
            "miles": 0,
        },
        {
            "status": "ON",
            "start": "2026-10-01T19:00:00",
            "end": "2026-10-01T21:00:00",
            "miles": 0,
        },
        {
            "status": "OFF",
            "start": "2026-10-01T21:00:00",
            "end": "2026-10-01T24:00:00",
            "miles": 0,
        },
    ]

    assert validate_timeline(fixture) is True

    totals = {"OFF": 10.0, "SB": 1.75, "D": 7.75, "ON": 4.5}
    for status, expected in totals.items():
        total = sum(
            ((parse_iso(seg["end"]) - parse_iso(seg["start"])).total_seconds() / 3600)
            for seg in fixture
            if seg["status"] == status
        )
        assert total == pytest.approx(expected)


def test_validator_rejects_invalid_cycle_usage():
    invalid = [
        {
            "status": "D",
            "start": "2026-10-01T08:00:00",
            "end": "2026-10-01T18:00:00",
            "miles": 0,
        },
        {
            "status": "OFF",
            "start": "2026-10-01T18:00:00",
            "end": "2026-10-01T24:00:00",
            "miles": 0,
        },
    ]

    assert validate_timeline(invalid) is False
