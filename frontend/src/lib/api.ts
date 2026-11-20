import {
  adminUserListSchema,
  adminUserSchema,
  authUserSchema,
  dashboardSummarySchema,
  geospatialNetworkSchema,
  healthSchema,
  hubPerformanceSchema,
  loginResponseSchema,
  monthlyTrendsSchema,
  shipmentDetailSchema,
  shipmentListSchema,
  shipmentOptionsSchema,
  shipmentTrackingSchema,
  routePerformanceSchema,
  temporaryPasswordSchema,
  type AuthUser,
  type DeliveryStatus,
  type ShipmentDetail,
  type ShipmentOptions,
  type ShipmentPriority,
  type ShipmentStatus,
  type StatusEventStatus,
} from './contracts'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH'
  body?: object
  signal?: AbortSignal
  csrf?: boolean
}

function csrfToken(): string {
  const token = document.cookie
    .split('; ')
    .find((cookie) => cookie.startsWith('fleettrack_csrf='))
    ?.slice('fleettrack_csrf='.length)
  if (!token) throw new ApiError('Your security token is missing. Refresh and retry.', 403)
  return decodeURIComponent(token)
}

async function requestJson(path: string, options: RequestOptions = {}): Promise<unknown> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.body) headers['Content-Type'] = 'application/json'
  if (options.csrf) headers['X-CSRF-Token'] = csrfToken()

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? 'GET',
      headers,
      credentials: 'include',
      signal: options.signal,
      body: options.body ? JSON.stringify(options.body) : undefined,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('Could not reach the FleetTrack API.', 0)
  }

  if (!response.ok) {
    let responseMessage: string | undefined
    try {
      const body = (await response.json()) as { error?: { message?: unknown } }
      if (typeof body.error?.message === 'string') responseMessage = body.error.message
    } catch {
      responseMessage = undefined
    }
    if (response.status === 503) {
      throw new ApiError('A required data service is currently unavailable.', 503)
    }
    if (response.status === 404) throw new ApiError('The requested record was not found.', 404)
    if (response.status < 500 && responseMessage) {
      throw new ApiError(responseMessage, response.status)
    }
    throw new ApiError(`The API request failed (${response.status}).`, response.status)
  }

  if (response.status === 204) return undefined
  return response.json() as Promise<unknown>
}

function parse<T>(schema: { parse: (value: unknown) => T }, value: unknown): T {
  try {
    return schema.parse(value)
  } catch {
    throw new ApiError('The API returned data in an unexpected format.', 502)
  }
}

