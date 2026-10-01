from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

import requests

from trips.services.geocoding import (
    autocomplete_locations,
    reverse_geocode_location,
    search_location,
    timezone_for_coordinates,
)
from trips.services.hos_engine import simulate_trip
from trips.services.log_sheets import build_log_sheets
from trips.services.routing import get_route_directions, place_stop_on_route
from trips.services.validator import validate_timeline

DEFAULT_ASSUMPTIONS = {
    "D1": (
        "Trip start time defaults to today at 08:00 and rounds to the nearest "
        "15-minute mark."
    ),
    "D2": "Home terminal timezone defaults to the current location zone.",
    "D3": (
        "Current cycle used is treated as prior on-duty hours from the day "
        "before the trip start."
    ),
    "D4": "When cycle hours are exhausted, the trip inserts a 34-hour OFF restart.",
    "D5": "Daily rest is logged as 10 consecutive hours in sleeper berth.",
    "D6": (
        "The 30-minute break is logged as OFF and is taken after 8 cumulative "
        "hours of driving."
    ),
    "D7": "Fuel stops are 30 minutes ON and occur every 1,000 miles driven.",
    "D8": "Pickup and dropoff each include 1 hour of ON-duty work.",
    "D9": "Pre-trip and post-trip inspections are 15 minutes ON.",
    "D10": "All boundaries fall on 15-minute marks.",
    "D11": (
        "The first and last log-sheet days include OFF time from midnight to "
        "trip start and after the trip ends."
    ),
    "D12": "Log sheet details are optional and may be filled with sample values.",
    "D13": "The planner is scoped to US addresses only.",
    "D14": "Frontend and backend are designed to work well with slow first requests.",
}

DEFAULT_LOG_DETAILS = {
    "driver_name": "Sample Driver",
    "co_driver": "",
    "carrier_name": "Sample Carrier LLC",
    "main_office_address": "100 Main Street, Chicago, IL",
    "home_terminal_address": "100 Main Street, Chicago, IL",
    "truck_number": "Truck 101",
    "trailer_number": "Trailer 202",
    "shipping_document_number": "Sample Load 123",
    "shipper_commodity": "",
}


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("Start datetime is invalid.")


def _round_to_quarter_hour(value: datetime) -> datetime:
    seconds = (
        value.hour * 3600
        + value.minute * 60
        + value.second
        + value.microsecond / 1_000_000
    )
    rounded_seconds = math.floor((seconds + 450) / 900) * 900
    day_offset, seconds_in_day = divmod(rounded_seconds, 86_400)
    rounded_day = value.date() + timedelta(days=day_offset)
    midnight = datetime.combine(rounded_day, datetime.min.time(), tzinfo=value.tzinfo)
    return midnight + timedelta(seconds=seconds_in_day)


def _cycle_hours_at_end(
    timeline: list[dict[str, Any]], start_date: datetime, prior_cycle_hours: float
) -> float:
    hours_by_day = {start_date.date() - timedelta(days=1): prior_cycle_hours}
    for segment in timeline:
        start = segment["start"]
        end = segment["end"]
        status = segment["status"]
        if status in {"OFF", "SB"} and str(segment.get("note", "")).startswith("34-hr"):
            if (end - start).total_seconds() >= 34 * 3600:
                hours_by_day.clear()
            continue
        if status not in {"D", "ON"}:
            continue
        cursor = start
        while cursor < end:
            next_midnight = datetime.combine(
                cursor.date() + timedelta(days=1),
                datetime.min.time(),
                tzinfo=cursor.tzinfo,
            )
            chunk_end = min(end, next_midnight)
            day_hours = (chunk_end - cursor).total_seconds() / 3600
            hours_by_day[cursor.date()] = (
                hours_by_day.get(cursor.date(), 0.0) + day_hours
            )
            cursor = chunk_end

    final_day = timeline[-1]["end"].date()
    window_start = final_day - timedelta(days=7)
    return sum(
        value for day, value in hours_by_day.items() if window_start <= day <= final_day
    )


