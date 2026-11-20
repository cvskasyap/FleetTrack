---
trigger: always_on
---
# FleetTrack rules

- Keep PostgreSQL schema changes normalised to 3NF and update `docs/erd.mmd` plus `docs/data_dictionary.md` whenever entities, columns, keys or dependencies change.
- All application SQL must be parameterised and use the `psycopg` DB-API helpers.
- Status changes must be appended to `shipment_status_history`; rely on the PostgreSQL trigger to update the shipment's current state.
- MongoDB documents represent tracking scans, not a second copy of the relational master tables.
- Keep the two aggregation pipelines in sync with the `tracking_events` document schema.
- Keep demo data synthetic and repeatable. Do not use real personal details in fixtures.
- Never place secrets in source code, notebooks, prompts, logs, commits or documentation.
- Run tests and inspect the resulting diff after modifications.
