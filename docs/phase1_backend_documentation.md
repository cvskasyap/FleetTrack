# FleetTrack 2.0 — Phase 1 Backend Documentation

Phase 1 adds a FastAPI backend alongside the existing Streamlit application. PostgreSQL remains the operational source of truth; MongoDB remains the tracking-event store. The API supports database-backed reads and controlled shipment operations. Additive migrations preserve the original eight operational tables while providing status-history consistency, authentication/RBAC, and an explicit cancellation status.

## Architecture

```text
Streamlit fallback ────────────────┐
                                   ├── PostgreSQL 16
FastAPI /api/v1 ─ PostgreSQL repo ─┘
       │
       └──────── MongoDB repo ─────── MongoDB 7 / tracking_events
```

The backend is organized under `backend/fleettrack_api/`:

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app factory, versioned router registration, request IDs, exception handlers, and request logging |
| `core/config.py` | Typed process-environment configuration |
| `core/logging.py` | Structured JSON application logs |
| `core/errors.py` | Safe dependency, not-found, and invalid-request errors |
| `api/v1/routes/` | Health, dashboard, shipment, authentication, and administration HTTP contracts |
| `schemas/` | Pydantic request/response models and domain enums |
| `repositories/postgres.py` | Parameterized PostgreSQL DB-API reads and transactional shipment operations |
| `repositories/mongodb.py` | Read-only access to the existing tracking-event collection |
| `repositories/auth.py` | Parameterized account, session, role, throttling, and audit queries |
| `services/` | Readiness, dashboard, shipment, authentication, and administration logic |
| `dependencies.py`, `dependencies_auth.py` | Injectable repositories, health checks, session/RBAC and CSRF dependencies |

PostgreSQL connections use `psycopg` with dictionary rows and are closed at the end of each request. MongoDB clients are created for the request dependency and closed after use. Shipment mutations use parameterized SQL and transaction boundaries. The API does not create database pools, new MongoDB collections/indexes, or automatically apply migrations.

The original eight operational tables, reference rows, MongoDB collections/indexes/pipelines, and Streamlit fallback are retained. The schema includes additive account-support tables, and sorted SQL migrations provide status-trigger concurrency/idempotency improvements, authentication/RBAC tables, and the `cancelled` status constraint. No old rows are automatically deleted or rewritten. Every status change is written to `shipment_status_history`; the existing database trigger synchronizes `shipments.status`. Delivery attempts are inserted only into `deliveries`, whose trigger appends the single corresponding history event. The API does not update `shipments.status` directly.

## API contracts

FastAPI serves the generated OpenAPI specification at `/openapi.json`, interactive Swagger documentation at `/docs`, and ReDoc at `/redoc`.

