import { z } from 'zod'

export const healthSchema = z.object({
  status: z.enum(['ready', 'not_ready']).or(z.literal('alive')),
  postgres: z.object({ status: z.enum(['ok', 'unavailable']) }).optional(),
  mongodb: z.object({ status: z.enum(['ok', 'unavailable']) }).optional(),
})

export const dashboardSummarySchema = z.object({
  total_shipments: z.number().int().nonnegative(),
  delivered_shipments: z.number().int().nonnegative(),
  in_progress_shipments: z.number().int().nonnegative(),
  on_time_pct: z.number().nullable(),
  average_transit_hours: z.number().nullable(),
})

export const monthlyTrendSchema = z.object({
  month: z.iso.date(),
  booked_count: z.number().int().nonnegative(),
  delivered_in_booking_cohort: z.number().int().nonnegative(),
  delivered_at_count: z.number().int().nonnegative(),
})

export const monthlyTrendsSchema = z.object({
  items: z.array(monthlyTrendSchema),
})

export const shipmentStatusSchema = z.enum([
  'booked',
  'picked_up',
  'in_transit',
  'at_hub',
  'out_for_delivery',
  'delivered',
  'failed',
  'exception',
  'returned',
  'cancelled',
])

export const shipmentSchema = z.object({
  shipment_id: z.number().int().positive(),
  tracking_number: z.string(),
  customer_name: z.string(),
  route_name: z.string(),
  status: shipmentStatusSchema,
  priority: z.enum(['standard', 'express', 'same_day']),
  booked_at: z.iso.datetime(),
  expected_delivery_at: z.iso.datetime(),
  delivered_at: z.iso.datetime().nullable(),
  on_time: z.boolean().nullable(),
  transit_hours: z.number().nullable(),
})

export const shipmentDetailSchema = shipmentSchema.extend({
  customer_id: z.number().int().positive(),
  customer_code: z.string(),
  route_id: z.number().int().positive(),
  origin_hub: z.string(),
  destination_hub: z.string(),
  assigned_driver_id: z.number().int().positive().nullable(),
  driver_code: z.string().nullable(),
  driver_name: z.string().nullable(),
  assigned_vehicle_id: z.number().int().positive().nullable(),
  registration_no: z.string().nullable(),
  weight_kg: z.number().positive(),
  shipping_cost: z.number().nonnegative(),
  notes: z.string().nullable(),
})

export const shipmentListSchema = z.object({
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
  items: z.array(shipmentSchema),
})

export const trackingEventSchema = z.object({
  status: shipmentStatusSchema,
  event_at: z.iso.datetime(),
  hub_id: z.number().int().nullable(),
  hub_name: z.string().nullable(),
  notes: z.string().nullable(),
  source: z.string(),
})

export const mongoTrackingEventSchema = z.object({
  tracking_number: z.string(),
  status: shipmentStatusSchema,
  event_at: z.iso.datetime(),
  hub_id: z.number().int().nullable(),
  hub_name: z.string().nullable(),
  hub_city: z.string().nullable(),
  dwell_minutes: z.number().int().nullable(),
  delay_flag: z.boolean(),
  event_source: z.string().nullable(),
  notes: z.string().nullable(),
})

export const deliveryAttemptSchema = z.object({
  delivery_id: z.number().int().positive(),
  attempt_no: z.number().int().positive(),
  delivery_status: z.enum(['delivered', 'failed', 'out_for_delivery', 'exception']),
  attempted_at: z.iso.datetime(),
  recipient_name: z.string().nullable(),
  failure_reason: z.string().nullable(),
  notes: z.string().nullable(),
})

export const shipmentTrackingSchema = z.object({
  shipment_id: z.number().int().positive(),
  tracking_number: z.string(),
  relational_events: z.array(trackingEventSchema),
  mongo_events: z.array(mongoTrackingEventSchema),
  delivery_attempts: z.array(deliveryAttemptSchema),
})

