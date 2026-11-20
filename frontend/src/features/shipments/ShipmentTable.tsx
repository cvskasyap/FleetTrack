import { Link } from 'react-router-dom'
import type { Shipment } from '../../lib/contracts'
import { formatDate } from '../../lib/utils'

function statusClass(status: Shipment['status']) {
  if (status === 'delivered') return 'status status-delivered'
  if (status === 'failed' || status === 'exception' || status === 'returned') return 'status status-issue'
  if (status === 'out_for_delivery') return 'status status-active'
  return 'status status-neutral'
}

export function ShipmentTable({
  shipments,
  compact = false,
}: {
  shipments: Shipment[]
  compact?: boolean
}) {
  return (
    <div className="table-scroll">
      <table className={compact ? 'data-table data-table-compact' : 'data-table'}>
        <thead>
          <tr>
            <th scope="col">Tracking number</th>
            <th scope="col">Route</th>
            <th scope="col">Status</th>
            <th scope="col">Priority</th>
            <th scope="col">Booked</th>
            <th scope="col">SLA</th>
          </tr>
        </thead>
        <tbody>
          {shipments.map((shipment) => (
            <tr key={shipment.shipment_id}>
              <td>
                <Link
                  className="tracking-link"
                  to={`/operations/${shipment.shipment_id}`}
                >
                  {shipment.tracking_number}
                </Link>
                <span className="cell-subtext">{shipment.customer_name}</span>
                <Link
                  className="shipment-table-track-link"
                  to={`/tracking?shipmentId=${shipment.shipment_id}`}
                >
                  View event stores
                </Link>
              </td>
              <td>{shipment.route_name}</td>
              <td>
                <span className={statusClass(shipment.status)}>
                  <span className="status-dot" />
                  {shipment.status.replaceAll('_', ' ')}
                </span>
              </td>
              <td>
                <span className="priority-label">{shipment.priority.replace('_', ' ')}</span>
              </td>
              <td className="muted-cell">{formatDate(shipment.booked_at)}</td>
              <td>
                {shipment.on_time === null ? (
                  <span className="muted-cell">Pending</span>
                ) : shipment.on_time ? (
                  <span className="sla-good">On time</span>
                ) : (
                  <span className="sla-late">Late</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
