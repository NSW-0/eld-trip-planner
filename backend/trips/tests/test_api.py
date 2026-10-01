from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


def _install_fake_trip_providers(monkeypatch):
    locations = {
        "Chicago, IL": {
            "latitude": 41.88,
            "longitude": -87.63,
            "place": "Chicago, IL",
        },
        "St. Louis, MO": {
            "latitude": 38.62,
            "longitude": -90.2,
            "place": "St. Louis, MO",
        },
        "Dallas, TX": {
            "latitude": 32.78,
            "longitude": -96.8,
            "place": "Dallas, TX",
        },
    }
    route = {
        "provider": "ors",
        "warnings": [],
        "total_miles": 100.0,
        "total_hours": 2.0,
        "geometry": [
            (41.88, -87.63),
            (40.0, -89.0),
            (38.62, -90.2),
            (35.0, -94.0),
            (32.78, -96.8),
        ],
        "legs": [
            {"distance_miles": 40.0, "duration_hours": 0.75, "geometry": []},
            {"distance_miles": 60.0, "duration_hours": 1.25, "geometry": []},
        ],
    }
    monkeypatch.setattr(
        "trips.services.planner.search_location", lambda value: locations[value]
    )
    monkeypatch.setattr(
        "trips.services.planner.get_route_directions", lambda points: route
    )


def test_geocode_autocomplete_returns_suggestions(api_client, monkeypatch):
    monkeypatch.setattr(
        "trips.views.autocomplete_suggestions",
        lambda query: [
            {"label": "Chicago, IL", "latitude": 41.88, "longitude": -87.63}
        ],
    )
    response = api_client.get(reverse("geocode_autocomplete"), {"q": "Chicago"})

    assert response.status_code == 200
    payload = response.json()
    assert "suggestions" in payload
    assert payload["suggestions"]
    assert any(
        "Chicago" in suggestion["label"] for suggestion in payload["suggestions"]
    )


def test_plan_endpoint_accepts_valid_trip_and_returns_shapes(api_client, monkeypatch):
    _install_fake_trip_providers(monkeypatch)
    payload = {
        "current_location": "Chicago, IL",
        "pickup_location": "St. Louis, MO",
        "dropoff_location": "Dallas, TX",
        "current_cycle_used_hours": 12,
        "start_datetime": "2026-10-05T08:00:00",
        "log_details": {"carrier_name": "Sample Carrier LLC"},
    }

    response = api_client.post(reverse("trip_plan"), payload, format="json")

    assert response.status_code == 200
    data = response.json()
    assert "route" in data
    assert "timeline" in data
    assert "summary" in data
    assert "assumptions" in data
    assert "days" in data
    assert "stops" in data
    assert data["route"]["total_miles"] > 0
    assert data["summary"]["trip_days"] >= 1
    assert data["days"][0]["recap"]["A"] == pytest.approx(16.5)


def test_plan_endpoint_rejects_invalid_cycle_hours(api_client):
    payload = {
        "current_location": "Chicago, IL",
        "pickup_location": "St. Louis, MO",
        "dropoff_location": "Dallas, TX",
        "current_cycle_used_hours": 71,
        "start_datetime": "2026-10-05T08:00:00",
    }

    response = api_client.post(reverse("trip_plan"), payload, format="json")

    assert response.status_code == 400
    assert "cycle" in response.json()["error"].lower()


def test_plan_endpoint_rejects_bad_datetime(api_client):
    payload = {
        "current_location": "Chicago, IL",
        "pickup_location": "St. Louis, MO",
        "dropoff_location": "Dallas, TX",
        "current_cycle_used_hours": 12,
        "start_datetime": "not-a-date",
    }

    response = api_client.post(reverse("trip_plan"), payload, format="json")

    assert response.status_code == 400
    assert "datetime" in response.json()["error"].lower()


@patch("trips.views.build_trip_plan")
def test_plan_endpoint_validates_driving_against_prior_cycle_hours(
    build_trip_plan, api_client
):
    build_trip_plan.return_value = {
        "timeline": [
            {
                "status": "D",
                "start": "2026-10-05T08:00:00",
                "end": "2026-10-05T09:00:00",
                "miles": 55,
            }
        ]
    }
    payload = {
        "current_location": "Chicago, IL",
        "pickup_location": "St. Louis, MO",
        "dropoff_location": "Dallas, TX",
        "current_cycle_used_hours": 69.5,
        "start_datetime": "2026-10-05T08:00:00",
    }

    response = api_client.post(reverse("trip_plan"), payload, format="json")

    assert response.status_code == 400


def test_planner_uses_provider_route_and_timeline_derived_daily_totals(monkeypatch):
    from trips.services import planner

    locations = {
        "Chicago, IL": {
            "latitude": 41.88,
            "longitude": -87.63,
            "place": "Chicago, IL",
        },
        "St. Louis, MO": {
            "latitude": 38.62,
            "longitude": -90.2,
            "place": "St. Louis, MO",
        },
        "Dallas, TX": {
            "latitude": 32.78,
            "longitude": -96.8,
            "place": "Dallas, TX",
        },
    }
    route_geometry = [
        (41.88, -87.63),
        (40.0, -89.0),
        (38.62, -90.2),
        (35.0, -94.0),
        (32.78, -96.8),
    ]
    route_data = {
        "provider": "ors",
        "warnings": [],
        "total_miles": 100.0,
        "total_hours": 2.0,
        "geometry": route_geometry,
        "legs": [
            {"distance_miles": 40.0, "duration_hours": 0.75, "geometry": []},
            {"distance_miles": 60.0, "duration_hours": 1.25, "geometry": []},
        ],
    }
    monkeypatch.setattr(
        planner, "search_location", lambda location: locations[location], raising=False
    )
    monkeypatch.setattr(
        planner,
        "get_route_directions",
        lambda points: route_data,
        raising=False,
    )

    plan = planner.build_trip_plan(
        {
            "current_location": "Chicago, IL",
            "pickup_location": "St. Louis, MO",
            "dropoff_location": "Dallas, TX",
            "current_cycle_used_hours": 0,
            "start_datetime": "2026-10-05T08:00:00",
        }
    )

    assert plan["route"]["total_miles"] == pytest.approx(100.0)
    assert plan["route"]["geometry"] == route_geometry
    assert plan["summary"]["total_driving_hours"] == pytest.approx(2.0)
    assert plan["days"][0]["row_totals"]["D"] == pytest.approx(2.0)
    assert plan["days"][0]["total_hours"] == pytest.approx(24.0)
