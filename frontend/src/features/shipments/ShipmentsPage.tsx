import { useQuery } from '@tanstack/react-query'
import { Search, SlidersHorizontal } from 'lucide-react'
import { useState } from 'react'
import { ErrorState, LoadingPanel, PageHeader, Panel, EmptyState } from '../../components/ui'
import { fleetApi } from '../../lib/api'
import type { ShipmentStatus } from '../../lib/contracts'
import { ShipmentCreateDialog } from './ShipmentCreateDialog'
import { ShipmentTable } from './ShipmentTable'

const statuses: { value: ShipmentStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'booked', label: 'Booked' },
  { value: 'picked_up', label: 'Picked up' },
  { value: 'in_transit', label: 'In transit' },
  { value: 'at_hub', label: 'At hub' },
  { value: 'out_for_delivery', label: 'Out for delivery' },
  { value: 'delivered', label: 'Delivered' },
  { value: 'failed', label: 'Failed' },
  { value: 'exception', label: 'Exception' },
  { value: 'returned', label: 'Returned' },
  { value: 'cancelled', label: 'Cancelled' },
]

export function ShipmentsPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<ShipmentStatus | 'all'>('all')
  const shipmentsQuery = useQuery({
    queryKey: ['shipments', status, search],
    queryFn: ({ signal }) =>
      fleetApi.shipments({
        status,
        trackingNumber: search.trim() || undefined,
        limit: 50,
        signal,
      }),
  })

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="OPERATIONS"
        title="Shipment register"
        description="Book and inspect shipments, then manage operational events from each shipment record."
        actions={<ShipmentCreateDialog />}
      />

      <Panel className="register-panel">
        <div className="register-toolbar">
          <label className="search-field">
            <Search size={16} aria-hidden="true" />
            <span className="sr-only">Search by tracking number</span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search tracking number"
              maxLength={32}
            />
          </label>
          <label className="filter-field">
            <SlidersHorizontal size={15} aria-hidden="true" />
            <span className="sr-only">Filter by shipment status</span>
            <select
              className="select-control"
              value={status}
              onChange={(event) => setStatus(event.target.value as ShipmentStatus | 'all')}
            >
              {statuses.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {shipmentsQuery.data && (
            <span className="results-count">{shipmentsQuery.data.total.toLocaleString()} records</span>
          )}
        </div>
        {shipmentsQuery.isLoading ? (
          <LoadingPanel rows={6} />
        ) : shipmentsQuery.isError ? (
          <ErrorState
            title="Shipment register unavailable"
            description="The FleetTrack API could not return shipment records."
            onRetry={() => void shipmentsQuery.refetch()}
          />
        ) : shipmentsQuery.data?.items.length ? (
          <>
            <ShipmentTable shipments={shipmentsQuery.data.items} />
            <div className="register-footnote">
              Showing up to {shipmentsQuery.data.limit} records. Select a tracking number to inspect its event history.
            </div>
          </>
        ) : (
          <EmptyState
            title="No matching shipments"
            description="Try a different tracking number or status filter."
          />
        )}
      </Panel>
    </div>
  )
}
