from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from fleettrack_api.core.errors import ConflictError, InvalidRequestError
from fleettrack_api.repositories.postgres import PostgresRepository

def create_shipment(database_url: str) -> int:
    suffix = uuid4().hex[:12]
    with psycopg.connect(database_url) as connection:
        customer_id = connection.execute(
            """
            INSERT INTO customers (customer_code, full_name, email, city, state)
            VALUES (%s, 'Integration Test', %s, 'Test City', 'Test State')
            RETURNING customer_id
            """,
            (f"IT-{suffix}", f"{suffix}@example.test"),
        ).fetchone()[0]
        origin_id = connection.execute(
            """
            INSERT INTO hubs (hub_code, hub_name, city, state, daily_capacity)
            VALUES (%s, %s, 'Test City', 'Test State', 100)
            RETURNING hub_id
            """,
            (f"O{suffix[:10]}", f"Origin {suffix}"),
        ).fetchone()[0]
        destination_id = connection.execute(
            """
            INSERT INTO hubs (hub_code, hub_name, city, state, daily_capacity)
            VALUES (%s, %s, 'Other City', 'Other State', 100)
            RETURNING hub_id
            """,
            (f"D{suffix[:10]}", f"Destination {suffix}"),
        ).fetchone()[0]
        route_id = connection.execute(
            """
            INSERT INTO routes
                (route_code, route_name, origin_hub_id, destination_hub_id, distance_km)
            VALUES (%s, %s, %s, %s, 100)
            RETURNING route_id
            """,
            (f"R-{suffix}", f"Integration Route {suffix}", origin_id, destination_id),
        ).fetchone()[0]
        shipment_id = connection.execute(
            """
            INSERT INTO shipments
                (tracking_number, customer_id, route_id, weight_kg, shipping_cost,
                 booked_at, expected_delivery_at)
            VALUES (%s, %s, %s, 1, 10, %s, %s)
            RETURNING shipment_id
            """,
            (
                f"IT-{suffix}",
                customer_id,
                route_id,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 3, tzinfo=timezone.utc),
            ),
        ).fetchone()[0]
    return shipment_id


def create_shipment_references(database_url: str) -> tuple[int, int]:
    suffix = uuid4().hex[:12]
    with psycopg.connect(database_url) as connection:
        customer_id = connection.execute(
            """
            INSERT INTO customers (customer_code, full_name, email, city, state)
            VALUES (%s, 'Operations Test', %s, 'Test City', 'Test State')
            RETURNING customer_id
            """,
            (f"OP-{suffix}", f"op-{suffix}@example.test"),
        ).fetchone()[0]
        origin_id = connection.execute(
            """
            INSERT INTO hubs (hub_code, hub_name, city, state, daily_capacity)
            VALUES (%s, %s, 'Test City', 'Test State', 100)
            RETURNING hub_id
            """,
            (f"A{suffix[:11]}", f"Operations Origin {suffix}"),
        ).fetchone()[0]
        destination_id = connection.execute(
            """
            INSERT INTO hubs (hub_code, hub_name, city, state, daily_capacity)
            VALUES (%s, %s, 'Other City', 'Other State', 100)
            RETURNING hub_id
            """,
            (f"B{suffix[:11]}", f"Operations Destination {suffix}"),
        ).fetchone()[0]
        route_id = connection.execute(
            """
            INSERT INTO routes
                (route_code, route_name, origin_hub_id, destination_hub_id, distance_km)
            VALUES (%s, %s, %s, %s, 100)
            RETURNING route_id
            """,
            (f"OP-{suffix}", f"Operations Route {suffix}", origin_id, destination_id),
        ).fetchone()[0]
    return customer_id, route_id


