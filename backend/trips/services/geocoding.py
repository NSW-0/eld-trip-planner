"""Small geocoding helpers used by trip planning."""

from __future__ import annotations

from typing import Any

try:
    from timezonefinder import TimezoneFinder
except ImportError:  # pragma: no cover - dependency is in the project requirements.
    TimezoneFinder = None


def format_city_state(city: str, state: str) -> str:
    city_name = (city or "").strip()
    state_name = (state or "").strip()
    if city_name and state_name:
        return f"{city_name}, {state_name}"
    return city_name or state_name


def cache_key_for_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    lat_value = round(float(latitude), 3)
    lng_value = round(float(longitude), 2)
    return (lat_value, lng_value)


def timezone_for_coordinates(latitude: float, longitude: float) -> str:
    if TimezoneFinder is not None:
        finder = TimezoneFinder()
        zone = finder.certain_timezone_at(lat=float(latitude), lng=float(longitude))
        if zone:
            return zone
    if -90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180:
        return "UTC"
    raise ValueError("Coordinates are outside valid latitude/longitude bounds.")


def reverse_geocode_place(
    latitude: float, longitude: float, city: str | None = None, state: str | None = None
) -> dict[str, Any]:
    loc_city = (city or "Unknown").strip()
    loc_state = (state or "").strip()
    return {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "place": format_city_state(loc_city, loc_state) or "Unknown, XX",
        "timezone": timezone_for_coordinates(latitude, longitude),
    }
