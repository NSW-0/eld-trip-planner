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
    duration = _hours_between(start, end)
    total_miles = float(segment.get("miles") or 0.0)
    pieces: list[dict[str, Any]] = []
    cursor = start
    while cursor < end:
        next_midnight = datetime.combine(
            cursor.date() + timedelta(days=1),
            datetime.min.time(),
            tzinfo=cursor.tzinfo,
        )
        piece_end = min(end, next_midnight)
        piece_hours = _hours_between(cursor, piece_end)
        pieces.append(
            {
                **segment,
                "start": cursor.isoformat(),
                "end": piece_end.isoformat(),
                "miles": total_miles * piece_hours / duration,
                "_continued_from_midnight": cursor != start,
            }
        )
        cursor = piece_end
    return pieces


def _minute_of_day(value: datetime) -> float:
    midnight = datetime.combine(value.date(), datetime.min.time(), tzinfo=value.tzinfo)
    return (value - midnight).total_seconds() / 60.0


def _restart_end_times(timeline: list[dict[str, Any]]) -> list[datetime]:
    restart_ends = []
    rest_start: datetime | None = None
    for segment in timeline:
        start = _as_datetime(segment["start"])
        end = _as_datetime(segment["end"])
        status = str(segment.get("status") or "OFF")
        if status in {"OFF", "SB"}:
            if rest_start is None:
                rest_start = start
            if _hours_between(rest_start, end) >= 34.0:
                restart_ends.append(end)
        else:
            rest_start = None
    return restart_ends


def _cycle_hours_in_window(
    timeline: list[dict[str, Any]],
    report_day,
    window_days: int,
    first_day,
    current_cycle_used_hours: float,
    restart_ends: list[datetime],
) -> float:
    window_start = report_day - timedelta(days=window_days - 1)
    completed_restarts = [end for end in restart_ends if end.date() <= report_day]
    latest_restart = max(completed_restarts) if completed_restarts else None
    total = 0.0
    prior_day = first_day - timedelta(days=1)
    if latest_restart is None and window_start <= prior_day <= report_day:
        total += current_cycle_used_hours

    for segment in timeline:
        if segment.get("status") not in {"D", "ON"}:
            continue
        start = _as_datetime(segment["start"])
        end = _as_datetime(segment["end"])
        if latest_restart is not None:
            if end <= latest_restart:
                continue
            start = max(start, latest_restart)
        cursor = start
        while cursor < end:
            next_midnight = datetime.combine(
                cursor.date() + timedelta(days=1),
                datetime.min.time(),
                tzinfo=cursor.tzinfo,
            )
            chunk_end = min(end, next_midnight)
            if window_start <= cursor.date() <= report_day:
                total += _hours_between(cursor, chunk_end)
            cursor = chunk_end
    return total


def build_log_sheets(
    timeline: list[dict[str, Any]], current_cycle_used_hours: float = 0.0
) -> list[dict[str, Any]]:
    """Build full-day log data and rolling-cycle recaps from the timeline."""
    per_day: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for segment in timeline:
        for split in _split_across_midnight(segment):
            start = _as_datetime(split["start"])
            per_day[start.date().isoformat()].append(split)

    first_day = (
        _as_datetime(timeline[0]["start"]).date() if timeline else datetime.min.date()
    )
    restart_ends = _restart_end_times(timeline)

    daily_sheets: list[dict[str, Any]] = []
    for day_key in sorted(per_day):
        day_segments = per_day[day_key]
        row_totals = {status: 0.0 for status in VALID_STATUSES}
        remarks: list[str] = []
        display_segments: list[dict[str, Any]] = []
        cursor_minute = 0.0
        miles_today = 0.0

        for segment in day_segments:
            status = str(segment.get("status") or "OFF")
            start = _as_datetime(segment["start"])
            end = _as_datetime(segment["end"])
            hours = _hours_between(start, end)
            row_totals[status] = row_totals.get(status, 0.0) + hours
            start_minute = _minute_of_day(start)
            end_minute = _minute_of_day(end)
            if end.date() > start.date():
                end_minute = 1440.0
            if start_minute > cursor_minute:
                display_segments.append(
                    {
                        "status": "OFF",
                        "start_minute": cursor_minute,
                        "end_minute": start_minute,
                        "miles": 0.0,
                        "place": segment.get("place") or "Unknown",
                        "note": "Off duty",
                    }
                )
                row_totals["OFF"] += (start_minute - cursor_minute) / 60.0
            miles = float(segment.get("miles") or 0.0)
            if status == "D":
                miles_today += miles
            display_segments.append(
                {
                    "status": status,
                    "start_minute": start_minute,
                    "end_minute": end_minute,
                    "miles": miles,
                    "lat": segment.get("lat"),
                    "lng": segment.get("lng"),
                    "place": segment.get("place") or "Unknown",
                    "note": segment.get("note") or status,
                }
            )
            note = str(segment.get("note") or status)
            place = str(segment.get("place") or "Unknown")
            if not segment.get("_continued_from_midnight"):
                remarks.append(f"{start.strftime('%H:%M')} {status} - {place}: {note}")
            cursor_minute = max(cursor_minute, end_minute)

        if cursor_minute < 1440.0:
            display_segments.append(
                {
                    "status": "OFF",
                    "start_minute": cursor_minute,
                    "end_minute": 1440.0,
                    "miles": 0.0,
                    "place": day_segments[-1].get("place") or "Unknown",
                    "note": "Off duty",
                }
            )
            row_totals["OFF"] += (1440.0 - cursor_minute) / 60.0

        row_totals = {status: round(hours, 2) for status, hours in row_totals.items()}
        row_totals["OFF"] = round(
            24.0
            - sum(hours for status, hours in row_totals.items() if status != "OFF"),
            2,
        )
        on_duty_today = row_totals["D"] + row_totals["ON"]
        day_date = datetime.fromisoformat(day_key).date()
        recap_a = _cycle_hours_in_window(
            timeline,
            day_date,
            7,
            first_day,
            float(current_cycle_used_hours),
            restart_ends,
        )
        recap_c = _cycle_hours_in_window(
            timeline,
            day_date,
            5,
            first_day,
            float(current_cycle_used_hours),
            restart_ends,
        )

        daily_sheets.append(
            {
                "date": day_key,
                "row_totals": row_totals,
                "remarks": remarks,
                "segments": display_segments,
                "total_hours": round(sum(row_totals.values()), 2),
                "total_miles_driving_today": round(miles_today, 2),
                "from_place": day_segments[0].get("place") or "Unknown",
                "to_place": day_segments[-1].get("place") or "Unknown",
                "on_duty_hours_today": round(on_duty_today, 2),
                "recap": {
                    "A": round(recap_a, 2),
                    "B": round(max(0.0, 70.0 - recap_a), 2),
                    "C": round(recap_c, 2),
                },
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
