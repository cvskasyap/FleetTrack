import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetApi } from '../../lib/api'
import { HubRouteIntelligencePage } from './HubRouteIntelligencePage'

vi.mock('../../lib/api', () => ({
  fleetApi: {
    hubPerformance: vi.fn(),
    routePerformance: vi.fn(),
  },
}))

vi.mock('../../components/charts', () => ({
  HubVolumeChart: ({ items }: { items: Array<{ hub_code: string }> }) => (
    <div data-testid="hub-volume-chart">{items.map((item) => item.hub_code).join(',')}</div>
  ),
  RouteOnTimeChart: ({ items }: { items: Array<{ route_code: string }> }) => (
    <div data-testid="route-on-time-chart">{items.map((item) => item.route_code).join(',')}</div>
  ),
}))

const hubItems = [
  {
    hub_id: 1,
    hub_code: 'H-1',
    hub_name: 'North Hub',
    city: 'North City',
    state: 'North State',
    daily_capacity: 200,
    shipments_handled: 4,
    scan_count: 8,
    delivered_shipments: 2,
    in_progress_shipments: 2,
    delivered_with_sla_count: 2,
    on_time_shipments: 1,
    on_time_pct: 50,
    average_transit_hours: 24.5,
  },
  {
    hub_id: 2,
    hub_code: 'H-2',
    hub_name: 'South Hub',
    city: 'South City',
    state: 'South State',
    daily_capacity: 150,
    shipments_handled: 0,
    scan_count: 0,
    delivered_shipments: 0,
    in_progress_shipments: 0,
    delivered_with_sla_count: 0,
    on_time_shipments: 0,
    on_time_pct: null,
    average_transit_hours: null,
  },
]

const routeItems = [
  {
    route_id: 1,
    route_code: 'R-1',
    route_name: 'North - South',
    origin_hub: 'North Hub',
    origin_city: 'North City',
    origin_state: 'North State',
    destination_hub: 'South Hub',
    destination_city: 'South City',
    destination_state: 'South State',
    distance_km: 450.5,
    shipment_count: 5,
    delivered_shipments: 3,
    in_progress_shipments: 2,
    delivered_with_sla_count: 3,
    on_time_shipments: 2,
    on_time_pct: 66.67,
    average_transit_hours: 42.5,
  },
  {
    route_id: 2,
    route_code: 'R-2',
    route_name: 'South - East',
    origin_hub: 'South Hub',
    origin_city: 'South City',
    origin_state: 'South State',
    destination_hub: 'East Hub',
    destination_city: 'East City',
    destination_state: 'East State',
    distance_km: 120,
    shipment_count: 0,
    delivered_shipments: 0,
    in_progress_shipments: 0,
    delivered_with_sla_count: 0,
    on_time_shipments: 0,
    on_time_pct: null,
    average_transit_hours: null,
  },
]

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <HubRouteIntelligencePage />
    </QueryClientProvider>,
  )
}

describe('hub and route intelligence', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fleetApi.hubPerformance).mockResolvedValue({ items: hubItems })
    vi.mocked(fleetApi.routePerformance).mockResolvedValue({ items: routeItems })
  })

  it('renders database aggregates and filters both comparisons', async () => {
    renderPage()

    const northHubRow = await screen.findByRole('row', { name: /H-1 · North Hub/ })
    expect(northHubRow).toHaveTextContent('North City, North State')
    expect(screen.getByText('50.0% (1/2)')).toBeInTheDocument()
    const firstRouteRow = screen.getByRole('row', { name: /R-1 · North - South/ })
    expect(firstRouteRow).toHaveTextContent('R-1 · North - South')
    expect(screen.getByText('66.7% (2/3)')).toBeInTheDocument()
    expect(screen.getByTestId('hub-volume-chart')).toHaveTextContent('H-1,H-2')
    expect(screen.getByTestId('route-on-time-chart')).toHaveTextContent('R-1,R-2')

    fireEvent.change(screen.getByLabelText('Hub'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('Route'), { target: { value: '2' } })

    expect(await screen.findByRole('row', { name: /H-2 · South Hub/ })).toBeInTheDocument()
    expect(screen.queryByRole('row', { name: /H-1 · North Hub/ })).not.toBeInTheDocument()
    expect(await screen.findByRole('row', { name: /R-2 · South - East/ })).toBeInTheDocument()
    expect(screen.queryByRole('row', { name: /R-1 · North - South/ })).not.toBeInTheDocument()
    expect(screen.getByTestId('hub-volume-chart')).toHaveTextContent('H-2')
    expect(screen.getByTestId('route-on-time-chart')).toHaveTextContent('R-2')

    fireEvent.change(screen.getByLabelText('Booked from'), { target: { value: '2026-11-01' } })
    fireEvent.change(screen.getByLabelText('Booked through'), { target: { value: '2026-11-30' } })

    await waitFor(() => {
      expect(fleetApi.hubPerformance).toHaveBeenLastCalledWith(
        expect.objectContaining({ fromDate: '2026-11-01', toDate: '2026-11-30' }),
      )
      expect(fleetApi.routePerformance).toHaveBeenLastCalledWith(
        expect.objectContaining({ fromDate: '2026-11-01', toDate: '2026-11-30' }),
      )
    })
  })

  it('shows a retryable error instead of analytics when an endpoint fails', async () => {
    vi.mocked(fleetApi.hubPerformance).mockRejectedValueOnce(new Error('Unavailable'))
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent('Hub and route analytics unavailable')
    expect(screen.queryByRole('heading', { name: 'Hub performance' })).not.toBeInTheDocument()
  })
})
