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
        seg["status"] in {"OFF", "SB", "ON"}
        and (seg["end"] - seg["start"]).total_seconds() >= 1800
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


def test_simulator_takes_ten_hour_rest_after_eleven_driving_hours():
    timeline = simulate_trip(
        legs=[make_leg(770, 14.0)],
        start_datetime=datetime(2026, 10, 1, 8, 0),
        current_cycle_used_hours=0,
    )

    driving_hours = sum(
        (segment["end"] - segment["start"]).total_seconds() / 3600
        for segment in timeline
        if segment["status"] == "D"
    )
    sleeper_rests = [
        segment
        for segment in timeline
        if segment["status"] == "SB"
        and (segment["end"] - segment["start"]).total_seconds() >= 10 * 3600
    ]

    assert driving_hours == pytest.approx(14.0)
    assert sleeper_rests


def test_validator_does_not_reset_eleven_hour_limit_after_thirty_minute_break():
    timeline = [
        {
            "status": "D",
            "start": datetime(2026, 10, 1, 8, 0),
            "end": datetime(2026, 10, 1, 16, 0),
            "miles": 440,
        },
        {
            "status": "OFF",
            "start": datetime(2026, 10, 1, 16, 0),
            "end": datetime(2026, 10, 1, 16, 30),
            "miles": 0,
            "note": "30-min break",
        },
        {
            "status": "D",
            "start": datetime(2026, 10, 1, 16, 30),
            "end": datetime(2026, 10, 1, 20, 0),
            "miles": 192.5,
        },
    ]

    assert validate_timeline(timeline) is False


def test_validator_rejects_driving_after_the_fourteen_hour_window():
    timeline = [
        {
            "status": "ON",
            "start": datetime(2026, 10, 1, 8, 0),
            "end": datetime(2026, 10, 1, 8, 15),
            "miles": 0,
        },
        {
            "status": "D",
            "start": datetime(2026, 10, 1, 8, 15),
            "end": datetime(2026, 10, 1, 16, 15),
            "miles": 440,
        },
        {
            "status": "OFF",
            "start": datetime(2026, 10, 1, 16, 15),
            "end": datetime(2026, 10, 1, 16, 45),
            "miles": 0,
        },
        {
            "status": "ON",
            "start": datetime(2026, 10, 1, 16, 45),
            "end": datetime(2026, 10, 1, 21, 45),
            "miles": 0,
        },
        {
            "status": "D",
            "start": datetime(2026, 10, 1, 21, 45),
            "end": datetime(2026, 10, 1, 22, 45),
            "miles": 55,
        },
    ]

    assert validate_timeline(timeline) is False


def test_validator_includes_prior_cycle_hours_in_the_seventy_hour_limit():
    timeline = [
        {
            "status": "D",
            "start": datetime(2026, 10, 1, 8, 0),
            "end": datetime(2026, 10, 1, 9, 0),
            "miles": 55,
        },
    ]

    assert validate_timeline(timeline, current_cycle_used_hours=69.5) is False


def test_simulator_restarts_when_the_cycle_runs_out_mid_trip():
    timeline = simulate_trip(
        legs=[make_leg(100, 100 / 55)],
        start_datetime=datetime(2026, 10, 1, 8, 0),
        current_cycle_used_hours=69.5,
    )

    assert any(
        segment["status"] == "OFF"
        and (segment["end"] - segment["start"]).total_seconds() >= 34 * 3600
        for segment in timeline
    )
    assert sum(
        segment["miles"] for segment in timeline if segment["status"] == "D"
    ) == pytest.approx(100)


def test_high_cycle_usage_restarts_and_finishes_longer_trip():
    timeline = simulate_trip(
        legs=[make_leg(500, 500 / 55)],
        start_datetime=datetime(2026, 10, 1, 8, 0),
        current_cycle_used_hours=65,
    )

    assert any(
        segment["status"] == "OFF"
        and segment["note"].startswith("34-hr")
        and (segment["end"] - segment["start"]).total_seconds() >= 34 * 3600
        for segment in timeline
    )
    assert sum(
        segment["miles"] for segment in timeline if segment["status"] == "D"
    ) == pytest.approx(500)
    assert validate_timeline(timeline, current_cycle_used_hours=65) is True


def test_validator_does_not_combine_rest_segments_across_driving():
    timeline = [
        {
            "status": "D",
            "start": datetime(2026, 10, 1, 8, 0),
            "end": datetime(2026, 10, 1, 9, 0),
            "miles": 55,
        },
        {
            "status": "OFF",
            "start": datetime(2026, 10, 1, 9, 0),
            "end": datetime(2026, 10, 1, 15, 0),
            "miles": 0,
        },
        {
            "status": "D",
            "start": datetime(2026, 10, 1, 15, 0),
            "end": datetime(2026, 10, 1, 16, 0),
            "miles": 55,
        },
        {
            "status": "OFF",
            "start": datetime(2026, 10, 1, 16, 0),
            "end": datetime(2026, 10, 1, 20, 0),
            "miles": 0,
        },
        {
            "status": "D",
            "start": datetime(2026, 10, 1, 20, 0),
            "end": datetime(2026, 10, 1, 23, 0),
            "miles": 165,
        },
    ]

    assert validate_timeline(timeline) is False


def test_validator_drops_prior_cycle_hours_after_eight_calendar_days():
    start = datetime(2026, 10, 1, 0, 0)
    timeline = []
    for day in range(7):
        day_start = start + timedelta(days=day)
        on_end = day_start + timedelta(minutes=15)
        next_day = day_start + timedelta(days=1)
        timeline.extend(
            [
                {"status": "ON", "start": day_start, "end": on_end, "miles": 0},
                {"status": "OFF", "start": on_end, "end": next_day, "miles": 0},
            ]
        )
    day_eight_start = start + timedelta(days=7, minutes=15)
    timeline.append(
        {
            "status": "ON",
            "start": start + timedelta(days=7),
            "end": day_eight_start,
            "miles": 0,
        }
    )
    timeline.append(
        {
            "status": "D",
            "start": day_eight_start,
            "end": day_eight_start + timedelta(hours=1),
            "miles": 55,
        }
    )

    assert validate_timeline(timeline, current_cycle_used_hours=69.5) is True


def test_validator_rejects_fuel_intervals_over_one_thousand_miles():
    timeline = [
        {
            "status": "D",
            "start": datetime(2026, 10, 1, 8, 0),
            "end": datetime(2026, 10, 1, 9, 0),
            "miles": 1001,
        },
    ]

    assert validate_timeline(timeline) is False


def test_long_trip_adds_sleeper_rests_and_regular_fuel_stops():
    timeline = simulate_trip(
        legs=[make_leg(2500, 2500 / 55)],
        start_datetime=datetime(2026, 10, 1, 8, 0),
        current_cycle_used_hours=0,
    )
    fuel_stops = [
        segment
        for segment in timeline
        if segment["status"] == "ON" and segment["note"].startswith("Fuel")
    ]
    sleeper_rests = [
        segment
        for segment in timeline
        if segment["status"] == "SB"
        and (segment["end"] - segment["start"]).total_seconds() >= 10 * 3600
    ]

    assert len(fuel_stops) >= 2
    assert len(sleeper_rests) >= 2
    assert sum(
        segment["miles"] for segment in timeline if segment["status"] == "D"
    ) == pytest.approx(2500)
    assert validate_timeline(timeline) is True
