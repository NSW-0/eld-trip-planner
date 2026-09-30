from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

VALID_STATUSES = ["OFF", "SB", "D", "ON"]


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


def _split_across_midnight(segment: dict[str, Any]) -> list[dict[str, Any]]:
    start = _as_datetime(segment["start"])
    end = _as_datetime(segment["end"])
    if end <= start:
        return [segment]

    day_start = datetime.combine(start.date(), datetime.min.time())
    next_midnight = day_start + timedelta(days=1)

    if end <= next_midnight:
        return [segment]

    first_end = min(end, next_midnight)
    first_duration = _hours_between(start, first_end)
    first_miles = float(segment.get("miles") or 0.0)
    first_fraction = first_duration / max(_hours_between(start, end), 1e-9)
    first = {
        **segment,
        "start": start.isoformat(),
        "end": first_end.isoformat(),
        "miles": first_miles * first_fraction,
    }

    second_start = first_end
    second_duration = _hours_between(second_start, end)
    second_miles = float(segment.get("miles") or 0.0)
    second_fraction = second_duration / max(_hours_between(start, end), 1e-9)
    second = {
        **segment,
        "start": second_start.isoformat(),
        "end": end.isoformat(),
        "miles": second_miles * second_fraction,
    }
    return [first, second]


def build_log_sheets(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build one daily log sheet per calendar date present in the timeline."""
    per_day: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for segment in timeline:
        for split in _split_across_midnight(segment):
            start = _as_datetime(split["start"])
            per_day[start.date().isoformat()].append(split)

    daily_sheets: list[dict[str, Any]] = []

    for day_key in sorted(per_day):
        segments = per_day[day_key]
        row_totals = {status: 0.0 for status in VALID_STATUSES}
        remarks: list[str] = []

        for segment in segments:
            status = str(segment.get("status") or "OFF")
            start = _as_datetime(segment["start"])
            end = _as_datetime(segment["end"])
            hours = _hours_between(start, end)
            row_totals[status] = row_totals.get(status, 0.0) + hours
            note = str(segment.get("note") or status)
            place = str(segment.get("place") or "Unknown")
            remarks.append(f"{start.strftime('%H:%M')} {status} – {place}: {note}")

        total = sum(row_totals.values())
        if total != 24.0:
            row_totals["OFF"] += 24.0 - total

        daily_sheets.append(
            {
                "date": day_key,
                "row_totals": row_totals,
                "remarks": remarks,
                "total_hours": round(sum(row_totals.values()), 2),
                "from_place": segments[0].get("place") or "Unknown",
                "to_place": segments[-1].get("place") or "Unknown",
            }
        )

    if not daily_sheets:
        return [
            {
                "date": "",
                "row_totals": {status: 0.0 for status in VALID_STATUSES},
                "remarks": [],
                "total_hours": 0.0,
                "from_place": "Unknown",
                "to_place": "Unknown",
            }
        ]

    return daily_sheets
