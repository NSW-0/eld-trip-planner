"""Helpers for normalizing route payloads and leg data."""

from __future__ import annotations

import math
import os
from typing import Any

import requests

EARTH_RADIUS_MILES = 3958.8
METERS_PER_MILE = 1609.344


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
    features = payload.get("features") or []
    routes = payload.get("routes") or []
    feature = features[0] if features else {}
    route = routes[0] if routes else {}
    properties = feature.get("properties") or {}
    summary = properties.get("summary") or route.get("summary") or route
    segments = (
        properties.get("segments") or route.get("segments") or route.get("legs") or []
    )

    raw_geometry = feature.get("geometry") or route.get("geometry") or {}
    if isinstance(raw_geometry, dict):
        raw_geometry = raw_geometry.get("coordinates") or []
    geometry = [
        (float(coordinate[1]), float(coordinate[0]))
        for coordinate in raw_geometry
        if len(coordinate) >= 2
    ]

    legs: list[dict[str, Any]] = []
    for segment in segments:
        distance_meters = float(segment.get("distance") or 0.0)
        duration_seconds = float(segment.get("duration") or 0.0)
        segment_geometry = segment.get("geometry") or []
        if isinstance(segment_geometry, dict):
            segment_geometry = segment_geometry.get("coordinates") or []
        legs.append(
            {
                "distance_miles": distance_meters / METERS_PER_MILE,
                "duration_hours": duration_seconds / 3600.0,
                "geometry": [
                    (float(coordinate[1]), float(coordinate[0]))
                    for coordinate in segment_geometry
                    if len(coordinate) >= 2
                ],
            }
        )

    total_distance = float(summary.get("distance") or 0.0)
    total_duration = float(summary.get("duration") or 0.0)
    if not total_distance:
        total_distance = sum(
            float(segment.get("distance") or 0.0) for segment in segments
        )
    if not total_duration:
        total_duration = sum(
            float(segment.get("duration") or 0.0) for segment in segments
        )

    return {
        "total_miles": total_distance / METERS_PER_MILE,
        "total_hours": total_duration / 3600.0,
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


def get_route_directions(points: list[tuple[float, float]]) -> dict[str, Any]:
    """Fetch an HGV route from ORS, falling back to OSRM with a warning."""
    if len(points) < 2:
        raise ValueError("At least two route points are required.")

    request_points = [points[0]]
    for point in points[1:]:
        if point != request_points[-1]:
            request_points.append(point)
    if len(request_points) < 2:
        return {
            "provider": "local",
            "warnings": [],
            "total_miles": 0.0,
            "total_hours": 0.0,
            "geometry": request_points,
            "legs": [],
        }

    coordinates = [[longitude, latitude] for latitude, longitude in request_points]
    api_key = os.environ.get("ORS_API_KEY", "").strip()
    warnings: list[str] = []

    if api_key:
        try:
            response = requests.post(
                "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson",
                headers={"Authorization": api_key, "Content-Type": "application/json"},
                json={"coordinates": coordinates},
                timeout=20,
            )
            response.raise_for_status()
            route = normalize_route_payload(response.json())
            if route["legs"] and route["geometry"]:
                return {**route, "provider": "ors", "warnings": []}
            warnings.append("ORS returned incomplete route data; using OSRM fallback.")
        except (requests.RequestException, ValueError, KeyError, TypeError):
            warnings.append("ORS routing was unavailable; using OSRM fallback.")
    else:
        warnings.append("ORS_API_KEY is not configured; using OSRM fallback.")

    coordinate_path = ";".join(
        f"{longitude:.6f},{latitude:.6f}" for latitude, longitude in request_points
    )
    try:
        response = requests.get(
            f"https://router.project-osrm.org/route/v1/driving/{coordinate_path}",
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            headers={"User-Agent": "ELDTripPlanner/1.0"},
            timeout=20,
        )
        response.raise_for_status()
        route = normalize_route_payload(response.json())
        if not route["legs"] or not route["geometry"]:
            raise ValueError("OSRM returned incomplete route data.")
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        raise ValueError("Unable to build a route with ORS or OSRM.") from exc

    warnings.append("Fallback route uses OSRM and is not truck-verified.")
    return {**route, "provider": "osrm", "warnings": warnings}


def place_stop_on_route(
    route_points: list[tuple[float, float]],
    target_distance_miles: float,
    total_route_miles: float | None = None,
) -> tuple[float, float]:
    if not route_points:
        raise ValueError("Route points cannot be empty.")
    if len(route_points) == 1:
        return route_points[0]

    geometry_miles = sum(
        haversine_miles(*start, *end)
        for start, end in zip(route_points[:-1], route_points[1:], strict=True)
    )
    if total_route_miles and total_route_miles > 0 and geometry_miles > 0:
        target_distance_miles *= geometry_miles / total_route_miles

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
