import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


def test_geocode_autocomplete_returns_suggestions(api_client):
    response = api_client.get(reverse("geocode_autocomplete"), {"q": "Chicago"})

    assert response.status_code == 200
    payload = response.json()
    assert "suggestions" in payload
    assert payload["suggestions"]
    assert any(
        "Chicago" in suggestion["label"] for suggestion in payload["suggestions"]
    )


def test_plan_endpoint_accepts_valid_trip_and_returns_shapes(api_client):
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
