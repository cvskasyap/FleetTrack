import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetApi } from '../../lib/api'
import type { ShipmentDetail, ShipmentOptions, ShipmentTracking } from '../../lib/contracts'
import { ShipmentDetailPage } from './ShipmentDetailPage'

vi.mock('../../lib/api', () => ({
  fleetApi: {
    shipment: vi.fn(),
    shipmentOptions: vi.fn(),
    tracking: vi.fn(),
    updateShipment: vi.fn(),
    addShipmentStatusEvent: vi.fn(),
    addDeliveryAttempt: vi.fn(),
    cancelShipment: vi.fn(),
  },
}))

const shipment: ShipmentDetail = {
  shipment_id: 9,
  tracking_number: 'FT-TEST-9',
  customer_name: 'Synthetic Customer',
  route_name: 'Origin - Destination',
  status: 'booked',
  priority: 'standard',
  booked_at: '2026-01-01T10:00:00Z',
  expected_delivery_at: '2026-01-03T10:00:00Z',
  delivered_at: null,
  on_time: null,
  transit_hours: null,
  customer_id: 1,
  customer_code: 'C-1',
  route_id: 2,
  origin_hub: 'Origin',
  destination_hub: 'Destination',
  assigned_driver_id: null,
  driver_code: null,
  driver_name: null,
  assigned_vehicle_id: null,
  registration_no: null,
  weight_kg: 2,
  shipping_cost: 12,
  notes: null,
}

const options: ShipmentOptions = {
  customers: [{ customer_id: 1, customer_code: 'C-1', full_name: 'Synthetic Customer' }],
  routes: [{
    route_id: 2,
    route_code: 'R-1',
    route_name: 'Origin - Destination',
    origin_hub: 'Origin',
    destination_hub: 'Destination',
  }],
  drivers: [],
  vehicles: [],
  hubs: [],
}

const tracking: ShipmentTracking = {
  shipment_id: shipment.shipment_id,
  tracking_number: shipment.tracking_number,
  relational_events: [],
  mongo_events: [],
  delivery_attempts: [],
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/operations/9']}>
        <Routes>
          <Route path="/operations/:shipmentId" element={<ShipmentDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('shipment detail operations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fleetApi.shipment).mockResolvedValue(shipment)
    vi.mocked(fleetApi.shipmentOptions).mockResolvedValue(options)
    vi.mocked(fleetApi.tracking).mockResolvedValue(tracking)
    vi.mocked(fleetApi.addShipmentStatusEvent).mockResolvedValue(shipment)
  })

  it('records an operational event from the detail workspace', async () => {
    renderPage()

    expect(await screen.findByRole('heading', { name: 'FT-TEST-9' })).toBeInTheDocument()
    expect(await screen.findByRole('option', { name: 'C-1 · Synthetic Customer' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'R-1 · Origin → Destination' })).toBeInTheDocument()
    expect(screen.getByLabelText('Weight (kg)')).toHaveValue(2)
    expect(screen.queryByText('Reference options unavailable')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Event notes'), {
      target: { value: 'Departed origin hub' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Record event' }))

    await waitFor(() => {
      expect(fleetApi.addShipmentStatusEvent).toHaveBeenCalledWith(9, {
        status: 'picked_up',
        hub_id: null,
        notes: 'Departed origin hub',
      })
    })
  })
})
