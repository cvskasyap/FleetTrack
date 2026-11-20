# FleetTrack 2.0 — Phase 0 Baseline and Acceptance Criteria

**Audit date:** 2026-11-19  
**Scope:** Baseline inspection and acceptance criteria only. No application code, SQL, database records, schema, `.env`, or Docker volumes were modified. PostgreSQL inspection used a read-only transaction. MongoDB inspection used read-only metadata, count, find, and aggregation operations; the CRUD demonstration was not run.

## Evidence labels

- **Verified:** directly observed in repository files or the running services during this audit.
- **Inference:** an explanation supported by the code and observed data, but not a separately measured causal experiment.
- **Recommendation:** proposed future work; not implemented or verified.

## Executive baseline

| Area | Verified result |
|---|---|
| Current application | Streamlit dashboard, operations, tracking search, and MongoDB insights; PostgreSQL and MongoDB accessed by Python |
| PostgreSQL | Connected successfully with `transaction_read_only=on`; eight operational tables and two views present |
| PostgreSQL row counts | 1,500 shipments; 9,346 status-history rows; 1,208 delivery attempts; detailed counts below |
| MongoDB | Connected successfully; one collection, `tracking_events`, with 9,346 documents |
| MongoDB pipelines | Both existing pipelines ran read-only; 12 hub-dwell groups and 33 delay-hotspot groups returned |
| Docker | PostgreSQL and MongoDB report healthy; app container is running |
| Application | Streamlit health endpoint returned HTTP 200 and `ok` |
| Automated tests | **Not run:** `pytest` is unavailable on the host and in the app container. No dependencies were installed. |
| November pattern | 451 shipments were booked in November, versus 188–206 in June–October; 92 shipments have a November `delivered_at`, while 86 November-booked shipments are currently delivered. See the analysis below. |

## 1. Existing architecture and deployment

**Verified:** The current system is a Python/Streamlit application backed by PostgreSQL 16 and MongoDB 7. The Streamlit pages query PostgreSQL through `psycopg` DB-API helpers and query MongoDB through PyMongo. pandas is used for tabular results; Plotly renders dashboard and aggregation charts.

The application currently provides:

- A dashboard in `app.py` with shipment totals, delivery and transit summaries, booking-month trends, route performance, hub activity, and recent shipments.
- Shipment creation, status-event entry, and a shipment register.
- A tracking lookup that reads relational status history and MongoDB scan documents.
- MongoDB event counts, index display, hub dwell analysis, and delay hotspots.

The existing Compose stack has `postgres`, `mongo`, and `app` services. The app waits for database health checks, runs bootstrap/seed scripts, then starts Streamlit. PostgreSQL and MongoDB each use named data volumes. The app has no configured Docker health check; its Streamlit health endpoint was checked separately and returned `200 ok`. All three containers were running during the audit. The database services reported healthy.

**Verified availability:** PostgreSQL and MongoDB connections and the read-only queries below succeeded from the app container. The Streamlit endpoint at `http://localhost:8501/_stcore/health` returned HTTP 200 with body `ok`.

**Deployment risk:** Compose publishes the application and database ports on all host interfaces by default. This is acceptable only in an appropriately protected local environment; before non-local deployment, review network binding, authentication, TLS, and database access controls. Existing named volumes observed were `fleettrack_fleettrack_postgres` and `fleettrack_fleettrack_mongo`; preserve them during migration.

## 2. PostgreSQL baseline

### Tables and row counts

The catalog contains the expected eight base tables. Counts below are actual read-only query results from this running database:

| Table | Rows |
|---|---:|
| `customers` | 20 |
| `hubs` | 12 |
| `vehicles` | 15 |
| `drivers` | 15 |
| `routes` | 18 |
| `shipments` | 1,500 |
| `deliveries` | 1,208 |
| `shipment_status_history` | 9,346 |

The 1,500-shipment count meets the project’s synthetic sample-data expectation. These figures describe the inspected database at audit time, not a general production capacity claim.

