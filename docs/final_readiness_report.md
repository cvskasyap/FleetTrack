# FleetTrack 2.0 — Final Readiness Report

## Verdict

**NOT READY — BLOCKING ISSUES REMAIN.**

The local stack is running and both databases report ready, but the live database has **zero user accounts**. As a result, Admin/User sign-in, the authenticated Control Tower, shipment workflows, and authenticated CSV download could not be verified end to end. Do not present this as a complete production release.

## Verified status

| Area | Result |
|---|---|
| FastAPI liveness | `GET /api/v1/health/live` returned `alive` |
| Database readiness | `GET /api/v1/health/ready` returned `ready`; PostgreSQL and MongoDB each returned `ok` |
| PostgreSQL records | Read-only counts: 1,500 shipments, 9,346 status-history rows, 0 users |
| MongoDB | API readiness ping succeeded. Direct collection inspection was not possible because the Mongo server requires authentication; no credentials were inspected. |
| React/Vite | `http://127.0.0.1:5173/login` returned HTTP 200 and rendered the sign-in form |
| Streamlit fallback | `http://localhost:8501/_stcore/health` returned `ok` |
| OpenAPI | Generated schema includes the new shipment CSV route |
| Authentication | Unauthenticated dashboard and CSV requests returned `401`, as expected. No Admin or User account exists to test a real login. |

### Compose services

At the last check, all four Compose containers were running:

- `fleettrack-api-1` — healthy
- `fleettrack-postgres-1` — healthy
- `fleettrack-mongo-1` — healthy
- `fleettrack-app-1` (Streamlit fallback) — running; this service has no Compose health status configured

The API alone was rebuilt for this sprint. PostgreSQL and MongoDB volumes were preserved.

## Changes and database safety

Before deploying, a custom-format PostgreSQL backup was created and its archive was verified. The backup was restored into a disposable PostgreSQL instance; migrations 001–003 were applied there first. The live migrations were then applied without changing the existing shipment or status-history counts. A status-history trigger check was run in a transaction and rolled back.

The backup is stored outside the project at:

`C:\Users\cvsch\.copilot\session-state\a6d0cf2d-4f7b-43d4-a6d1-8c77c6cf44e5\files\fleettrack-pre-readiness.dump`

No database volume was deleted or reset, `.env` was not opened or overwritten, and no credentials were printed. See [Phase 1 backend documentation](./phase1_backend_documentation.md) for the API, database, and migration details.

## Working code and remaining verification

### Implemented and checked

- FastAPI liveness/readiness checks and generated OpenAPI.
- React sign-in page and standalone Vite development server.
- Database-backed shipment CSV endpoint at `GET /api/v1/reports/shipments.csv`. It requires an authenticated session, queries `vw_delivery_performance`, and returns `Cache-Control: no-store`. The API test verifies CSV headers and database-derived row content with a fake repository.
- Shipment create/update/status/delivery/cancellation code and trigger behavior passed a prior **53-test isolated PostgreSQL integration run**. That full disposable-database suite was not rerun during this sprint.

### Not verified against the live stack

- Admin and User credentials/sign-in: **not verified**; there are no accounts in the live database.
- Authenticated Control Tower and dashboard data: **not verified**. The live summary endpoint rejects anonymous requests with `401`.
- Authenticated shipment creation, status changes, tracking, and CSV download: **not verified** in the browser or against the live API.
- MongoDB collection contents and pipeline execution: not verified directly during this sprint; readiness confirms connection only.
- Streamlit health is verified, but its full application workflows were not smoke-tested.

The new Reports page provides the CSV download link. Geospatial intelligence, SLA prediction, hub/route analytics, MongoDB event analytics, data-quality monitoring, research/model evaluation, and simulation remain development placeholders. No map coordinates or model results were fabricated. Seeded project records are synthetic demonstration data, not real logistics performance. See [Phase 2 frontend documentation](./phase2_frontend_documentation.md) for current frontend scope.

## Test results

Commands executed after the CSV change:

- `python -m pytest -q` — **36 passed, 18 skipped**, one Starlette/httpx deprecation warning. The skipped tests require a disposable PostgreSQL test database; none were pointed at the live database.
- `python -m pytest -q ..\tests\test_backend_api.py` from `backend\` — **21 passed**, one deprecation warning.
- From `frontend\`: `npm.cmd run typecheck` — passed.
- `npm.cmd run lint` — passed.
- `npm.cmd test` — **22 passed across 7 files**.
- `npm.cmd run build` — passed. Vite warns that the main JavaScript bundle is **1,146.57 kB minified / 368.14 kB gzip**, above its 500 kB advisory threshold.

The previous 53-test isolated PostgreSQL run predates this sprint's CSV endpoint; the new endpoint is covered by the targeted API test but has not yet been exercised with an authenticated live download.

## Working URLs

- React development frontend: [http://127.0.0.1:5173/login](http://127.0.0.1:5173/login)
- FastAPI Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- FastAPI readiness: [http://localhost:8000/api/v1/health/ready](http://localhost:8000/api/v1/health/ready)
- Streamlit fallback: [http://localhost:8501](http://localhost:8501)

The React frontend is independently run with Vite and is not a Compose service.

## Startup and account setup

From the project root in PowerShell:

```powershell
docker compose up --build -d
docker compose ps
```

After the API and databases are ready, provision the initial accounts interactively. The command prompts without echoing passwords; choose and confirm the Admin and User passwords yourself:

```powershell
docker compose exec api python -m fleettrack_api.cli bootstrap-users
```

Start the standalone frontend in another PowerShell terminal:

```powershell
Set-Location frontend
npm.cmd run dev -- --host 127.0.0.1
```

Do not use `docker compose down -v` or any volume-removal/reset command.

## Demonstration checklist after account provisioning

1. Sign in with the Admin account and verify the Control Tower loads database-backed metrics.
2. Verify Admin account-management access; sign out and verify a User cannot access administration.
3. Use the shipment register to inspect tracking, create a booking, and record a status or delivery event; confirm the status-history trigger remains authoritative.
4. Download the shipment CSV from Reports and confirm the response contains the current database records.
5. Confirm the Streamlit fallback remains available.

Until these authenticated live checks pass, the correct readiness decision remains **NOT READY — BLOCKING ISSUES REMAIN**.
