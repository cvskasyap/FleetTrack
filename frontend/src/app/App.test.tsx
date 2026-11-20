import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { AppErrorBoundary } from './AppErrorBoundary'
import { AppProviders } from './providers'
import { ApiError, fleetApi } from '../lib/api'
import type { AuthUser } from '../lib/contracts'

vi.mock('../lib/api', () => ({
  ApiError: class ApiError extends Error {
    readonly status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  },
  fleetApi: {
    currentUser: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
    adminUsers: vi.fn(),
    createAdminUser: vi.fn(),
    updateAdminUser: vi.fn(),
    resetAdminPassword: vi.fn(),
    ready: vi.fn(),
    dashboardSummary: vi.fn(),
    monthlyTrends: vi.fn(),
    shipments: vi.fn(),
    geospatialNetwork: vi.fn(),
  },
}))

const authenticatedAdmin: AuthUser = {
  user_id: 1,
  username: 'admin',
  display_name: 'FleetTrack Administrator',
  roles: ['ADMIN'],
  must_change_password: false,
}

describe('application shell routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fleetApi.currentUser).mockResolvedValue(authenticatedAdmin)
    vi.mocked(fleetApi.login).mockResolvedValue(authenticatedAdmin)
    vi.mocked(fleetApi.logout).mockResolvedValue(undefined)
    vi.mocked(fleetApi.changePassword).mockResolvedValue(undefined)
    vi.mocked(fleetApi.adminUsers).mockResolvedValue({ total: 0, items: [] })
    vi.mocked(fleetApi.ready).mockResolvedValue({ status: 'ready' })
    vi.mocked(fleetApi.dashboardSummary).mockResolvedValue({
      total_shipments: 1500,
      delivered_shipments: 1005,
      in_progress_shipments: 388,
      on_time_pct: 32.04,
      average_transit_hours: 42.12,
    })
    vi.mocked(fleetApi.monthlyTrends).mockResolvedValue({ items: [] })
    vi.mocked(fleetApi.shipments).mockResolvedValue({
      total: 0,
      limit: 6,
      offset: 0,
      items: [],
    })
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
  })

  it('provides all twelve modules and marks unsupported pages as development', async () => {
    render(
      <AppProviders>
        <App />
      </AppProviders>,
    )

    expect(await screen.findByRole('heading', { name: 'Executive control tower' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Primary navigation' }).querySelectorAll('a')).toHaveLength(12)
    expect(screen.getByText('Predictive SLA intelligence')).toBeInTheDocument()
  })

  it('opens the live geospatial network workspace from navigation', async () => {
    render(
      <AppProviders>
        <App />
      </AppProviders>,
    )

    await screen.findByRole('heading', { name: 'Executive control tower' })
    fireEvent.click(screen.getByRole('link', { name: /Geospatial intelligence/ }))

    expect(await screen.findByRole('heading', { name: 'Geospatial intelligence' })).toBeInTheDocument()
    expect(await screen.findByText('No network records available')).toBeInTheDocument()
  })

  it('sends unauthenticated visitors to the sign-in page', async () => {
    vi.mocked(fleetApi.currentUser).mockRejectedValue(
      new ApiError('Unauthorized', 401),
    )
    render(
      <AppProviders>
        <App />
      </AppProviders>,
    )

    expect(await screen.findByRole('heading', { name: 'Sign in to FleetTrack' })).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
  })

  it('signs in and routes a normal account to the control tower', async () => {
    vi.mocked(fleetApi.currentUser).mockRejectedValue(new ApiError('Unauthorized', 401))
    render(
      <AppProviders>
        <App />
      </AppProviders>,
    )

    await screen.findByRole('heading', { name: 'Sign in to FleetTrack' })
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'admin' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Executive control tower' })).toBeInTheDocument()
    expect(fleetApi.login).toHaveBeenCalledWith('admin', 'secret')
  })

  it('requires a new password before showing application modules', async () => {
    vi.mocked(fleetApi.currentUser).mockResolvedValue({
      ...authenticatedAdmin,
      must_change_password: true,
    })
    render(
      <AppProviders>
        <App />
      </AppProviders>,
    )

    await screen.findByRole('heading', { name: 'Choose a new password' })
    fireEvent.change(screen.getByLabelText('Temporary password'), { target: { value: 'temporary-password' } })
    fireEvent.change(screen.getByLabelText(/^New password/), { target: { value: 'a-strong-password-123' } })
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'a-strong-password-123' } })
    fireEvent.click(screen.getByRole('button', { name: 'Update password' }))

    expect(await screen.findByRole('heading', { name: 'Sign in to FleetTrack' })).toBeInTheDocument()
    expect(fleetApi.changePassword).toHaveBeenCalledWith(
      'temporary-password',
      'a-strong-password-123',
      'a-strong-password-123',
    )
  })

  it('hides administration and redirects direct access for a USER account', async () => {
    window.history.replaceState({}, '', '/administration')
    vi.mocked(fleetApi.currentUser).mockResolvedValue({
      ...authenticatedAdmin,
      roles: ['USER'],
    })
    render(
      <AppProviders>
        <App />
      </AppProviders>,
    )

    expect(await screen.findByRole('heading', { name: 'Executive control tower' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'System administration' })).not.toBeInTheDocument()
  })

  it('supports arrow-key selection and Enter navigation in the command palette', async () => {
    render(
      <AppProviders>
        <App />
      </AppProviders>,
    )

    await screen.findByRole('button', { name: 'Search FleetTrack' })
    fireEvent.click(screen.getByRole('button', { name: 'Search FleetTrack' }))
    const search = screen.getByRole('combobox', { name: 'Search modules and workspaces' })
    fireEvent.change(search, { target: { value: 'shipment' } })
    fireEvent.keyDown(search, { key: 'ArrowDown' })
    expect(search).toHaveAttribute('aria-activedescendant', 'command-option-tracking')
    fireEvent.keyDown(search, { key: 'Enter' })

    expect(await screen.findByRole('heading', { name: 'Shipment tracking' })).toBeInTheDocument()
  })

  it('shows a recoverable fallback when a route throws during rendering', () => {
    function BrokenView(): never {
      throw new Error('render failure')
    }

    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    try {
      render(
        <AppErrorBoundary>
          <BrokenView />
        </AppErrorBoundary>,
      )
      expect(screen.getByRole('heading', { name: 'FleetTrack could not render this view' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Reload application' })).toBeInTheDocument()
    } finally {
      consoleError.mockRestore()
    }
  })
})
