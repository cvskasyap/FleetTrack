import { useQuery } from '@tanstack/react-query'
import { MapPinOff, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { Button, EmptyState, ErrorState, LoadingPanel, PageHeader, Panel } from '../../components/ui'
import { fleetApi } from '../../lib/api'
import type { GeospatialHub, GeospatialRoute } from '../../lib/contracts'
import { formatNumber } from '../../lib/utils'

function percentage(value: number | null) {
  return value === null ? 'Unavailable' : `${value.toFixed(1)}%`
}

function HubTable({
  items,
  selectedHubId,
  onSelect,
}: {
  items: GeospatialHub[]
  selectedHubId: number | null
  onSelect: (hubId: number) => void
}) {
  if (items.length === 0) {
    return <EmptyState title="No hubs to display" description="No hub records match the current filter." />
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Hub</th>
            <th scope="col">Location label</th>
            <th scope="col">Coordinates</th>
            <th scope="col">Shipments handled</th>
            <th scope="col">Delivered</th>
            <th scope="col">In progress</th>
          </tr>
        </thead>
        <tbody>
          {items.map((hub) => (
            <tr key={hub.hub_id} aria-selected={selectedHubId === hub.hub_id}>
              <td>
                <Button
                  type="button"
                  variant="ghost"
                  className="geospatial-record-button"
                  aria-pressed={selectedHubId === hub.hub_id}
                  aria-label={`Select hub ${hub.hub_code}, ${hub.hub_name}`}
                  onClick={() => onSelect(hub.hub_id)}
                >
                  <strong>{hub.hub_code} · {hub.hub_name}</strong>
                </Button>
              </td>
              <td>{hub.city}, {hub.state}</td>
              <td><span className="geospatial-status">{hub.coordinate_status}</span></td>
              <td>{formatNumber(hub.shipments_handled)}</td>
              <td>{formatNumber(hub.delivered_shipments)}</td>
              <td>{formatNumber(hub.in_progress_shipments)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RouteTable({
  items,
  selectedRouteId,
  onSelect,
}: {
  items: GeospatialRoute[]
  selectedRouteId: number | null
  onSelect: (routeId: number) => void
}) {
  if (items.length === 0) {
    return <EmptyState title="No routes to display" description="No route records match the current filter." />
  }

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Route</th>
            <th scope="col">Origin</th>
            <th scope="col">Destination</th>
            <th scope="col">Recorded distance</th>
            <th scope="col">Shipments</th>
            <th scope="col">Delivered</th>
            <th scope="col">In progress</th>
            <th scope="col">On time</th>
            <th scope="col">Geometry</th>
          </tr>
        </thead>
        <tbody>
          {items.map((route) => (
            <tr key={route.route_id} aria-selected={selectedRouteId === route.route_id}>
              <td>
                <Button
                  type="button"
                  variant="ghost"
                  className="geospatial-record-button"
                  aria-pressed={selectedRouteId === route.route_id}
                  aria-label={`Select route ${route.route_code}, ${route.route_name}`}
                  onClick={() => onSelect(route.route_id)}
                >
                  <strong>{route.route_code} · {route.route_name}</strong>
                </Button>
              </td>
              <td>{route.origin.hub_name}<span className="cell-subtext">{route.origin.city}, {route.origin.state}</span></td>
              <td>{route.destination.hub_name}<span className="cell-subtext">{route.destination.city}, {route.destination.state}</span></td>
              <td>{formatNumber(route.distance_km, 1)} km</td>
              <td>{formatNumber(route.shipment_count)}</td>
              <td>{formatNumber(route.delivered_shipments)}</td>
              <td>{formatNumber(route.in_progress_shipments)}</td>
              <td>{percentage(route.on_time_pct)}</td>
              <td><span className="geospatial-status">{route.geometry_status}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function HubDetails({ hub }: { hub: GeospatialHub }) {
  return (
    <dl className="geospatial-detail-grid">
      <div><dt>Hub identifier</dt><dd>{hub.hub_code} · {hub.hub_id}</dd></div>
      <div><dt>Recorded location</dt><dd>{hub.city}, {hub.state}</dd></div>
      <div><dt>Coordinates</dt><dd>{hub.coordinate_status === 'missing' ? 'Not recorded' : 'Withheld: not verified'}</dd></div>
      <div><dt>Shipment volume</dt><dd>{formatNumber(hub.shipments_handled)}</dd></div>
      <div><dt>Delivered / in progress</dt><dd>{formatNumber(hub.delivered_shipments)} / {formatNumber(hub.in_progress_shipments)}</dd></div>
      <div><dt>On-time delivery</dt><dd>{percentage(hub.on_time_pct)}</dd></div>
    </dl>
  )
}

function RouteDetails({ route }: { route: GeospatialRoute }) {
  return (
    <>
      <div className="geospatial-relationship" aria-label="Recorded route relationship, not to scale">
        <div>
          <span>ORIGIN</span>
          <strong>{route.origin.hub_name}</strong>
          <small>{route.origin.city}, {route.origin.state}</small>
        </div>
        <span className="geospatial-relationship-arrow" aria-hidden="true">→</span>
        <div>
          <span>DESTINATION</span>
          <strong>{route.destination.hub_name}</strong>
          <small>{route.destination.city}, {route.destination.state}</small>
        </div>
      </div>
      <dl className="geospatial-detail-grid">
        <div><dt>Route identifier</dt><dd>{route.route_code} · {route.route_id}</dd></div>
        <div><dt>Recorded distance</dt><dd>{formatNumber(route.distance_km, 1)} km</dd></div>
        <div><dt>Shipment volume</dt><dd>{formatNumber(route.shipment_count)}</dd></div>
        <div><dt>Delivered / in progress</dt><dd>{formatNumber(route.delivered_shipments)} / {formatNumber(route.in_progress_shipments)}</dd></div>
        <div><dt>On-time delivery</dt><dd>{percentage(route.on_time_pct)}</dd></div>
        <div><dt>Average transit</dt><dd>{route.average_transit_hours === null ? 'Unavailable' : `${formatNumber(route.average_transit_hours, 1)} h`}</dd></div>
      </dl>
      <p className="geospatial-method-note">
        This is a database relationship only, not a mapped road path. The recorded distance is not
        route geometry.
      </p>
    </>
  )
}

export function GeospatialPage() {
  const [hubFilter, setHubFilter] = useState('all')
  const [routeFilter, setRouteFilter] = useState('all')
  const networkQuery = useQuery({
    queryKey: ['geospatial', 'network'],
    queryFn: ({ signal }) => fleetApi.geospatialNetwork(signal),
  })

  const hubs = networkQuery.data?.hubs ?? []
  const routes = networkQuery.data?.routes ?? []
  const visibleHubs = hubFilter === 'all'
    ? hubs
    : hubs.filter((hub) => hub.hub_id === Number(hubFilter))
  const visibleRoutes = routeFilter === 'all'
    ? routes
    : routes.filter((route) => route.route_id === Number(routeFilter))
  const selectedHub = hubFilter === 'all' ? null : hubs.find((hub) => hub.hub_id === Number(hubFilter))
  const selectedRoute = routeFilter === 'all' ? null : routes.find((route) => route.route_id === Number(routeFilter))

  if (networkQuery.isError) {
    return (
      <div className="page-stack">
        <PageHeader
          eyebrow="NETWORK LOCATION DATA"
          title="Geospatial intelligence"
          description="Review verified geographic coverage and database-backed hub and route relationships."
        />
        <ErrorState
          title="Geospatial network unavailable"
          description="The FleetTrack API could not retrieve hub and route records."
          onRetry={() => void networkQuery.refetch()}
        />
      </div>
    )
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="NETWORK LOCATION DATA"
        title="Geospatial intelligence"
        description="Review location-data coverage and database-backed hub and route relationships."
        actions={
          <Button
            variant="icon"
            aria-label="Refresh geospatial network"
            onClick={() => void networkQuery.refetch()}
          >
            <RefreshCw size={16} aria-hidden="true" />
          </Button>
        }
      />

      <div className="data-notice" role="note">
        <span className="notice-dot" />
        <span>
          <strong>Synthetic demonstration dataset</strong>
          <span className="notice-divider">·</span>
          City/state labels are not facility coordinates; no locations are inferred
        </span>
      </div>

      {networkQuery.isLoading ? (
        <Panel><LoadingPanel rows={7} /></Panel>
      ) : !networkQuery.data || (hubs.length === 0 && routes.length === 0) ? (
        <Panel>
          <EmptyState
            title="No network records available"
            description="The database returned no hub or route records for this view."
          />
        </Panel>
      ) : (
        <>
          <Panel className="geospatial-map-panel">
            <div className="panel-heading">
              <div>
                <h2>Spatial coverage</h2>
                <p>Map rendering is withheld until spatial data and a configured map renderer are available.</p>
              </div>
              <span className="chart-unit">VERIFIED DATA ONLY</span>
            </div>
            <div className="geospatial-map-empty" role="status">
              <div className="geospatial-map-icon"><MapPinOff size={21} aria-hidden="true" /></div>
              {networkQuery.data.data_quality.spatial_map_available ? (
                <>
                  <h3>Map renderer is not configured</h3>
                  <p>Verified coordinate records exist, but this release has no configured map renderer or tile provider.</p>
                </>
              ) : (
                <>
                  <h3>No verified hub coordinates</h3>
                  <p>
                    PostgreSQL provides city and state labels, but no facility addresses or coordinates.
                    City centroids would not identify these hubs, so no markers, tiles, or connecting
                    lines are shown.
                  </p>
                </>
              )}
              <div className="geospatial-coverage-grid">
                <div>
                  <strong>{formatNumber(networkQuery.data.data_quality.hubs_with_verified_coordinates)} / {formatNumber(networkQuery.data.data_quality.total_hubs)}</strong>
                  <span>Hubs with verified coordinates</span>
                </div>
                <div>
                  <strong>{formatNumber(networkQuery.data.data_quality.routes_with_verified_geometry)} / {formatNumber(networkQuery.data.data_quality.total_routes)}</strong>
                  <span>Routes with geometry</span>
                </div>
              </div>
              <p className="geospatial-map-footnote">
                {networkQuery.data.data_quality.spatial_map_available
                  ? 'Pan, zoom, fit-to-network and tile layers are not configured in this release.'
                  : 'Pan, zoom, fit-to-network and tile layers are unavailable until source geography is added and validated.'}
                {' '}No arbitrary markers or schematic lines are substituted.
              </p>
            </div>
          </Panel>

          <Panel className="analytics-filter-panel">
            <div className="analytics-filter-grid geospatial-filter-grid">
              <label>
                Hub
                <select
                  className="select-control"
                  aria-label="Hub filter"
                  value={hubFilter}
                  onChange={(event) => setHubFilter(event.target.value)}
                >
                  <option value="all">All hubs</option>
                  {hubs.map((hub) => (
                    <option key={hub.hub_id} value={hub.hub_id}>{hub.hub_code} · {hub.hub_name}</option>
                  ))}
                </select>
              </label>
              <label>
                Route
                <select
                  className="select-control"
                  aria-label="Route filter"
                  value={routeFilter}
                  onChange={(event) => setRouteFilter(event.target.value)}
                >
                  <option value="all">All routes</option>
                  {routes.map((route) => (
                    <option key={route.route_id} value={route.route_id}>{route.route_code} · {route.route_name}</option>
                  ))}
                </select>
              </label>
            </div>
          </Panel>

          <div className="geospatial-detail-panels">
            <Panel className="geospatial-detail-panel">
              <div className="panel-heading">
                <div>
                  <h2>Selected hub</h2>
                  <p>{selectedHub ? 'Database-backed hub record and shipment aggregates.' : 'Choose a hub to inspect its record.'}</p>
                </div>
              </div>
              {selectedHub ? (
                <HubDetails hub={selectedHub} />
              ) : (
                <EmptyState title="No hub selected" description="Select a hub from the table below." />
              )}
            </Panel>
            <Panel className="geospatial-detail-panel">
              <div className="panel-heading">
                <div>
                  <h2>Selected route</h2>
                  <p>{selectedRoute ? 'Recorded origin, destination and route aggregates.' : 'Choose a route to inspect its relationship.'}</p>
                </div>
              </div>
              {selectedRoute ? (
                <RouteDetails route={selectedRoute} />
              ) : (
                <EmptyState title="No route selected" description="Select a route from the table below." />
              )}
            </Panel>
          </div>

          <Panel className="analytics-table-panel">
            <div className="panel-heading table-heading">
              <div>
                <h2>Hub records</h2>
                <p>Shipments handled count distinct shipments with a status-history event at the hub.</p>
              </div>
              <span className="table-count">{formatNumber(visibleHubs.length)} hubs</span>
            </div>
            <HubTable
              items={visibleHubs}
              selectedHubId={selectedHub?.hub_id ?? null}
              onSelect={(hubId) => setHubFilter(String(hubId))}
            />
          </Panel>

          <Panel className="analytics-table-panel">
            <div className="panel-heading table-heading">
              <div>
                <h2>Route relationships</h2>
                <p>Links show stored origin and destination fields only; they are not road geometry or directional telemetry.</p>
              </div>
              <span className="table-count">{formatNumber(visibleRoutes.length)} routes</span>
            </div>
            <RouteTable
              items={visibleRoutes}
              selectedRouteId={selectedRoute?.route_id ?? null}
              onSelect={(routeId) => setRouteFilter(String(routeId))}
            />
          </Panel>

          <p className="geospatial-method-note">
            On-time percentage is null when no delivered shipment has an SLA result. Transit time is
            based on recorded booking and delivery timestamps; absent values remain unavailable.
            Hub shipment counts can overlap because a shipment may have events at multiple hubs.
          </p>
        </>
      )}
    </div>
  )
}
