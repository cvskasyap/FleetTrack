import { Download, FileSpreadsheet } from 'lucide-react'
import { PageHeader, Panel } from '../../components/ui'

export function ReportsPage() {
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="REPORTS & EXPORTS"
        title="Operational reports"
        description="Export the current PostgreSQL shipment snapshot for analysis or review."
      />
      <Panel className="report-export-panel">
        <div className="report-export-icon" aria-hidden="true">
          <FileSpreadsheet size={20} />
        </div>
        <div className="report-export-copy">
          <p className="eyebrow">DATABASE-BACKED EXPORT</p>
          <h2>Shipment register · CSV</h2>
          <p>
            Includes shipment identifiers, customer and route labels, status, SLA timestamps,
            delivery outcome, transit time, weight, and shipping cost. Values are queried when
            downloaded; no report data is fabricated in the frontend.
          </p>
          <p className="synthetic-notice">
            Seeded project records are synthetic demonstration data, not real logistics performance.
          </p>
          <a
            className="button button-primary inline-flex items-center gap-2"
            href="/api/v1/reports/shipments.csv"
            download="fleettrack_shipments.csv"
          >
            <Download size={15} aria-hidden="true" />
            Download shipment CSV
          </a>
        </div>
      </Panel>
    </div>
  )
}
