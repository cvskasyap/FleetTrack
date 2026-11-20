import { useQuery } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useMemo, useState } from 'react'
import { HubVolumeChart, RouteOnTimeChart } from '../../components/charts'
import { Button, EmptyState, ErrorState, LoadingPanel, PageHeader, Panel } from '../../components/ui'
import { fleetApi } from '../../lib/api'
import type { HubPerformance, RoutePerformance } from '../../lib/contracts'
import { formatNumber } from '../../lib/utils'

function onTimeLabel(item: {
  on_time_pct?: number | null
  on_time_shipments: number
  delivered_with_sla_count: number
}) {
  if (item.on_time_pct == null) return '—'
  return `${item.on_time_pct.toFixed(1)}% (${item.on_time_shipments}/${item.delivered_with_sla_count})`
}

function HubTable({ items }: { items: HubPerformance[] }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Hub</th>
            <th scope="col">Location</th>
            <th scope="col">Daily capacity</th>
            <th scope="col">Shipments handled</th>
            <th scope="col">Status events</th>
            <th scope="col">Delivered</th>
            <th scope="col">In progress</th>
            <th scope="col">On time</th>
            <th scope="col">Avg transit</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.hub_id}>
              <td>
                <strong>{item.hub_code} · {item.hub_name}</strong>
              </td>
              <td>{item.city}, {item.state}</td>
              <td>{formatNumber(item.daily_capacity)}</td>
              <td>{formatNumber(item.shipments_handled)}</td>
              <td>{formatNumber(item.scan_count)}</td>
              <td>{formatNumber(item.delivered_shipments)}</td>
              <td>{formatNumber(item.in_progress_shipments)}</td>
              <td>{onTimeLabel(item)}</td>
              <td>{item.average_transit_hours === null ? '—' : `${formatNumber(item.average_transit_hours, 1)} h`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RouteTable({ items }: { items: RoutePerformance[] }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Route</th>
            <th scope="col">Origin</th>
            <th scope="col">Destination</th>
            <th scope="col">Distance</th>
            <th scope="col">Shipments</th>
            <th scope="col">Delivered</th>
            <th scope="col">In progress</th>
            <th scope="col">On time</th>
            <th scope="col">Avg transit</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.route_id}>
              <td>
                <strong>{item.route_code} · {item.route_name}</strong>
              </td>
              <td>{item.origin_hub}<span className="cell-subtext">{item.origin_city}, {item.origin_state}</span></td>
              <td>{item.destination_hub}<span className="cell-subtext">{item.destination_city}, {item.destination_state}</span></td>
              <td>{formatNumber(item.distance_km, 1)} km</td>
              <td>{formatNumber(item.shipment_count)}</td>
              <td>{formatNumber(item.delivered_shipments)}</td>
              <td>{formatNumber(item.in_progress_shipments)}</td>
              <td>{onTimeLabel(item)}</td>
              <td>{item.average_transit_hours === null ? '—' : `${formatNumber(item.average_transit_hours, 1)} h`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function HubRouteIntelligencePage() {
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [selectedHubId, setSelectedHubId] = useState('all')
  const [selectedRouteId, setSelectedRouteId] = useState('all')
  const invalidDateRange = Boolean(fromDate && toDate && fromDate > toDate)
  const filter = useMemo(
    () => ({ fromDate: fromDate || undefined, toDate: toDate || undefined }),
    [fromDate, toDate],
  )
  const hubQuery = useQuery({
    queryKey: ['analytics', 'hubs', filter],
    queryFn: ({ signal }) => fleetApi.hubPerformance({ ...filter, signal }),
    enabled: !invalidDateRange,
  })
  const routeQuery = useQuery({
    queryKey: ['analytics', 'routes', filter],
    queryFn: ({ signal }) => fleetApi.routePerformance({ ...filter, signal }),
    enabled: !invalidDateRange,
  })

  const hubs = hubQuery.data?.items ?? []
  const routes = routeQuery.data?.items ?? []
  const visibleHubs = selectedHubId === 'all'
    ? hubs
    : hubs.filter((item) => item.hub_id === Number(selectedHubId))
  const visibleRoutes = selectedRouteId === 'all'
    ? routes
    : routes.filter((item) => item.route_id === Number(selectedRouteId))
  const retry = () => {
    void hubQuery.refetch()
    void routeQuery.refetch()
  }
  const isLoading = hubQuery.isLoading || routeQuery.isLoading
  const isError = hubQuery.isError || routeQuery.isError

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="NETWORK PERFORMANCE"
        title="Hub & route intelligence"
        description="Compare shipment activity, delivery outcomes and transit time across recorded hubs and routes."
        actions={
          <Button variant="icon" aria-label="Refresh hub and route data" onClick={retry}>
            <RefreshCw size={16} aria-hidden="true" />
          </Button>
        }
      />

      <div className="data-notice">
        <span className="notice-dot" />
        <span>
          <strong>Synthetic demonstration dataset</strong>
          <span className="notice-divider">·</span>
          Hub locations are city/state labels; no coordinates are available
        </span>
      </div>

      <Panel className="analytics-filter-panel">
        <div className="analytics-filter-grid">
          <label>
            Booked from
            <input
              type="date"
              className="select-control"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </label>
          <label>
            Booked through
            <input
              type="date"
              className="select-control"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </label>
          <label>
            Hub
            <select className="select-control" value={selectedHubId} onChange={(event) => setSelectedHubId(event.target.value)}>
              <option value="all">All hubs</option>
              {hubs.map((item) => (
                <option key={item.hub_id} value={item.hub_id}>
                  {item.hub_code} · {item.hub_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Route
            <select className="select-control" value={selectedRouteId} onChange={(event) => setSelectedRouteId(event.target.value)}>
              <option value="all">All routes</option>
              {routes.map((item) => (
                <option key={item.route_id} value={item.route_id}>
                  {item.route_code} · {item.route_name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {invalidDateRange && (
          <p className="analytics-filter-error" role="alert">
            The start date must be on or before the end date.
          </p>
        )}
      </Panel>

      {invalidDateRange ? (
        <Panel>
          <EmptyState
            title="Adjust the booking date range"
            description="Choose a start date on or before the end date to view analytics."
          />
        </Panel>
      ) : isError ? (
        <ErrorState
          title="Hub and route analytics unavailable"
          description="The FleetTrack API could not retrieve performance aggregates."
          onRetry={retry}
        />
      ) : isLoading ? (
        <div className="chart-grid">
          <Panel className="chart-panel"><LoadingPanel rows={6} /></Panel>
          <Panel className="chart-panel"><LoadingPanel rows={6} /></Panel>
        </div>
      ) : (
        <>
          <div className="chart-grid">
            <Panel className="chart-panel">
              <div className="panel-heading">
                <div>
                  <h2>Shipment volume by hub</h2>
                  <p>Distinct shipments with at least one status event recorded at the hub.</p>
                </div>
                <span className="chart-unit">SHIPMENTS</span>
              </div>
              {visibleHubs.length ? (
                <HubVolumeChart items={visibleHubs} />
              ) : (
                <EmptyState title="No hub activity" description="No hubs match the current filters." />
              )}
            </Panel>
            <Panel className="chart-panel">
              <div className="panel-heading">
                <div>
                  <h2>Route on-time comparison</h2>
                  <p>Delivered shipments with a recorded SLA result; routes without results are omitted from the rate.</p>
                </div>
                <span className="chart-unit">ON TIME %</span>
              </div>
              {visibleRoutes.length ? (
                <RouteOnTimeChart items={visibleRoutes} />
              ) : (
                <EmptyState title="No route activity" description="No routes match the current filters." />
              )}
            </Panel>
          </div>

          <Panel className="analytics-table-panel">
            <div className="panel-heading table-heading">
              <div>
                <h2>Hub performance</h2>
                <p>Delivery outcomes are the current status of shipments that recorded an event at each hub.</p>
              </div>
              <span className="table-count">{formatNumber(visibleHubs.length)} hubs</span>
            </div>
            {visibleHubs.length ? (
              <HubTable items={visibleHubs} />
            ) : (
              <EmptyState title="No hubs to display" description="Change the hub filter to view available records." />
            )}
          </Panel>

          <Panel className="analytics-table-panel">
            <div className="panel-heading table-heading">
              <div>
                <h2>Route performance</h2>
                <p>Transit hours are measured from booking to the recorded delivered timestamp.</p>
              </div>
              <span className="table-count">{formatNumber(visibleRoutes.length)} routes</span>
            </div>
            {visibleRoutes.length ? (
              <RouteTable items={visibleRoutes} />
            ) : (
              <EmptyState title="No routes to display" description="Change the route filter to view available records." />
            )}
          </Panel>

          <p className="analytics-method-note">
            Date filters select shipments by booking date. A shipment is counted once for each hub where
            its history records an event, so totals across hubs are not additive. On-time percentage is
            on-time delivered shipments divided by delivered shipments with a non-null SLA result; a
            zero denominator is shown as unavailable. In-progress excludes delivered, failed, returned
            and cancelled shipments.
          </p>
        </>
      )}
    </div>
  )
}
