from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from pymongo import MongoClient

from fleettrack.config import DATABASE_URL, MONGODB_DATABASE, MONGODB_URI
from fleettrack.demo_data import STATUS_STAGES, build_timeline

ROOT = Path(__file__).resolve().parents[1]
RNG_SEED = int(os.environ.get("FLEETTRACK_SEED", "20261119"))
SHIPMENT_COUNT = 1500
DEFAULT_SEED_ANCHOR = datetime(2026, 11, 19, tzinfo=timezone.utc)


def get_seed_anchor() -> datetime:
    value = os.environ.get("FLEETTRACK_SEED_ANCHOR")
    if value is None:
        return DEFAULT_SEED_ANCHOR
    anchor = datetime.fromisoformat(value)
    if anchor.tzinfo is None or anchor.utcoffset() is None:
        raise ValueError("FLEETTRACK_SEED_ANCHOR must include a UTC offset")
    return anchor.astimezone(timezone.utc)


def booking_age_days(final_status: str, rng: random.Random) -> int:
    if final_status in ("delivered", "failed", "exception", "returned"):
        return rng.randint(7, 180)
    return rng.randint(0, 60)

STATUS_WEIGHTS = [
    ("delivered", 0.68), ("in_transit", 0.09), ("at_hub", 0.08),
    ("out_for_delivery", 0.06), ("failed", 0.05), ("exception", 0.02),
    ("returned", 0.01), ("booked", 0.01),
]


def weighted_status(rng: random.Random) -> str:
    value = rng.random()
    cumulative = 0.0
    for status, weight in STATUS_WEIGHTS:
        cumulative += weight
        if value <= cumulative:
            return status
    return "delivered"