### Constraints and relationships

**Verified from PostgreSQL catalogs:** the eight tables have 8 primary-key, 9 foreign-key, 16 check, and 10 unique constraints. The foreign-key relationships are:

- `routes.origin_hub_id` and `routes.destination_hub_id` → `hubs`
- `shipments.customer_id` → `customers`
- `shipments.route_id` → `routes`
- `shipments.assigned_vehicle_id` → `vehicles`
- `shipments.assigned_driver_id` → `drivers`
- `deliveries.shipment_id` → `shipments`
- `shipment_status_history.shipment_id` → `shipments`
- `shipment_status_history.hub_id` → `hubs`

This is the existing normalized operational model. Customers, hubs, vehicles, drivers, and routes are separate reference entities; shipments refer to them by key, and delivery attempts and status events are separate relations.

### Triggers and views

**Verified:** the database has two non-internal triggers:

1. `trg_apply_shipment_status_event` on `shipment_status_history`, which updates the shipment’s current `status` after an event is inserted and sets `delivered_at` when the inserted status is `delivered`.
2. `trg_log_delivery_attempt` on `deliveries`, which writes a status-history event after a delivery row is inserted or its `delivery_status` changes.

The database has two views:

| View | Current rows | Purpose |
|---|---:|---|
| `vw_delivery_performance` | 1,500 | Shipment, customer, route, hub, driver, transit-time, and SLA fields |
| `vw_hub_load_daily` | 1,629 | Status-scan and issue counts grouped by hub and day |

The DDL, reference data, analytics queries, and documented model are in [`schema.sql`](../sql/schema.sql), [`data.sql`](../sql/data.sql), [`queries.sql`](../sql/queries.sql), [`erd.mmd`](erd.mmd), and [`data_dictionary.md`](data_dictionary.md).

## 3. MongoDB baseline

**Verified:** MongoDB is reachable and the `fleettrack` database currently contains one collection, `tracking_events`, with **9,346 documents**.

A representative document was inspected without printing record values. Its observed fields and types are:

| Field | Type |
|---|---|
| `delay_flag` | bool |
| `dwell_minutes` | int |
| `event_at` | datetime |
| `event_source` | str |
| `hub_city`, `hub_code`, `hub_name` | str |
| `hub_id`, `route_id`, `shipment_id` | int |
| `notes`, `route_name`, `status`, `tracking_number` | str |

MongoDB reports the default `_id_` index and four secondary indexes:

- `tracking_number`
- `(shipment_id, event_at)`
- `(hub_id, event_at descending)`
- `(delay_flag, hub_id)`

Both pipeline definitions in [`mongo_pipelines.py`](../src/fleettrack/mongo_pipelines.py) are read-only pipelines without `$out` or `$merge`. The hub-dwell pipeline returned 12 groups with scan counts, average and total dwell, and delay-scan counts. The delay-hotspots pipeline returned 33 groups by hub and status with delay-event counts and average dwell. These are counts of matching documents/events, not necessarily distinct shipments.

The CRUD demonstration exists in [`mongo_demo.py`](../scripts/mongo_demo.py), but was deliberately not executed because it inserts, updates, and deletes documents. MongoDB count/find/index inspection and aggregation were performed without changing documents.

## 4. Existing shipment workflows

**Verified from the application and database code:**

1. **Shipment creation:** the operations page loads customer, route, driver, and vehicle choices, inserts a shipment using DB-API parameters, then inserts an initial `booked` status-history event. The status trigger updates the current shipment status.
2. **Status update:** an operator selects a shipment and status, optionally selects a hub, and inserts into `shipment_status_history`. Application code relies on the database trigger rather than directly changing `shipments.status`.
3. **Delivery attempt:** inserting or updating a delivery status fires the delivery trigger, which appends an event to shipment history.
4. **Tracking search:** an exact tracking-number lookup reads PostgreSQL history with optional hub details, then reads MongoDB tracking documents sorted by event time.
5. **Hub activity and delays:** PostgreSQL provides daily hub load and issue counts through `vw_hub_load_daily`; MongoDB provides hub-dwell and delay-hotspot aggregations.