export const shipmentOptionsSchema = z.object({
  customers: z.array(z.object({
    customer_id: z.number().int().positive(),
    customer_code: z.string(),
    full_name: z.string(),
  })),
  routes: z.array(z.object({
    route_id: z.number().int().positive(),
    route_code: z.string(),
    route_name: z.string(),
    origin_hub: z.string(),
    destination_hub: z.string(),
  })),
  drivers: z.array(z.object({
    driver_id: z.number().int().positive(),
    driver_code: z.string(),
    full_name: z.string(),
  })),
  vehicles: z.array(z.object({
    vehicle_id: z.number().int().positive(),
    registration_no: z.string(),
    vehicle_type: z.string(),
    capacity_kg: z.number().positive(),
  })),
  hubs: z.array(z.object({
    hub_id: z.number().int().positive(),
    hub_code: z.string(),
    hub_name: z.string(),
  })),
})

export const hubPerformanceSchema = z.object({
  items: z.array(z.object({
    hub_id: z.number().int().positive(),
    hub_code: z.string(),
    hub_name: z.string(),
    city: z.string(),
    state: z.string(),
    daily_capacity: z.number().int().positive(),
    shipments_handled: z.number().int().nonnegative(),
    scan_count: z.number().int().nonnegative(),
    delivered_shipments: z.number().int().nonnegative(),
    in_progress_shipments: z.number().int().nonnegative(),
    delivered_with_sla_count: z.number().int().nonnegative(),
    on_time_shipments: z.number().int().nonnegative(),
    on_time_pct: z.number().min(0).max(100).nullable(),
    average_transit_hours: z.number().nonnegative().nullable(),
  })),
})

export const routePerformanceSchema = z.object({
  items: z.array(z.object({
    route_id: z.number().int().positive(),
    route_code: z.string(),
    route_name: z.string(),
    origin_hub: z.string(),
    origin_city: z.string(),
    origin_state: z.string(),
    destination_hub: z.string(),
    destination_city: z.string(),
    destination_state: z.string(),
    distance_km: z.number().positive(),
    shipment_count: z.number().int().nonnegative(),
    delivered_shipments: z.number().int().nonnegative(),
    in_progress_shipments: z.number().int().nonnegative(),
    delivered_with_sla_count: z.number().int().nonnegative(),
    on_time_shipments: z.number().int().nonnegative(),
    on_time_pct: z.number().min(0).max(100).nullable(),
    average_transit_hours: z.number().nonnegative().nullable(),
  })),
})

export const geospatialHubSchema = z.object({
  hub_id: z.number().int().positive(),
  hub_code: z.string(),
  hub_name: z.string(),
  city: z.string(),
  state: z.string(),
  latitude: z.number().min(-90).max(90).nullable(),
  longitude: z.number().min(-180).max(180).nullable(),
  coordinate_status: z.enum(['verified', 'missing', 'invalid']),
  shipments_handled: z.number().int().nonnegative(),
  delivered_shipments: z.number().int().nonnegative(),
  in_progress_shipments: z.number().int().nonnegative(),
  scan_count: z.number().int().nonnegative(),
  on_time_pct: z.number().min(0).max(100).nullable(),
}).superRefine((hub, context) => {
  const hasLatitude = hub.latitude !== null
  const hasLongitude = hub.longitude !== null
  if (hasLatitude !== hasLongitude) {
    context.addIssue({
      code: 'custom',
      message: 'Latitude and longitude must be supplied together.',
    })
  }
  if (hub.coordinate_status === 'verified' && (!hasLatitude || !hasLongitude)) {
    context.addIssue({
      code: 'custom',
      message: 'Verified coordinates must include latitude and longitude.',
    })
  }
  if (hub.coordinate_status !== 'verified' && (hasLatitude || hasLongitude)) {
    context.addIssue({
      code: 'custom',
      message: 'Only verified coordinates may be returned.',
    })
  }
})

export const geospatialEndpointSchema = z.object({
  hub_name: z.string(),
  city: z.string(),
  state: z.string(),
})

export const geospatialRouteSchema = z.object({
  route_id: z.number().int().positive(),
  route_code: z.string(),
  route_name: z.string(),
  origin: geospatialEndpointSchema,
  destination: geospatialEndpointSchema,
  distance_km: z.number().positive(),
  route_geometry: z.array(
    z.tuple([z.number().min(-180).max(180), z.number().min(-90).max(90)]),
  ).nullable(),
  geometry_status: z.enum(['verified', 'missing', 'invalid']),
  shipment_count: z.number().int().nonnegative(),
  delivered_shipments: z.number().int().nonnegative(),
  in_progress_shipments: z.number().int().nonnegative(),
  on_time_pct: z.number().min(0).max(100).nullable(),
  average_transit_hours: z.number().nonnegative().nullable(),
}).superRefine((route, context) => {
  if (route.geometry_status === 'verified' && (route.route_geometry === null || route.route_geometry.length < 2)) {
    context.addIssue({
      code: 'custom',
      message: 'Verified route geometry must contain at least two points.',
    })
  }
  if (route.geometry_status !== 'verified' && route.route_geometry !== null) {
    context.addIssue({
      code: 'custom',
      message: 'Unverified route geometry must not be returned.',
    })
  }
})