def build_shipment_rows(conn: psycopg.Connection) -> None:
    with conn.cursor(row_factory=dict_row) as cur:
        if cur.execute("SELECT COUNT(*) AS n FROM shipments").fetchone()["n"] > 0:
            print("Shipment sample data already exists; skipping relational generation.")
            return

        customers = cur.execute("SELECT customer_id FROM customers ORDER BY customer_id").fetchall()
        routes = cur.execute(
            "SELECT route_id, origin_hub_id, destination_hub_id, distance_km FROM routes ORDER BY route_id"
        ).fetchall()
        drivers = cur.execute("SELECT driver_id FROM drivers ORDER BY driver_id").fetchall()
        vehicles = cur.execute("SELECT vehicle_id, capacity_kg FROM vehicles ORDER BY vehicle_id").fetchall()
        hubs = cur.execute("SELECT hub_id, hub_code, hub_name, city FROM hubs ORDER BY hub_id").fetchall()

        if min(len(customers), len(routes), len(drivers), len(vehicles), len(hubs)) == 0:
            raise RuntimeError("Reference data is missing. Run scripts/init_db.py before seeding.")

        hub_lookup = {h["hub_id"]: h for h in hubs}
        rng = random.Random(RNG_SEED)
        now = get_seed_anchor().replace(microsecond=0)
        shipment_rows: list[tuple] = []
        metadata: dict[str, dict] = {}

        for i in range(1, SHIPMENT_COUNT + 1):
            route = rng.choice(routes)
            customer = rng.choice(customers)
            vehicle = rng.choice(vehicles)
            driver = rng.choice(drivers)
            weight = round(rng.uniform(0.3, min(45.0, float(vehicle["capacity_kg"]) * 0.85)), 2)
            priority = rng.choices(["standard", "express", "same_day"], weights=[0.72, 0.23, 0.05])[0]
            tracking = f"FT2026{i:06d}"
            final_status = weighted_status(rng)
            # Keep recent in-progress records spread over two months rather than
            # concentrating a status cohort in the anchor month.
            age_days = booking_age_days(final_status, rng)
            booked = now - timedelta(days=age_days, hours=rng.randint(0, 23))
            base_hours = max(18.0, float(route["distance_km"]) / 38.0 + 12.0)
            if priority == "express":
                base_hours *= 0.78
            elif priority == "same_day":
                base_hours *= 0.55
            expected = booked + timedelta(hours=base_hours + rng.uniform(4, 15))
            shipment_rows.append((
                tracking, customer["customer_id"], route["route_id"], vehicle["vehicle_id"],
                driver["driver_id"], weight, round(65 + float(route["distance_km"]) * 0.38 + weight * 1.7, 2),
                priority, booked, expected, "booked", "Synthetic training record",
            ))
            metadata[tracking] = {
                "route": route, "final_status": final_status, "booked": booked,
                "expected": expected, "base_hours": base_hours,
            }

        cur.executemany(
            """INSERT INTO shipments
               (tracking_number, customer_id, route_id, assigned_vehicle_id, assigned_driver_id,
                weight_kg, shipping_cost, priority, booked_at, expected_delivery_at, status, notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            shipment_rows,
        )
        tracking_numbers = list(metadata)
        shipment_map_rows = cur.execute(
            "SELECT shipment_id, tracking_number FROM shipments WHERE tracking_number = ANY(%s)",
            (tracking_numbers,),
        ).fetchall()
        shipment_ids = {r["tracking_number"]: r["shipment_id"] for r in shipment_map_rows}

        history_rows: list[tuple] = []
        delivery_rows: list[tuple] = []
        for tracking, meta in metadata.items():
            shipment_id = shipment_ids[tracking]
            status = meta["final_status"]
            stages = STATUS_STAGES[status]
            # Build monotonic event offsets. Travel time varies with route length.
            offsets = [0]
            for j in range(1, len(stages)):
                step = rng.randint(35, 180) if stages[j] in ("picked_up", "out_for_delivery") else rng.randint(120, 900)
                offsets.append(offsets[-1] + step)
            if status == "delivered":
                final_at = meta["expected"] + timedelta(hours=rng.uniform(-16, 30))
                offsets[-1] = max(offsets[-2] + 30, int((final_at - meta["booked"]).total_seconds() / 60))
            elif status in ("failed", "exception", "returned"):
                offsets[-1] = max(offsets[-2] + 30, int((meta["base_hours"] * 60) + rng.randint(0, 600)))
            timeline = build_timeline(status, meta["booked"], offsets)
            origin_id = meta["route"]["origin_hub_id"]
            destination_id = meta["route"]["destination_hub_id"]
            for stage, event_at in timeline:
                if status in ("delivered", "failed", "exception", "out_for_delivery") and stage == status:
                    continue
                if stage in ("booked", "picked_up"):
                    hub_id = origin_id
                elif stage in ("at_hub", "out_for_delivery", "delivered", "failed", "returned"):
                    hub_id = destination_id
                else:
                    hub_id = None
                note = f"Automated synthetic scan: {stage.replace('_', ' ')}"
                history_rows.append((shipment_id, stage, hub_id, event_at, note, "seed"))

            if status in ("delivered", "failed", "exception", "out_for_delivery"):
                delivery_status = status if status in ("delivered", "failed", "exception", "out_for_delivery") else "out_for_delivery"
                last_time = timeline[-1][1]
                recipient = rng.choice(["Reception", "Security Desk", "Customer", "Warehouse Team"]) if status == "delivered" else None
                reason = None if status == "delivered" else rng.choice([
                    "Customer unavailable", "Address clarification required", "Access restricted", "Weather disruption"
                ])
                delivery_rows.append((shipment_id, 1, delivery_status, last_time, recipient, reason,
                                      "Generated delivery-attempt sample"))

        history_rows.sort(key=lambda row: (row[0], row[3]))
        cur.executemany(
            """INSERT INTO shipment_status_history
               (shipment_id, status, hub_id, event_at, notes, source)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            history_rows,
        )
        if delivery_rows:
            cur.executemany(
                """INSERT INTO deliveries
                   (shipment_id, attempt_no, delivery_status, attempted_at, recipient_name, failure_reason, notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                delivery_rows,
            )
    conn.commit()
    print(f"Generated {SHIPMENT_COUNT:,} shipments, {len(history_rows):,} status scans and {len(delivery_rows):,} delivery attempts.")


def seed_mongodb() -> None:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    collection = client[MONGODB_DATABASE]["tracking_events"]
    if collection.count_documents({}) > 0:
        print("MongoDB tracking events already exist; skipping document generation.")
        client.close()
        return

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            rows = cur.execute(
                """SELECT sh.shipment_id, s.tracking_number, s.route_id, r.route_name,
                          sh.status, sh.hub_id, h.hub_code, h.hub_name, h.city AS hub_city,
                          sh.event_at, sh.notes, s.expected_delivery_at, s.delivered_at
                   FROM shipment_status_history sh
                   JOIN shipments s ON s.shipment_id = sh.shipment_id
                   JOIN routes r ON r.route_id = s.route_id
                   LEFT JOIN hubs h ON h.hub_id = sh.hub_id
                   ORDER BY sh.shipment_id, sh.event_at"""
            ).fetchall()

    docs = []
    rng = random.Random(RNG_SEED + 99)
    for row in rows:
        dwell = rng.randint(20, 520) if row["status"] in ("at_hub", "out_for_delivery") else rng.randint(0, 45)
        late_delivery = row["status"] == "delivered" and row["delivered_at"] and row["delivered_at"] > row["expected_delivery_at"]
        delay_flag = bool(row["status"] in ("failed", "exception") or late_delivery or (row["status"] == "at_hub" and dwell >= 300))
        docs.append({
            "shipment_id": row["shipment_id"],
            "tracking_number": row["tracking_number"],
            "route_id": row["route_id"],
            "route_name": row["route_name"],
            "status": row["status"],
            "hub_id": row["hub_id"],
            "hub_code": row["hub_code"],
            "hub_name": row["hub_name"],
            "hub_city": row["hub_city"],
            "event_at": row["event_at"],
            "dwell_minutes": dwell,
            "delay_flag": delay_flag,
            "event_source": "synthetic_scan_generator",
            "notes": row["notes"],
        })
    if docs:
        collection.insert_many(docs, ordered=False)
    collection.create_index("tracking_number")
    collection.create_index([("shipment_id", 1), ("event_at", 1)])
    collection.create_index([("hub_id", 1), ("event_at", -1)])
    collection.create_index([("delay_flag", 1), ("hub_id", 1)])
    client.close()
    print(f"Loaded {len(docs):,} MongoDB tracking-event documents and created four indexes.")


def main() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        build_shipment_rows(conn)
    seed_mongodb()


if __name__ == "__main__":
    main()
