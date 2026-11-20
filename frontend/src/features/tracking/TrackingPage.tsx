import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingPanel, PageHeader, Panel, Button } from '../../components/ui'
import { fleetApi } from '../../lib/api'
import type { ShipmentTracking } from '../../lib/contracts'
import { formatDate } from '../../lib/utils'

function EventTimeline({
  title,
  events,
  source,
}: {
  title: string
  events: { status: string; event_at: string; hub_name?: string | null; notes?: string | null }[]
  source: string
}) {
  if (!events.length) {
    return (
      <Panel className="timeline-panel">
        <div className="panel-heading">
          <div>
            <h2>{title}</h2>
            <p>{source}</p>
          </div>
        </div>
        <EmptyState title="No events found" description="No records are available in this event store." />
      </Panel>
    )
  }

  return (
    <Panel className="timeline-panel">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          <p>{source}</p>
        </div>
        <span className="table-count">{events.length} events</span>
      </div>
      <ol className="event-timeline">
        {events.map((event, index) => (
          <li key={`${event.event_at}-${event.status}-${index}`}>
            <span className="timeline-marker" aria-hidden="true" />
            <div className="timeline-content">
              <div className="timeline-topline">
                <strong>{event.status.replaceAll('_', ' ')}</strong>
                <time dateTime={event.event_at}>{formatDate(event.event_at)}</time>
              </div>
              <span>{event.hub_name ?? 'Location not recorded'}</span>
              {event.notes && <p>{event.notes}</p>}
            </div>
          </li>
        ))}
      </ol>
    </Panel>
  )
}

function TrackingDetails({ tracking }: { tracking: ShipmentTracking }) {
  const relational = useMemo(
    () => [...tracking.relational_events].sort((a, b) => a.event_at.localeCompare(b.event_at)),
    [tracking.relational_events],
  )
  const mongo = useMemo(
    () => [...tracking.mongo_events].sort((a, b) => a.event_at.localeCompare(b.event_at)),
    [tracking.mongo_events],
  )

  return (
    <>
      <Panel className="tracking-summary">
        <div>
          <p className="eyebrow">TRACKING NUMBER</p>
          <h2>{tracking.tracking_number}</h2>
          <p>Separate event views from the relational audit and MongoDB scan store.</p>
        </div>
        <div className="tracking-counts">
          <div>
            <strong>{relational.length}</strong>
            <span>PostgreSQL events</span>
          </div>
          <div>
            <strong>{mongo.length}</strong>
            <span>MongoDB scans</span>
          </div>
        </div>
      </Panel>
      <div className="timeline-grid">
        <EventTimeline
          title="Status history"
          source="PostgreSQL · shipment_status_history"
          events={relational}
        />
        <EventTimeline
          title="Tracking scans"
          source="MongoDB · tracking_events"
          events={mongo}
        />
      </div>
    </>
  )
}

export function TrackingPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialId = searchParams.get('shipmentId') ?? ''
  const [trackingNumber, setTrackingNumber] = useState(searchParams.get('tracking') ?? '')
  const [submittedTrackingNumber, setSubmittedTrackingNumber] = useState(
    searchParams.get('tracking') ?? '',
  )
  const shipmentId = Number(initialId) || undefined

  const lookupQuery = useQuery({
    queryKey: ['tracking', 'lookup', submittedTrackingNumber],
    queryFn: ({ signal }) =>
      fleetApi.shipments({ trackingNumber: submittedTrackingNumber, limit: 1, signal }),
    enabled: Boolean(submittedTrackingNumber) && !shipmentId,
  })
  const resolvedShipmentId = shipmentId ?? lookupQuery.data?.items[0]?.shipment_id
  const trackingQuery = useQuery({
    queryKey: ['tracking', resolvedShipmentId],
    queryFn: ({ signal }) => fleetApi.tracking(resolvedShipmentId!, signal),
    enabled: Boolean(resolvedShipmentId),
  })

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const value = trackingNumber.trim()
    setSubmittedTrackingNumber(value)
    if (value) setSearchParams({ tracking: value })
    else setSearchParams({})
  }

  const hasLookupMiss =
    Boolean(submittedTrackingNumber) &&
    lookupQuery.isSuccess &&
    lookupQuery.data.items.length === 0

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="SHIPMENT VISIBILITY"
        title="Shipment tracking"
        description="Inspect the relational status audit and document-store scans without merging their source histories."
      />
      <Panel className="tracking-search-panel">
        <form className="tracking-search-form" onSubmit={submitSearch}>
          <label className="search-field tracking-search-input">
            <Search size={16} aria-hidden="true" />
            <span className="sr-only">Tracking number</span>
            <input
              value={trackingNumber}
              onChange={(event) => setTrackingNumber(event.target.value)}
              placeholder="Enter a tracking number"
              maxLength={32}
            />
          </label>
          <Button variant="primary" type="submit">
            Find shipment
          </Button>
        </form>
        {shipmentId && (
          <div className="tracking-context">
            Opened from shipment register · shipment ID {shipmentId}
            <button type="button" onClick={() => setSearchParams({})}>
              Clear
            </button>
          </div>
        )}
      </Panel>

      {lookupQuery.isLoading || trackingQuery.isLoading ? (
        <LoadingPanel rows={6} />
      ) : lookupQuery.isError || trackingQuery.isError ? (
        <ErrorState
          title="Tracking information unavailable"
          description="The shipment or one of its event stores could not be reached."
          onRetry={() => {
            void lookupQuery.refetch()
            void trackingQuery.refetch()
          }}
        />
      ) : hasLookupMiss ? (
        <EmptyState
          title="Shipment not found"
          description="No shipment matches that tracking number. Check the value and try again."
        />
      ) : trackingQuery.data ? (
        <TrackingDetails tracking={trackingQuery.data} />
      ) : !shipmentId && !submittedTrackingNumber ? (
        <Panel>
          <EmptyState
            title="Search a shipment"
            description="Enter a tracking number to retrieve its PostgreSQL history and MongoDB scans."
          />
        </Panel>
      ) : null}
    </div>
  )
}
