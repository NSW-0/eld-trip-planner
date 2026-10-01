import pytest
from trips.services.geocoding import cache_key_for_coordinates, format_city_state
from trips.services.routing import build_route_data, normalize_route_payload


def test_normalize_route_payload_uses_leg_distances_and_geometry():
    payload = {
        "routes": [
            {
                "summary": {"distance": 2500.0, "duration": 3600.0},
                "segments": [
                    {
                        "distance": 1200.0,
                        "duration": 1800.0,
                        "geometry": [[0, 0], [1, 1]],
                    },
                    {
                        "distance": 1300.0,
                        "duration": 1800.0,
                        "geometry": [[1, 1], [2, 2]],
                    },
                ],
            }
        ],
        "features": [{"geometry": {"coordinates": [[0, 0], [1, 1], [2, 2]]}}],
    }

    route = normalize_route_payload(payload)

    assert route["total_miles"] == pytest.approx(1.553, rel=1e-3)
    assert len(route["legs"]) == 2
    assert route["legs"][0]["distance_miles"] == pytest.approx(1200 / 1609.344)
    assert route["legs"][1]["distance_miles"] == pytest.approx(1300 / 1609.344)


def test_normalize_ors_geojson_converts_meters_and_coordinates():
    payload = {
        "features": [
            {
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-87.0, 41.0], [-90.0, 38.0], [-96.0, 32.0]],
                },
                "properties": {
                    "summary": {"distance": 160934.4, "duration": 7200},
                    "segments": [
                        {"distance": 80467.2, "duration": 3600},
                        {"distance": 80467.2, "duration": 3600},
                    ],
                },
            }
        ]
    }

    route = normalize_route_payload(payload)

    assert route["total_miles"] == pytest.approx(100.0)
    assert route["total_hours"] == pytest.approx(2.0)
    assert [leg["distance_miles"] for leg in route["legs"]] == pytest.approx(
        [50.0, 50.0]
    )
    assert route["geometry"] == [(41.0, -87.0), (38.0, -90.0), (32.0, -96.0)]


def test_build_route_data_uses_leg_geometry_and_average_speed():
    route = build_route_data(
        points=[(40.7128, -74.0060), (41.8781, -87.6298), (32.7767, -96.7970)],
        legs=[
            {
                "distance_miles": 100.0,
                "duration_hours": 2.0,
                "geometry": [(0, 0), (1, 1)],
            },
            {
                "distance_miles": 200.0,
                "duration_hours": 4.0,
                "geometry": [(1, 1), (2, 2)],
            },
        ],
    )

    assert route["total_miles"] == pytest.approx(300.0)
    assert route["legs"][0]["average_speed_mph"] == pytest.approx(50.0)
    assert route["legs"][1]["average_speed_mph"] == pytest.approx(50.0)
    assert len(route["geometry"]) == 3


def test_stop_placement_scales_geometry_to_reported_route_distance():
    from trips.services.routing import place_stop_on_route

    point = place_stop_on_route(
        [(0.0, 0.0), (0.0, 2.0)],
        target_distance_miles=50.0,
        total_route_miles=100.0,
    )

    assert point == pytest.approx((0.0, 1.0), abs=0.01)


def test_geocoding_helpers_round_and_format_coordinates():
    assert cache_key_for_coordinates(41.8781, -87.6298) == (41.878, -87.63)
    assert format_city_state("Chicago", "IL") == "Chicago, IL"


def test_route_provider_uses_ors_truck_profile_when_key_is_configured(monkeypatch):
    from trips.services.routing import get_route_directions

    monkeypatch.setenv("ORS_API_KEY", "test-ors-key")
    response_payload = {
        "features": [
            {
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-87.0, 41.0], [-90.0, 38.0]],
                },
                "properties": {
                    "summary": {"distance": 160934.4, "duration": 7200},
                    "segments": [{"distance": 160934.4, "duration": 7200}],
                },
            }
        ]
    }
    request_args = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return response_payload

    def fake_post(url, **kwargs):
        request_args["url"] = url
        request_args.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("trips.services.routing.requests.post", fake_post)

    route = get_route_directions([(41.0, -87.0), (38.0, -90.0)])

    assert request_args["url"].endswith("/driving-hgv/geojson")
    assert request_args["headers"]["Authorization"] == "test-ors-key"
    assert request_args["json"]["coordinates"] == [[-87.0, 41.0], [-90.0, 38.0]]
    assert route["provider"] == "ors"
    assert route["total_miles"] == pytest.approx(100.0)
    assert route["warnings"] == []


