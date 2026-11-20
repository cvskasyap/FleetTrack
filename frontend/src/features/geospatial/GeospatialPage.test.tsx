import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetApi } from '../../lib/api'
import type { GeospatialNetwork } from '../../lib/contracts'
import { GeospatialPage } from './GeospatialPage'

vi.mock('../../lib/api', () => ({
  fleetApi: {
    geospatialNetwork: vi.fn(),
  },
}))

const network: GeospatialNetwork = {
  hubs: [
    {
      hub_id: 1,
      hub_code: 'H-1',
      hub_name: 'North Hub',
      city: 'North City',
      state: 'North State',
      latitude: null,
      longitude: null,
      coordinate_status: 'missing',
      shipments_handled: 4,
      delivered_shipments: 2,
      in_progress_shipments: 2,
      scan_count: 8,
      on_time_pct: 50,
    },
    {
      hub_id: 2,
      hub_code: 'H-2',
      hub_name: 'South Hub',
      city: 'South City',
      state: 'South State',
      latitude: null,
      longitude: null,
      coordinate_status: 'missing',
      shipments_handled: 3,
      delivered_shipments: 1,
      in_progress_shipments: 2,
      scan_count: 5,
      on_time_pct: null,
    },
  ],
  routes: [
    {
      route_id: 1,
      route_code: 'R-1',
      route_name: 'North - South',
      origin: { hub_name: 'North Hub', city: 'North City', state: 'North State' },
      destination: { hub_name: 'South Hub', city: 'South City', state: 'South State' },
      distance_km: 450.5,
      route_geometry: null,
      geometry_status: 'missing',
      shipment_count: 5,
      delivered_shipments: 3,
      in_progress_shipments: 2,
      on_time_pct: 66.67,
      average_transit_hours: 42.5,
    },
  ],
  data_quality: {
    total_hubs: 2,
    hubs_with_verified_coordinates: 0,
    hubs_missing_coordinates: 2,
    hubs_with_invalid_coordinates: 0,
    total_routes: 1,
    routes_with_verified_geometry: 0,
    routes_missing_geometry: 1,
    routes_with_invalid_geometry: 0,
    spatial_map_available: false,
  },
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <GeospatialPage />
    </QueryClientProvider>,
  )
}

describe('geospatial intelligence', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fleetApi.geospatialNetwork).mockResolvedValue(network)
  })

  it('shows real hub and route records without inventing map locations', async () => {
    renderPage()

    expect(await screen.findByText('No verified hub coordinates')).toBeInTheDocument()
    expect(screen.getByText('0 / 2')).toBeInTheDocument()
    expect(screen.getByText('0 / 1')).toBeInTheDocument()
    expect(screen.getByRole('row', { name: /H-1 · North Hub/ })).toHaveTextContent('missing')
    expect(screen.getByRole('row', { name: /R-1 · North - South/ })).toHaveTextContent('450.5 km')
    expect(screen.queryByRole('button', { name: /zoom in/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Select hub H-1, North Hub' }))
    expect(screen.getByText('H-1 · 1')).toBeInTheDocument()
    expect(screen.getAllByText('North City, North State').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'Select route R-1, North - South' }))
    expect(screen.getByText('R-1 · 1')).toBeInTheDocument()
    expect(screen.getByText(/not a mapped road path/i)).toBeInTheDocument()
    expect(screen.getAllByText('66.7%').length).toBeGreaterThan(0)

    fireEvent.change(screen.getByRole('combobox', { name: 'Hub filter' }), {
      target: { value: '2' },
    })
    expect(screen.getByRole('row', { name: /H-2 · South Hub/ })).toBeInTheDocument()
    expect(screen.queryByRole('row', { name: /H-1 · North Hub/ })).not.toBeInTheDocument()
  })

  it('offers retry when the network request fails', async () => {
    vi.mocked(fleetApi.geospatialNetwork).mockRejectedValueOnce(new Error('Unavailable'))
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent('Geospatial network unavailable')
    expect(screen.queryByRole('heading', { name: 'Hub records' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('No verified hub coordinates')).toBeInTheDocument()
  })

  it('shows an honest empty state when the database has no network records', async () => {
    vi.mocked(fleetApi.geospatialNetwork).mockResolvedValue({
      hubs: [],
      routes: [],
      data_quality: {
        total_hubs: 0,
        hubs_with_verified_coordinates: 0,
        hubs_missing_coordinates: 0,
        hubs_with_invalid_coordinates: 0,
        total_routes: 0,
        routes_with_verified_geometry: 0,
        routes_missing_geometry: 0,
        routes_with_invalid_geometry: 0,
        spatial_map_available: false,
      },
    })
    renderPage()

    expect(await screen.findByText('No network records available')).toBeInTheDocument()
    expect(screen.queryByText('No verified hub coordinates')).not.toBeInTheDocument()
  })
})
