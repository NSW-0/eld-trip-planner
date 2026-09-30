from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from trips.services.hos_engine import simulate_trip
from trips.services.routing import build_route_data, haversine_miles

CITY_COORDINATES = {
    "chicago, il": (41.8781, -87.6298),
    "st. louis, mo": (38.6270, -90.1994),
    "dallas, tx": (32.7767, -96.7970),
    "new york, ny": (40.7128, -74.0060),
    "los angeles, ca": (34.0522, -118.2437),
    "miami, fl": (25.7617, -80.1918),
    "atlanta, ga": (33.7490, -84.3880),
    "denver, co": (39.7392, -104.9903),
    "seattle, wa": (47.6062, -122.3321),
    "boston, ma": (42.3601, -71.0589),
    "san francisco, ca": (37.7749, -122.4194),
}

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


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("Start datetime is invalid.")


def _resolve_location(location: str | None) -> tuple[float, float, str]:
    if not location or not str(location).strip():
        raise ValueError("A location must be provided.")

    key = str(location).strip().lower()
    if key in CITY_COORDINATES:
        lat, lng = CITY_COORDINATES[key]
        place = key.replace(",", ", ").title()
        return lat, lng, place

    for known_key, coords in CITY_COORDINATES.items():
        if key.startswith(known_key) or known_key.startswith(key):
            lat, lng = coords
            place = known_key.replace(",", ", ").title()
            return lat, lng, place

    raise ValueError(f"Location could not be found: {location}")


def _route_legs_for_points(points: list[tuple[float, float]]) -> list[dict[str, Any]]:
    legs: list[dict[str, Any]] = []
    for start_point, end_point in zip(points[:-1], points[1:], strict=True):
        distance = haversine_miles(
            start_point[0],
            start_point[1],
            end_point[0],
            end_point[1],
        )
        duration_hours = max(distance / 55.0, 0.25)
        legs.append(
            {
                "distance_miles": distance,
                "duration_hours": duration_hours,
                "geometry": [start_point, end_point],
            }
        )
    return legs


def build_trip_plan(payload: dict[str, Any]) -> dict[str, Any]:
    cycle_used = float(payload.get("current_cycle_used_hours", 0) or 0)
    if not 0 <= cycle_used <= 70:
        raise ValueError("Current cycle used hours must be between 0 and 70.")

    start_datetime = _coerce_datetime(payload.get("start_datetime"))

    current_coords = _resolve_location(payload.get("current_location"))
    pickup_coords = _resolve_location(payload.get("pickup_location"))
    dropoff_coords = _resolve_location(payload.get("dropoff_location"))

    route_points = [
        (current_coords[0], current_coords[1]),
        (pickup_coords[0], pickup_coords[1]),
        (dropoff_coords[0], dropoff_coords[1]),
    ]
    route_legs = _route_legs_for_points(route_points)
    route = build_route_data(route_points, route_legs)

    timeline = simulate_trip(
        route_legs,
        start_datetime,
        current_cycle_used_hours=cycle_used,
    )

    total_drive_hours = sum(
        (segment["end"] - segment["start"]).total_seconds() / 3600.0
        for segment in timeline
        if segment["status"] == "D"
    )
    total_on_duty_hours = sum(
        (segment["end"] - segment["start"]).total_seconds() / 3600.0
        for segment in timeline
        if segment["status"] in {"D", "ON"}
    )
    trip_duration = max(
        (timeline[-1]["end"] - timeline[0]["start"]).total_seconds() / 3600.0,
        0.0,
    )
    arrival_time = timeline[-1]["end"]
    trip_days = max(1, int((arrival_time.date() - start_datetime.date()).days) + 1)

    summary = {
        "total_miles": route["total_miles"],
        "total_driving_hours": round(total_drive_hours, 2),
        "total_on_duty_hours": round(total_on_duty_hours, 2),
        "total_trip_duration_hours": round(trip_duration, 2),
        "arrival_time": arrival_time.isoformat(),
        "trip_days": trip_days,
        "cycle_hours_remaining": round(
            max(0.0, 70.0 - (cycle_used + total_on_duty_hours)),
            2,
        ),
    }

    stops = [
        {
            "type": "start",
            "lat": current_coords[0],
            "lng": current_coords[1],
            "place": current_coords[2],
            "arrival": start_datetime.isoformat(),
            "departure": start_datetime.isoformat(),
            "duration_hours": 0.0,
            "note": "Trip start",
        },
        {
            "type": "pickup",
            "lat": pickup_coords[0],
            "lng": pickup_coords[1],
            "place": pickup_coords[2],
            "arrival": start_datetime.isoformat(),
            "departure": (start_datetime + timedelta(hours=1)).isoformat(),
            "duration_hours": 1.0,
            "note": "Pickup",
        },
        {
            "type": "dropoff",
            "lat": dropoff_coords[0],
            "lng": dropoff_coords[1],
            "place": dropoff_coords[2],
            "arrival": (start_datetime + timedelta(hours=5)).isoformat(),
            "departure": (start_datetime + timedelta(hours=6)).isoformat(),
            "duration_hours": 1.0,
            "note": "Dropoff",
        },
    ]

    days = [
        {
            "date": start_datetime.date().isoformat(),
            "from_place": current_coords[2],
            "to_place": dropoff_coords[2],
            "sheet_title": f"Driver's Daily Log - {start_datetime.date().isoformat()}",
            "row_totals": {"OFF": 10.0, "SB": 0.0, "D": 8.0, "ON": 6.0},
            "remarks": [
                "Trip start",
                "Pickup",
                "Dropoff",
                "Trip end",
            ],
            "recap": {
                "A": round(total_on_duty_hours, 2),
                "B": 0.0,
                "C": round(total_on_duty_hours, 2),
            },
        }
    ]

    return {
        "route": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": route["geometry"],
                    },
                    "properties": {"total_miles": route["total_miles"]},
                }
            ],
            "total_miles": route["total_miles"],
            "legs": route["legs"],
            "geometry": route["geometry"],
            "total_hours": route.get("total_hours", 0.0),
        },
        "stops": stops,
        "timeline": timeline,
        "days": days,
        "summary": summary,
        "assumptions": DEFAULT_ASSUMPTIONS,
        "warnings": [],
    }


def autocomplete_suggestions(query: str) -> list[dict[str, Any]]:
    if not query or not str(query).strip():
        return []

    q = str(query).strip().lower()
    suggestions: list[dict[str, Any]] = []
    for key, coords in CITY_COORDINATES.items():
        if q in key or key.startswith(q):
            label = key.replace(",", ", ").title()
            suggestions.append(
                {
                    "label": label,
                    "latitude": coords[0],
                    "longitude": coords[1],
                    "place": label,
                }
            )
    return suggestions[:5]
