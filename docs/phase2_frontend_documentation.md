# FleetTrack 2.0 — Phase 2 Frontend Documentation

The standalone React/TypeScript frontend under `frontend/` connects to the FastAPI backend and remains independently runnable; it is not served by Docker Compose. The Streamlit fallback remains available. The authentication stage adds server-session sign-in, forced password rotation, and an administrator-only account management page.

## Architecture

```text
Browser
  └── React 19 + TypeScript + Vite
       ├── React Router — application routes
       ├── TanStack Query — API state, caching, loading and retry behavior
       ├── Zod — runtime validation of API responses
       ├── Apache ECharts — data-backed cohort and event-time charts
       ├── Tailwind CSS + design tokens — layout/styling foundation
       └── Radix UI Dialog / Dropdown Menu — accessible command and menu primitives
             └── Vite /api proxy → http://localhost:8000/api/v1
```

Feature-oriented source layout:

| Path | Responsibility |
|---|---|
| `frontend/src/app/` | Providers, theme state, app shell, route metadata, navigation |
| `frontend/src/components/` | Shared controls, state views, and ECharts visualizations |
| `frontend/src/features/control-tower/` | Executive dashboard |
| `frontend/src/features/shipments/` | Searchable register, authenticated booking dialog, shipment detail, and operations workflows |
| `frontend/src/features/tracking/` | Tracking lookup and separate source timelines |
| `frontend/src/features/admin/` | Administrator-only account management and one-time credential display |
| `frontend/src/features/reports/` | Authenticated PostgreSQL-backed shipment CSV export |
| `frontend/src/features/hub-route-intelligence/` | Hub and route aggregate analytics, comparison charts, filters, and tables |
| `frontend/src/features/geospatial/` | Authenticated network coverage, geographic data-quality states, and selectable hub/route records |
| `frontend/src/features/placeholders/` | Honest development-state pages for unsupported modules |
| `frontend/src/lib/api.ts` | Central typed API client, HTTP errors, and Zod validation |
| `frontend/src/lib/contracts.ts` | Runtime schemas and inferred API types |
| `frontend/src/auth/` | Session context, sign-in, forced password change, and session status states |
| `frontend/src/index.css` | Dark/light tokens, responsive shell, component styles, reduced-motion support |
| `frontend/src/test/` | Shared Vitest test setup |

Tailwind is configured in `tailwind.config.cjs` and `postcss.config.cjs`; accessible primitives use Radix UI where interactive menus/dialogs need managed focus and keyboard behavior. Shared button, panel, page-header, loading, empty, and error components establish a consistent UI pattern.

## Routes and module readiness

| Route | Module | Phase 2 state |
|---|---|---|
| `/control-tower` | Executive Control Tower | Live API-backed KPIs, trends, and recent shipment table |
| `/geospatial` | Geospatial Intelligence | Authenticated hub/route records, shipment aggregates, selectable details, and geographic data-quality coverage; map display withheld because verified facility coordinates and route geometry are absent |
| `/operations` | Shipment Operations | Database-backed, filtered register and shipment creation |
| `/operations/:shipmentId` | Shipment detail | Booking edits, history events, delivery attempts, and eligible pre-dispatch cancellation |
| `/tracking` | Shipment Tracking | Tracking-number lookup and PostgreSQL/MongoDB histories |
| `/sla-intelligence` | Predictive SLA Intelligence | Development state; no prediction endpoint/model |
| `/hub-route-intelligence` | Hub & Route Intelligence | Live authenticated hub/route aggregates, booking-date filters, charts, and tables |
| `/event-analytics` | MongoDB Event Analytics | Development state; aggregation API not exposed in Phase 1 |
| `/data-quality` | Data Quality Monitoring | Development state; no data-quality endpoints |
| `/research-lab` | Research & Model Evaluation Lab | Development state; no experiment API |
| `/simulation` | Simulation & What-if Studio | Development state; no simulation API |
| `/reports` | Reports & Exports | Authenticated download of the current shipment register as CSV |
| `/administration` | System Administration | Live for ADMIN role; user creation, role/status management, and password reset |

All 12 modules are registered. Five unsupported workspaces remain clearly marked development and show no fabricated KPIs or simulated operational results. System Administration is hidden from USER navigation/search and is protected by backend role checks.

## API integration

The central client is `frontend/src/lib/api.ts`. It uses same-origin `/api/v1` requests by default and validates response bodies using the Zod schemas in `frontend/src/lib/contracts.ts`. The Vite server proxies `/api` to `http://localhost:8000` and forwards the API origin expected by the sign-in origin check; no CORS change is needed for local frontend development. `VITE_API_BASE_URL` can override the client base URL for a separately configured deployment.

Connected endpoints:

