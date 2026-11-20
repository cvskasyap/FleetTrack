# Synthetic sample data

The project generates deterministic synthetic courier records with a fixed PRNG seed (`20261119`). `sql/data.sql` supplies reference/master data. `scripts/seed_data.py` generates 1,500 shipments with multiple status-history events, delivery attempts and corresponding MongoDB tracking-event documents.

The generator uses fictional names, reserved `.example.test` email addresses, fictional phone/vehicle/licence identifiers and approximate route distances. Timestamps are generated relative to the bootstrap time so the dashboard has a recent rolling history. These are illustrative training data, not a public dataset or observed carrier operations.

To regenerate from a clean state, stop the compose stack and remove the database volumes with `docker compose down -v`, then run `docker compose up --build -d` again. This permanently deletes local database content.
