# FleetTrack — Logistics Shipment and Delivery Performance Analytics

**Problem statement 08 · Logistics · M.Sc. Data Science · DBMS for Analytics (25MSDA1S04)**

FleetTrack is an end-to-end DBMS analytics project for a courier/logistics operation. PostgreSQL stores the normalised operational model, Python connects through the DB-API and produces pandas/Plotly analysis, MongoDB stores shipment tracking scans as event documents, and Streamlit provides an interactive operations and analytics dashboard.

> **Data note:** the bundled seed data is synthetic and reproducible. It is suitable for a classroom demonstration, not for operational decisions. No real customer or carrier data is included.

## 1. Assignment requirements covered

| Brief requirement | FleetTrack implementation |
|---|---|
| MySQL or PostgreSQL schema normalised to 3NF; 5+ related tables | PostgreSQL 16; 8 related tables in `sql/schema.sql` |
| Primary and foreign keys, constraints | PK/FK, UNIQUE, CHECK, NOT NULL constraints on core entities |
| At least one trigger and one view | Two triggers and two views: shipment-status synchronisation, delivery-attempt audit, `vw_delivery_performance`, `vw_hub_load_daily` |
| At least 500 rows across tables | `scripts/seed_data.py` generates 1,500 shipments, delivery attempts and several thousand status-history rows |
| `schema.sql`, `data.sql`, `queries.sql` | `sql/schema.sql`, `sql/data.sql`, `sql/queries.sql` |
| Python DB-API notebook, data loading, queries and charts | `notebooks/fleettrack_analysis.ipynb` uses `psycopg`, pandas and matplotlib |
| MongoDB CRUD, indexes and 2+ aggregation pipelines | `scripts/mongo_demo.py`, `tracking_events` collection, indexes and two pipelines in `src/fleettrack/mongo_pipelines.py` |
| SQL vs NoSQL comparison | `docs/sql_vs_mongodb.md` |
| Findings and live demo | `docs/demo_guide.md` and `docs/presentation_mapping.md` |

## 2. Architecture

```text
                         ┌───────────────────────────┐
                         │     Streamlit interface   │
                         │ KPI dashboard / operations│
                         │ tracking / Mongo insights │
                         └─────────────┬─────────────┘
                                       │
                     ┌─────────────────┴──────────────────┐
                     │                                    │
              Python DB-API                         PyMongo
              psycopg 3                                  │
                     │                                    │
          ┌──────────▼──────────┐              ┌──────────▼──────────┐
          │    PostgreSQL 16   │              │      MongoDB 7      │
          │ Customers, Hubs,   │              │ tracking_events     │
          │ Routes, Vehicles,  │              │ event scans, dwell, │
          │ Drivers, Shipments,│              │ delay flags          │
          │ Deliveries, History│              └─────────────────────┘
          └────────────────────┘
```

- PostgreSQL is the system of record for entities, assignments, shipment status, delivery attempts and auditable status history.
- MongoDB holds high-volume tracking scan documents with event timestamps, hub metadata, dwell time and delay flags.
- Streamlit provides an interactive browser interface. Analytical charts are computed from live database queries, not hard-coded screenshots.
- FastAPI provides versioned database-backed analytics, authentication, and controlled shipment operations; the Streamlit application remains available as a fallback.

## 3. Quick start (recommended: Docker Desktop)

### Prerequisites

- Docker Desktop with Docker Compose v2.
- Git (optional for local execution; required for GitHub publishing).
- A browser.

### Start the project

1. Extract the project ZIP and open a terminal in the `FleetTrack` folder.
2. Create your local environment file:

   **Windows PowerShell**
   ```powershell
   Copy-Item .env.example .env
   ```
   **macOS/Linux**
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and replace both placeholder passwords. Keep `.env` private; it is ignored by Git.
4. Build and start the application, API and database services:
   ```bash
   docker compose up --build -d
   ```
5. Open **http://localhost:8501** for the Streamlit fallback or **http://localhost:8000/docs** for the FastAPI OpenAPI documentation. The API readiness endpoint is **http://localhost:8000/api/v1/health/ready**.
6. The Streamlit application waits for both databases, creates the schema and reference data, then generates the synthetic sample data on first boot. The API connects to the same databases using their internal Compose service addresses.
7. View container output when needed:
   ```bash
   docker compose logs -f app
   docker compose logs -f api
   ```

