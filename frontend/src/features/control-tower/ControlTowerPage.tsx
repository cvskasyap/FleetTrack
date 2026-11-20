import { useQuery } from '@tanstack/react-query'
import { Clock3, PackageCheck, PackageOpen, RefreshCw, Truck } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import { BookingTrendChart, DeliveryEventChart } from '../../components/charts'
import { EmptyState, ErrorState, LoadingPanel, PageHeader, Panel, Button } from '../../components/ui'
import { fleetApi } from '../../lib/api'
import { formatDate, formatNumber } from '../../lib/utils'
import { ShipmentTable } from '../shipments/ShipmentTable'

type TrendRange = '6m' | '12m' | 'all'

function rangeStart(range: TrendRange) {
  if (range === 'all') return undefined
  const date = new Date()
  date.setUTCDate(1)
  date.setUTCMonth(date.getUTCMonth() - (range === '6m' ? 5 : 11))
  return date.toISOString().slice(0, 7)
}

function MetricCard({
  label,
  value,
  note,
  icon: Icon,
  tone,
}: {
  label: string
  value: string
  note: string
  icon: LucideIcon
  tone: 'blue' | 'green' | 'amber' | 'violet'
}) {
  return (
    <Panel className="metric-card">
      <div className="metric-top">
        <span className="metric-label">{label}</span>
        <span className={`metric-icon metric-${tone}`} aria-hidden="true">
          <Icon size={17} strokeWidth={1.8} />
        </span>
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-note">{note}</div>
    </Panel>
  )
}

