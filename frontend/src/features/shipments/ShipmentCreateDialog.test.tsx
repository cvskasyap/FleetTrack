import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetApi } from '../../lib/api'
import type { ShipmentDetail, ShipmentOptions } from '../../lib/contracts'
import { ShipmentCreateDialog } from './ShipmentCreateDialog'

vi.mock('../../lib/api', () => ({
  fleetApi: {
    shipmentOptions: vi.fn(),
    createShipment: vi.fn(),
  },
}))

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

const createdShipment: ShipmentDetail = {
  shipment_id: 10,
  tracking_number: 'FT-TEST-10',
  customer_name: 'Synthetic Customer',
  route_name: 'Origin - Destination',
  status: 'booked',
  priority: 'standard',
  booked_at: '2026-01-01T10:00:00Z',
  expected_delivery_at: '2026-01-02T10:00:00Z',
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

function renderDialog() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ShipmentCreateDialog />
    </QueryClientProvider>,
  )
}

describe('shipment creation dialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fleetApi.shipmentOptions).mockResolvedValue(options)
    vi.mocked(fleetApi.createShipment).mockResolvedValue(createdShipment)
  })

  it('creates a booking using active reference options and closes on success', async () => {
    renderDialog()
    fireEvent.click(screen.getByRole('button', { name: /new shipment/i }))

    expect(await screen.findByText('Book a shipment')).toBeInTheDocument()
    expect(await screen.findByRole('option', { name: 'C-1 · Synthetic Customer' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'R-1 · Origin → Destination' })).toBeInTheDocument()
    await screen.findByLabelText('Customer')
    fireEvent.change(screen.getByLabelText('Customer'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Route'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('Weight (kg)'), { target: { value: '2.5' } })
    fireEvent.change(screen.getByLabelText('Shipping cost'), { target: { value: '15.75' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create booking' }))

    await waitFor(() => {
      expect(fleetApi.createShipment).toHaveBeenCalledWith(
        expect.objectContaining({
          customer_id: 1,
          route_id: 2,
          weight_kg: 2.5,
          shipping_cost: 15.75,
          priority: 'standard',
        }),
        expect.any(Object),
      )
    })
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })
})