The initial seed generates 1,500 shipment records. It also generates the related operational history and MongoDB scan documents. Re-running bootstrap does not duplicate shipment or scan data.

After the Streamlit service has completed bootstrap and the API is healthy, create the initial FleetTrack accounts using the interactive no-echo prompt:

```powershell
docker compose exec api python -m fleettrack_api.cli bootstrap-users
```

Set and confirm the initial `admin` and `user` passwords in the prompt; no default credentials are provided. The command does not print, log, or replace existing passwords. Production deployments must use HTTPS and set `SESSION_COOKIE_SECURE=true` before creating sessions.

### Stop the project

```bash
docker compose down
```

This stops containers but preserves database volumes. Do not use volume-removal options when stopping the project.

## 4. Run without Docker (optional)

Install Python 3.10+ and run PostgreSQL 16 and MongoDB 7 locally. Create the databases/users to match `.env`, then:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
python -m scripts.bootstrap
streamlit run app.py
```

For this local mode, `.env` uses `localhost` in both connection strings. `scripts.bootstrap` applies the SQL files, seeds the relational data, loads MongoDB documents and builds indexes.

## 4.1 React frontend development

The standalone React/TypeScript frontend is under `frontend/`. Start the FastAPI backend first, then in a second PowerShell terminal:

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

Open **http://127.0.0.1:5173** and sign in with an account created by the bootstrap command. Vite proxies `/api` requests to `http://localhost:8000`, so the frontend can run locally without changing Docker Compose or the Streamlit fallback. Frontend checks are `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd test`, and `npm.cmd run build`. See [`docs/phase2_frontend_documentation.md`](docs/phase2_frontend_documentation.md) for routes, authentication, and integration details.

## 5. Application walkthrough

Open the Streamlit sidebar to navigate:

1. **FleetTrack dashboard** — total shipments, completed shipments, in-progress volume, on-time percentage, mean transit time, monthly trend, route performance, status mix, hub load and recent shipments.
2. **Shipment Operations** — create a shipment, assign a route/driver/vehicle, add a status event, filter the shipment register. Inserting a row into `shipment_status_history` fires the database trigger that updates `shipments.status`.
3. **Shipment Tracking** — search a tracking number and compare its PostgreSQL status audit with MongoDB scan documents.
4. **MongoDB Tracking Insights** — execute two MongoDB aggregation pipelines: average hub dwell and delay hotspots by hub/status.

## 6. Database design and normalisation

The schema contains eight relational tables:

`customers`, `hubs`, `vehicles`, `drivers`, `routes`, `shipments`, `deliveries`, `shipment_status_history`.

The core functional dependencies and 3NF rationale are documented in [`docs/data_dictionary.md`](docs/data_dictionary.md). The Mermaid ER diagram is in [`docs/erd.mmd`](docs/erd.mmd).

### Important trigger behaviour

- `trg_apply_shipment_status_event`: serializes history inserts on the parent shipment, projects the latest event by timestamp and history ID, and retains an existing legitimate `delivered_at`.
- `trg_log_delivery_attempt`: appends an idempotently keyed event to `shipment_status_history` for each delivery-attempt status.

Existing status-history rows are preserved by the additive migration. Existing duplicate rows are not silently deleted or rewritten.

### Views

- `vw_delivery_performance`: shipment facts plus customer, route, hubs, driver, transit time and SLA outcome.
- `vw_hub_load_daily`: scan/issue volume grouped by hub and day.

## 7. SQL and MongoDB scripts

| File | Purpose |
|---|---|
| `sql/schema.sql` | DDL, keys, checks, indexes, triggers and views |
| `sql/data.sql` | Reproducible dimension/reference data |
| `sql/queries.sql` | Ten business analytics queries |
| `scripts/init_db.py` | Applies the schema, sorted additive migrations, and reference seed scripts |
| `scripts/seed_data.py` | Generates the 1,500-shipment relational data and MongoDB tracking scans |
| `scripts/mongo_demo.py` | Demonstrates MongoDB insert, find, update and delete in a sandbox collection |
| `src/fleettrack/mongo_pipelines.py` | Two reusable MongoDB aggregation pipelines |

Run the CRUD demonstration after the databases are up:

```bash
python -m scripts.mongo_demo
```

## 8. Python DB-API notebook