export function ControlTowerPage() {
  const [range, setRange] = useState<TrendRange>('all')
  const fromMonth = rangeStart(range)
  const summaryQuery = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: ({ signal }) => fleetApi.dashboardSummary(signal),
  })
  const trendsQuery = useQuery({
    queryKey: ['dashboard', 'monthly-trends', range],
    queryFn: ({ signal }) => fleetApi.monthlyTrends(fromMonth, undefined, signal),
  })
  const shipmentsQuery = useQuery({
    queryKey: ['shipments', 'latest'],
    queryFn: ({ signal }) => fleetApi.shipments({ limit: 6, signal }),
  })

  const freshness = useMemo(() => {
    const updatedAt = Math.max(
      summaryQuery.dataUpdatedAt,
      trendsQuery.dataUpdatedAt,
      shipmentsQuery.dataUpdatedAt,
    )
    return updatedAt ? new Date(updatedAt) : null
  }, [summaryQuery.dataUpdatedAt, trendsQuery.dataUpdatedAt, shipmentsQuery.dataUpdatedAt])

  const isError = summaryQuery.isError || trendsQuery.isError
  const retry = () => {
    void summaryQuery.refetch()
    void trendsQuery.refetch()
  }
  const rangeOptions: { value: TrendRange; label: string }[] = [
    { value: '6m', label: '6 months' },
    { value: '12m', label: '12 months' },
    { value: 'all', label: 'All available' },
  ]

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="OPERATIONS OVERVIEW"
        title="Executive control tower"
        description="A clear view of shipment throughput and delivery performance across the active network."
        actions={
          <div className="dashboard-actions">
            <label className="sr-only" htmlFor="trend-range">
              Trend date range
            </label>
            <select
              id="trend-range"
              className="select-control"
              value={range}
              onChange={(event) => setRange(event.target.value as TrendRange)}
            >
              {rangeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <Button
              variant="icon"
              aria-label="Refresh dashboard data"
              title="Refresh dashboard data"
              onClick={retry}
            >
              <RefreshCw size={16} />
            </Button>
          </div>
        }
      />

      <div className="data-notice">
        <span className="notice-dot" />
        <span>
          <strong>Synthetic demonstration dataset</strong>
          <span className="notice-divider">·</span>
          Not live carrier telemetry or real-world performance
        </span>
        <span className="freshness">
          <Clock3 size={13} />
          {freshness ? `Updated ${freshness.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Waiting for data'}
        </span>
      </div>

      {isError ? (
        <ErrorState
          title="Control tower data unavailable"
          description="The dashboard could not retrieve current data from the FleetTrack API."
          onRetry={retry}
        />
      ) : summaryQuery.isLoading ? (
        <div className="metric-grid" aria-label="Loading dashboard metrics">
          {Array.from({ length: 4 }, (_, index) => (
            <Panel key={index} className="metric-card metric-skeleton">
              <LoadingPanel rows={3} />
            </Panel>
          ))}
        </div>
      ) : summaryQuery.data ? (
        <div className="metric-grid">
          <MetricCard
            label="Shipments in dataset"
            value={formatNumber(summaryQuery.data.total_shipments)}
            note="All currently recorded shipments"
            icon={PackageOpen}
            tone="blue"
          />
          <MetricCard
            label="Delivered"
            value={formatNumber(summaryQuery.data.delivered_shipments)}
            note="Current status is delivered"
            icon={PackageCheck}
            tone="green"
          />
          <MetricCard
            label="In progress"
            value={formatNumber(summaryQuery.data.in_progress_shipments)}
            note="Excludes delivered, failed, returned and cancelled"
            icon={Truck}
            tone="violet"
          />
          <MetricCard
            label="On-time delivery"
            value={summaryQuery.data.on_time_pct === null ? '—' : `${summaryQuery.data.on_time_pct.toFixed(1)}%`}
            note={
              summaryQuery.data.average_transit_hours === null
                ? 'No completed transit records'
                : `${summaryQuery.data.average_transit_hours.toFixed(1)} h mean transit`
            }
            icon={Clock3}
            tone="amber"
          />
        </div>
      ) : (
        <Panel>
          <EmptyState title="No shipment data" description="The API returned no dashboard summary." />
        </Panel>
      )}

      <div className="chart-grid">
        <Panel className="chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Booking cohorts</h2>
              <p>Shipments booked and currently delivered, grouped by booking month.</p>
            </div>
            <span className="chart-unit">SHIPMENTS</span>
          </div>
          {trendsQuery.isLoading ? (
            <LoadingPanel rows={5} />
          ) : trendsQuery.isError ? (
            <ErrorState
              title="Booking trend unavailable"
              description="The monthly booking query could not be completed."
              onRetry={() => void trendsQuery.refetch()}
            />
          ) : trendsQuery.data?.items.length ? (
            <BookingTrendChart items={trendsQuery.data.items} />
          ) : (
            <EmptyState title="No booking history" description="There are no booking records in this time range." />
          )}
          <div className="chart-footnote">
            A cohort view: delivered counts refer to the current status of shipments booked in that month.
          </div>
        </Panel>

        <Panel className="chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Delivery event trend</h2>
              <p>Shipments grouped by their recorded delivery timestamp.</p>
            </div>
            <span className="chart-unit">SHIPMENTS / MONTH</span>
          </div>
          {trendsQuery.isLoading ? (
            <LoadingPanel rows={5} />
          ) : trendsQuery.isError ? (
            <ErrorState
              title="Delivery trend unavailable"
              description="The monthly delivery query could not be completed."
              onRetry={() => void trendsQuery.refetch()}
            />
          ) : trendsQuery.data?.items.length ? (
            <DeliveryEventChart items={trendsQuery.data.items} />
          ) : (
            <EmptyState title="No delivery events" description="There are no recorded deliveries in this time range." />
          )}
          <div className="chart-footnote">
            This is delivery-event timing, separate from the booking-month cohort chart.
          </div>
        </Panel>
      </div>

      <Panel className="table-panel">
        <div className="panel-heading table-heading">
          <div>
            <h2>Latest shipment activity</h2>
            <p>Recently booked shipments from the operational register.</p>
          </div>
          {shipmentsQuery.data && (
            <span className="table-count">{formatNumber(shipmentsQuery.data.total)} total</span>
          )}
        </div>
        {shipmentsQuery.isLoading ? (
          <LoadingPanel rows={5} />
        ) : shipmentsQuery.isError ? (
          <ErrorState
            title="Shipment register unavailable"
            description="Recent operational records could not be retrieved."
            onRetry={() => void shipmentsQuery.refetch()}
          />
        ) : shipmentsQuery.data?.items.length ? (
          <ShipmentTable shipments={shipmentsQuery.data.items} compact />
        ) : (
          <EmptyState title="No shipments yet" description="Shipment records will appear here when available." />
        )}
      </Panel>

      {freshness && <p className="source-note">Source: FleetTrack API · Snapshot read at {formatDate(freshness.toISOString())}</p>}
    </div>
  )
}