export const fleetApi = {
  async live(signal?: AbortSignal) {
    return parse(healthSchema, await requestJson('/health/live', { signal }))
  },

  async ready(signal?: AbortSignal) {
    return parse(healthSchema, await requestJson('/health/ready', { signal }))
  },

  async dashboardSummary(signal?: AbortSignal) {
    return parse(
      dashboardSummarySchema,
      await requestJson('/dashboard/summary', { signal }),
    )
  },

  async monthlyTrends(fromMonth?: string, toMonth?: string, signal?: AbortSignal) {
    const params = new URLSearchParams()
    if (fromMonth) params.set('from_month', `${fromMonth}-01`)
    if (toMonth) params.set('to_month', `${toMonth}-01`)
    const suffix = params.size > 0 ? `?${params.toString()}` : ''
    return parse(
      monthlyTrendsSchema,
      await requestJson(`/dashboard/monthly-trends${suffix}`, { signal }),
    )
  },

  async shipments(options: {
    status?: ShipmentStatus | 'all'
    trackingNumber?: string
    limit?: number
    offset?: number
    signal?: AbortSignal
  } = {}) {
    const params = new URLSearchParams()
    if (options.status && options.status !== 'all') params.set('status', options.status)
    if (options.trackingNumber) params.set('tracking_number', options.trackingNumber)
    params.set('limit', String(options.limit ?? 50))
    params.set('offset', String(options.offset ?? 0))
    return parse(
      shipmentListSchema,
      await requestJson(`/shipments?${params.toString()}`, { signal: options.signal }),
    )
  },

  async shipment(shipmentId: number, signal?: AbortSignal) {
    return parse(
      shipmentDetailSchema,
      await requestJson(`/shipments/${shipmentId}`, { signal }),
    )
  },

  async shipmentOptions(signal?: AbortSignal): Promise<ShipmentOptions> {
    return parse(
      shipmentOptionsSchema,
      await requestJson('/shipments/options', { signal }),
    )
  },

  async hubPerformance(options: {
    fromDate?: string
    toDate?: string
    signal?: AbortSignal
  } = {}) {
    const params = new URLSearchParams()
    if (options.fromDate) params.set('from_date', options.fromDate)
    if (options.toDate) params.set('to_date', options.toDate)
    const suffix = params.size > 0 ? `?${params.toString()}` : ''
    return parse(
      hubPerformanceSchema,
      await requestJson(`/analytics/hubs${suffix}`, { signal: options.signal }),
    )
  },

  async routePerformance(options: {
    fromDate?: string
    toDate?: string
    signal?: AbortSignal
  } = {}) {
    const params = new URLSearchParams()
    if (options.fromDate) params.set('from_date', options.fromDate)
    if (options.toDate) params.set('to_date', options.toDate)
    const suffix = params.size > 0 ? `?${params.toString()}` : ''
    return parse(
      routePerformanceSchema,
      await requestJson(`/analytics/routes${suffix}`, { signal: options.signal }),
    )
  },

  async geospatialNetwork(signal?: AbortSignal) {
    return parse(
      geospatialNetworkSchema,
      await requestJson('/geospatial/network', { signal }),
    )
  },

  async tracking(shipmentId: number, signal?: AbortSignal) {
    return parse(
      shipmentTrackingSchema,
      await requestJson(`/shipments/${shipmentId}/tracking`, { signal }),
    )
  },

  async createShipment(payload: {
    customer_id: number
    route_id: number
    assigned_driver_id?: number | null
    assigned_vehicle_id?: number | null
    weight_kg: number
    shipping_cost: number
    priority: ShipmentPriority
    expected_delivery_at: string
    notes?: string | null
  }): Promise<ShipmentDetail> {
    return parse(
      shipmentDetailSchema,
      await requestJson('/shipments', {
        method: 'POST',
        csrf: true,
        body: payload,
      }),
    )
  },

  async updateShipment(
    shipmentId: number,
    payload: {
      customer_id?: number
      route_id?: number
      assigned_driver_id?: number | null
      assigned_vehicle_id?: number | null
      weight_kg?: number
      shipping_cost?: number
      priority?: ShipmentPriority
      expected_delivery_at?: string
      notes?: string | null
    },
  ): Promise<ShipmentDetail> {
    return parse(
      shipmentDetailSchema,
      await requestJson(`/shipments/${shipmentId}`, {
        method: 'PATCH',
        csrf: true,
        body: payload,
      }),
    )
  },

  async addShipmentStatusEvent(
    shipmentId: number,
    payload: {
      status: StatusEventStatus
      hub_id?: number | null
      event_at?: string
      notes?: string | null
    },
  ): Promise<ShipmentDetail> {
    return parse(
      shipmentDetailSchema,
      await requestJson(`/shipments/${shipmentId}/status`, {
        method: 'POST',
        csrf: true,
        body: payload,
      }),
    )
  },

  async addDeliveryAttempt(
    shipmentId: number,
    payload: {
      delivery_status: DeliveryStatus
      attempted_at?: string
      recipient_name?: string | null
      failure_reason?: string | null
      notes?: string | null
    },
  ): Promise<ShipmentDetail> {
    return parse(
      shipmentDetailSchema,
      await requestJson(`/shipments/${shipmentId}/deliveries`, {
        method: 'POST',
        csrf: true,
        body: payload,
      }),
    )
  },

  async cancelShipment(shipmentId: number, reason: string): Promise<ShipmentDetail> {
    return parse(
      shipmentDetailSchema,
      await requestJson(`/shipments/${shipmentId}/cancel`, {
        method: 'POST',
        csrf: true,
        body: { reason },
      }),
    )
  },

  async login(username: string, password: string): Promise<AuthUser> {
    return parse(
      loginResponseSchema,
      await requestJson('/auth/login', {
        method: 'POST',
        body: { username, password },
      }),
    ).user
  },

  async currentUser(signal?: AbortSignal): Promise<AuthUser> {
    return parse(authUserSchema, await requestJson('/auth/me', { signal }))
  },

  async logout(): Promise<void> {
    await requestJson('/auth/logout', { method: 'POST', csrf: true })
  },

  async changePassword(
    currentPassword: string,
    newPassword: string,
    confirmPassword: string,
  ): Promise<void> {
    await requestJson('/auth/password', {
      method: 'POST',
      csrf: true,
      body: {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      },
    })
  },

  async adminUsers(signal?: AbortSignal) {
    return parse(adminUserListSchema, await requestJson('/admin/users', { signal }))
  },

  async createAdminUser(payload: {
    username: string
    display_name: string
    email?: string | null
    roles: Array<'ADMIN' | 'USER'>
  }) {
    return parse(
      temporaryPasswordSchema,
      await requestJson('/admin/users', {
        method: 'POST',
        csrf: true,
        body: payload,
      }),
    )
  },

  async updateAdminUser(
    userId: number,
    payload: { display_name?: string; email?: string | null; is_active?: boolean; roles?: Array<'ADMIN' | 'USER'> },
  ) {
    return parse(
      adminUserSchema,
      await requestJson(`/admin/users/${userId}`, {
        method: 'PATCH',
        csrf: true,
        body: payload,
      }),
    )
  },

  async resetAdminPassword(userId: number) {
    return parse(
      temporaryPasswordSchema,
      await requestJson(`/admin/users/${userId}/reset-password`, {
        method: 'POST',
        csrf: true,
        body: {},
      }),
    )
  },
}
