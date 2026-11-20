# Antigravity starter prompt

You are helping maintain FleetTrack, an M.Sc. Data Science DBMS for Analytics project. First inspect `README.md`, `AGENTS.md`, `.agents/rules/fleettrack.md`, `docs/data_dictionary.md`, `docs/erd.mmd`, and the SQL scripts. Do not modify files in this first pass.

Please report:
1. The architecture and responsibility split between PostgreSQL, Python/Streamlit and MongoDB.
2. The eight relational tables, their key relationships and why the model is in 3NF.
3. How the shipment-status trigger and delivery-attempt trigger work.
4. The DB-API and MongoDB aggregation workflows.
5. Any likely defects, missing tests or setup risks you can verify from the code.

After the review, wait for a specific change request. Preserve the course requirements: PostgreSQL 3NF, 500+ synthetic relational rows, PK/FK/check constraints, trigger(s), view(s), `schema.sql`/`data.sql`/`queries.sql`, Python DB-API notebook and charts, MongoDB CRUD/indexes/two aggregations, and a live demonstration path. Parameterise SQL and do not write secrets to the repository.
