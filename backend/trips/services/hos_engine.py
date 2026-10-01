from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _segment(
    status: str, start: datetime, end: datetime, miles: float = 0.0, note: str = ""
) -> dict[str, Any]:
    return {
        "status": status,
        "start": start,
        "end": end,
        "miles": float(miles),
        "lat": 0.0,
        "lng": 0.0,
        "place": "",
        "note": note,
    }


def simulate_trip(
    legs: list[dict[str, Any]],
    start_datetime: datetime | str,
    current_cycle_used_hours: float = 0.0,
) -> list[dict[str, Any]]:
    """Simulate a trip while tracking separate driving, shift, and cycle limits."""
    current_time = _as_datetime(start_datetime)
    cycle_used = float(current_cycle_used_hours)
    if not 0.0 <= cycle_used <= 70.0:
        raise ValueError("Current cycle used hours must be between 0 and 70.")

    segments: list[dict[str, Any]] = []
    cycle_by_day = {current_time.date() - timedelta(days=1): cycle_used}
    shift_start: datetime | None = None
    drive_since_reset = 0.0
    drive_since_break = 0.0
    non_driving_since_break = 0.0
    miles_since_fuel = 0.0

    def cycle_hours(at: datetime) -> float:
        first_day = at.date() - timedelta(days=7)
        return sum(
            hours
            for day, hours in cycle_by_day.items()
            if first_day <= day <= at.date()
        )

    def append_segment(
        status: str, duration_hours: float, miles: float = 0.0, note: str = ""
    ) -> None:
        nonlocal current_time, drive_since_break, non_driving_since_break
        if duration_hours <= 0:
            return

        start = current_time
        end = start + timedelta(hours=duration_hours)
        segments.append(_segment(status, start, end, miles=miles, note=note))

        if status in {"D", "ON"}:
            cursor = start
            while cursor < end:
                next_midnight = datetime.combine(
                    cursor.date() + timedelta(days=1),
                    datetime.min.time(),
                    tzinfo=cursor.tzinfo,
                )
                chunk_end = min(end, next_midnight)
                chunk_hours = (chunk_end - cursor).total_seconds() / 3600.0
                cycle_by_day[cursor.date()] = (
                    cycle_by_day.get(cursor.date(), 0.0) + chunk_hours
                )
                cursor = chunk_end

        if status == "D":
            drive_since_break += duration_hours
            non_driving_since_break = 0.0
        else:
            non_driving_since_break += duration_hours
            if non_driving_since_break >= 0.5:
                drive_since_break = 0.0
        current_time = end

    def begin_duty_period() -> None:
        nonlocal shift_start, drive_since_reset, drive_since_break
        nonlocal non_driving_since_break
        shift_start = current_time
        drive_since_reset = 0.0
        drive_since_break = 0.0
        non_driving_since_break = 0.0
        append_segment("ON", 0.25, note="Pre-trip inspection")

    def take_rest(reason: str) -> None:
        nonlocal shift_start, drive_since_reset, drive_since_break
        nonlocal non_driving_since_break, miles_since_fuel
        if reason == "cycle":
            append_segment("OFF", 34.0, note="34-hr restart")
            cycle_by_day.clear()
            shift_start = None
            drive_since_reset = 0.0
            drive_since_break = 0.0
            non_driving_since_break = 0.0
            begin_duty_period()
        elif reason == "shift":
            append_segment("SB", 10.0, note="10-hr rest (sleeper)")
            shift_start = None
            drive_since_reset = 0.0
            drive_since_break = 0.0
            non_driving_since_break = 0.0
            begin_duty_period()
        else:
            append_segment("OFF", 0.5, note="30-min break")

    def available_driving_hours() -> float:
        nonlocal shift_start
        while True:
            if shift_start is None:
                begin_duty_period()
            assert shift_start is not None
            cycle_remaining = 70.0 - cycle_hours(current_time)
            window_remaining = (
                14.0 - (current_time - shift_start).total_seconds() / 3600.0
            )
            available = min(
                11.0 - drive_since_reset,
                window_remaining,
                8.0 - drive_since_break,
                cycle_remaining,
            )
            if available > 1e-9:
                return available
            if cycle_remaining <= 1e-9:
                take_rest("cycle")
            elif drive_since_reset >= 11.0 - 1e-9 or window_remaining <= 1e-9:
                take_rest("shift")
            elif drive_since_break >= 8.0 - 1e-9:
                take_rest("break")
            else:
                raise RuntimeError("Unable to determine the required HOS rest.")

    if cycle_hours(current_time) >= 70.0:
        take_rest("cycle")
    else:
        begin_duty_period()

    for leg_index, leg in enumerate(legs):
        leg_distance = float(leg.get("distance_miles") or 0.0)
        if leg_distance < 0:
            raise ValueError("Route leg distance cannot be negative.")
        leg_duration = float(leg.get("duration_hours") or 0.0)
        speed_mph = (
            leg_distance / leg_duration
            if leg_distance > 0 and leg_duration > 0
            else 55.0
        )
        remaining_distance = leg_distance

        while remaining_distance > 1e-8:
            available = available_driving_hours()
            miles_to_fuel = max(0.0, 1000.0 - miles_since_fuel)
            if miles_to_fuel <= 1e-8:
                append_segment("ON", 0.5, note="Fuel stop")
                miles_since_fuel = 0.0
                continue

            distance_to_stop = min(remaining_distance, miles_to_fuel)
            exact_hours = distance_to_stop / speed_mph
            rounded_hours = math.ceil((exact_hours - 1e-10) * 4.0) / 4.0
            if exact_hours <= available + 1e-9 and rounded_hours <= available + 1e-9:
                drive_hours = rounded_hours
                miles_driven = distance_to_stop
            else:
                drive_hours = available
                miles_driven = min(distance_to_stop, speed_mph * drive_hours)

            if drive_hours <= 1e-9 or miles_driven <= 1e-9:
                raise RuntimeError("Trip simulation made no driving progress.")

            append_segment("D", drive_hours, miles=miles_driven, note="Drive")
            drive_since_reset += drive_hours
            miles_since_fuel += miles_driven
            remaining_distance = max(0.0, remaining_distance - miles_driven)

            future_miles = remaining_distance + sum(
                float(next_leg.get("distance_miles") or 0.0)
                for next_leg in legs[leg_index + 1 :]
            )
            if miles_since_fuel >= 1000.0 - 1e-8 and future_miles > 1e-8:
                append_segment("ON", 0.5, note="Fuel stop")
                miles_since_fuel = 0.0

        if leg_index == 0:
            append_segment("ON", 1.0, note="Pickup")
        if leg_index == len(legs) - 1:
            append_segment("ON", 1.0, note="Dropoff")

    append_segment("ON", 0.25, note="Post-trip inspection")
    return segments
