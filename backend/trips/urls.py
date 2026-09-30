from django.urls import path

from trips.views import geocode_autocomplete, health, trip_plan

urlpatterns = [
    path("health/", health, name="health"),
    path("geocode/autocomplete", geocode_autocomplete, name="geocode_autocomplete"),
    path("trips/plan", trip_plan, name="trip_plan"),
]
