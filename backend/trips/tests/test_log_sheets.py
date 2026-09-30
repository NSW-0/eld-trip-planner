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