| Endpoint | Success response | Behavior |
|---|---|---|
| `GET /api/v1/health/live` | `200` `{"status":"alive"}` | Process liveness only; does not require either database |
| `GET /api/v1/health/ready` | `200` when both stores respond; otherwise `503` | Independently checks PostgreSQL (`SELECT 1`) and MongoDB (`ping`), returning each status |
| `GET /api/v1/dashboard/summary` | `200` `DashboardSummary` | Computes shipment totals, delivered/in-progress counts, on-time percentage, and mean transit hours from `vw_delivery_performance` |
| `GET /api/v1/dashboard/monthly-trends` | `200` `MonthlyTrendsResponse` | Returns booking-month cohort counts and delivery-timestamp-month counts |
| `GET /api/v1/analytics/hubs` | `200` `HubPerformanceResponse`; `401` without a session | Aggregates shipment-history touches, current shipment outcomes, SLA results and transit measures by hub |
| `GET /api/v1/analytics/routes` | `200` `RoutePerformanceResponse`; `401` without a session | Aggregates shipment volume, current outcomes, SLA results and transit measures by route |
| `GET /api/v1/geospatial/network` | `200` `GeospatialNetworkResponse`; `401` without a session | Returns hub/route SQL aggregates, stored origin/destination labels, and explicit coordinate/geometry quality; never infers geographic positions |
| `GET /api/v1/shipments` | `200` `ShipmentListResponse` | Lists shipments with optional filters and bounded pagination |
| `GET /api/v1/shipments/options` | `200` `ShipmentOptions` | Returns active customers, routes, drivers, vehicles and hubs for operation forms |
| `GET /api/v1/shipments/{shipment_id}` | `200` `ShipmentDetail`; `404` if absent | Reads shipment, assignment and route detail from the existing model/view |
| `GET /api/v1/shipments/{shipment_id}/tracking` | `200` `ShipmentTrackingResponse`; `404` if absent | Returns PostgreSQL status history and delivery attempts separately from MongoDB events |
| `GET /api/v1/reports/shipments.csv` | `200` CSV; `401` without a session | Exports the current shipment register from `vw_delivery_performance`; response is marked `Cache-Control: no-store` |
| `POST /api/v1/shipments` | `201` `ShipmentDetail` | Creates a booking and its initial `booked` history event atomically; requires session and CSRF |
| `PATCH /api/v1/shipments/{shipment_id}` | `200` `ShipmentDetail` | Updates booking metadata only; does not accept or write status; requires session and CSRF |
| `POST /api/v1/shipments/{shipment_id}/status` | `200` `ShipmentDetail` | Appends an eligible operator event to `shipment_status_history`; booking/delivery outcomes and cancellation use dedicated operations; requires session and CSRF |
| `POST /api/v1/shipments/{shipment_id}/deliveries` | `200` `ShipmentDetail` | Inserts one delivery attempt and relies on the existing database trigger for history; requires session and CSRF |
| `POST /api/v1/shipments/{shipment_id}/cancel` | `200` `ShipmentDetail` | Appends `cancelled` to history only when still booked with no dispatch/delivery activity; requires session and CSRF |
| `POST /api/v1/auth/login` | `200` `AuthLoginResponse`; `401` or `429` on denial | Verifies credentials and issues opaque server-side session and CSRF cookies |
| `GET /api/v1/auth/me` | `200` `AuthUser`; `401` without a valid session | Reads the active account and roles |
| `POST /api/v1/auth/logout` | `204` | Revokes the session; requires the CSRF header |
| `POST /api/v1/auth/password` | `204` | Changes the signed-in user’s password and revokes existing sessions; requires CSRF |
| `GET /api/v1/admin/users` | `200` `AdminUserList` | Administrator-only account listing |
| `POST /api/v1/admin/users` | `201` `TemporaryPasswordResponse` | Administrator-only account creation; requires CSRF, displays a one-time password, and forces password rotation |
| `PATCH /api/v1/admin/users/{user_id}` | `200` `AdminUserView` | Administrator-only account/role update; requires CSRF |
| `POST /api/v1/admin/users/{user_id}/reset-password` | `200` `TemporaryPasswordResponse` | Administrator-only password reset; requires CSRF and revokes sessions |
| `GET /api/v1/admin/login-attempts` | `200` list of `LoginAttemptView` | Administrator-only login activity |
| `GET /api/v1/admin/audit-logs` | `200` list of `AuditLogView` | Administrator-only audit events |

### Request parameters

- `monthly-trends`: optional `from_month` and `to_month` dates. Any date within the month selects that whole month. The range is inclusive by month; reversed ranges return `422`.
- `analytics/hubs` and `analytics/routes`: optional inclusive `from_date` and `to_date` booking-date filters; reversed ranges return `422`.
- `shipments`: optional `status` (including `cancelled`), `tracking_number` (case-insensitive substring), `limit` (default 50, maximum 100), and `offset` (default 0, non-negative).
- Shipment IDs must be positive integers.
- Shipment create/update inputs validate bounds, timestamps and reference availability. Active vehicles must have sufficient capacity for the shipment weight.
- Status and delivery-event timestamps cannot precede booking or be in the future. Generic status events cannot write booking or delivery-outcome statuses (`booked`, `delivered`, `failed`, `out_for_delivery`, `exception`, `cancelled`); successful delivery can be followed only by a `returned` event.

Migration `sql/migrations/003_cancelled_shipment_status.sql` adds the cancellation value to the two status checks. It is idempotent and changes no existing rows. It must be applied through the project bootstrap/migration process before deploying the new cancellation endpoint; the running database was not changed during implementation.