Start Jupyter from the project root and open `notebooks/fleettrack_analysis.ipynb`:

```bash
pip install jupyter
jupyter notebook notebooks/fleettrack_analysis.ipynb
```

The notebook uses `DATABASE_URL` from `.env`, opens a `psycopg` DB-API connection, loads query results into pandas, computes on-time performance and plots delivery trends and route comparisons. It also displays MongoDB aggregation outputs.

## 9. Tests

```bash
python -B -m pytest -q -p no:cacheprovider
```

The host test suite does not require user database credentials; database integration tests are skipped unless `FLEETTRACK_TEST_DATABASE_URL` explicitly targets an empty local database named `fleettrack_test`. The test fixture refuses to proceed if that database already contains public tables. Never point it at the project database.

Frontend checks run from `frontend/`:

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd test
npm.cmd run build
```

The tests cover the original DBMS requirements, backend API contracts, auth/session/CSRF behavior, bootstrap password handling, and frontend route/authentication states.

The React Shipment Operations workspace also supports creating and updating bookings, appending operational status events, recording delivery attempts, and cancelling eligible pre-dispatch bookings. Status changes remain history-triggered; delivery attempts are recorded only in `deliveries`, and cancellation is an appended `cancelled` history event. The API requires a signed-in session and CSRF token for these mutations. Migration `sql/migrations/003_cancelled_shipment_status.sql` adds the cancellation value without changing existing records; the regular Streamlit/bootstrap migration process applies it before the cancellation operation is deployed.

## 10. Antigravity workspace setup

This repository includes `AGENTS.md`, `.agents/rules/fleettrack.md` and `prompts/antigravity-bootstrap.md` so Google Antigravity has the project context and engineering constraints when it opens the folder.

1. Install the Google Antigravity IDE or its supported editor extension from the [official getting-started guide](https://antigravity.google/docs/getting-started).
2. In Antigravity, create a Project and add the extracted `FleetTrack` folder/repository as the workspace.
3. Trust the workspace when prompted. Antigravity automatically discovers repository rules such as `AGENTS.md` and `.agents/rules/*.md`.
4. Open `prompts/antigravity-bootstrap.md`, copy the starter prompt into the Agent panel and ask it to review the codebase before changing anything.
5. Use the terminal commands in this README for the actual test/run cycle. Review diffs before accepting generated changes.

See [`docs/antigravity_setup.md`](docs/antigravity_setup.md) for the standalone setup guide.

**Do not paste database passwords or GitHub tokens into Agent prompts.** Keep credentials in the ignored `.env` file or your machine's credential manager.

## 11. Publish to GitHub

The local project can be committed and pushed to your own account. This environment does not have an authenticated GitHub session, so the final push must be performed from your computer after signing in.

1. Sign in to GitHub and create a **new empty repository** named `FleetTrack` (choose Public or Private according to your course submission rules). Do not add a README, licence or `.gitignore`; these already exist here.
2. In the project terminal, configure your author identity if Git asks:
   ```bash
   git config user.name "Your Name"
   git config user.email "your-github-email@example.com"
   ```
3. Initialise/commit (skip this if the repository already has the initial commit):
   ```bash
   git init
   git add .
   git commit -m "Build FleetTrack logistics analytics project"
   git branch -M main
   ```
4. Add your actual remote and push:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/FleetTrack.git
   git push -u origin main
   ```
5. Confirm the files appear in the repository. Share the resulting GitHub URL in the course submission.

Never commit `.env`, database dumps containing private information, passwords or access tokens. The `.gitignore` excludes `.env` and common local artefacts. See [`docs/github_publish.md`](docs/github_publish.md) for the standalone publishing checklist.

## 12. Project structure

```text
FleetTrack/
├── app.py                         # Streamlit dashboard
├── pages/                         # operations, tracking and Mongo analytics
├── backend/                       # FastAPI app, API contracts and repositories
├── sql/                           # schema.sql, data.sql, queries.sql
├── scripts/                       # bootstrap, seed and Mongo CRUD demo
├── src/fleettrack/                # DB-API, config, data logic and pipelines
├── notebooks/                     # Python analysis notebook
├── docs/                          # ERD, data dictionary, demo and presentation map
├── tests/                          # unit and SQL contract tests
├── .agents/rules/                  # Antigravity workspace rules
├── AGENTS.md                       # agent context/instructions
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```
