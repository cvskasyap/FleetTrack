import * as Dialog from '@radix-ui/react-dialog'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Button, EmptyState, ErrorState, LoadingPanel } from '../../components/ui'
import { fleetApi } from '../../lib/api'

function defaultPromiseDate(): string {
  const date = new Date(Date.now() + 24 * 60 * 60 * 1000)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

function currentLocalDateTime(): string {
  const date = new Date()
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

function localDateTimeToIso(value: string): string {
  return new Date(value).toISOString()
}

export function ShipmentCreateDialog() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const optionsQuery = useQuery({
    queryKey: ['shipment-options'],
    queryFn: ({ signal }) => fleetApi.shipmentOptions(signal),
    enabled: open,
    staleTime: 60_000,
  })
  const createMutation = useMutation({
    mutationFn: fleetApi.createShipment,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['shipments'] })
      setOpen(false)
    },
  })

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const optionalId = (name: string) => {
      const value = String(form.get(name) ?? '')
      return value ? Number(value) : null
    }
    createMutation.mutate({
      customer_id: Number(form.get('customer_id')),
      route_id: Number(form.get('route_id')),
      assigned_driver_id: optionalId('assigned_driver_id'),
      assigned_vehicle_id: optionalId('assigned_vehicle_id'),
      weight_kg: Number(form.get('weight_kg')),
      shipping_cost: Number(form.get('shipping_cost')),
      priority: String(form.get('priority')) as 'standard' | 'express' | 'same_day',
      expected_delivery_at: localDateTimeToIso(String(form.get('expected_delivery_at'))),
      notes: String(form.get('notes') ?? '').trim() || null,
    })
  }

  const options = optionsQuery.data

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button variant="primary">
          <Plus size={16} aria-hidden="true" />
          New shipment
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="command-overlay" />
        <Dialog.Content className="operation-dialog">
          <div className="operation-dialog-heading">
            <div>
              <p className="eyebrow">SHIPMENT OPERATIONS</p>
              <Dialog.Title>Book a shipment</Dialog.Title>
              <Dialog.Description>
                Create a booking using active customer, route and fleet records.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button type="button" className="command-close" aria-label="Close shipment form">
                <X size={17} />
              </button>
            </Dialog.Close>
          </div>

          {optionsQuery.isLoading ? (
            <LoadingPanel rows={4} />
          ) : optionsQuery.isError ? (
            <ErrorState
              title="Booking options unavailable"
              description="Active reference records could not be loaded."
              onRetry={() => void optionsQuery.refetch()}
            />
          ) : options && (!options.customers.length || !options.routes.length) ? (
            <EmptyState
              title="Booking references unavailable"
              description="Active customers and routes are required before a shipment can be booked."
            />
          ) : options ? (
            <form className="operation-form" onSubmit={submit}>
              <div className="operation-form-grid">
                <label className="operation-field">
                  Customer
                  <select name="customer_id" required defaultValue="">
                    <option value="" disabled>Select customer</option>
                    {options.customers.map((item) => (
                      <option key={item.customer_id} value={item.customer_id}>
                        {item.customer_code} · {item.full_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="operation-field">
                  Route
                  <select name="route_id" required defaultValue="">
                    <option value="" disabled>Select route</option>
                    {options.routes.map((item) => (
                      <option key={item.route_id} value={item.route_id}>
                        {item.route_code} · {item.origin_hub} → {item.destination_hub}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="operation-field">
                  Weight (kg)
                  <input name="weight_kg" type="number" min="0.01" max="99999999.99" step="0.01" required />
                </label>
                <label className="operation-field">
                  Shipping cost
                  <input name="shipping_cost" type="number" min="0" max="9999999999.99" step="0.01" required />
                </label>
                <label className="operation-field">
                  Priority
                  <select name="priority" defaultValue="standard">
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
                    min={currentLocalDateTime()}
                    defaultValue={defaultPromiseDate()}
                    required
                  />
                </label>
                <label className="operation-field">
                  Assign driver
                  <select name="assigned_driver_id" defaultValue="">
                    <option value="">Unassigned</option>
                    {options.drivers.map((item) => (
                      <option key={item.driver_id} value={item.driver_id}>
                        {item.driver_code} · {item.full_name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="operation-field">
                  Assign vehicle
                  <select name="assigned_vehicle_id" defaultValue="">
                    <option value="">Unassigned</option>
                    {options.vehicles.map((item) => (
                      <option key={item.vehicle_id} value={item.vehicle_id}>
                        {item.registration_no} · {item.vehicle_type} · {item.capacity_kg} kg
                      </option>
                    ))}
                  </select>
                </label>
                <label className="operation-field operation-field-wide">
                  Booking notes
                  <textarea name="notes" maxLength={2000} rows={3} />
                </label>
              </div>
              {createMutation.isError && (
                <p className="operation-error" role="alert">{createMutation.error.message}</p>
              )}
              <div className="operation-form-actions">
                <Dialog.Close asChild>
                  <Button type="button">Cancel</Button>
                </Dialog.Close>
                <Button variant="primary" type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? 'Booking…' : 'Create booking'}
                </Button>
              </div>
            </form>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