def insert_status(database_url: str, shipment_id: int, status: str, event_at: datetime) -> None:
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO shipment_status_history (shipment_id, status, event_at, source)
            VALUES (%s, %s, %s, 'operator')
            """,
            (shipment_id, status, event_at),
        )


def test_late_event_does_not_regress_current_status(disposable_database_url):
    shipment_id = create_shipment(disposable_database_url)
    booked_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    insert_status(disposable_database_url, shipment_id, "in_transit", booked_at + timedelta(hours=4))
    insert_status(disposable_database_url, shipment_id, "picked_up", booked_at + timedelta(hours=2))

    with psycopg.connect(disposable_database_url) as connection:
        status = connection.execute(
            "SELECT status FROM shipments WHERE shipment_id = %s",
            (shipment_id,),
        ).fetchone()[0]
    assert status == "in_transit"


def test_equal_timestamps_use_history_identity_as_tie_break(disposable_database_url):
    shipment_id = create_shipment(disposable_database_url)
    event_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    insert_status(disposable_database_url, shipment_id, "in_transit", event_at)
    insert_status(disposable_database_url, shipment_id, "at_hub", event_at)

    with psycopg.connect(disposable_database_url) as connection:
        status = connection.execute(
            "SELECT status FROM shipments WHERE shipment_id = %s",
            (shipment_id,),
        ).fetchone()[0]
    assert status == "at_hub"


def test_later_non_delivery_status_preserves_delivered_at(disposable_database_url):
    shipment_id = create_shipment(disposable_database_url)
    delivered_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    insert_status(disposable_database_url, shipment_id, "delivered", delivered_at)
    insert_status(disposable_database_url, shipment_id, "returned", delivered_at + timedelta(hours=1))

    with psycopg.connect(disposable_database_url) as connection:
        status, saved_delivery_at = connection.execute(
            "SELECT status, delivered_at FROM shipments WHERE shipment_id = %s",
            (shipment_id,),
        ).fetchone()
    assert status == "returned"
    assert saved_delivery_at == delivered_at


def test_delivery_trigger_event_is_idempotent_for_repeated_status_updates(disposable_database_url):
    shipment_id = create_shipment(disposable_database_url)
    attempted_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    insert_status(
        disposable_database_url,
        shipment_id,
        "out_for_delivery",
        attempted_at - timedelta(minutes=10),
    )
    with psycopg.connect(disposable_database_url) as connection:
        delivery_id = connection.execute(
            """
            INSERT INTO deliveries
                (shipment_id, attempt_no, delivery_status, attempted_at, recipient_name)
            VALUES (%s, 1, 'delivered', %s, 'Test Recipient')
            RETURNING delivery_id
            """,
            (shipment_id, attempted_at),
        ).fetchone()[0]
        connection.execute(
            "UPDATE deliveries SET delivery_status = 'delivered' WHERE delivery_id = %s",
            (delivery_id,),
        )
        event_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM shipment_status_history
            WHERE event_key LIKE %s
            """,
            (f"delivery:{delivery_id}:delivered:%",),
        ).fetchone()[0]
        delivered_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM shipment_status_history
            WHERE shipment_id = %s AND status = 'delivered'
            """,
            (shipment_id,),
        ).fetchone()[0]
    assert event_count == delivered_count == 1


def test_concurrent_events_leave_status_at_canonical_latest(disposable_database_url):
    shipment_id = create_shipment(disposable_database_url)
    event_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    barrier = Barrier(2)

    def write_event(status: str, event_time: datetime) -> None:
        with psycopg.connect(disposable_database_url) as connection:
            connection.execute("SET lock_timeout = '10s'")
            barrier.wait(timeout=5)
            connection.execute(
                """
                INSERT INTO shipment_status_history (shipment_id, status, event_at, source)
                VALUES (%s, %s, %s, 'operator')
                """,
                (shipment_id, status, event_time),
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        earlier = executor.submit(write_event, "in_transit", event_at)
        later = executor.submit(write_event, "at_hub", event_at + timedelta(minutes=5))
        earlier.result(timeout=15)
        later.result(timeout=15)

    with psycopg.connect(disposable_database_url) as connection:
        current_status, canonical_status = connection.execute(
            """
            SELECT s.status,
                   (SELECT h.status
                    FROM shipment_status_history h
                    WHERE h.shipment_id = s.shipment_id
                    ORDER BY h.event_at DESC, h.status_history_id DESC
                    LIMIT 1)
            FROM shipments s
            WHERE s.shipment_id = %s
            """,
            (shipment_id,),
        ).fetchone()
    assert current_status == canonical_status == "at_hub"


def test_repository_create_writes_booking_history_and_update_preserves_status(
    disposable_database_url,
):
    customer_id, route_id = create_shipment_references(disposable_database_url)
    with psycopg.connect(disposable_database_url, row_factory=dict_row) as connection:
        repository = PostgresRepository(connection)
        shipment_id = repository.create_shipment(
            {
                "customer_id": customer_id,
                "route_id": route_id,
                "weight_kg": 2,
                "shipping_cost": 12,
                "priority": "standard",
                "expected_delivery_at": datetime.now(timezone.utc) + timedelta(days=2),
                "notes": "Operations integration test",
            }
        )
        assert repository.update_shipment(shipment_id, {"notes": "Updated note"})
        detail = repository.get_shipment_detail(shipment_id)
        history = repository.get_tracking_history(shipment_id)
        options = repository.shipment_options()

    assert detail is not None
    assert detail["status"] == "booked"
    assert detail["notes"] == "Updated note"
    assert detail["tracking_number"].startswith("FT-")
    assert [event["status"] for event in history] == ["booked"]
    assert any(item["customer_id"] == customer_id for item in options["customers"])
    assert any(item["route_id"] == route_id for item in options["routes"])


def test_delivery_attempts_trigger_their_history_events(disposable_database_url):
    shipment_id = create_shipment(disposable_database_url)
    booked_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    attempted_at = booked_at + timedelta(days=1)
    with psycopg.connect(disposable_database_url, row_factory=dict_row) as connection:
        repository = PostgresRepository(connection)
        repository.create_delivery_attempt(
            shipment_id,
            delivery_status="out_for_delivery",
            attempted_at=attempted_at - timedelta(minutes=10),
            recipient_name=None,
            failure_reason=None,
            notes=None,
        )
        repository.create_delivery_attempt(
            shipment_id,
            delivery_status="delivered",
            attempted_at=attempted_at,
            recipient_name="Integration Recipient",
            failure_reason=None,
            notes="Recorded by operations",
        )
        detail = repository.get_shipment_detail(shipment_id)
        history = repository.get_tracking_history(shipment_id)
        attempts = repository.get_delivery_attempts(shipment_id)

    assert detail is not None
    assert detail["status"] == "delivered"
    assert detail["delivered_at"] == attempted_at
    assert [event["status"] for event in history].count("out_for_delivery") == 1
    assert [event["status"] for event in history].count("delivered") == 1
    assert len(attempts) == 2
    assert [attempt["attempt_no"] for attempt in attempts] == [1, 2]


def test_cancel_is_history_only_and_rejects_dispatched_shipments(disposable_database_url):
    cancelable_id = create_shipment(disposable_database_url)
    dispatched_id = create_shipment(disposable_database_url)
    event_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    with psycopg.connect(disposable_database_url, row_factory=dict_row) as connection:
        repository = PostgresRepository(connection)
        repository.cancel_shipment(
            cancelable_id,
            event_at=event_at,
            reason="Customer requested cancellation",
        )
        repository.add_status_event(
            dispatched_id,
            status="picked_up",
            hub_id=None,
            event_at=event_at,
            notes=None,
        )
        with pytest.raises(ConflictError):
            repository.cancel_shipment(
                dispatched_id,
                event_at=event_at + timedelta(hours=1),
                reason="Too late to cancel",
            )
        cancelled_detail = repository.get_shipment_detail(cancelable_id)
        dispatched_detail = repository.get_shipment_detail(dispatched_id)
        cancelled_events = repository.get_tracking_history(cancelable_id)

    assert cancelled_detail is not None
    assert cancelled_detail["status"] == "cancelled"
    assert dispatched_detail is not None
    assert dispatched_detail["status"] == "picked_up"
    assert [event["status"] for event in cancelled_events] == ["cancelled"]


def test_status_api_cannot_regress_delivery_or_continue_after_return(
    disposable_database_url,
):
    shipment_id = create_shipment(disposable_database_url)
    delivered_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    insert_status(disposable_database_url, shipment_id, "delivered", delivered_at)
    with psycopg.connect(disposable_database_url, row_factory=dict_row) as connection:
        repository = PostgresRepository(connection)
        with pytest.raises(ConflictError):
            repository.add_status_event(
                shipment_id,
                status="in_transit",
                hub_id=None,
                event_at=delivered_at + timedelta(minutes=5),
                notes=None,
            )
        repository.add_status_event(
            shipment_id,
            status="returned",
            hub_id=None,
            event_at=delivered_at + timedelta(days=1),
            notes="Return confirmed",
        )
        with pytest.raises(ConflictError):
            repository.add_status_event(
                shipment_id,
                status="at_hub",
                hub_id=None,
                event_at=delivered_at + timedelta(days=2),
                notes=None,
            )
        detail = repository.get_shipment_detail(shipment_id)

    assert detail is not None
    assert detail["status"] == "returned"
    assert detail["delivered_at"] == delivered_at


def test_repository_rejects_invalid_shipment_reference(disposable_database_url):
    customer_id, route_id = create_shipment_references(disposable_database_url)
    with psycopg.connect(disposable_database_url, row_factory=dict_row) as connection:
        repository = PostgresRepository(connection)
        with pytest.raises(InvalidRequestError):
            repository.create_shipment(
                {
                    "customer_id": customer_id,
                    "route_id": route_id,
                    "assigned_driver_id": 999999999,
                    "weight_kg": 1,
                    "shipping_cost": 0,
                    "priority": "standard",
                    "expected_delivery_at": datetime.now(timezone.utc) + timedelta(days=1),
                    "notes": None,
                }
            )
