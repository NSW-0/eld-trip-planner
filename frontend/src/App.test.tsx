import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the trip planning workspace', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'Trip planning workspace' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent(
      'Planning tools are being set up.',
    )
  })
})