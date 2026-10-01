"""Small geocoding helpers used by trip planning."""

from __future__ import annotations

import os
import threading
import time
from typing import Any

import requests

try:
    from timezonefinder import TimezoneFinder
except ImportError:  # pragma: no cover - dependency is in the project requirements.
    TimezoneFinder = None

ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
_location_cache: dict[str, dict[str, Any] | None] = {}
_autocomplete_cache: dict[str, list[dict[str, Any]]] = {}
_reverse_cache: dict[tuple[float, float], dict[str, Any]] = {}
_nominatim_lock = threading.Lock()
_last_nominatim_request = 0.0
_US_STATE_CODES = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}


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


def _format_us_place(address: dict[str, Any], properties: dict[str, Any]) -> str:
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or properties.get("locality")
        or properties.get("name")
        or ""
    )
    state_code = (
        address.get("ISO3166-2-lvl4")
        or properties.get("region_a")
        or properties.get("region")
        or address.get("state")
        or ""
    )
    state_code = str(state_code).strip().split("-")[-1]
    if len(state_code) != 2:
        state_code = _US_STATE_CODES.get(state_code.lower(), state_code)
    return format_city_state(str(city), state_code)


def _nominatim_get(endpoint: str, params: dict[str, Any]) -> requests.Response:
    global _last_nominatim_request
    with _nominatim_lock:
        wait_seconds = 1.0 - (time.monotonic() - _last_nominatim_request)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        _last_nominatim_request = time.monotonic()
    user_agent = os.environ.get(
        "NOMINATIM_USER_AGENT", "ELDTripPlanner/1.0 (HOS trip planning)"
    )
    response = requests.get(
        f"{NOMINATIM_URL}/{endpoint}",
        params=params,
        headers={"User-Agent": user_agent},
        timeout=15,
    )
    response.raise_for_status()
    return response


def _nominatim_search(query: str, limit: int) -> list[dict[str, Any]]:
    response = _nominatim_get(
        "search",
        {
            "format": "jsonv2",
            "q": query,
            "countrycodes": "us",
            "addressdetails": 1,
            "limit": limit,
        },
    )
    results = []
    for item in response.json():
        address = item.get("address") or {}
        place = _format_us_place(address, {}) or item.get("display_name", "")
        results.append(
            {
                "label": place,
                "latitude": float(item["lat"]),
                "longitude": float(item["lon"]),
                "place": place,
            }
        )
    return results


def _ors_search(query: str, endpoint: str, size: int) -> list[dict[str, Any]]:
    api_key = os.environ.get("ORS_API_KEY", "").strip()
    if not api_key:
        return []
    response = requests.get(
        f"{ORS_GEOCODE_URL}/{endpoint}",
        params={"text": query, "boundary.country": "USA", "size": size},
        headers={"Authorization": api_key},
        timeout=15,
    )
    response.raise_for_status()
    results = []
    for feature in response.json().get("features") or []:
        properties = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) < 2:
            continue
        place = _format_us_place({}, properties) or properties.get("label", "")
        results.append(
            {
                "label": place,
                "latitude": float(coordinates[1]),
                "longitude": float(coordinates[0]),
                "place": place,
            }
        )
    return results


def search_location(query: str) -> dict[str, Any]:
    normalized = str(query or "").strip()
    if not normalized:
        raise ValueError("A location must be provided.")
    cache_key = normalized.casefold()
    if cache_key in _location_cache and _location_cache[cache_key] is not None:
        return dict(_location_cache[cache_key])

    try:
        results = _ors_search(normalized, "search", 1)
    except requests.RequestException:
        results = []
    if not results:
        try:
            results = _nominatim_search(normalized, 1)
        except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Location could not be found: {normalized}") from exc
    if not results:
        raise ValueError(f"Location could not be found: {normalized}")

    result = results[0]
    location = {
        "latitude": result["latitude"],
        "longitude": result["longitude"],
        "place": result["place"],
    }
    _location_cache[cache_key] = location
    return dict(location)


def autocomplete_locations(query: str) -> list[dict[str, Any]]:
    normalized = str(query or "").strip()
    if not normalized:
        return []
    cache_key = normalized.casefold()
    if cache_key in _autocomplete_cache:
        return [dict(item) for item in _autocomplete_cache[cache_key]]

    try:
        results = _ors_search(normalized, "autocomplete", 5)
    except requests.RequestException:
        results = []
    if not results:
        try:
            results = _nominatim_search(normalized, 5)
        except (requests.RequestException, KeyError, TypeError, ValueError):
            results = []
    _autocomplete_cache[cache_key] = results
    return [dict(item) for item in results]


def reverse_geocode_location(latitude: float, longitude: float) -> dict[str, Any]:
    cache_key = cache_key_for_coordinates(latitude, longitude)
    if cache_key in _reverse_cache:
        return dict(_reverse_cache[cache_key])

    properties: dict[str, Any] = {}
    address: dict[str, Any] = {}
    api_key = os.environ.get("ORS_API_KEY", "").strip()
    if api_key:
        try:
            response = requests.get(
                f"{ORS_GEOCODE_URL}/reverse",
                params={
                    "point.lat": float(latitude),
                    "point.lon": float(longitude),
                    "boundary.country": "USA",
                    "size": 1,
                },
                headers={"Authorization": api_key},
                timeout=15,
            )
            response.raise_for_status()
            features = response.json().get("features") or []
            if features:
                properties = features[0].get("properties") or {}
        except (requests.RequestException, ValueError, TypeError):
            properties = {}

    if not properties:
        try:
            response = _nominatim_get(
                "reverse",
                {
                    "format": "jsonv2",
                    "lat": float(latitude),
                    "lon": float(longitude),
                    "addressdetails": 1,
                },
            )
            address = response.json().get("address") or {}
        except (requests.RequestException, ValueError, TypeError):
            address = {}

    place = _format_us_place(address, properties) or "Unknown, US"
    result = {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "place": place,
        "timezone": timezone_for_coordinates(latitude, longitude),
    }
    _reverse_cache[cache_key] = result
    return dict(result)
