# ELD Trip Planner

ELD Trip Planner is a trip-planning app for property-carrying drivers. Its Django API and React interface plan routes, simulate FMCSA 70-hour / 8-day HOS schedules, and render daily driver logs.

## Current implementation status

The frontend submits trips to `POST /api/trips/plan` and displays the returned route, stops, summary, assumptions, and SVG daily logs. The backend prefers ORS HGV routing when `ORS_API_KEY` is configured; without it, the app uses Nominatim and OSRM and clearly marks the route as not truck-verified. The code is validated locally, but production hosting, screenshots, and the recorded Loom walkthrough remain outstanding.

## What the app does

- accepts searchable US locations, current cycle hours, start date/time, and log-sheet details
- builds a truck route, simulates and validates HOS duty, and creates stops and daily log data
- displays the returned route, stops, summary, warnings, assumptions, and daily SVG log sheets

The frontend uses a warm ivory, cobalt blue, and pink palette. Map stop colors are identified by the legend, and the page header scrolls with the document rather than staying fixed.

## Stack

- Backend: Django, Django REST Framework, Python 3.12+
- Frontend: React + Vite + TypeScript
- Routing and geocoding: OpenRouteService with Nominatim/OSRM fallback
- Mapping: Leaflet + OpenStreetMap
- Testing: pytest + Vitest
- Linting: Ruff + ESLint

## Repository layout

```text
/backend
  config/
  trips/
    services/
    tests/
/frontend
  src/
/docs
CLAUDE.md
README.md
plan.md
```

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 22+
- Git

### Install backend dependencies

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Install frontend dependencies

```powershell
cd frontend
npm install
```

### Run the app locally

Start the backend in one terminal:

```powershell
cd backend
.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev -- --host 0.0.0.0
```

The frontend is expected to run at `http://localhost:5173` and proxy API traffic to the Django backend at `http://localhost:8000`.

## Environment variables

Copy the example files and set real values for your environment.

Backend example:

```env
DJANGO_SECRET_KEY=replace-with-a-secret
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
ORS_API_KEY=
NOMINATIM_USER_AGENT=ELDTripPlanner/1.0 (HOS trip planning)
```

Frontend example:

```env
VITE_API_BASE_URL=/api
```

Important notes:

- `ORS_API_KEY` must remain on the backend only.
- `ORS_API_KEY` enables truck-verified ORS routing; without it, OSRM fallback is used and marked not truck-verified.
- `NOMINATIM_USER_AGENT` identifies the app to Nominatim; fallback requests are rate-limited to one per second.
- never expose the API key in browser code or frontend source control.
- CORS must allow the deployed frontend origin in production.
- In local development, Vite proxies `/api` to Django. For production, set `VITE_API_BASE_URL` to the deployed backend API base URL, such as `https://api.example.com/api`.
- Django reads environment variables from the process or host configuration; `.env.example` is a reference and is not auto-loaded.

## API endpoints

The app exposes these backend endpoints:

- `GET /api/health/` — health check
- `GET /api/geocode/autocomplete?q=...` — address suggestion proxy
- `POST /api/trips/plan` — build a trip plan, route, timeline, and daily logs

## Validation and checks

Run the backend checks:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\ruff.exe check .
.venv\Scripts\ruff.exe format --check .
```

Run the frontend checks:

```powershell
cd frontend
npm run lint
npm test -- --run
npm run build
```

The project was verified locally with the following results:

- backend pytest: 37 passed
- backend Ruff lint and format checks: passed
- frontend ESLint: passed
- frontend Vitest: 3 tests passed, including the trip submission and John Doe log-sheet fixture
- frontend build: successful Vite production build
- live browser smoke test: trip request completed through the Django API using OSRM fallback; route, stop schedule, map, and two log sheets rendered

## Deployment guidance

### Deploy frontend and backend on Vercel

Vercel supports this Django backend as a serverless function. This avoids a separate paid always-on service, but the backend may cold-start after inactivity and is subject to Vercel plan/function limits. Test the deployed API against the assessment trips before submission.

Create two Vercel projects from this GitHub repository:

1. Frontend project: set the project root to `frontend`. The checked-in `frontend/vercel.json` configures the Vite build and `dist` output.
2. Backend project: set the project root to `backend`. Vercel detects `manage.py` and the Django WSGI application.
3. Deploy the backend first. In its Vercel project settings, add `DJANGO_SECRET_KEY` (generate a new random value), `DJANGO_DEBUG=false`, `CORS_ALLOWED_ORIGINS` (the exact frontend origin), and `NOMINATIM_USER_AGENT=ELDTripPlanner/1.0 (HOS trip planning)`. Add `ORS_API_KEY` privately if available.
4. Django adds Vercel's `VERCEL_URL` hostname to `ALLOWED_HOSTS`. If you attach a custom backend domain, add that host to `DJANGO_ALLOWED_HOSTS` too.
5. Set frontend `VITE_API_BASE_URL` to the backend URL ending in `/api`, for example `https://eld-trip-planner-api.vercel.app/api`, then redeploy the frontend.

Keep `ORS_API_KEY` only in backend environment settings. Without it, routing uses OSRM and the UI marks the route as not truck-verified. Do not paste secrets into chat, README files, or source control.

### Production checklist

- Vercel frontend and backend projects have not yet been created from the account dashboard
- backend is reachable over HTTPS
- frontend CORS allows the production frontend origin
- API keys are server-side only
- the deployed app returns a valid route and stop timeline for a sample trip
- the health endpoint and plan endpoint respond after a cold start
- capture submission screenshots and record the Loom walkthrough

## Assumptions used by the planner

The app follows the project brief defaults:

- trip starts at a user-selected date/time, defaulting to today at 08:00
- home-terminal time zone follows the current location time zone
- prior cycle hours are treated as being on day -1 and remain in the rolling window until they age out
- a 34-hour restart is inserted when the 70-hour cycle is exhausted
- fueling occurs every 1,000 miles and counts as 30 minutes ON duty
- pickup and dropoff each count as 1 hour ON duty
- pre-trip and post-trip inspections each count as 15 minutes ON duty
- all duty boundaries fall on 15-minute marks

## Loom / walkthrough outline

The final project walkthrough should cover:

1. what the app is and why it exists
2. the trip-planning form and assumptions panel
3. how the backend builds the route and validates the HOS timeline
4. how daily log sheets are split and explained
5. how the map and summary components display the route and stop schedule
6. the deployment environment and the production-only API-key setup

## Notes

- This implementation follows the project brief and the in-scope FMCSA rules documented in the project files.
- Out-of-scope exceptions such as adverse driving conditions, short-haul exemptions, and split sleeper berth options are intentionally not implemented.
- The app is designed to prioritize HOS correctness and a clean user experience while keeping deployment simple and production-safe.