The operations page’s shipment filter is parameterized. Existing status-history and tracking access patterns should remain supported by the replacement API.

## 5. November shipment distribution

### Observed monthly data

The following are actual read-only query results from the inspected database. “Delivered in booking cohort” means the shipment’s current status is `delivered`, grouped by `booked_at`. “Delivery-event month” uses the shipment’s non-null `delivered_at` timestamp and counts shipments, not raw history rows.

| Month | Booked shipments | Currently delivered in booking cohort | Shipments with `delivered_at` in month |
|---|---:|---:|---:|
| 2026-05 | 66 | 57 | 48 |
| 2026-06 | 188 | 158 | 158 |
| 2026-07 | 193 | 169 | 171 |
| 2026-08 | 196 | 174 | 171 |
| 2026-09 | 206 | 185 | 189 |
| 2026-10 | 200 | 176 | 176 |
| 2026-11 | 451 | 86 | 92 |

November’s 451 bookings break down into 356 `booked`, `in_transit`, `at_hub`, or `out_for_delivery` shipments, two `exception` shipments, 86 currently `delivered`, and seven `failed`. The 356 recent operational shipments have booking timestamps from November 14–19. The 86 delivered November booking-cohort records were booked November 1–12. The 92 November delivery timestamps include shipments booked in earlier months.

### Cause and interpretation

**Verified in [`seed_data.py`](../scripts/seed_data.py):** the generator uses a fixed random seed for selections, but anchors timestamps to `datetime.now()`. It assigns final statuses `in_transit`, `at_hub`, `out_for_delivery`, and `booked` booking ages of 0–4 days. Their configured weights sum to 24% of generated shipments. Completed/terminal records (including `exception`) receive ages of 7–180 days.

**Inference, strongly supported by the observed counts and generator logic:** the dominant reason for the November booking spike is the seed design: nearly all records in those four recent operational statuses are deliberately concentrated in the five days before bootstrap. Since the sample was generated on November 19, those records all fall in November. That recent cohort is added to the older records whose booking dates are distributed over a rolling 7–180-day interval. This explains the specific observed distribution; it is not evidence of a real carrier-volume spike.

**Booking versus delivery trend:** the current dashboard groups both its “booked” and “delivered” series by booking month. It therefore depicts booking cohorts and current completion status, not delivery volume by delivery date. The inspected November cohort has 86 currently delivered shipments, while 92 shipments have a November `delivered_at`; the latter is the more appropriate shipment-level delivery-time trend for this sample. November is a partial month, so comparisons with full months also need a partial-period label or normalization.

**Additional verified caveat:** the seed generator inserts a `delivered` history event for a delivered shipment and then inserts its delivery-attempt row. The delivery trigger creates a second `delivered` history row. In this database, delivered history has exactly two rows per delivered shipment per month: 184 November `delivered` history rows represent 92 distinct shipments (92 `seed` source and 92 `delivery` source). MongoDB is seeded from this history, so its document count also includes these duplicate delivered-event representations. Raw event counts and distinct-shipment counts must not be conflated.

**Reproducibility limitation:** `RNG_SEED = 20261119` fixes random choices, but `now = datetime.now(...)` changes the timestamps, month boundaries, and trend shape on each fresh seed. Re-running bootstrap against existing non-empty shipment/event collections skips generation, so a partially populated or partially failed seed is not automatically reconciled. This limits exact time-series reproduction even when the pseudorandom seed is fixed.

## 6. Status trigger issue and safe correction proposal

**Verified:** `fn_apply_shipment_status_event` sets `shipments.status = NEW.status` for every inserted history row. It does not compare the event timestamp with the latest existing history event.

**Failure mode:** if an older or delayed event is inserted after a newer event, the trigger can replace the newer current status with the stale event status. History remains present, but the cached current status can disagree with the chronologically latest event. Seed inserts are sorted by shipment and event time, which avoids this particular order in the seed path; late-arriving production events can still expose it.

