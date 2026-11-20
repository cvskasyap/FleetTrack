# FleetTrack data dictionary and normalisation

## Relational entities

| Table | Primary key | Important foreign keys | Purpose |
|---|---|---|---|
| `customers` | `customer_id` | — | Sender/customer master data |
| `hubs` | `hub_id` | — | Logistics hub master data and capacity |
| `vehicles` | `vehicle_id` | — | Fleet/vehicle master data |
| `drivers` | `driver_id` | — | Driver and licence master data |
| `routes` | `route_id` | `origin_hub_id`, `destination_hub_id` → `hubs` | Directed lane and route distance |
| `shipments` | `shipment_id` | customer, route, vehicle, driver | Booking, parcel metrics, SLA promise and current status |
| `deliveries` | `delivery_id` | `shipment_id` → `shipments` | Delivery attempts, outcome and recipient/failure detail |
| `shipment_status_history` | `status_history_id` | `shipment_id` → `shipments`; optional `hub_id` → `hubs` | Append-only operational event/audit history; optional unique `event_key` makes retried projections idempotent |

## Functional dependencies

The principal determinants are:

- `customer_id → customer_code, full_name, email, phone, city, state, created_at`
- `hub_id → hub_code, hub_name, city, state, daily_capacity, active`
- `vehicle_id → registration_no, vehicle_type, capacity_kg, active`
- `driver_id → driver_code, full_name, license_no, phone, hire_date, active`
- `route_id → route_code, route_name, origin_hub_id, destination_hub_id, distance_km`
- `shipment_id → tracking_number, customer_id, route_id, assigned_vehicle_id, assigned_driver_id, weight_kg, shipping_cost, priority, booked_at, expected_delivery_at, delivered_at, status, notes`
- `delivery_id → shipment_id, attempt_no, delivery_status, attempted_at, recipient_name, failure_reason, notes`
- `status_history_id → shipment_id, status, hub_id, event_at, notes, source, event_key`

Additional candidate keys are `customer_code`, `email`, `hub_code`, `registration_no`, `driver_code`, `license_no`, `route_code`, `route_name`, `tracking_number`, and `(shipment_id, attempt_no)`.

## Why 3NF is reached

1. **1NF:** attributes are atomic; repeating delivery attempts and status scans are represented as separate rows rather than repeating groups/arrays in a shipment row.
2. **2NF:** each relation uses a single-column surrogate primary key except the delivery-attempt business uniqueness constraint. There are no non-key attributes dependent on only part of a composite primary key.
3. **3NF:** descriptive customer, hub, vehicle, driver and route attributes are stored in their respective master tables. A shipment stores foreign keys rather than repeating customer/hub/driver names or route descriptions. The status audit stores an optional hub key, not repeated hub city/state descriptions. Thus non-key attributes depend on the key, the whole key and no other non-key attribute.

## Derived attributes and history

- `shipments.status` is the status from the latest history row ordered by `event_at DESC, status_history_id DESC`, synchronised by a trigger that locks the parent shipment before inserting history.
- `shipments.delivered_at` is populated from the earliest delivered history event when missing; an existing value is retained if a later status is inserted.
- Delivery-trigger events receive an idempotency key derived from the delivery attempt, status and event timestamp. Older history rows are not deleted or rewritten by the migration.
- `cancelled` is an explicit terminal status added by migration 003. It is valid only for a booked shipment with no dispatch or delivery-attempt history; cancellation is recorded as a status-history event and never deletes the shipment.
- `vw_delivery_performance.on_time` is derived from `delivered_at <= expected_delivery_at`; it is `NULL` for undelivered shipments.
- `transit_hours` is derived from delivered and booked timestamps. It is not duplicated as a stored measure.
- `vw_hub_load_daily` derives daily scan counts from status history.

## Constraints

The schema enforces uniqueness for business identifiers, referential integrity through foreign keys, positive weights/distances/capacities, non-negative delivery costs, allowed status and priority values (including the additive `cancelled` status), and valid booking/expected-delivery chronology. Delivery attempts are unique by `(shipment_id, attempt_no)`.
