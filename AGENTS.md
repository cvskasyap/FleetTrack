# FleetTrack workspace instructions

You are working in the FleetTrack M.Sc. Data Science DBMS for Analytics project (problem statement 08).

## Project invariants
- PostgreSQL is the relational source of truth. Preserve the eight-table 3NF model unless a migration and documentation update are included.
- Keep SQL DDL in `sql/schema.sql`, reference data in `sql/data.sql`, and analytics in `sql/queries.sql`.
- Shipment status changes must be written to `shipment_status_history`. The database trigger is responsible for synchronising `shipments.status`; do not bypass it in application logic.
- MongoDB is for shipment scan/event documents. Keep CRUD, indexes and at least two useful aggregation pipelines demonstrable.
- Python SQL access must use DB-API (`psycopg`) and parameterised queries. Never interpolate user-supplied values into SQL.
- Do not hard-code secrets. Read connection strings from environment variables; `.env` is local and must not be committed.
- Synthetic records must remain clearly labelled as synthetic. Never claim generated data is real logistics performance.

## Development workflow
1. Read `README.md` and relevant files before editing.
2. Make focused changes and update the data dictionary/ERD if the relational model changes.
3. Run `pytest -q` after changes.
4. For database changes, run `python -m scripts.bootstrap` against a disposable local database and test trigger behaviour.
5. Preserve the dashboard's operations, tracking search and MongoDB analytics flows.
6. Review `git diff` before proposing a commit. Do not push to a remote without the user's explicit request and authenticated credentials.

## Commands
- Start full stack: `docker compose up --build -d`
- View app logs: `docker compose logs -f app`
- Tests: `pytest -q`
- Mongo CRUD demonstration: `python -m scripts.mongo_demo`
