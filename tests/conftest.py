from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def disposable_database_url():
    database_url = os.environ.get("FLEETTRACK_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("Set FLEETTRACK_TEST_DATABASE_URL to an empty local disposable database.")

    parsed = urlsplit(database_url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.path != "/fleettrack_test":
        raise RuntimeError("Integration tests require a local database named fleettrack_test.")

    with psycopg.connect(database_url) as connection:
        existing_tables = connection.execute(
            "SELECT COUNT(*) FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
        ).fetchone()[0]
        if existing_tables:
            raise RuntimeError("Integration tests require an empty disposable database.")

        schema_sql = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
        connection.execute(schema_sql, prepare=False)
        for migration in sorted((ROOT / "sql" / "migrations").glob("*.sql")):
            migration_sql = migration.read_text(encoding="utf-8")
            connection.execute(migration_sql, prepare=False)
            connection.execute(migration_sql, prepare=False)
        data_sql = (ROOT / "sql" / "data.sql").read_text(encoding="utf-8")
        connection.execute(data_sql, prepare=False)

    return database_url