def test_route_provider_falls_back_to_osrm_with_warning(monkeypatch):
    from trips.services.routing import get_route_directions

    monkeypatch.delenv("ORS_API_KEY", raising=False)
    response_payload = {
        "routes": [
            {
                "distance": 160934.4,
                "duration": 7200,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-87.0, 41.0], [-90.0, 38.0]],
                },
                "legs": [{"distance": 160934.4, "duration": 7200}],
            }
        ]
    }
    request_args = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return response_payload

    def fake_get(url, **kwargs):
        request_args["url"] = url
        request_args.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("trips.services.routing.requests.get", fake_get)

    route = get_route_directions([(41.0, -87.0), (38.0, -90.0)])

    assert "/route/v1/driving/" in request_args["url"]
    assert route["provider"] == "osrm"
    assert route["total_miles"] == pytest.approx(100.0)
    assert any("not truck-verified" in warning for warning in route["warnings"])


def test_location_search_uses_ors_and_limits_results_to_the_us(monkeypatch):
    from trips.services.geocoding import search_location

    monkeypatch.setenv("ORS_API_KEY", "test-ors-key")
    request_args = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "features": [
                    {
                        "geometry": {"coordinates": [-87.63, 41.88]},
                        "properties": {
                            "label": "Chicago, Illinois, USA",
                            "locality": "Chicago",
                            "region": "Illinois",
                            "region_a": "IL",
                        },
                    }
                ]
            }

    def fake_get(url, **kwargs):
        request_args["url"] = url
        request_args.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("trips.services.geocoding.requests.get", fake_get)

    location = search_location("Chicago, IL")

    assert request_args["url"].endswith("/geocode/search")
    assert request_args["headers"]["Authorization"] == "test-ors-key"
    assert request_args["params"]["boundary.country"] == "USA"
    assert location == {
        "latitude": 41.88,
        "longitude": -87.63,
        "place": "Chicago, IL",
    }


def test_autocomplete_uses_us_nominatim_fallback_and_custom_user_agent(monkeypatch):
    from trips.services.geocoding import autocomplete_locations

    monkeypatch.delenv("ORS_API_KEY", raising=False)
    request_args = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {
                    "lat": "41.88",
                    "lon": "-87.63",
                    "display_name": "Chicago, Cook County, Illinois, United States",
                    "address": {
                        "city": "Chicago",
                        "state": "Illinois",
                        "ISO3166-2-lvl4": "US-IL",
                    },
                }
            ]

    def fake_get(url, **kwargs):
        request_args["url"] = url
        request_args.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("trips.services.geocoding.requests.get", fake_get)

    suggestions = autocomplete_locations("Chicago")

    assert request_args["url"].endswith("/search")
    assert request_args["params"]["countrycodes"] == "us"
    assert request_args["headers"]["User-Agent"].startswith("ELDTripPlanner/")
    assert suggestions[0]["label"] == "Chicago, IL"
    assert suggestions[0]["latitude"] == pytest.approx(41.88)


def test_reverse_geocoding_caches_rounded_coordinates(monkeypatch):
    from trips.services.geocoding import reverse_geocode_location

    monkeypatch.delenv("ORS_API_KEY", raising=False)
    requests_made = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "address": {
                    "city": "Chicago",
                    "state": "Illinois",
                    "ISO3166-2-lvl4": "US-IL",
                }
            }

    def fake_get(url, **kwargs):
        requests_made.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("trips.services.geocoding.requests.get", fake_get)

    first = reverse_geocode_location(41.8781, -87.6298)
    second = reverse_geocode_location(41.8782, -87.6299)

    assert first["place"] == "Chicago, IL"
    assert second["place"] == "Chicago, IL"
    assert len(requests_made) == 1
    assert requests_made[0][1]["headers"]["User-Agent"].startswith("ELDTripPlanner/")
