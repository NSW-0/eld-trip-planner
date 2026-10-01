# ELD Trip Planner

**Live application:** [https://nabeel-eld-trip-planner.vercel.app](https://nabeel-eld-trip-planner.vercel.app)

**Backend health:** [https://eld-trip-planner-nsw-0.vercel.app/api/health/](https://eld-trip-planner-nsw-0.vercel.app/api/health/)

ELD Trip Planner is a trip-planning app for property-carrying drivers. Its Django API and React interface plan routes, simulate FMCSA 70-hour / 8-day HOS schedules, and render daily driver logs.

## Current implementation status

The frontend submits trips to `POST /api/trips/plan` and displays the returned route, stops, summary, assumptions, and SVG daily logs. The backend prefers ORS HGV routing when `ORS_API_KEY` is configured; without it, the app uses Nominatim and OSRM and clearly marks the route as not truck-verified. The app is deployed on Vercel. The full live trip-plan flow, screenshots, and recorded Loom walkthrough still need final verification/completion.

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
- In local development, Vite proxies `/api` to Django. Production uses the Vercel backend URL shown below.
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

### Vercel deployment

The frontend and Django API are separate Vercel projects from the same public GitHub repository, both deploying from `main` on pushes. The backend runs as a Vercel serverless function, so its first request after inactivity may take about three seconds. Vercel's project dashboard is the source of truth for each deployment's `Ready` status.

**Live projects**

- Frontend project `nabeel-eld-trip-planner`: [https://nabeel-eld-trip-planner.vercel.app](https://nabeel-eld-trip-planner.vercel.app)
- Backend project `eld-trip-planner`: [https://eld-trip-planner-nsw-0.vercel.app](https://eld-trip-planner-nsw-0.vercel.app)
- API base URL: `https://eld-trip-planner-nsw-0.vercel.app/api`

**Project configuration**

- Frontend root directory: `frontend`; `frontend/vercel.json` sets the Vite build and `dist` output.
- Backend root directory: `backend`; import as a single project so Vercel does not detect the unrelated root `pyproject.toml` as another Python app.
- Frontend `VITE_API_BASE_URL`: `https://eld-trip-planner-nsw-0.vercel.app/api`.
- Backend `DJANGO_ALLOWED_HOSTS`: `.vercel.app`. Django also accepts the per-deployment `VERCEL_URL`; do not rely on `VERCEL_URL` alone for the stable production domain.
- Backend `CORS_ALLOWED_ORIGINS`: `https://nabeel-eld-trip-planner.vercel.app`.
- Backend secrets such as `DJANGO_SECRET_KEY` and `ORS_API_KEY` belong only in the Vercel backend project's environment settings. No secret values belong in this README or source control.
- Vercel Deployment Protection / Vercel Authentication is disabled on both projects so public visitors can access the app.

**Deployment gotchas**

- Use the actual domains shown in your Vercel dashboard; do not infer a domain from a project name.
- Django's `VERCEL_URL` is deployment-specific. The stable production hostname must also be allowed through `DJANGO_ALLOWED_HOSTS`.
- Disable Vercel Authentication on both public projects or visitors will be redirected to a Vercel login page.
- The serverless backend can cold-start; autocomplete's initial request may take around three seconds.
- Without `ORS_API_KEY`, OSRM fallback is used and marked not truck-verified.

Both Vercel projects deploy from `main`. After future pushes, check that each project's latest deployment is `Ready` and that Deployment Protection remains off for the public assessment links.

### Production checklist

- [x] Frontend and backend are publicly reachable over HTTPS.
- [x] Backend health endpoint returns `{"status":"ok"}`.
- [x] Production autocomplete returns HTTP 200 from the backend.
- [x] Cross-origin frontend-to-backend requests work with the configured CORS origin.
- [x] Secret environment values are configured in Vercel rather than committed to the repository.
- [x] Vercel Authentication is disabled on both public projects.
- [ ] Complete and verify a full live `Plan trip` request, including the returned schedule and log sheets.
- [ ] Capture submission screenshots and record the Loom walkthrough.

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