- `GET /health/live` — process liveness.
- `GET /health/ready` — service readiness shown in the command bar.
- `GET /dashboard/summary` — measured PostgreSQL shipment summary.
- `GET /dashboard/monthly-trends` — bookings/cohorts and delivered-at event month.
- `GET /analytics/hubs` and `GET /analytics/routes` — SQL-aggregated shipment touch/route cohorts, current outcomes, on-time rates and delivered transit times; optional inclusive booking-date range.
- `GET /geospatial/network` — authenticated hub/route aggregates, stored origin/destination labels, and validated coordinate/geometry quality. Missing geography is returned as `null` with an explicit `missing` status.
- `GET /shipments` — shipment register, status, and tracking-number filters.
- `GET /shipments/{shipment_id}` — typed shipment detail contract.
- `GET /shipments/options` — active relational records for shipment forms.
- `GET /shipments/{shipment_id}/tracking` — separate relational and MongoDB histories.
- `GET /reports/shipments.csv` — authenticated CSV export of shipment records queried from PostgreSQL at download time.
- `POST /shipments` and `PATCH /shipments/{shipment_id}` — create/update booking metadata.
- `POST /shipments/{shipment_id}/status` — append non-delivery operational events.
- `POST /shipments/{shipment_id}/deliveries` — record delivery outcomes once in `deliveries`; database trigger creates the status-history event.
- `POST /shipments/{shipment_id}/cancel` — append cancellation for eligible booked shipments.
- `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`, and `POST /auth/password` — server-side session and password lifecycle.
- `/admin/users` and its create/update/password-reset operations — ADMIN-only account management.

The API client includes same-origin credentials, validates responses with Zod, and sends the readable CSRF cookie in `X-CSRF-Token` for authenticated mutations. Session tokens are never stored in browser storage. The Executive Control Tower labels the sample as synthetic, shows the time at which its data was last refreshed, and distinguishes booking-month cohorts from shipment delivery timestamps. It uses actual API responses; no analytical values are seeded in frontend source. Shipment mutations use the existing PostgreSQL normalized tables and status-history triggers.

Hub and route intelligence uses the authenticated read-only analytics endpoints. Shipment volume by hub counts each shipment once per hub with a recorded history event; scans count event rows, so hub totals can overlap. Delivery outcomes use current shipment status, and on-time rate uses delivered shipments with a non-null SLA result as its denominator. Transit means use recorded delivered timestamps. Date filters apply to booking date; hub locations show only the city/state fields available in PostgreSQL.

Geospatial Intelligence uses the same database-backed aggregates. The current schema contains hub city/state labels, but no facility addresses, coordinates, or route geometry. The page therefore shows actual hub/route records and lets users select and filter them, while the spatial map remains unavailable. It does not geocode city centroids, draw schematic lines, or represent stored route distances as road paths. No mapping library, tile provider, tile URL, or private map key is configured; pan/zoom/fit controls are intentionally absent until verified spatial data and a map renderer are available.

Administrators can create accounts and assign ADMIN/USER roles, disable accounts, and reset passwords. Temporary passwords are displayed once in the current page state; accounts are required to rotate the temporary password before accessing workspaces. Account and audit changes are enforced and recorded by the backend.

## Design and interaction

- Dark theme is the default; the light theme is switchable from the command bar or account menu and persists locally in the browser.
- Desktop navigation collapses to an icon rail. At smaller viewports it becomes an accessible overlay drawer.
- The command search (`Ctrl+K` or `⌘K`) filters and opens module routes.
- The command search supports listbox semantics, arrow-key selection, Enter activation, and Escape dismissal.
- Breadcrumbs reflect the current route. Health status is refreshed periodically from the readiness API.
- The notification menu clearly reports that no alert feed is connected. The account menu shows the signed-in user and role and provides session sign-out.
- Charts use restrained colors, readable axes, tooltips, and analytical labels. Reduced-motion preferences are respected.
- Loading skeletons, API error states with retry, empty states, `aria` labels, keyboard focus rings, and semantic tables are implemented.
- A route-level React error boundary presents a recoverable reload state when an unexpected render error escapes a page.

## Local development

Prerequisites: Node.js compatible with the installed Vite version (Node 20.19+ or 22.12+), npm, the FastAPI service, and an initialized FleetTrack database.

From PowerShell:

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

Open **http://127.0.0.1:5173**. The frontend remains independently runnable; it does not start, stop, or rebuild API or database services.

On a first deployment, start the normal Compose stack so the Streamlit fallback can apply the idempotent schema/migrations. Then create the initial accounts through the API container’s no-echo bootstrap prompt:

```powershell
docker compose up --build -d
docker compose exec api python -m fleettrack_api.cli bootstrap-users
```

Choose and confirm the initial `admin` and `user` passwords in the interactive prompt; no default passwords are shipped. Do not run first-account setup on an internet-exposed deployment until TLS and production secrets are configured.

