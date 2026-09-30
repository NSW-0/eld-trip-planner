# ELD Trip Planner

A Django REST Framework backend and React/Vite frontend for planning commercial trips with hours-of-service schedules and daily logs.

## Requirements

- Python 3.12 or newer
- Node.js 22 or newer

## Run locally

In PowerShell, install the backend once:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

Start Django in one terminal:

```powershell
backend/.venv/Scripts/python.exe backend/manage.py runserver
```

Start the frontend in another terminal:

```powershell
npm ci --prefix frontend
npm run dev --prefix frontend
```

The Vite development server proxies `/api` requests to Django at `http://127.0.0.1:8000`. The health endpoint is available at `/api/health/`.

For local configuration, set environment variables in the backend process environment. See `backend/.env.example` for the supported names; the example file is a reference and is not automatically loaded. Never put real API keys in the frontend.

## Checks

```powershell
npm run lint --prefix frontend
npm run test --prefix frontend
npm run build --prefix frontend
backend/.venv/Scripts/ruff.exe check backend
backend/.venv/Scripts/ruff.exe format --check backend
backend/.venv/Scripts/python.exe -m pytest
```

Frontend and backend checks also run in separate GitHub Actions workflows.
