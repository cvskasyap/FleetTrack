import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, PackageCheck } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Button, EmptyState, ErrorState, LoadingPanel, PageHeader, Panel } from '../../components/ui'
import { fleetApi } from '../../lib/api'
import type { StatusEventStatus } from '../../lib/contracts'
import { formatDate } from '../../lib/utils'

const eventStatuses: StatusEventStatus[] = [
  'picked_up',
  'in_transit',
  'at_hub',
  'returned',
]

function localDateTimeValue(value: string): string {
  const date = new Date(value)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

function dateTimeToIso(value: string): string {
  return new Date(value).toISOString()
}

export function ShipmentDetailPage() {
  const { shipmentId: shipmentIdText } = useParams()
  const shipmentId = Number(shipmentIdText)
  const validId = Number.isInteger(shipmentId) && shipmentId > 0
  const queryClient = useQueryClient()
  const [deliveryStatus, setDeliveryStatus] = useState<
    'delivered' | 'failed' | 'out_for_delivery' | 'exception'
  >('failed')
  const [bookingMessage, setBookingMessage] = useState('')
  const shipmentQuery = useQuery({
    queryKey: ['shipment', shipmentId],
    queryFn: ({ signal }) => fleetApi.shipment(shipmentId, signal),
    enabled: validId,
  })
  const optionsQuery = useQuery({
    queryKey: ['shipment-options'],
    queryFn: ({ signal }) => fleetApi.shipmentOptions(signal),
    enabled: shipmentQuery.isSuccess,
    staleTime: 60_000,
  })
  const trackingQuery = useQuery({
    queryKey: ['tracking', shipmentId],
    queryFn: ({ signal }) => fleetApi.tracking(shipmentId, signal),
    enabled: shipmentQuery.isSuccess,
  })
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['shipment', shipmentId] }),
      queryClient.invalidateQueries({ queryKey: ['tracking', shipmentId] }),
      queryClient.invalidateQueries({ queryKey: ['shipments'] }),
    ])
  }
  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof fleetApi.updateShipment>[1]) =>
      fleetApi.updateShipment(shipmentId, payload),
    onSuccess: refresh,
  })
  const statusMutation = useMutation({
    mutationFn: (payload: Parameters<typeof fleetApi.addShipmentStatusEvent>[1]) =>
      fleetApi.addShipmentStatusEvent(shipmentId, payload),
    onSuccess: refresh,
  })
  const deliveryMutation = useMutation({
    mutationFn: (payload: Parameters<typeof fleetApi.addDeliveryAttempt>[1]) =>
      fleetApi.addDeliveryAttempt(shipmentId, payload),
    onSuccess: refresh,
  })
  const cancellationMutation = useMutation({
    mutationFn: (reason: string) => fleetApi.cancelShipment(shipmentId, reason),
    onSuccess: refresh,
  })

  if (!validId) {
    return (
      <div className="page-stack">
        <PageHeader eyebrow="SHIPMENT OPERATIONS" title="Shipment not found" description="The shipment identifier is invalid." />
        <EmptyState title="Invalid shipment identifier" description="Return to the register and select a shipment." />
      </div>
    )
  }

  if (shipmentQuery.isLoading) {
    return <LoadingPanel rows={7} />
  }

  if (shipmentQuery.isError || !shipmentQuery.data) {
    return (
      <div className="page-stack">
        <PageHeader eyebrow="SHIPMENT OPERATIONS" title="Shipment details" description="Shipment information could not be loaded." />
        <ErrorState
          title="Shipment unavailable"
          description="The shipment could not be retrieved from the FleetTrack API."
          onRetry={() => void shipmentQuery.refetch()}
        />
      </div>
    )
  }

  const shipment = shipmentQuery.data
  const options = optionsQuery.data

  function updateBooking(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const optionalId = (name: string) => {
      const value = String(form.get(name) ?? '')
      return value ? Number(value) : null
    }
    const changes: Parameters<typeof fleetApi.updateShipment>[1] = {}
    const customerId = Number(form.get('customer_id'))
    const routeId = Number(form.get('route_id'))
    const driverId = optionalId('assigned_driver_id')
    const vehicleId = optionalId('assigned_vehicle_id')
    const weight = Number(form.get('weight_kg'))
    const cost = Number(form.get('shipping_cost'))
    const priority = String(form.get('priority')) as 'standard' | 'express' | 'same_day'
    const expectedAt = dateTimeToIso(String(form.get('expected_delivery_at')))
    const notes = String(form.get('notes') ?? '').trim() || null
    if (customerId !== shipment.customer_id) changes.customer_id = customerId
    if (routeId !== shipment.route_id) changes.route_id = routeId
    if (driverId !== shipment.assigned_driver_id) changes.assigned_driver_id = driverId
    if (vehicleId !== shipment.assigned_vehicle_id) changes.assigned_vehicle_id = vehicleId
    if (weight !== shipment.weight_kg) changes.weight_kg = weight
    if (cost !== shipment.shipping_cost) changes.shipping_cost = cost
    if (priority !== shipment.priority) changes.priority = priority
    if (new Date(expectedAt).getTime() !== new Date(shipment.expected_delivery_at).getTime()) {
      changes.expected_delivery_at = expectedAt
    }
    if (notes !== shipment.notes) changes.notes = notes
    if (!Object.keys(changes).length) {
      setBookingMessage('No booking changes to save.')
      return
    }
    setBookingMessage('')
    updateMutation.mutate(changes)
  }

  function recordStatus(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const hubId = String(form.get('hub_id') ?? '')
    statusMutation.mutate({
      status: String(form.get('status')) as StatusEventStatus,
      hub_id: hubId ? Number(hubId) : null,
      notes: String(form.get('notes') ?? '').trim() || null,
    }, {
      onSuccess: () => formElement.reset(),
    })
  }

  function recordDelivery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    deliveryMutation.mutate({
      delivery_status: String(form.get('delivery_status')) as typeof deliveryStatus,
      recipient_name: String(form.get('recipient_name') ?? '').trim() || null,
      failure_reason: String(form.get('failure_reason') ?? '').trim() || null,
      notes: String(form.get('notes') ?? '').trim() || null,
    }, {
      onSuccess: () => {
        formElement.reset()
        setDeliveryStatus('failed')
      },
    })
  }

  function cancelShipment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    cancellationMutation.mutate(String(form.get('reason') ?? '').trim(), {
      onSuccess: () => formElement.reset(),
    })
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="SHIPMENT OPERATIONS"
        title={shipment.tracking_number}
        description={`${shipment.customer_name} · ${shipment.route_name}`}
        actions={
          <>
            <Link className="button button-secondary inline-flex items-center gap-2" to="/operations">
              <ArrowLeft size={15} aria-hidden="true" />
              Register
            </Link>
            <Link
              className="button button-secondary inline-flex items-center gap-2"
              to={`/tracking?shipmentId=${shipment.shipment_id}`}
            >
              <ExternalLink size={15} aria-hidden="true" />
              Tracking view
            </Link>
          </>
        }
      />

      <Panel className="shipment-record-summary">
        <div>
          <p className="eyebrow">CURRENT STATUS</p>
          <strong className={`status status-${shipment.status === 'delivered' ? 'delivered' : shipment.status === 'cancelled' ? 'neutral' : 'active'}`}>
            <span className="status-dot" />
            {shipment.status.replaceAll('_', ' ')}
          </strong>
        </div>
        <div>
          <p className="eyebrow">BOOKED</p>
          <strong>{formatDate(shipment.booked_at)}</strong>
        </div>
        <div>
          <p className="eyebrow">SLA PROMISE</p>
          <strong>{formatDate(shipment.expected_delivery_at)}</strong>
        </div>
        <div>
          <p className="eyebrow">DELIVERY PERFORMANCE</p>
          <strong>
            {shipment.on_time === null ? 'Pending' : shipment.on_time ? 'On time' : 'Late'}
            {shipment.transit_hours !== null && ` · ${shipment.transit_hours.toFixed(1)} h`}
          </strong>
        </div>
      </Panel>

      <div className="shipment-detail-grid">
        <Panel className="operation-section">
          <div className="panel-heading">
            <div>
              <h2>Booking details</h2>
              <p>Update booking metadata; status remains controlled by event history.</p>
            </div>
          </div>
          {optionsQuery.isLoading ? (
            <LoadingPanel rows={4} />
          ) : optionsQuery.isError || !options ? (
            <ErrorState
              title="Reference options unavailable"
              description="Shipment details are available, but booking fields cannot be edited until reference data loads."
              onRetry={() => void optionsQuery.refetch()}
            />
          ) : (
            <form className="operation-form" onSubmit={updateBooking}>
              <div className="operation-form-grid">
                <label className="operation-field">
                  Customer
                  <select name="customer_id" defaultValue={shipment.customer_id} required>
                    {options.customers.map((item) => (
                      <option key={item.customer_id} value={item.customer_id}>
                        {item.customer_code} · {item.full_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="operation-field">
                  Route
                  <select name="route_id" defaultValue={shipment.route_id} required>
                    {!options.routes.some((item) => item.route_id === shipment.route_id) && (
                      <option value={shipment.route_id}>
                        {shipment.route_name} · current route unavailable
                      </option>
                    )}
                    {options.routes.map((item) => (
                      <option key={item.route_id} value={item.route_id}>
                        {item.route_code} · {item.origin_hub} → {item.destination_hub}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="operation-field">
                  Weight (kg)
                  <input name="weight_kg" type="number" min="0.01" max="99999999.99" step="0.01" defaultValue={shipment.weight_kg} required />
                </label>
                <label className="operation-field">
                  Shipping cost
                  <input name="shipping_cost" type="number" min="0" max="9999999999.99" step="0.01" defaultValue={shipment.shipping_cost} required />
                </label>
                <label className="operation-field">
                  Priority
                  <select name="priority" defaultValue={shipment.priority}>
                    <option value="standard">Standard</option>
                    <option value="express">Express</option>
                    <option value="same_day">Same day</option>
                  </select>
                </label>
                <label className="operation-field">
                  SLA promise
                  <input
                    name="expected_delivery_at"
                    type="datetime-local"
                    defaultValue={localDateTimeValue(shipment.expected_delivery_at)}
                    required
                  />
                </label>
                <label className="operation-field">
                  Driver
                  <select name="assigned_driver_id" defaultValue={shipment.assigned_driver_id ?? ''}>
                    <option value="">Unassigned</option>
                    {shipment.assigned_driver_id !== null &&
                      !options.drivers.some((item) => item.driver_id === shipment.assigned_driver_id) && (
                        <option value={shipment.assigned_driver_id}>
                          {shipment.driver_code ?? `Driver ${shipment.assigned_driver_id}`} · current assignment unavailable
                        </option>
                      )}
                    {options.drivers.map((item) => (
                      <option key={item.driver_id} value={item.driver_id}>
                        {item.driver_code} · {item.full_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="operation-field">
                  Vehicle
                  <select name="assigned_vehicle_id" defaultValue={shipment.assigned_vehicle_id ?? ''}>
                    <option value="">Unassigned</option>
                    {shipment.assigned_vehicle_id !== null &&
                      !options.vehicles.some((item) => item.vehicle_id === shipment.assigned_vehicle_id) && (
                        <option value={shipment.assigned_vehicle_id}>
                          {shipment.registration_no ?? `Vehicle ${shipment.assigned_vehicle_id}`} · current assignment unavailable
                        </option>
                      )}
                    {options.vehicles.map((item) => (
                      <option key={item.vehicle_id} value={item.vehicle_id}>
                        {item.registration_no} · {item.vehicle_type} · {item.capacity_kg} kg
                      </option>
                    ))}
                  </select>
                </label>
                <label className="operation-field operation-field-wide">
                  Booking notes
                  <textarea name="notes" maxLength={2000} rows={3} defaultValue={shipment.notes ?? ''} />
                </label>
              </div>
              {updateMutation.isError && <p className="operation-error" role="alert">{updateMutation.error.message}</p>}
              {(bookingMessage || updateMutation.isSuccess) && (
                <p className="operation-success" role="status">
                  {bookingMessage || 'Booking details saved.'}
                </p>
              )}
              <div className="operation-form-actions">
                <Button variant="primary" type="submit" disabled={updateMutation.isPending || !options}>
                  {updateMutation.isPending ? 'Saving…' : 'Save booking'}
                </Button>
              </div>
            </form>
          )}
        </Panel>

        <div className="shipment-operations-stack">
          <Panel className="operation-section">
            <div className="panel-heading">
              <div>
                <h2>Record status event</h2>
                <p>Writes to shipment_status_history; database trigger projects canonical status.</p>
              </div>
            </div>
            <form className="operation-form" onSubmit={recordStatus}>
              <div className="operation-form-grid">
                <label className="operation-field">
                  Status
                  <select name="status" defaultValue="picked_up">
                    {eventStatuses.map((status) => (
                      <option key={status} value={status}>{status.replaceAll('_', ' ')}</option>
                    ))}
                  </select>
                </label>
                <label className="operation-field">
                  Hub
                  <select name="hub_id" defaultValue="">
                    <option value="">No hub recorded</option>
                    {options?.hubs.map((hub) => (
                      <option key={hub.hub_id} value={hub.hub_id}>{hub.hub_code} · {hub.hub_name}</option>
                    ))}
                  </select>
                </label>
                <label className="operation-field operation-field-wide">
                  Event notes
                  <textarea name="notes" maxLength={500} rows={2} />
                </label>
              </div>
              {statusMutation.isError && <p className="operation-error" role="alert">{statusMutation.error.message}</p>}
              <div className="operation-form-actions">
                <Button variant="primary" type="submit" disabled={statusMutation.isPending || shipment.status === 'cancelled'}>
                  {statusMutation.isPending ? 'Recording…' : 'Record event'}
                </Button>
              </div>
            </form>
          </Panel>

          <Panel className="operation-section">
            <div className="panel-heading">
              <div>
                <h2>Delivery attempt</h2>
                <p>Delivery records create their own idempotent history events through the database trigger.</p>
              </div>
            </div>
            <form className="operation-form" onSubmit={recordDelivery}>
              <div className="operation-form-grid">
                <label className="operation-field">
                  Outcome
                  <select
                    name="delivery_status"
                    value={deliveryStatus}
                    onChange={(event) => setDeliveryStatus(event.target.value as typeof deliveryStatus)}
                  >
                    <option value="failed">Failed</option>
                    <option value="delivered">Delivered</option>
                    <option value="out_for_delivery">Out for delivery</option>
                    <option value="exception">Exception</option>
                  </select>
                </label>
                <label className="operation-field">
                  Recipient
                  <input name="recipient_name" maxLength={120} required={deliveryStatus === 'delivered'} />
                </label>
                <label className="operation-field operation-field-wide">
                  Failure reason
                  <input name="failure_reason" maxLength={240} />
                </label>
                <label className="operation-field operation-field-wide">
                  Attempt notes
                  <textarea name="notes" maxLength={500} rows={2} />
                </label>
              </div>
              {deliveryMutation.isError && <p className="operation-error" role="alert">{deliveryMutation.error.message}</p>}
              <div className="operation-form-actions">
                <Button
                  variant="primary"
                  type="submit"
                  disabled={deliveryMutation.isPending || ['delivered', 'returned', 'cancelled'].includes(shipment.status)}
                >
                  {deliveryMutation.isPending ? 'Recording…' : 'Record attempt'}
                </Button>
              </div>
            </form>
          </Panel>

          {shipment.status === 'booked' && (
            <Panel className="operation-section operation-cancel-section">
              <div className="panel-heading">
                <div>
                  <h2>Cancel booking</h2>
                  <p>Only bookings without dispatch or delivery activity can be cancelled.</p>
                </div>
              </div>
              <form className="operation-form" onSubmit={cancelShipment}>
                <label className="operation-field">
                  Cancellation reason
                  <input name="reason" minLength={3} maxLength={240} required />
                </label>
                {cancellationMutation.isError && <p className="operation-error" role="alert">{cancellationMutation.error.message}</p>}
                <div className="operation-form-actions">
                  <Button type="submit" disabled={cancellationMutation.isPending}>
                    {cancellationMutation.isPending ? 'Cancelling…' : 'Cancel shipment'}
                  </Button>
                </div>
              </form>
            </Panel>
          )}
        </div>
      </div>

      <Panel className="operation-section">
        <div className="panel-heading">
          <div>
            <h2>Operational history</h2>
            <p>PostgreSQL status audit, delivery attempts and MongoDB scan documents remain distinct sources.</p>
          </div>
        </div>
        {trackingQuery.isLoading ? (
          <LoadingPanel rows={4} />
        ) : trackingQuery.isError || !trackingQuery.data ? (
          <ErrorState
            title="Event history unavailable"
            description="The PostgreSQL or MongoDB event source could not be reached."
            onRetry={() => void trackingQuery.refetch()}
          />
        ) : (
          <div className="shipment-history-grid">
            <EventList
              title="Status audit · PostgreSQL"
              empty="No relational status events are recorded."
              items={trackingQuery.data.relational_events.map((item) => ({
                key: `${item.event_at}-${item.status}`,
                label: item.status.replaceAll('_', ' '),
                date: item.event_at,
                detail: [item.hub_name, item.notes].filter(Boolean).join(' · '),
              }))}
            />
            <EventList
              title="Delivery attempts"
              empty="No delivery attempts are recorded."
              items={trackingQuery.data.delivery_attempts.map((item) => ({
                key: String(item.delivery_id),
                label: `Attempt ${item.attempt_no} · ${item.delivery_status.replaceAll('_', ' ')}`,
                date: item.attempted_at,
                detail: [item.recipient_name, item.failure_reason, item.notes].filter(Boolean).join(' · '),
              }))}
            />
            <EventList
              title="Scan events · MongoDB"
              empty="No document-store scans are recorded."
              items={trackingQuery.data.mongo_events.map((item, index) => ({
                key: `${item.event_at}-${item.status}-${index}`,
                label: item.status.replaceAll('_', ' '),
                date: item.event_at,
                detail: [item.hub_name, item.hub_city, item.notes].filter(Boolean).join(' · '),
              }))}
            />
          </div>
        )}
      </Panel>
    </div>
  )
}

function EventList({
  title,
  empty,
  items,
}: {
  title: string
  empty: string
  items: { key: string; label: string; date: string; detail: string }[]
}) {
  return (
    <section className="shipment-history-source">
      <h3>{title}</h3>
      {items.length ? (
        <ol className="shipment-history-list">
          {items.map((item) => (
            <li key={item.key}>
              <span className="timeline-marker" aria-hidden="true" />
              <div>
                <strong>{item.label}</strong>
                <time dateTime={item.date}>{formatDate(item.date)}</time>
                {item.detail && <p>{item.detail}</p>}
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="shipment-history-empty"><PackageCheck size={15} />{empty}</p>
      )}
    </section>
  )
}
