"""Helpers for normalizing route payloads and leg data."""

from __future__ import annotations

import math
from typing import Any

EARTH_RADIUS_MILES = 3958.8


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def normalize_route_payload(payload: dict[str, Any]) -> dict[str, Any]:
    routes = payload.get("routes") or []
    route = routes[0] if routes else {}

    summary = route.get("summary") or {}
    total_distance = float(summary.get("distance") or 0.0)
    total_duration = float(summary.get("duration") or 0.0)

    legs: list[dict[str, Any]] = []
    for segment in route.get("segments") or []:
        distance = float(segment.get("distance") or 0.0)
        duration = float(segment.get("duration") or 0.0)
        geometry = segment.get("geometry") or []
        legs.append(
            {
                "distance_miles": distance,
                "duration_hours": duration / 3600.0 if duration else 0.0,
                "geometry": geometry,
            }
        )

    geometry = []
    feature_list = payload.get("features") or []
    if feature_list:
        geometry = feature_list[0].get("geometry", {}).get("coordinates", [])

    return {
        "total_miles": total_distance / 1609.344
        if total_distance > 1000
        else total_distance,
        "total_hours": total_duration / 3600.0 if total_duration else 0.0,
        "geometry": geometry,
        "legs": legs,
    }


def build_route_data(
    points: list[tuple[float, float]],
    legs: list[dict[str, Any]],
) -> dict[str, Any]:
    total_miles = sum(float(leg.get("distance_miles") or 0.0) for leg in legs)
    return {
        "points": list(points),
        "geometry": list(points),
        "total_miles": total_miles,
        "legs": [
            {
                **leg,
                "average_speed_mph": (
                    float(leg.get("distance_miles") or 0.0)
                    / max(float(leg.get("duration_hours") or 0.0), 1e-9)
                ),
            }
            for leg in legs
        ],
    }


def place_stop_on_route(
    route_points: list[tuple[float, float]],
    target_distance_miles: float,
) -> tuple[float, float]:
    if not route_points:
        raise ValueError("Route points cannot be empty.")
    if len(route_points) == 1:
        return route_points[0]

    cumulative = 0.0
    for index in range(len(route_points) - 1):
        lat1, lon1 = route_points[index]
        lat2, lon2 = route_points[index + 1]
        segment_distance = haversine_miles(lat1, lon1, lat2, lon2)
        if cumulative + segment_distance >= target_distance_miles:
            remaining = target_distance_miles - cumulative
            if segment_distance <= 0:
                return route_points[index + 1]
            ratio = remaining / segment_distance
            lat = lat1 + (lat2 - lat1) * ratio
            lon = lon1 + (lon2 - lon1) * ratio
            return (lat, lon)
        cumulative += segment_distance

    return route_points[-1]