Available scripts:

```powershell
npm.cmd run dev
npm.cmd run typecheck
npm.cmd run lint
npm.cmd test
npm.cmd run build
npm.cmd run preview
```

`npm run build` type-checks and produces a static Vite build in `frontend/dist/`. The build can be served independently by a static web server; deployment integration is not part of this phase.

## Testing performed

Vitest, Testing Library, jsdom, and ESLint are configured in the frontend package. Tests cover:

- Runtime API response validation, service errors, and query parameter encoding.
- The dashboard’s real-data interface contract, synthetic-data notice, separate trend definitions, error state, and date-range query.
- Hub/route response validation, null SLA handling, API date filters, chart/table rendering, dimension filters, and retryable errors.
- Geospatial API contract validation, coordinate range/pair checks, missing-geometry rendering, route/hub selection, filtering, empty state, and API error state.
- Application navigation containing all 12 modules, sign-in routing, and forced password rotation.
- Session creation, CSRF header behavior, and one-time admin credential presentation.

**Actual results:** after Geospatial Intelligence was added, `npm.cmd run typecheck`, `npm.cmd run lint`, and `npm.cmd run build` passed; `npm.cmd test` passed **34 tests across 10 files**. The production bundle is **1,177.53 kB minified (373.77 kB gzip)** and retains the existing large-chunk advisory; ECharts remains the primary bundle-size contributor and code splitting is a follow-up optimization. Targeted backend API tests passed **33 tests**. The complete Python suite reported **46 passed, 18 skipped, and 2 failed** in pre-existing `tests/test_auth_cli.py` cases: their mocks patch `getpass`, while the CLI calls `input()`. These failures are unrelated to geospatial code. The API tests emit the existing Starlette/httpx deprecation warning.

Live API verification was performed with the Vite proxy and existing backend: readiness, dashboard summary, filtered shipment list, shipment detail, and combined tracking returned successfully. Integrated browser smoke checks rendered the dashboard charts and data, opened the mobile navigation and command palette, navigated to a development placeholder, and loaded real tracking history from both stores. At 320 px, 768 px, and 1440 px viewport widths, the document did not overflow horizontally; shipment tables remain individually scrollable on narrow screens.

For Hub & Route Intelligence, the deployed API image was rebuilt without restarting PostgreSQL, MongoDB, or the Streamlit fallback. Authenticated browser requests returned 12 hub aggregates and 18 route aggregates; the page rendered both charts and tables. A valid date range returned filtered results, and a reversed range returned the documented `422` validation error. Readiness continued to report both databases healthy.

For Geospatial Intelligence, the rebuilt API returned 12 hubs and 18 routes from PostgreSQL; all 12 hubs reported missing verified coordinates and all 18 routes reported missing geometry. Authenticated browser rendering showed the database-backed shipment aggregates, origin/destination labels, selectable records, and explicit unavailable-map state. Hub and route selections worked, and the document had no horizontal overflow at a 375 px viewport. No markers, tile requests, or inferred lines were emitted.

## Known limitations

- This is a frontend foundation, not a complete implementation of the 12 product modules. Five unsupported modules intentionally remain marked development.
- Shipment operations are protected by authenticated sessions and CSRF. Status and cancellation are appended to `shipment_status_history`; delivery attempts are inserted once into `deliveries` and the database trigger records their history. The delivery endpoint is the only API path for delivery outcomes, avoiding duplicate/manual delivery-history inserts.
- Tracking search currently resolves a tracking number through the bounded shipment-list API, then loads tracking by shipment ID.
- Dashboard trends are bounded to the API’s available booking and delivered-at measures. They are synthetic demonstration data, not live logistics telemetry.
- Authentication currently provides local username/password, server-side sessions, ADMIN/USER roles, CSRF protection, throttling, password rotation, and audit support. SSO, MFA, and account recovery are not implemented. No alert feed, authoritative map-coordinate source, scheduled export job, or model endpoint is connected.
- Component tests use deterministic API fixtures; the Hub & Route page also received an authenticated live browser smoke test. Automated browser end-to-end tests and automated accessibility scanning are not yet configured.
- The chart bundle warning should be addressed before performance-sensitive production deployment.
- The Reports page exports the current shipment register, not a scheduled/reporting warehouse snapshot. Seeded rows are synthetic demonstration data.
- A production geospatial map is blocked on authoritative hub coordinates and route geometry (or facility-level addresses suitable for a permitted, auditable geocoding workflow), plus a configured tile provider with attribution. Current city/state labels do not establish hub locations.
- The production bundle contains no `localhost:8000` or `127.0.0.1:8000` API origin. A broad asset scan does find React Router's generic `http://localhost` URL-resolution fallback; it is not the API base and is used only when no browser location is available.
