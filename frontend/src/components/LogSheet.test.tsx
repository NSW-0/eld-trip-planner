import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import LogSheet, { type DailyLogDay } from './LogSheet'

const johnDoeDay: DailyLogDay = {
  date: '2026-10-01',
  from_place: 'Richmond, VA',
  to_place: 'Newark, NJ',
  total_miles_driving_today: 350,
  row_totals: { OFF: 10, SB: 1.75, D: 7.75, ON: 4.5 },
  total_hours: 24,
  on_duty_hours_today: 12.25,
  recap: { A: 55, B: 15, C: 42 },
  remarks: [
    '06:00 ON - Richmond, VA: Pre-trip inspection',
    '07:30 D - Richmond, VA: Drive',
    '19:00 ON - Newark, NJ: Dropoff',
  ],
  log_details: {
    driver_name: 'John Doe',
    co_driver: '',
    carrier_name: 'Sample Carrier LLC',
    main_office_address: '100 Main Street, Richmond, VA',
    home_terminal_address: '100 Main Street, Richmond, VA',
    truck_number: 'Truck 101',
    trailer_number: 'Trailer 202',
    shipping_document_number: 'Manifest 123',
    shipper_commodity: 'Paper products',
  },
  segments: [
    { status: 'OFF', start_minute: 0, end_minute: 360, miles: 0, place: 'Richmond, VA', note: 'Off duty' },
    { status: 'ON', start_minute: 360, end_minute: 450, miles: 0, place: 'Richmond, VA', note: 'Pre-trip inspection' },
    { status: 'D', start_minute: 450, end_minute: 540, miles: 70, place: 'Richmond, VA', note: 'Drive' },
    { status: 'ON', start_minute: 540, end_minute: 570, miles: 0, place: 'Richmond, VA', note: 'Fuel stop' },
    { status: 'D', start_minute: 570, end_minute: 720, miles: 110, place: 'Richmond, VA', note: 'Drive' },
    { status: 'OFF', start_minute: 720, end_minute: 780, miles: 0, place: 'Richmond, VA', note: '30-min break' },
    { status: 'D', start_minute: 780, end_minute: 900, miles: 80, place: 'Richmond, VA', note: 'Drive' },
    { status: 'ON', start_minute: 900, end_minute: 930, miles: 0, place: 'Richmond, VA', note: 'Fuel stop' },
    { status: 'D', start_minute: 930, end_minute: 960, miles: 20, place: 'Newark, NJ', note: 'Drive' },
    { status: 'SB', start_minute: 960, end_minute: 1065, miles: 0, place: 'Newark, NJ', note: '10-hr rest (sleeper)' },
    { status: 'D', start_minute: 1065, end_minute: 1140, miles: 70, place: 'Newark, NJ', note: 'Drive' },
    { status: 'ON', start_minute: 1140, end_minute: 1260, miles: 0, place: 'Newark, NJ', note: 'Dropoff' },
    { status: 'OFF', start_minute: 1260, end_minute: 1440, miles: 0, place: 'Newark, NJ', note: 'Off duty' },
  ],
}

describe('LogSheet', () => {
  it('renders the daily log header, duty grid, totals, and cycle recap', () => {
    render(<LogSheet day={johnDoeDay} />)

    expect(screen.getByRole('img', { name: /driver's daily log for 2026-10-01/i })).toBeInTheDocument()
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Richmond, VA')).toBeInTheDocument()
    expect(screen.getByText('Newark, NJ')).toBeInTheDocument()
    expect(screen.getAllByText('350')).toHaveLength(2)
    expect(screen.getByText('10.00')).toBeInTheDocument()
    expect(screen.getByText('1.75')).toBeInTheDocument()
    expect(screen.getByText('7.75')).toBeInTheDocument()
    expect(screen.getByText('4.50')).toBeInTheDocument()
    expect(screen.getByText('70 Hour / 8 Day')).toBeInTheDocument()
    expect(screen.getByText('15.00')).toBeInTheDocument()
    expect(screen.getByTestId('duty-line')).toHaveAttribute('d')
    expect(screen.getByText('Manifest 123')).toBeInTheDocument()
  })
})