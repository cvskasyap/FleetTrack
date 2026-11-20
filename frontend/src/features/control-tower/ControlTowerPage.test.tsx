import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetApi } from '../../lib/api'
import { ThemeProvider } from '../../app/providers'
import { ControlTowerPage } from './ControlTowerPage'

vi.mock('../../lib/api', () => ({
  fleetApi: {
    dashboardSummary: vi.fn(),
    monthlyTrends: vi.fn(),
    shipments: vi.fn(),
  },
}))

vi.mock('echarts-for-react/lib/core', () => ({
  default: () => <div data-testid="interactive-chart" />,
}))

const summary = {
  total_shipments: 1500,
  delivered_shipments: 1005,
  in_progress_shipments: 388,
  on_time_pct: 32.04,
  average_transit_hours: 42.12,
}

const trends = {
  items: [
    {
      month: '2026-11-01',
      booked_count: 451,
      delivered_in_booking_cohort: 86,
      delivered_at_count: 92,
    },
  ],
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <MemoryRouter>
          <ControlTowerPage />
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

describe('Executive control tower', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fleetApi.dashboardSummary).mockResolvedValue(summary)
    vi.mocked(fleetApi.monthlyTrends).mockResolvedValue(trends)
    vi.mocked(fleetApi.shipments).mockResolvedValue({
      total: 0,
      limit: 6,
      offset: 0,
      items: [],
    })
  })

  it('renders measured API metrics and distinguishes both trend definitions', async () => {
    renderPage()

    expect(await screen.findByText('1,500')).toBeInTheDocument()
    expect(screen.getByText('32.0%')).toBeInTheDocument()
    expect(screen.getByText('Synthetic demonstration dataset')).toBeInTheDocument()
    expect(
      screen.getByText('A cohort view: delivered counts refer to the current status of shipments booked in that month.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('This is delivery-event timing, separate from the booking-month cohort chart.'),
    ).toBeInTheDocument()
    expect(screen.getAllByTestId('interactive-chart')).toHaveLength(2)
  })

  it('shows a useful error state when dashboard data cannot be retrieved', async () => {
    vi.mocked(fleetApi.dashboardSummary).mockRejectedValue(new Error('API unavailable'))
    renderPage()

    expect(await screen.findByText('Control tower data unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('requests a bounded date window when the trend filter changes', async () => {
    renderPage()
    await screen.findByText('1,500')
    fireEvent.change(screen.getByLabelText('Trend date range'), {
      target: { value: '6m' },
    })

    await waitFor(() => {
      expect(fleetApi.monthlyTrends).toHaveBeenLastCalledWith(
        expect.stringMatching(/^\d{4}-\d{2}$/),
        undefined,
        expect.any(AbortSignal),
      )
    })
  })
})
