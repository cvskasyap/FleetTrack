import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ReportsPage } from './ReportsPage'

describe('reports page', () => {
  it('links to the authenticated shipment export and labels synthetic seed data', () => {
    render(<ReportsPage />)

    expect(screen.getByRole('link', { name: /download shipment csv/i })).toHaveAttribute(
      'href',
      '/api/v1/reports/shipments.csv',
    )
    expect(screen.getByText(/seeded project records are synthetic/i)).toBeInTheDocument()
  })
})