**Recommendation (not implemented):** retain the append-only history and trigger-driven synchronization. In the trigger, serialize event synchronization per shipment by locking the parent shipment row, then derive the current status from the latest history row ordered by `(event_at DESC, status_history_id DESC)` instead of blindly using `NEW.status`. Define the equal-timestamp tie-break explicitly. Keep `delivered_at` semantics explicit and derived consistently from delivery history; do not clear a genuine delivery timestamp merely because a later status such as `returned` becomes current. Document the transaction-isolation expectation and test concurrent event insertion as well as late events.

**Required trigger tests:**

- Chronological inserts advance the current status to the newest event.
- Inserting an older event after a newer event does not regress current status.
- Equal event timestamps resolve deterministically using the documented tie-break.
- A later non-delivery status does not erase a valid delivery timestamp.
- Concurrent inserts for the same shipment leave current status equal to the canonical latest event.
- Every status change remains represented in `shipment_status_history`, and the application does not bypass the trigger.

No trigger or database record was modified or used for a write-based experiment during this audit.

## 7. Existing test coverage and test result

**Verified from the checked-in tests:** the current suite defines nine tests:

- Five helper tests for status timeline order/validation and SLA outcomes.
- Four source/contract tests for the eight-table schema, trigger/view definitions, seed and SQL assets, MongoDB pipeline/CRUD definitions, and documentation presence.

There are **no live PostgreSQL or MongoDB integration tests** in the current suite. The checked-in CI workflow runs pytest, but CI status was not queried as part of this local audit.

**Actual local test attempt:** `pytest -q` could not start because `pytest` is not recognized in the host environment. `python -B -m pytest -q -p no:cacheprovider` reported `No module named pytest`; the same module check in the app container also reported that pytest is not installed. Therefore **zero tests executed and no passing test result is claimed**. Dependencies were not installed, as instructed.

## 8. Known limitations and migration risks

- Synthetic data is explicitly labeled in seed notes and MongoDB `event_source`, but its generated timing profile is intentionally artificial and should not be presented as real logistics performance.
- The fixed PRNG seed does not fix the timestamp anchor; repeated clean seeds will not reproduce the same calendar-month chart.
- Delivery-attempt trigger behavior can create duplicate delivered history rows alongside generated lifecycle events.
- The current status trigger does not protect against late-arriving or backdated history inserts.
- PostgreSQL/Streamlit dashboard trends are grouped by booking cohort; event-time trends need their own definition and query.
- The existing tests validate source contracts and helper behavior but do not validate actual database triggers, integration between the stores, or UI workflows.
- The current app container lacks a Docker health check; its HTTP health endpoint was reachable in this audit.
- Hub cities exist, but coordinates and route geometries were not verified in the relational schema. A map must not imply precise geospatial data without provenance.
- Preserve the current app and the two named database volumes during the migration. Do not use volume deletion/reset commands.
- Before external deployment, add an explicit security design for identity, authorization, least-privilege database access, CORS, TLS, secret handling, and safe network exposure.

## 9. Measurable acceptance criteria for Phases 0–6

These are proposed release gates. They do not assert future model scores or current test success.

### Phase 0 — Baseline and acceptance criteria

- This report records the current architecture, all eight table counts, catalog constraints and relationships, triggers/views, MongoDB collection/count/indexes/pipeline results, application workflows, data limitations, and deployment state.
- All database inspection is read-only; no database, application, environment, or volume changes are made.
- Test execution status is stated accurately, including unavailable tooling.
- Each conclusion is labeled or worded as verified evidence, inference, or recommendation.

### Phase 1 — Backend foundation

- FastAPI exposes versioned liveness and readiness endpoints with typed responses; readiness independently reports PostgreSQL and MongoDB checks without exposing connection strings.
- OpenAPI generation succeeds and all public route request/response models validate.
- API tests cover success, invalid input, database unavailable, and MongoDB unavailable paths.
- Application SQL values are parameterized; shipment status writes insert history rows and do not directly update `shipments.status`.
- Configuration tests confirm missing required production secrets fail explicitly rather than silently using example credentials.

