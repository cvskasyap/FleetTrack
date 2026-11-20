# Live demo plan and validation checklist

## Before the presentation

- Start services: `docker compose up --build -d`.
- Confirm dashboard loads at `http://localhost:8501`.
- Confirm relational row counts:

```sql
SELECT 'customers' AS table_name, COUNT(*) FROM customers
UNION ALL SELECT 'hubs', COUNT(*) FROM hubs
UNION ALL SELECT 'routes', COUNT(*) FROM routes
UNION ALL SELECT 'shipments', COUNT(*) FROM shipments
UNION ALL SELECT 'deliveries', COUNT(*) FROM deliveries
UNION ALL SELECT 'shipment_status_history', COUNT(*) FROM shipment_status_history;
```

- Confirm MongoDB scan volume and indexes from Mongo Insights or `mongosh`.
- Open the notebook and run all cells. Use the generated values from the notebook/dashboard in the presentation; do not invent numbers.

## Suggested 7–9 minute sequence

1. **Problem and model (1 minute):** explain why late shipments are hard to trace across hubs; show `docs/erd.mmd` and the eight-table 3NF model.
2. **DDL and normalisation (1 minute):** open `sql/schema.sql`; explain a functional dependency such as `route_id → route_code, origin_hub_id, destination_hub_id, distance_km`; identify the master tables that remove update anomalies.
3. **Trigger and view (1 minute):** show `trg_apply_shipment_status_event` and `vw_delivery_performance`.
4. **SQL analytics (1 minute):** run query 1 (on-time delivery rate), query 3 (average transit by route) and query 4 (busiest hubs) from `sql/queries.sql`.
5. **Python DB-API (1–2 minutes):** run the notebook connection cell, read SQL data into pandas, show the monthly/route charts and state the actual KPI values.
6. **MongoDB (1–2 minutes):** run `python -m scripts.mongo_demo` for CRUD, show the `tracking_events` indexes and run both pipelines from `src/fleettrack/mongo_pipelines.py`.
7. **Application (1 minute):** create a test shipment in Shipment Operations, add an `in_transit` or `out_for_delivery` event, and show that the trigger updates current status and that the tracking page displays the event.

## Trigger demonstration SQL

Use a test shipment and an explicit history insert (replace the tracking number with one from your seed data):

```sql
SELECT shipment_id FROM shipments WHERE tracking_number = 'FT2026000001';

INSERT INTO shipment_status_history (shipment_id, status, event_at, notes, source)
SELECT shipment_id, 'in_transit', NOW(), 'Live trigger demonstration', 'operator'
FROM shipments WHERE tracking_number = 'FT2026000001';

SELECT tracking_number, status
FROM shipments WHERE tracking_number = 'FT2026000001';
```

The final query should show `in_transit`. For the UI demonstration, choose a shipment that is safe to use as a sample and explain that its status has been changed by the presenter.

## Submission checklist

- [ ] GitHub repository contains the full source, SQL, notebook, documentation and tests.
- [ ] No `.env`, credentials, database dump or personal data committed.
- [ ] README has setup instructions and project structure.
- [ ] Notebook runs against the seeded databases and actual chart values are added to the presentation.
- [ ] Both MongoDB pipelines return non-empty outputs.
- [ ] Course presentation template is completed with actual results and screenshots from the live run.
