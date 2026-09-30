from __future__ import annotations

from datetime import datetime, timedelta
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


def validate_timeline(timeline: list[dict[str, Any]]) -> bool:
    """Independently validate a fully-built driver timeline."""
    if not isinstance(timeline, list) or not timeline:
        return False

    previous_end: datetime | None = None
    duty_start: datetime | None = None
    duty_hours_since_reset = 0.0
    driving_hours_since_break = 0.0
    fuel_miles_since_last_stop = 0.0

    for segment in timeline:
        status = segment.get("status")
        if status not in VALID_STATUSES:
            return False

        start = _as_datetime(segment.get("start"))
        end = _as_datetime(segment.get("end"))
        if end < start:
            return False

        if previous_end is not None and start != previous_end:
            return False
        previous_end = end

        hours = _hours_between(start, end)
        if hours < 0:
            return False

        if status == "D":
            if duty_start is None:
                duty_start = start

            duty_hours_since_reset += hours
            driving_hours_since_break += hours

            if driving_hours_since_break > 8.0:
                return False
            if duty_hours_since_reset > 14.0:
                return False
            if driving_hours_since_break > 11.0:
                return False

            fuel_miles_since_last_stop += float(segment.get("miles") or 0.0)

        elif status == "OFF":
            if hours >= 10 and (segment.get("note") or "").lower().startswith("34"):
                duty_start = end
                duty_hours_since_reset = 0.0
                driving_hours_since_break = 0.0
            elif hours >= 0.5:
                duty_start = end
                duty_hours_since_reset = 0.0
                driving_hours_since_break = 0.0
            fuel_miles_since_last_stop = 0.0

        elif status == "SB":
            if hours >= 10:
                duty_start = end
                duty_hours_since_reset = 0.0
                driving_hours_since_break = 0.0
            else:
                duty_start = end
                duty_hours_since_reset = 0.0
                driving_hours_since_break = 0.0

        elif status == "ON":
            if duty_start is None:
                duty_start = start
            duty_hours_since_reset += hours
            if duty_hours_since_reset > 14.0:
                return False

            if (segment.get("note") or "").lower().startswith("fuel"):
                if fuel_miles_since_last_stop > 1000.0:
                    return False
                fuel_miles_since_last_stop = 0.0

    return True