Authentication uses Argon2id password hashes and random opaque cookies whose session token digests are stored server-side. The session cookie is `HttpOnly`, `SameSite=Strict`, and scoped to `/api/v1`; the separate CSRF cookie is readable by the browser and must be echoed in `X-CSRF-Token` on session and administrator mutations. Session/account responses are marked `Cache-Control: no-store`. Admin and User roles are checked in the API, not only in the frontend.

Create the initial `admin` and `user` accounts only after the schema migrations have run. The bootstrap command prompts without echoing passwords, validates confirmation, hashes with Argon2id, and never prints or logs the password:

```powershell
docker compose exec api python -m fleettrack_api.cli bootstrap-users
```

For local host execution, provide the database connection through the process environment and run `python -m fleettrack_api.cli bootstrap-users` with `PYTHONPATH=backend;src`. If an initial account is missing from a partially initialized database, an existing active administrator must authorize adding it. The command does not overwrite existing credentials.

The monthly response intentionally separates:

- `booked_count`: bookings grouped by `booked_at` month.
- `delivered_in_booking_cohort`: shipments currently marked delivered, grouped by their booking month.
- `delivered_at_count`: shipments grouped by their non-null `delivered_at` month.

These are different measures. The delivered booking cohort is not a delivery-event trend. The latter is a shipment-level timestamp measure; raw history-event counts can include duplicate delivered rows from the existing delivery trigger.

Shipment detail and reference-option measurements (`weight_kg`, `shipping_cost`, and vehicle `capacity_kg`) are returned as JSON numbers for the frontend contract. Shipment create/update inputs continue to use bounded `Decimal` validation before parameterized database writes.

Hub analytics count a shipment once per hub when at least one `shipment_status_history` event has that `hub_id`; the separate scan count is the number of matching history rows. A shipment can therefore contribute to multiple hubs. Delivered and in-progress outcomes use each touched shipment's current status. Route analytics use `shipments.route_id` joined to `vw_delivery_performance`. Both analytics endpoints apply date filters to `shipments.booked_at`. On-time percentage is the count of delivered shipments with `on_time IS TRUE` divided by delivered shipments with a non-null `on_time`, multiplied by 100; it is `NULL` when the denominator is zero. Mean transit hours use non-null `vw_delivery_performance.transit_hours` for currently delivered shipments, which is based on the recorded `delivered_at` and `booked_at`. Hub location is city/state only; the schema has no coordinates.

The geospatial endpoint reuses those read-only hub and route aggregates. It returns explicit `null` coordinate/geometry values and `missing` quality statuses because the current PostgreSQL schema has no facility address, latitude/longitude, or route geometry fields. City/state names are insufficient to geocode a specific facility; no city centroid, map marker, road polyline, or external geocoding result is substituted. Coordinate ranges and coordinate-pair consistency are validated by the typed response schema. The endpoint requires the same authenticated application session as the analytics endpoints and marks its response `Cache-Control: no-store`.

### Error contract

Application errors use a consistent JSON envelope:

```json
{
  "error": {
    "code": "dependency_unavailable",
    "message": "A required data service is unavailable.",
    "dependency": "postgresql"
  }
}
```

Validation errors return `422`, missing shipments return `404`, unavailable dependencies return `503`, and unexpected errors return a generic `500` message. Internal driver messages, connection strings, and exception details are not returned. Responses include an `X-Request-ID` for correlation.

## Environment and Docker

The API reads configuration from its process environment:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `MONGODB_URI` | MongoDB connection string |
| `MONGODB_DATABASE` | Mongo database name; defaults to `fleettrack` |
| `MONGODB_COLLECTION` | Tracking collection; defaults to `tracking_events` |
| `APP_ENV` | Environment label |
| `LOG_LEVEL` | Python logging level; defaults to `INFO` |
| `SESSION_COOKIE_SECURE` | Set `true` behind HTTPS; production settings reject `false` |
| `SESSION_LIFETIME_SECONDS` | Session lifetime; defaults to 28,800 seconds |
| `LOGIN_FAILURE_LIMIT` | Failed attempts per username in the rate-limit window |
| `LOGIN_IP_FAILURE_LIMIT` | Failed attempts per client IP in the rate-limit window |
| `LOGIN_FAILURE_WINDOW_SECONDS` | Rate-limit window; defaults to 900 seconds |

