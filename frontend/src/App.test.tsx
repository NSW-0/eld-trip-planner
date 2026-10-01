import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('App', () => {
  it('renders the trip planning form and core sections', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: /ELD Trip Planner/i }),
    ).toBeInTheDocument()
    expect(screen.getByLabelText(/Current location/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Pickup location/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Dropoff location/i)).toBeInTheDocument()
    expect(screen.getByText(/Trip summary/i)).toBeInTheDocument()
  })

  it('submits trip inputs and renders the returned summary', async () => {
    const plannedTrip = {
      route: {
        geometry: [
          [41.88, -87.63],
          [38.62, -90.2],
          [32.78, -96.8],
        ],
        legs: [],
        total_miles: 123.4,
        total_hours: 3,
        provider: 'ors',
      },
      stops: [
        {
          type: 'start',
          lat: 41.88,
          lng: -87.63,
          place: 'Chicago, IL',
          arrival: '2026-10-05T08:00:00',
          departure: '2026-10-05T08:00:00',
          duration_hours: 0,
          note: 'Trip start',
        },
        {
          type: 'pickup',
          lat: 38.62,
          lng: -90.2,
          place: 'St. Louis, MO',
          arrival: '2026-10-05T10:00:00',
          departure: '2026-10-05T11:00:00',
          duration_hours: 1,
          note: 'Pickup',
        },
        {
          type: 'dropoff',
          lat: 32.78,
          lng: -96.8,
          place: 'Dallas, TX',
          arrival: '2026-10-05T14:45:00',
          departure: '2026-10-05T15:45:00',
          duration_hours: 1,
          note: 'Dropoff',
        },
      ],
      summary: {
        total_miles: 123.4,
        total_driving_hours: 3,
        total_trip_duration_hours: 7.75,
        arrival_time: '2026-10-05T14:45:00',
        trip_days: 1,
        cycle_hours_remaining: 60,
      },
      days: [],
      assumptions: { home_terminal_timezone: 'America/Chicago' },
      warnings: [],
    }
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => ({
      ok: true,
      json: async () => (init?.method === 'POST' ? plannedTrip : { suggestions: [] }),
    }))
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    fireEvent.change(screen.getByLabelText(/Start date/i), {
      target: { value: '2026-10-05' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Plan trip/i }))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/trips/plan',
        expect.objectContaining({ method: 'POST' }),
      ),
    )
    await waitFor(() =>
      expect(screen.getByText('123.4')).toBeInTheDocument(),
    )

    const planRequest = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(JSON.parse(String(planRequest?.[1]?.body))).toMatchObject({
      current_location: 'Chicago, IL',
      pickup_location: 'St. Louis, MO',
      dropoff_location: 'Dallas, TX',
      current_cycle_used_hours: 12,
      start_datetime: '2026-10-05T08:00:00',
    })
  })
})