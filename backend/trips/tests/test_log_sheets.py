from datetime import datetime

import pytest
from trips.services.log_sheets import build_log_sheets


def parse_iso(value):
    return datetime.fromisoformat(value)


def test_john_doe_fixture_builds_correct_row_totals():
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

    sheets = build_log_sheets(fixture)

    assert len(sheets) == 1
    row_totals = sheets[0]["row_totals"]
    assert row_totals["OFF"] == pytest.approx(10.0)
    assert row_totals["SB"] == pytest.approx(1.75)
    assert row_totals["D"] == pytest.approx(7.75)
    assert row_totals["ON"] == pytest.approx(4.5)
    assert sum(row_totals.values()) == pytest.approx(24.0)


def test_midnight_split_keeps_hours_balanced():
    timeline = [
        {
            "status": "OFF",
            "start": "2026-10-01T22:00:00",
            "end": "2026-10-02T00:00:00",
            "miles": 0,
        },
        {
            "status": "D",
            "start": "2026-10-02T00:00:00",
            "end": "2026-10-02T02:00:00",
            "miles": 0,
        },
    ]

    sheets = build_log_sheets(timeline)

    assert len(sheets) == 2
    assert sum(sheets[0]["row_totals"].values()) == pytest.approx(24.0)
    assert sum(sheets[1]["row_totals"].values()) == pytest.approx(24.0)
    assert sheets[0]["segments"][-1]["end_minute"] == pytest.approx(1440.0)
    assert sheets[1]["segments"][0]["start_minute"] == pytest.approx(0.0)


def test_long_rest_splits_into_a_sheet_for_every_calendar_day():
    timeline = [
        {
            "status": "OFF",
            "start": "2026-10-01T12:00:00",
            "end": "2026-10-03T22:00:00",
            "miles": 0,
            "note": "34-hr restart",
        }
    ]

    sheets = build_log_sheets(timeline)

    assert [sheet["date"] for sheet in sheets] == [
        "2026-10-01",
        "2026-10-02",
        "2026-10-03",
    ]
    assert all(sheet["total_hours"] == pytest.approx(24.0) for sheet in sheets)
    first_rest_piece = next(
        segment
        for segment in sheets[0]["segments"]
        if segment["note"] == "34-hr restart"
    )
    assert first_rest_piece["start_minute"] == pytest.approx(720.0)
    assert first_rest_piece["end_minute"] == pytest.approx(1440.0)
    assert sheets[1]["segments"][0]["start_minute"] == pytest.approx(0.0)
    assert sheets[2]["segments"][-1]["end_minute"] == pytest.approx(1440.0)


def test_midnight_split_preserves_miles_proportionally_in_grid_data():
    sheets = build_log_sheets(
        [
            {
                "status": "D",
                "start": "2026-10-01T23:00:00",
                "end": "2026-10-02T01:00:00",
                "miles": 100,
            }
        ]
    )

    assert [sheet["total_miles_driving_today"] for sheet in sheets] == [50, 50]
    assert sheets[0]["segments"][-1]["end_minute"] == pytest.approx(1440.0)
    assert sheets[1]["segments"][0]["end_minute"] == pytest.approx(60.0)


def test_recap_includes_prior_cycle_hours_before_a_later_restart():
    timeline = [
        {
            "status": "ON",
            "start": "2026-10-01T08:00:00",
            "end": "2026-10-01T10:00:00",
            "miles": 0,
        },
        {
            "status": "OFF",
            "start": "2026-10-01T10:00:00",
            "end": "2026-10-02T20:00:00",
            "miles": 0,
            "note": "34-hr restart",
        },
        {
            "status": "ON",
            "start": "2026-10-02T20:00:00",
            "end": "2026-10-02T21:00:00",
            "miles": 0,
        },
    ]

    sheets = build_log_sheets(timeline, current_cycle_used_hours=12)

    assert sheets[0]["recap"]["A"] == pytest.approx(14.0)
    assert sheets[1]["recap"]["A"] == pytest.approx(1.0)