The API does not load a dotenv file. Docker Compose passes database settings to the API and uses the internal service hostnames `postgres` and `mongo`, not `localhost`. Keep credentials in the existing local deployment configuration and out of source, logs, and requests. The existing Streamlit service applies `sql/schema.sql`, sorted migrations, and reference data during bootstrap; do not remove or recreate either named database volume.

To apply pending schema/migrations through the existing Streamlit bootstrap and start the API while retaining the fallback:

```powershell
docker compose up --build -d app api
docker compose ps
```

The API is published on port `8000`; Streamlit remains on port `8501`. The API has a separate container health check against `/api/v1/health/live`. Its startup depends on the PostgreSQL and MongoDB health checks. On an already-migrated database, the API can also be started independently with `docker compose up --build -d api`. No database volume is recreated or reset by these commands.

To run the current project test suite after installing its declared development and API requirements:

```powershell
python -m pip install -r requirements-dev.txt -r backend\requirements.txt
python -B -m pytest -q -p no:cacheprovider
```

For local execution without Compose, set `DATABASE_URL` and `MONGODB_URI` in the process environment to reachable database endpoints, then run:

```powershell
$env:PYTHONPATH = "backend;src"
python -m uvicorn fleettrack_api.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

## Verification instructions

PowerShell examples:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health/live
Invoke-RestMethod http://localhost:8000/api/v1/health/ready
Invoke-RestMethod http://localhost:8000/api/v1/dashboard/summary
Invoke-RestMethod http://localhost:8000/api/v1/dashboard/monthly-trends
Invoke-RestMethod "http://localhost:8000/api/v1/shipments?limit=10"
Invoke-RestMethod http://localhost:8000/api/v1/shipments/1
Invoke-RestMethod http://localhost:8000/api/v1/shipments/1/tracking
```

The shipment CSV export is authenticated and is intended to be downloaded from the signed-in Reports page.

Use `/docs` to inspect schemas and issue requests interactively. `health/live` should work even if databases are unavailable; `health/ready` should report each dependency independently and return `503` if either check fails. Dashboard and shipment responses are queried from the connected databases, not static metrics.

## Testing performed for Phase 1

The automated suite includes API/OpenAPI validation, authentication and authorization tests, CSRF enforcement, login throttling, password rotation, account administration, trigger behavior, parameterized shipment filters, query/path validation, readiness failures, and safe unexpected-error responses.

**Current verification:** the full Python suite completed with **53 passed** against a temporary PostgreSQL 16 container using a tmpfs database; no project database or named volume was used. This includes authenticated create/update/status/delivery/cancel workflows, cancellation eligibility, reference validation, event-trigger behavior, and post-delivery status protection. The host API test client emitted one Starlette deprecation warning about its current `httpx` integration.

The Docker API image also built and started. Manual HTTP checks succeeded for all seven endpoints against the existing database services. Readiness returned `200` with both dependencies `ok`; the existing Streamlit health endpoint continued to return `200 ok`. These are development-stack checks, not a production security or load test.

## Known limitations

- Shipment operations do not yet include role-granular operational permissions or an idempotency header for user-initiated writes. Authentication/CSRF applies to mutations; operation history is recorded in the existing relational event model.
- Predictive scoring, model evaluation, and MongoDB aggregation endpoints are not implemented.
- Shipment-list pagination uses bounded limit/offset; cursor pagination and total-count optimization are not included.
- Monthly buckets follow the PostgreSQL session timezone. Configure and document a consistent database timezone before comparing deployments.
- Authentication covers local username/password, server-side sessions, ADMIN/USER roles, CSRF, login throttling, password rotation, and audit events; SSO, MFA, account recovery, and external identity-provider integration are not implemented.
- Compose’s local defaults are for development. Configure HTTPS, `SESSION_COOKIE_SECURE=true`, least-privilege database credentials, host/network restrictions, and an operational secret-management system before production exposure.
- Existing seed-time reproducibility and historical duplicate delivered events are not retroactively corrected; see the Phase 0 report.
- The legacy Streamlit application remains active as a fallback and is not proxied through FastAPI.
