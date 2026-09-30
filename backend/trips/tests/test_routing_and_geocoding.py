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
    assert route["legs"][0]["distance_miles"] == pytest.approx(1200.0)
    assert route["legs"][1]["distance_miles"] == pytest.approx(1300.0)


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


def test_geocoding_helpers_round_and_format_coordinates():
    assert cache_key_for_coordinates(41.8781, -87.6298) == (41.878, -87.63)
    assert format_city_state("Chicago", "IL") == "Chicago, IL"
