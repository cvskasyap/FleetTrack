# Mapping FleetTrack to the supplied DBMS project presentation template

Use the supplied six-slide structure. Capture screenshots from the running dashboard and live SQL/Mongo sessions; the project does not fabricate result screenshots or KPI values.

| Template slide | Suggested FleetTrack content |
|---|---|
| Cover / problem introduction | FleetTrack · Problem statement 08 · Logistics. Explain that courier operators need on-time delivery, hub-load and cost-per-delivery visibility, while delays are difficult to trace across hubs. Add student name, registration number, guide/date and GitHub URL. |
| 01 Schema design and normalisation | Insert the ER diagram from `docs/erd.mmd`. List all eight tables and PK/FK relationships. Use the functional dependencies from `docs/data_dictionary.md`; highest normal form: 3NF. Explain that master tables remove repeated customer/hub/driver/route descriptions from shipments and history. |
| 02 SQL: tables, triggers and queries | Show `shipments` DDL from `sql/schema.sql`, constraints, `trg_apply_shipment_status_event`, and `vw_delivery_performance`. Report real row counts from the count query in `docs/demo_guide.md`. Table results for on-time rate, route transit and busiest hubs come from `sql/queries.sql`. |
| 03 Python DB-API and analysis | Show the `psycopg` connection cell in `notebooks/fleettrack_analysis.ipynb`, two charts (monthly shipments/on-time trend and route transit), and three insights supported by the actual chart output. |
| 04 MongoDB model and aggregation | Show one `tracking_events` document, indexes, and `python -m scripts.mongo_demo` CRUD output. Present both pipelines: hub dwell and delay hotspots. Complete the SQL vs MongoDB comparison with `docs/sql_vs_mongodb.md`. |
| 05 Findings and live demo | Summarise measured on-time rate, routes with longer transit, and hubs with higher dwell/delay scans. Discuss generated-data assumptions as a limitation. Follow `docs/demo_guide.md` for the live demonstration. |

**Important:** record exact numeric findings only after running the seeded project. The synthetic sample changes its event timestamps relative to the seed run, and the assignment expects actual numbers from the DB/API output.
