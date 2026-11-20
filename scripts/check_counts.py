from __future__ import annotations

import psycopg
from pymongo import MongoClient

from fleettrack.config import DATABASE_URL, MONGODB_DATABASE, MONGODB_URI


def main() -> None:
    tables = ["customers", "hubs", "vehicles", "drivers", "routes", "shipments", "deliveries", "shipment_status_history"]
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for table in tables:
                cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                print(f"{table:28s} {cur.fetchone()[0]:>8,}")
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    collection = client[MONGODB_DATABASE]["tracking_events"]
    print(f"{'MongoDB tracking_events':28s} {collection.count_documents({}):>8,}")
    print("MongoDB indexes:", ", ".join(collection.index_information().keys()))
    client.close()


if __name__ == "__main__":
    main()