def build_trip_plan(payload: dict[str, Any]) -> dict[str, Any]:
    cycle_used = float(payload.get("current_cycle_used_hours", 0) or 0)
    if not 0 <= cycle_used <= 70:
        raise ValueError("Current cycle used hours must be between 0 and 70.")

    start_datetime = _round_to_quarter_hour(
        _coerce_datetime(payload.get("start_datetime"))
    )
    location_labels = [
        payload.get("current_location"),
        payload.get("pickup_location"),
        payload.get("dropoff_location"),
    ]
    resolved_locations = [search_location(label) for label in location_labels]
    route_points = [
        (float(location["latitude"]), float(location["longitude"]))
        for location in resolved_locations
    ]
    route = get_route_directions(route_points)
    route_legs = route["legs"]
    route_geometry = route["geometry"]
    total_miles = float(route["total_miles"])

    timeline = simulate_trip(
        route_legs,
        start_datetime,
        current_cycle_used_hours=cycle_used,
    )
    if not validate_timeline(timeline, current_cycle_used_hours=cycle_used):
        raise ValueError("Generated timeline violates the HOS rules.")

    current_place, pickup_place, dropoff_place = [
        location["place"] for location in resolved_locations
    ]
    first_leg_miles = float(route_legs[0]["distance_miles"]) if route_legs else 0.0
    miles_along_route = 0.0
    active_place = current_place
    for segment in timeline:
        note = str(segment.get("note") or "")
        target_miles = miles_along_route
        if route_geometry:
            point = place_stop_on_route(
                route_geometry, target_miles, total_route_miles=total_miles
            )
        else:
            point = route_points[0]

        if note.startswith("Pickup"):
            point = route_points[1]
            active_place = pickup_place
        elif note.startswith("Dropoff"):
            point = route_points[2]
            active_place = dropoff_place
        elif target_miles <= 1e-6:
            active_place = current_place
        elif abs(target_miles - first_leg_miles) <= 0.5:
            active_place = pickup_place
        elif abs(target_miles - total_miles) <= 0.5:
            active_place = dropoff_place
        elif segment["status"] != "D" and note in {
            "Fuel stop",
            "30-min break",
            "10-hr rest (sleeper)",
            "34-hr restart",
        }:
            try:
                active_place = reverse_geocode_location(*point)["place"]
            except (ValueError, requests.RequestException):
                active_place = "En route"

        segment["lat"], segment["lng"] = point
        segment["place"] = active_place
        if segment["status"] == "D":
            miles_along_route += float(segment.get("miles") or 0.0)

    stops = [
        {
            "type": "start",
            "lat": route_points[0][0],
            "lng": route_points[0][1],
            "place": current_place,
            "arrival": start_datetime.isoformat(),
            "departure": start_datetime.isoformat(),
            "duration_hours": 0.0,
            "note": "Trip start",
        }
    ]
    stop_types = {
        "Pickup": "pickup",
        "Dropoff": "dropoff",
        "Fuel stop": "fuel",
        "30-min break": "break",
        "10-hr rest (sleeper)": "rest",
        "34-hr restart": "restart",
    }
    for segment in timeline:
        stop_type = stop_types.get(str(segment.get("note") or ""))
        if not stop_type:
            continue
        start = segment["start"]
        end = segment["end"]
        stops.append(
            {
                "type": stop_type,
                "lat": segment["lat"],
                "lng": segment["lng"],
                "place": segment["place"],
                "arrival": start.isoformat(),
                "departure": end.isoformat(),
                "duration_hours": (end - start).total_seconds() / 3600,
                "note": segment["note"],
            }
        )

    daily_sheets = build_log_sheets(timeline, current_cycle_used_hours=cycle_used)
    log_details = {
        key: (payload.get("log_details") or {}).get(key) or default
        for key, default in DEFAULT_LOG_DETAILS.items()
    }
    for sheet in daily_sheets:
        sheet["sheet_title"] = f"Driver's Daily Log - {sheet['date']}"
        sheet["log_details"] = log_details

    driving_hours = sum(
        (segment["end"] - segment["start"]).total_seconds() / 3600
        for segment in timeline
        if segment["status"] == "D"
    )
    on_duty_hours = sum(
        (segment["end"] - segment["start"]).total_seconds() / 3600
        for segment in timeline
        if segment["status"] in {"D", "ON"}
    )
    arrival = next(
        (stop["arrival"] for stop in stops if stop["type"] == "dropoff"),
        timeline[-1]["end"].isoformat(),
    )
    trip_duration = (timeline[-1]["end"] - start_datetime).total_seconds() / 3600
    timezone = timezone_for_coordinates(*route_points[0])
    geojson_coordinates = [
        [longitude, latitude] for latitude, longitude in route_geometry
    ]
    route_response = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": geojson_coordinates},
                "properties": {
                    "total_miles": total_miles,
                    "provider": route["provider"],
                },
            }
        ],
        "total_miles": total_miles,
        "legs": route_legs,
        "geometry": route_geometry,
        "total_hours": route["total_hours"],
        "provider": route["provider"],
    }

    return {
        "route": route_response,
        "stops": stops,
        "timeline": timeline,
        "days": daily_sheets,
        "summary": {
            "total_miles": total_miles,
            "total_driving_hours": round(driving_hours, 2),
            "total_on_duty_hours": round(on_duty_hours, 2),
            "total_trip_duration_hours": round(trip_duration, 2),
            "arrival_time": arrival,
            "trip_days": len(daily_sheets),
            "cycle_hours_remaining": round(
                max(
                    0.0,
                    70.0 - _cycle_hours_at_end(timeline, start_datetime, cycle_used),
                ),
                2,
            ),
        },
        "assumptions": {
            **DEFAULT_ASSUMPTIONS,
            "home_terminal_timezone": timezone,
        },
        "warnings": route["warnings"],
    }


def autocomplete_suggestions(query: str) -> list[dict[str, Any]]:
    return autocomplete_locations(query)
