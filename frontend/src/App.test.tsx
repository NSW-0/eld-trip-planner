import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

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
})