### Phase 2 — Frontend foundation

- All ten requested modules have a defined route/navigation entry or an explicitly marked not-yet-implemented state; no dead-end navigation is present.
- Shared layout, theme switching, global-filter state, and accessible loading/error/empty states are implemented and covered by tests.
- Critical pages render without horizontal overflow at 320 px, 768 px, and 1440 px viewport widths.
- Keyboard navigation and automated accessibility checks on critical flows show no serious/critical violations; any exceptions are documented and approved.
- API errors and empty datasets are visible to users and are not represented as successful zero-valued analytics.

### Phase 3 — Operational parity

- End-to-end tests cover shipment creation, status-history insertion, trigger-updated current status, shipment register filtering, tracking lookup, and MongoDB event display.
- Tests verify the status-history trigger behavior and the late-arriving-event cases listed in §6 using a disposable database.
- Both existing MongoDB aggregation workflows remain executable and tested; CRUD remains demonstrable in an isolated sandbox.
- Existing tables, SQL scripts, views, and volumes remain intact; any additive migration has a documented rollback/forward-recovery plan.

### Phase 4 — Intelligence and geospatial

- P50, P90, and P95 transit-time results are computed from the selected data and shown with population, time-window, completion, and synthetic-data definitions.
- SLA risk responses include model/version, prediction timestamp/cutoff, cohort/window, and the basis for the score; no static or fabricated score is presented as a prediction.
- No prediction feature uses data timestamped after its prediction cutoff; a leakage test fails if post-cutoff fields are introduced.
- Hub/route map features display only coordinates with recorded provenance and quality status; missing or synthetic coordinates are visibly labeled and never implied to be live telemetry.
- Data-quality and database-monitoring checks show query time/window and source; service failures render as errors, not normal analytics.

### Phase 5 — Research and simulation

- At least one simple baseline and one candidate SLA model are evaluated on chronological train/validation/test periods, with split boundaries and feature cutoff saved in an experiment manifest.
- A repeat run using the same data snapshot, code/configuration, and seed reproduces the same split and model configuration; metric comparisons use a documented numerical tolerance where dependencies introduce nondeterminism.
- Evaluation reports class prevalence, confusion/threshold metrics, PR-AUC and ROC-AUC where meaningful, Brier score, calibration results, and confidence intervals. No predetermined accuracy or lift is required or claimed.
- Transit-time percentile analysis and model evaluation identify the evaluated cohort, missing/censored outcomes, and synthetic-data assumptions.
- Model explanations are tied to the evaluated model and features; simulation inputs and outputs are labeled as scenarios, not observed outcomes.
- A model is not presented as decision-ready unless it is compared with baseline on the predeclared primary metric on the held-out temporal test set and uncertainty is reported.

### Phase 6 — Hardening and deployment

- A clean Compose build starts frontend, API, PostgreSQL, and MongoDB; health checks pass and documented smoke tests cover all critical services.
- The Streamlit fallback remains available until explicit cutover approval; the migration process preserves existing named volumes and never requires a volume reset.
- CI runs Python tests, frontend typecheck/lint/tests, and container/build checks successfully on a clean environment.
- Before any external deployment, authentication/authorization, least-privilege roles, TLS, restricted network exposure, secret handling, and dependency/image scanning are configured and verified; no credentials appear in logs or source.
- A rollback procedure restores the legacy app route without data loss, and database migrations are forward/backward compatibility reviewed.

## 10. Audit limits and next decision

The database and application checks represent the running local Compose stack at audit time. No external monitoring, CI run status, production deployment, historical data snapshot, real carrier data, or model performance was inspected. The CRUD demonstration was not run to honor the no-write constraint. Pytest could not execute because it is absent from both checked Python environments.

**Phase 0 documentation is complete.** The next step is Phase 1 only after separate approval.