export const geospatialNetworkSchema = z.object({
  hubs: z.array(geospatialHubSchema),
  routes: z.array(geospatialRouteSchema),
  data_quality: z.object({
    total_hubs: z.number().int().nonnegative(),
    hubs_with_verified_coordinates: z.number().int().nonnegative(),
    hubs_missing_coordinates: z.number().int().nonnegative(),
    hubs_with_invalid_coordinates: z.number().int().nonnegative(),
    total_routes: z.number().int().nonnegative(),
    routes_with_verified_geometry: z.number().int().nonnegative(),
    routes_missing_geometry: z.number().int().nonnegative(),
    routes_with_invalid_geometry: z.number().int().nonnegative(),
    spatial_map_available: z.boolean(),
  }).superRefine((quality, context) => {
    if (
      quality.hubs_with_verified_coordinates
        + quality.hubs_missing_coordinates
        + quality.hubs_with_invalid_coordinates !== quality.total_hubs
    ) {
      context.addIssue({
        code: 'custom',
        message: 'Hub coordinate quality counts must match the hub total.',
      })
    }
    if (
      quality.routes_with_verified_geometry
        + quality.routes_missing_geometry
        + quality.routes_with_invalid_geometry !== quality.total_routes
    ) {
      context.addIssue({
        code: 'custom',
        message: 'Route geometry quality counts must match the route total.',
      })
    }
    if (quality.spatial_map_available !== (quality.hubs_with_verified_coordinates > 0)) {
      context.addIssue({
        code: 'custom',
        message: 'Map availability must reflect verified hub coordinates.',
      })
    }
  }),
})

export const authUserSchema = z.object({
  user_id: z.number().int().positive(),
  username: z.string(),
  display_name: z.string(),
  email: z.string().nullable(),
  roles: z.array(z.enum(['ADMIN', 'USER'])),
  must_change_password: z.boolean(),
})

export const loginResponseSchema = z.object({
  user: authUserSchema,
})

export const adminUserSchema = authUserSchema.extend({
  is_active: z.boolean(),
  created_at: z.iso.datetime(),
  last_login_at: z.iso.datetime().nullable(),
})

export const adminUserListSchema = z.object({
  total: z.number().int().nonnegative(),
  items: z.array(adminUserSchema),
})

export const temporaryPasswordSchema = z.object({
  user: adminUserSchema,
  temporary_password: z.string(),
})

export type DashboardSummary = z.infer<typeof dashboardSummarySchema>
export type MonthlyTrend = z.infer<typeof monthlyTrendSchema>
export type Shipment = z.infer<typeof shipmentSchema>
export type ShipmentDetail = z.infer<typeof shipmentDetailSchema>
export type ShipmentStatus = z.infer<typeof shipmentStatusSchema>
export type StatusEventStatus = Exclude<
  ShipmentStatus,
  'booked' | 'cancelled' | 'delivered' | 'failed' | 'out_for_delivery' | 'exception'
>
export type ShipmentTracking = z.infer<typeof shipmentTrackingSchema>
export type ShipmentPriority = Shipment['priority']
export type ShipmentOptions = z.infer<typeof shipmentOptionsSchema>
export type HubPerformance = z.infer<typeof hubPerformanceSchema>['items'][number]
export type RoutePerformance = z.infer<typeof routePerformanceSchema>['items'][number]
export type GeospatialHub = z.infer<typeof geospatialHubSchema>
export type GeospatialRoute = z.infer<typeof geospatialRouteSchema>
export type GeospatialNetwork = z.infer<typeof geospatialNetworkSchema>
export type DeliveryStatus = z.infer<typeof deliveryAttemptSchema>['delivery_status']
export type AuthUser = z.infer<typeof authUserSchema>
export type AdminUser = z.infer<typeof adminUserSchema>
