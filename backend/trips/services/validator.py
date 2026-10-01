from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

VALID_STATUSES = {"OFF", "SB", "D", "ON"}


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        value = value.strip()
        if value.endswith("24:00:00"):
            base = value.replace("24:00:00", "00:00:00")
            return datetime.fromisoformat(base) + timedelta(days=1)
        if value.endswith("24:00"):
            base = value.replace("24:00", "00:00")
            return datetime.fromisoformat(base) + timedelta(days=1)
        return datetime.fromisoformat(value)
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600.0


def _date_chunks(start: datetime, end: datetime):
    cursor = start
    while cursor < end:
        next_midnight = datetime.combine(
            cursor.date() + timedelta(days=1), time.min, tzinfo=cursor.tzinfo
        )
        chunk_end = min(end, next_midnight)
        yield cursor, chunk_end
        cursor = chunk_end


def validate_timeline(
    timeline: list[dict[str, Any]], current_cycle_used_hours: float = 0.0
) -> bool:
    """Independently validate HOS limits and continuity for a finished timeline."""
    if not isinstance(timeline, list) or not timeline:
        return False
    try:
        initial_cycle_hours = float(current_cycle_used_hours)
    except (TypeError, ValueError):
        return False
    if not 0.0 <= initial_cycle_hours <= 70.0:
        return False

    previous_end: datetime | None = None
    previous_status: str | None = None
    duty_start: datetime | None = None
    rest_start: datetime | None = None
    non_driving_start: datetime | None = None
    drive_since_reset = 0.0
    drive_since_break = 0.0
    fuel_miles = 0.0
    on_duty_by_day: dict[Any, float] = {}
    first_start: datetime | None = None

    for segment in timeline:
        status = segment.get("status")
        if status not in VALID_STATUSES:
            return False
        try:
            start = _as_datetime(segment["start"])
            end = _as_datetime(segment["end"])
            miles = float(segment.get("miles") or 0.0)
        except (KeyError, TypeError, ValueError):
            return False
        if end <= start or miles < 0:
            return False
        if previous_end is not None and start != previous_end:
            return False
        if first_start is None:
            first_start = start
            on_duty_by_day[first_start.date() - timedelta(days=1)] = initial_cycle_hours

        hours = _hours_between(start, end)
        if status == "D":
            rest_start = None
            if non_driving_start is not None:
                if _hours_between(non_driving_start, start) >= 0.5:
                    drive_since_break = 0.0
                non_driving_start = None
            if duty_start is None:
                duty_start = start
            if drive_since_reset + hours > 11.0 + 1e-9:
                return False
            if drive_since_break + hours > 8.0 + 1e-9:
                return False
            driving_end = start + timedelta(hours=hours)
            window_end = duty_start + timedelta(hours=14)
            if driving_end > window_end + timedelta(microseconds=1):
                return False
            for chunk_start, chunk_end in _date_chunks(start, end):
                day = chunk_start.date()
                window_start = day - timedelta(days=7)
                cycle_hours = sum(
                    value
                    for on_duty_day, value in on_duty_by_day.items()
                    if window_start <= on_duty_day <= day
                )
                chunk_hours = _hours_between(chunk_start, chunk_end)
                if cycle_hours + chunk_hours > 70.0 + 1e-9:
                    return False
                on_duty_by_day[day] = on_duty_by_day.get(day, 0.0) + chunk_hours
            drive_since_reset += hours
            drive_since_break += hours
            fuel_miles += miles
            if fuel_miles > 1000.0 + 1e-6:
                return False
        else:
            if previous_status == "D" or non_driving_start is None:
                non_driving_start = start
            if status in {"OFF", "SB"}:
                if rest_start is None:
                    rest_start = start
                rest_hours = _hours_between(rest_start, end)
                if rest_hours >= 10.0:
                    drive_since_reset = 0.0
                    duty_start = None
                if rest_hours >= 34.0:
                    on_duty_by_day.clear()
            else:
                rest_start = None
                if duty_start is None:
                    duty_start = start

            for chunk_start, chunk_end in _date_chunks(start, end):
                day = chunk_start.date()
                chunk_hours = _hours_between(chunk_start, chunk_end)
                if status == "ON":
                    on_duty_by_day[day] = on_duty_by_day.get(day, 0.0) + chunk_hours

            note = str(segment.get("note") or "").strip().lower()
            if status == "ON" and note.startswith("fuel"):
                fuel_miles = 0.0

        previous_end = end
        previous_status = status

    return True
