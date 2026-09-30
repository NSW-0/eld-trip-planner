from __future__ import annotations

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
    """Build a basic HOS timeline for a trip without any network dependency.

    This is intentionally pure-Python and designed around the brief's default decisions:
    - 15-minute pre/post trip inspections
    - 1-hour pickup and 1-hour dropoff
    - 30-minute OFF break after 8 hours of cumulative driving unless already reset by a
      qualifying duty stop
    - 34-hour restart when the 70-hour cycle is exhausted
    """
    current_time = _as_datetime(start_datetime)
    segments: list[dict[str, Any]] = []
    cycle_used = float(current_cycle_used_hours)

    if cycle_used >= 70:
        restart_end = current_time + timedelta(hours=34)
        segments.append(
            _segment("OFF", current_time, restart_end, miles=0.0, note="34-hr restart")
        )
        current_time = restart_end
        cycle_used = 0.0

    inspection_end = current_time + timedelta(minutes=15)
    segments.append(
        _segment(
            "ON", current_time, inspection_end, miles=0.0, note="Pre-trip inspection"
        )
    )
    current_time = inspection_end

    driving_hours = 0.0
    total_trip_miles = 0.0

    for index, leg in enumerate(legs):
        leg_distance = float(leg.get("distance_miles") or 0.0)
        if leg_distance <= 0:
            continue

        leg_duration_hours = float(leg.get("duration_hours") or (leg_distance / 55.0))
        remaining_distance = leg_distance
        remaining_duration = leg_duration_hours

        while remaining_distance > 0:
            remaining_drive_hours = max(0.0, 8.0 - driving_hours)
            available_hours = min(
                11.0 - driving_hours,
                14.0,
                remaining_drive_hours if remaining_drive_hours > 0 else 0.0,
            )

            if available_hours <= 0:
                break_start = current_time
                break_end = break_start + timedelta(minutes=30)
                segments.append(
                    _segment(
                        "OFF", break_start, break_end, miles=0.0, note="30-min break"
                    )
                )
                current_time = break_end
                driving_hours = 0.0
                continue

            drive_hours = min(
                remaining_duration,
                available_hours,
                remaining_distance
                / max(leg_distance / max(leg_duration_hours, 1e-9), 1e-9),
            )
            if drive_hours <= 0:
                drive_hours = min(remaining_duration, 1.0)

            drive_end = current_time + timedelta(hours=drive_hours)
            miles_driven = leg_distance * (drive_hours / max(leg_duration_hours, 1e-9))
            segments.append(
                _segment("D", current_time, drive_end, miles=miles_driven, note="Drive")
            )
            current_time = drive_end
            remaining_distance -= miles_driven
            remaining_duration -= drive_hours
            total_trip_miles += miles_driven
            driving_hours += drive_hours
            cycle_used += drive_hours

            if driving_hours >= 8 and remaining_distance > 0:
                break_start = current_time
                break_end = break_start + timedelta(minutes=30)
                segments.append(
                    _segment(
                        "OFF", break_start, break_end, miles=0.0, note="30-min break"
                    )
                )
                current_time = break_end
                driving_hours = 0.0

        if index == 0:
            pickup_end = current_time + timedelta(hours=1)
            segments.append(
                _segment("ON", current_time, pickup_end, miles=0.0, note="Pickup")
            )
            current_time = pickup_end
        elif index == len(legs) - 1:
            dropoff_end = current_time + timedelta(hours=1)
            segments.append(
                _segment("ON", current_time, dropoff_end, miles=0.0, note="Dropoff")
            )
            current_time = dropoff_end

    post_trip_end = current_time + timedelta(minutes=15)
    segments.append(
        _segment(
            "ON", current_time, post_trip_end, miles=0.0, note="Post-trip inspection"
        )
    )

    return segments
