from datetime import datetime

from rest_framework.decorators import api_view
from rest_framework.response import Response

from trips.services.planner import autocomplete_suggestions, build_trip_plan
from trips.services.validator import validate_timeline


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def geocode_autocomplete(request):
    query = request.query_params.get("q", "")
    return Response({"suggestions": autocomplete_suggestions(query)})


@api_view(["POST"])
def trip_plan(request):
    payload = request.data or {}
    if not isinstance(payload, dict):
        return Response(
            {"error": "Trip request payload must be a JSON object."},
            status=400,
        )

    try:
        start_datetime = payload.get("start_datetime")
        if not start_datetime:
            raise ValueError("Start datetime is required.")
        datetime.fromisoformat(str(start_datetime))
    except ValueError:
        return Response({"error": "Start datetime is invalid."}, status=400)

    try:
        plan = build_trip_plan(payload)
    except ValueError as exc:
        message = str(exc)
        if "cycle" in message.lower():
            return Response({"error": message}, status=400)
        if "location" in message.lower():
            return Response({"error": message}, status=400)
        return Response({"error": message}, status=400)

    if not validate_timeline(plan["timeline"]):
        return Response(
            {"error": "Generated timeline violates the HOS rules."},
            status=400,
        )

    return Response(plan)
