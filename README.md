# ELD Trip Planner

ELD Trip Planner is a full-stack trip planning and hours-of-service tool for property-carrying drivers. It accepts a trip start, current cycle usage, and pickup/dropoff locations, then generates a route, duty timeline, and daily log-sheet breakdown aligned to the FMCSA 70-hour / 8-day schedule.

## What the app does

- accepts current location, pickup, dropoff, cycle used, and start datetime
- builds a truck route using the backend route planner
- simulates duty events including driving, rest, inspection, fueling, and pickup/dropoff
- validates the timeline against the HOS rules in-scope for the project
- splits trip data into daily log sheets and totals
- displays the route on a map and summarizes trip metrics in the React UI
- provides searchable location fields, separate start date/time inputs, and a numeric cycle-hours field

The frontend uses a warm ivory, cobalt blue, and pink palette. Map stop colors are identified by the legend, and the page header scrolls with the document rather than staying fixed.

## Stack

- Backend: Django, Django REST Framework, Python 3.12+
- Frontend: React + Vite + TypeScript
- Routing and geocoding: OpenRouteService
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
```

Frontend example:

```env
VITE_API_BASE_URL=/api
```

Important notes:

- `ORS_API_KEY` must remain on the backend only.
- never expose the API key in browser code or frontend source control.
- CORS must allow the deployed frontend origin in production.

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
npm test -- --run
npm run build
```

The project was verified locally with the following results:

- backend pytest: 15 passed
- frontend Vitest: 1 test passed
- frontend build: successful Vite production build
- live smoke test: Django health and trip-plan endpoint both returned HTTP 200 with valid sample payloads

## Deployment guidance

### Frontend deployment (Vercel)

1. import the `frontend` directory into Vercel
2. set the build command to `npm run build`
3. set the output directory to `dist`
4. set the environment variable
   - `VITE_API_BASE_URL` to the deployed backend base URL, or keep `/api` if the backend is hosted under the same origin

### Backend deployment

Deploy the Django app to a host that keeps the service warm, such as Render, Railway, Fly.io, or an equivalent managed platform.

Required backend environment variables:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS=your-host-name`
- `CORS_ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app`
- `ORS_API_KEY=...`

### Production checklist

- backend is reachable over HTTPS
- frontend CORS allows the production frontend origin
- API keys are server-side only
- the deployed app returns a valid route and stop timeline for a sample trip
- the health endpoint responds and does not sleep before first request

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
