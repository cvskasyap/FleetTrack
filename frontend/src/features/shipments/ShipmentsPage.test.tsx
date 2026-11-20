import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetApi } from '../../lib/api'
import { ShipmentsPage } from './ShipmentsPage'

vi.mock('../../lib/api', () => ({
  fleetApi: {
    shipments: vi.fn(),
    shipmentOptions: vi.fn(),
    createShipment: vi.fn(),
  },
}))

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ShipmentsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('shipment register', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fleetApi.shipments).mockResolvedValue({
      total: 1,
      limit: 50,
      offset: 0,
      items: [{
        shipment_id: 1306,
        tracking_number: 'FT-TEST-1306',
        customer_name: 'Synthetic Customer',
        route_name: 'Origin - Destination',
        status: 'in_transit',
        priority: 'standard',
        booked_at: '2026-11-01T10:00:00Z',
        expected_delivery_at: '2026-11-03T10:00:00Z',
        delivered_at: null,
        on_time: null,
        transit_hours: null,
      }],
    })
  })

  it('renders the shipment record and links to its detail page', async () => {
    renderPage()

    expect(await screen.findByRole('link', { name: 'FT-TEST-1306' })).toHaveAttribute(
      'href',
      '/operations/1306',
    )
    expect(screen.getByText('Synthetic Customer')).toBeInTheDocument()
    expect(screen.getByText('Origin - Destination')).toBeInTheDocument()
  })
})
