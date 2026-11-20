from __future__ import annotations

import time

import psycopg
from pymongo import MongoClient

from fleettrack.config import DATABASE_URL, MONGODB_URI
from fleettrack.mongo import ensure_indexes
from scripts.init_db import main as init_db
from scripts.seed_data import main as seed_data


def wait_for_dependencies(retries: int = 40, delay_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with psycopg.connect(DATABASE_URL, connect_timeout=3):
                pass
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
            client.close()
            print("PostgreSQL and MongoDB are ready.")
            return
        except Exception as exc:  # retry while compose services initialise
            last_error = exc
            print(f"Waiting for databases ({attempt}/{retries}): {exc}")
            time.sleep(delay_seconds)
    raise RuntimeError("Databases did not become ready in time") from last_error


def main() -> None:
    wait_for_dependencies()
    init_db()
    seed_data()
    ensure_indexes()
    print("FleetTrack bootstrap completed.")


if __name__ == "__main__":
    main()
