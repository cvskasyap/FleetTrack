import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, fleetApi } from './api'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('FleetTrack API client', () => {
  it('parses shipment detail measurements as JSON numbers', async () => {
    const shipment = {
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
      weight_kg: 1.25,
      shipping_cost: 10.5,
      notes: null,
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(shipment), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(fleetApi.shipment(1306)).resolves.toMatchObject({
      weight_kg: 1.25,
      shipping_cost: 10.5,
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/shipments/1306',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('parses booking options with numeric vehicle capacities', async () => {
    const options = {
      customers: [{ customer_id: 1, customer_code: 'C-1', full_name: 'Synthetic Customer' }],
      routes: [{
        route_id: 2,
        route_code: 'R-1',
        route_name: 'Origin - Destination',
        origin_hub: 'Origin',
        destination_hub: 'Destination',
      }],
      drivers: [],
      vehicles: [{
        vehicle_id: 3,
        registration_no: 'TEST-3',
        vehicle_type: 'van',
        capacity_kg: 12.5,
      }],
      hubs: [{ hub_id: 4, hub_code: 'H-4', hub_name: 'Origin' }],
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(options), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(fleetApi.shipmentOptions()).resolves.toMatchObject({
      customers: [{ customer_id: 1 }],
      routes: [{ route_id: 2 }],
      vehicles: [{ capacity_kg: 12.5 }],
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/shipments/options',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('validates database-backed dashboard response data', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          total_shipments: 10,
          delivered_shipments: 7,
          in_progress_shipments: 2,
          on_time_pct: null,
          average_transit_hours: null,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    const data = await fleetApi.dashboardSummary()

    expect(data.total_shipments).toBe(10)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/dashboard/summary',
      expect.objectContaining({ headers: { Accept: 'application/json' } }),
    )
  })

  it('rejects malformed API responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ total_shipments: 'many' }), { status: 200 }),
      ),
    )

    await expect(fleetApi.dashboardSummary()).rejects.toMatchObject({
      status: 502,
      message: 'The API returned data in an unexpected format.',
    })
  })

  it('maps service unavailability to a user-safe API error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 503 })))

    await expect(fleetApi.ready()).rejects.toBeInstanceOf(ApiError)
    await expect(fleetApi.ready()).rejects.toMatchObject({
      status: 503,
      message: 'A required data service is currently unavailable.',
    })
  })

  it('URL-encodes shipment filter parameters', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ total: 0, limit: 10, offset: 0, items: [] }), {
        status: 200,
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await fleetApi.shipments({
      status: 'in_transit',
      trackingNumber: 'FT 0001',
      limit: 10,
    })

    expect(fetchMock.mock.calls[0][0]).toBe(
      '/api/v1/shipments?status=in_transit&tracking_number=FT+0001&limit=10&offset=0',
    )
  })

  it('fetches hub aggregates with booking-date filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        items: [{
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
        }],
      }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(fleetApi.hubPerformance({
      fromDate: '2026-11-01',
      toDate: '2026-11-30',
    })).resolves.toMatchObject({ items: [{ shipments_handled: 4, on_time_pct: 50 }] })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/analytics/hubs?from_date=2026-11-01&to_date=2026-11-30',
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('accepts null route performance when no delivered SLA result exists', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        items: [{
          route_id: 7,
          route_code: 'R-7',
          route_name: 'North - East',
          origin_hub: 'North Hub',
          origin_city: 'North City',
          origin_state: 'North State',
          destination_hub: 'East Hub',
          destination_city: 'East City',
          destination_state: 'East State',
          distance_km: 120,
          shipment_count: 1,
          delivered_shipments: 0,
          in_progress_shipments: 1,
          delivered_with_sla_count: 0,
          on_time_shipments: 0,
          on_time_pct: null,
          average_transit_hours: null,
        }],
      }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(fleetApi.routePerformance()).resolves.toMatchObject({
      items: [{ on_time_pct: null, average_transit_hours: null }],
    })
  })

  it('fetches and validates the authenticated geospatial network contract', async () => {
    const network = {
      hubs: [{
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
      }],
      routes: [],
      data_quality: {
        total_hubs: 1,
        hubs_with_verified_coordinates: 0,
        hubs_missing_coordinates: 1,
        hubs_with_invalid_coordinates: 0,
        total_routes: 0,
        routes_with_verified_geometry: 0,
        routes_missing_geometry: 0,
        routes_with_invalid_geometry: 0,
        spatial_map_available: false,
      },
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(network), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(fleetApi.geospatialNetwork()).resolves.toMatchObject({
      hubs: [{ coordinate_status: 'missing', latitude: null, shipments_handled: 4 }],
      data_quality: { hubs_missing_coordinates: 1 },
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/geospatial/network',
      expect.objectContaining({ credentials: 'include' }),
    )

    const invalidNetwork = {
      ...network,
      hubs: [{ ...network.hubs[0], latitude: 91, longitude: 0, coordinate_status: 'verified' }],
      data_quality: {
        ...network.data_quality,
        hubs_with_verified_coordinates: 1,
        hubs_missing_coordinates: 0,
        spatial_map_available: true,
      },
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify(invalidNetwork), { status: 200 })),
    )
    await expect(fleetApi.geospatialNetwork()).rejects.toMatchObject({
      status: 502,
      message: 'The API returned data in an unexpected format.',
    })
  })

  it('creates a session with credentials and validates the returned account', async () => {
    const user = {
      user_id: 4,
      username: 'operator',
      display_name: 'Fleet Operator',
      email: null,
      roles: ['USER'],
      must_change_password: false,
    }
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ user }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(fleetApi.login('operator', 'one-time-password')).resolves.toMatchObject(user)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/login',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        body: JSON.stringify({ username: 'operator', password: 'one-time-password' }),
      }),
    )
  })

  it('sends the readable CSRF cookie as a header for session mutations', async () => {
    document.cookie = 'fleettrack_csrf=csrf-test-value; path=/'
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)

    await fleetApi.logout()

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/logout',
      expect.objectContaining({
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'X-CSRF-Token': 'csrf-test-value',
        },
      }),
    )
  })

  it('refuses to send a session mutation without a CSRF cookie', async () => {
    document.cookie = 'fleettrack_csrf=; path=/'
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    await expect(fleetApi.logout()).rejects.toMatchObject({ status: 403 })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('sends shipment mutations with the CSRF token and typed request body', async () => {
    document.cookie = 'fleettrack_csrf=operation-token; path=/'
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ error: { code: 'conflict', message: 'Only booked shipments can be cancelled.' } }),
        { status: 409, headers: { 'Content-Type': 'application/json' } },
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(fleetApi.cancelShipment(23, 'Customer request')).rejects.toMatchObject({
      status: 409,
      message: 'Only booked shipments can be cancelled.',
    })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/shipments/23/cancel',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-CSRF-Token': 'operation-token',
        },
        body: JSON.stringify({ reason: 'Customer request' }),
      }),
    )
  })
})
