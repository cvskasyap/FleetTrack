from __future__ import annotations

import logging
import secrets
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, NoReturn

import psycopg

from fleettrack_api.core.errors import (
    ConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
)

logger = logging.getLogger(__name__)

SHIPMENT_FIELDS = """
    shipment_id, tracking_number, customer_name, route_name, status, priority,
    booked_at, expected_delivery_at, delivered_at, on_time, transit_hours
"""


class PostgresRepository:
    def __init__(self, connection: psycopg.Connection[Any]):
        self.connection = connection

    def dashboard_summary(self) -> dict[str, Any]:
        query = """
            SELECT COUNT(*)::int AS total_shipments,
                   COUNT(*) FILTER (WHERE status = 'delivered')::int AS delivered_shipments,
                   COUNT(*) FILTER (
                       WHERE status NOT IN ('delivered', 'failed', 'returned', 'cancelled')
                   )::int AS in_progress_shipments,
                   ROUND(
                       100.0 * COUNT(*) FILTER (WHERE on_time IS TRUE)
                       / NULLIF(COUNT(*) FILTER (WHERE status = 'delivered'), 0),
                       2
                   ) AS on_time_pct,
                   ROUND(
                       AVG(transit_hours) FILTER (WHERE status = 'delivered'),
                       2
                   ) AS average_transit_hours
            FROM vw_delivery_performance
        """
        return self._fetch_one(query)

    def monthly_trends(
        self,
        from_month: date | None,
        to_month: date | None,
    ) -> list[dict[str, Any]]:
        query = """
            WITH booking_month AS (
                SELECT date_trunc('month', booked_at)::date AS month,
                       COUNT(*)::int AS booked_count,
                       COUNT(*) FILTER (WHERE status = 'delivered')::int
                           AS delivered_in_booking_cohort
                FROM shipments
                WHERE (%s::date IS NULL OR
                       booked_at >= date_trunc('month', %s::date))
                  AND (%s::date IS NULL OR
                       booked_at < date_trunc('month', %s::date) + INTERVAL '1 month')
                GROUP BY 1
            ),
            delivery_month AS (
                SELECT date_trunc('month', delivered_at)::date AS month,
                       COUNT(*)::int AS delivered_at_count
                FROM shipments
                WHERE delivered_at IS NOT NULL
                  AND (%s::date IS NULL OR
                       delivered_at >= date_trunc('month', %s::date))
                  AND (%s::date IS NULL OR
                       delivered_at < date_trunc('month', %s::date) + INTERVAL '1 month')
                GROUP BY 1
            )
            SELECT COALESCE(b.month, d.month) AS month,
                   COALESCE(b.booked_count, 0)::int AS booked_count,
                   COALESCE(b.delivered_in_booking_cohort, 0)::int
                       AS delivered_in_booking_cohort,
                   COALESCE(d.delivered_at_count, 0)::int AS delivered_at_count
            FROM booking_month b
            FULL OUTER JOIN delivery_month d USING (month)
            ORDER BY month
        """
        params = (
            from_month,
            from_month,
            to_month,
            to_month,
            from_month,
            from_month,
            to_month,
            to_month,
        )
        return self._fetch_all(query, params)

    def list_shipments(
        self,
        *,
        status: str | None,
        tracking_number: str | None,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        where = """
            WHERE (%s::varchar IS NULL OR status = %s)
              AND (%s::varchar IS NULL OR tracking_number ILIKE %s)
        """
        pattern = f"%{tracking_number}%" if tracking_number is not None else None
        filter_params = (status, status, tracking_number, pattern)
        count_query = "SELECT COUNT(*)::int AS total FROM vw_delivery_performance " + where
        total = self._fetch_one(count_query, filter_params)["total"]
        rows_query = (
            f"SELECT {SHIPMENT_FIELDS} FROM vw_delivery_performance "
            + where
            + " ORDER BY booked_at DESC, shipment_id DESC LIMIT %s OFFSET %s"
        )
        rows = self._fetch_all(rows_query, (*filter_params, limit, offset))
        return total, rows

    def get_shipment(self, shipment_id: int) -> dict[str, Any] | None:
        query = (
            f"SELECT {SHIPMENT_FIELDS} FROM vw_delivery_performance "
            "WHERE shipment_id = %s"
        )
        return self._fetch_optional_one(query, (shipment_id,))

    def get_tracking_history(self, shipment_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT h.status, h.event_at, h.hub_id, hub.hub_name, h.notes, h.source
            FROM shipment_status_history h
            LEFT JOIN hubs hub ON hub.hub_id = h.hub_id
            WHERE h.shipment_id = %s
            ORDER BY h.event_at, h.status_history_id
        """
        return self._fetch_all(query, (shipment_id,))

    def get_delivery_attempts(self, shipment_id: int) -> list[dict[str, Any]]:
        query = """
            SELECT delivery_id, attempt_no, delivery_status, attempted_at,
                   recipient_name, failure_reason, notes
            FROM deliveries
            WHERE shipment_id = %s
            ORDER BY attempt_no
        """
        return self._fetch_all(query, (shipment_id,))

    def get_shipment_detail(self, shipment_id: int) -> dict[str, Any] | None:
        query = """
            SELECT p.shipment_id, p.tracking_number, p.customer_name,
                   p.route_name, p.status, p.priority, p.booked_at,
                   p.expected_delivery_at, p.delivered_at, p.on_time,
                   p.transit_hours, s.customer_id, p.customer_code, s.route_id,
                   p.origin_hub, p.destination_hub, s.assigned_driver_id,
                   p.driver_code, p.driver_name, s.assigned_vehicle_id,
                   p.registration_no, p.weight_kg, p.shipping_cost, s.notes
            FROM vw_delivery_performance p
            JOIN shipments s ON s.shipment_id = p.shipment_id
            WHERE p.shipment_id = %s
        """
        return self._fetch_optional_one(query, (shipment_id,))

    def shipment_options(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "customers": self._fetch_all(
                """
                SELECT customer_id, customer_code, full_name
                FROM customers
                ORDER BY full_name, customer_id
                """
            ),
            "routes": self._fetch_all(
                """
                SELECT r.route_id, r.route_code, r.route_name,
                       origin.hub_name AS origin_hub,
                       destination.hub_name AS destination_hub
                FROM routes r
                JOIN hubs origin ON origin.hub_id = r.origin_hub_id
                JOIN hubs destination ON destination.hub_id = r.destination_hub_id
                WHERE origin.active AND destination.active
                ORDER BY r.route_name, r.route_id
                """
            ),
            "drivers": self._fetch_all(
                """
                SELECT driver_id, driver_code, full_name
                FROM drivers
                WHERE active
                ORDER BY full_name, driver_id
                """
            ),
            "vehicles": self._fetch_all(
                """
                SELECT vehicle_id, registration_no, vehicle_type, capacity_kg
                FROM vehicles
                WHERE active
                ORDER BY registration_no, vehicle_id
                """
            ),
            "hubs": self._fetch_all(
                """
                SELECT hub_id, hub_code, hub_name
                FROM hubs
                WHERE active
                ORDER BY hub_name, hub_id
                """
            ),
        }

    def hub_performance(
        self,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict[str, Any]]:
        query = """
            WITH filtered_shipments AS (
                SELECT s.shipment_id, s.status, p.on_time, p.transit_hours
                FROM shipments s
                JOIN vw_delivery_performance p USING (shipment_id)
                WHERE (%s::date IS NULL OR s.booked_at >= %s::date)
                  AND (%s::date IS NULL OR
                       s.booked_at < %s::date + INTERVAL '1 day')
            ),
            hub_touches AS (
                SELECT h.hub_id, h.shipment_id, COUNT(*)::int AS scan_count
                FROM shipment_status_history h
                JOIN filtered_shipments fs USING (shipment_id)
                WHERE h.hub_id IS NOT NULL
                GROUP BY h.hub_id, h.shipment_id
            ),
            hub_metrics AS (
                SELECT ht.hub_id,
                       COUNT(*)::int AS shipments_handled,
                       SUM(ht.scan_count)::int AS scan_count,
                       COUNT(*) FILTER (
                           WHERE fs.status = 'delivered'
                       )::int AS delivered_shipments,
                       COUNT(*) FILTER (
                           WHERE fs.status NOT IN
                               ('delivered', 'failed', 'returned', 'cancelled')
                       )::int AS in_progress_shipments,
                       COUNT(*) FILTER (
                           WHERE fs.status = 'delivered'
                             AND fs.on_time IS NOT NULL
                       )::int AS delivered_with_sla_count,
                       COUNT(*) FILTER (
                           WHERE fs.status = 'delivered'
                             AND fs.on_time IS TRUE
                       )::int AS on_time_shipments,
                       ROUND(
                           100.0 * COUNT(*) FILTER (
                               WHERE fs.status = 'delivered'
                                 AND fs.on_time IS TRUE
                           ) / NULLIF(COUNT(*) FILTER (
                               WHERE fs.status = 'delivered'
                                 AND fs.on_time IS NOT NULL
                           ), 0),
                           2
                       ) AS on_time_pct,
                       ROUND(
                           AVG(fs.transit_hours) FILTER (
                               WHERE fs.status = 'delivered'
                                 AND fs.transit_hours IS NOT NULL
                           ),
                           2
                       ) AS average_transit_hours
                FROM hub_touches ht
                JOIN filtered_shipments fs USING (shipment_id)
                GROUP BY ht.hub_id
            )
            SELECT h.hub_id, h.hub_code, h.hub_name, h.city, h.state,
                   h.daily_capacity,
                   COALESCE(m.shipments_handled, 0)::int AS shipments_handled,
                   COALESCE(m.scan_count, 0)::int AS scan_count,
                   COALESCE(m.delivered_shipments, 0)::int AS delivered_shipments,
                   COALESCE(m.in_progress_shipments, 0)::int AS in_progress_shipments,
                   COALESCE(m.delivered_with_sla_count, 0)::int
                       AS delivered_with_sla_count,
                   COALESCE(m.on_time_shipments, 0)::int AS on_time_shipments,
                   m.on_time_pct,
                   m.average_transit_hours
            FROM hubs h
            LEFT JOIN hub_metrics m USING (hub_id)
            ORDER BY h.hub_name, h.hub_id
        """
        params = (from_date, from_date, to_date, to_date)
        return self._fetch_all(query, params)

    def route_performance(
        self,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict[str, Any]]:
        query = """
            WITH filtered_shipments AS (
                SELECT s.shipment_id, s.route_id, s.status,
                       p.on_time, p.transit_hours
                FROM shipments s
                JOIN vw_delivery_performance p USING (shipment_id)
                WHERE (%s::date IS NULL OR s.booked_at >= %s::date)
                  AND (%s::date IS NULL OR
                       s.booked_at < %s::date + INTERVAL '1 day')
            ),
            route_metrics AS (
                SELECT fs.route_id,
                       COUNT(*)::int AS shipment_count,
                       COUNT(*) FILTER (
                           WHERE fs.status = 'delivered'
                       )::int AS delivered_shipments,
                       COUNT(*) FILTER (
                           WHERE fs.status NOT IN
                               ('delivered', 'failed', 'returned', 'cancelled')
                       )::int AS in_progress_shipments,
                       COUNT(*) FILTER (
                           WHERE fs.status = 'delivered'
                             AND fs.on_time IS NOT NULL
                       )::int AS delivered_with_sla_count,
                       COUNT(*) FILTER (
                           WHERE fs.status = 'delivered'
                             AND fs.on_time IS TRUE
                       )::int AS on_time_shipments,
                       ROUND(
                           100.0 * COUNT(*) FILTER (
                               WHERE fs.status = 'delivered'
                                 AND fs.on_time IS TRUE
                           ) / NULLIF(COUNT(*) FILTER (
                               WHERE fs.status = 'delivered'
                                 AND fs.on_time IS NOT NULL
                           ), 0),
                           2
                       ) AS on_time_pct,
                       ROUND(
                           AVG(fs.transit_hours) FILTER (
                               WHERE fs.status = 'delivered'
                                 AND fs.transit_hours IS NOT NULL
                           ),
                           2
                       ) AS average_transit_hours
                FROM filtered_shipments fs
                GROUP BY fs.route_id
            )
            SELECT r.route_id, r.route_code, r.route_name,
                   origin.hub_name AS origin_hub,
                   origin.city AS origin_city,
                   origin.state AS origin_state,
                   destination.hub_name AS destination_hub,
                   destination.city AS destination_city,
                   destination.state AS destination_state,
                   r.distance_km,
                   COALESCE(m.shipment_count, 0)::int AS shipment_count,
                   COALESCE(m.delivered_shipments, 0)::int AS delivered_shipments,
                   COALESCE(m.in_progress_shipments, 0)::int AS in_progress_shipments,
                   COALESCE(m.delivered_with_sla_count, 0)::int
                       AS delivered_with_sla_count,
                   COALESCE(m.on_time_shipments, 0)::int AS on_time_shipments,
                   m.on_time_pct,
                   m.average_transit_hours
            FROM routes r
            JOIN hubs origin ON origin.hub_id = r.origin_hub_id
            JOIN hubs destination ON destination.hub_id = r.destination_hub_id
            LEFT JOIN route_metrics m USING (route_id)
            ORDER BY r.route_code, r.route_id
        """
        params = (from_date, from_date, to_date, to_date)
        return self._fetch_all(query, params)

    def report_shipments(self) -> list[dict[str, Any]]:
        return self._fetch_all(
            """
            SELECT tracking_number, customer_name, route_name, origin_hub,
                   destination_hub, status, priority, booked_at,
                   expected_delivery_at, delivered_at, on_time, transit_hours,
                   weight_kg, shipping_cost
            FROM vw_delivery_performance
            ORDER BY booked_at DESC, shipment_id DESC
            """
        )

    def create_shipment(self, values: dict[str, Any]) -> int:
        booked_at = datetime.now(timezone.utc)
        tracking_number = (
            f"FT-{booked_at:%y%m%d}-{secrets.token_hex(6).upper()}"
        )
        try:
            with self.connection.transaction():
                self._validate_shipment_references(
                    customer_id=values["customer_id"],
                    route_id=values["route_id"],
                    driver_id=values.get("assigned_driver_id"),
                    vehicle_id=values.get("assigned_vehicle_id"),
                    weight_kg=values["weight_kg"],
                )
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO shipments
                            (tracking_number, customer_id, route_id,
                             assigned_vehicle_id, assigned_driver_id, weight_kg,
                             shipping_cost, priority, booked_at,
                             expected_delivery_at, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING shipment_id
                        """,
                        (
                            tracking_number,
                            values["customer_id"],
                            values["route_id"],
                            values.get("assigned_vehicle_id"),
                            values.get("assigned_driver_id"),
                            values["weight_kg"],
                            values["shipping_cost"],
                            values["priority"],
                            booked_at,
                            values["expected_delivery_at"],
                            values.get("notes"),
                        ),
                    )
                    shipment_id = cursor.fetchone()["shipment_id"]
                    cursor.execute(
                        """
                        INSERT INTO shipment_status_history
                            (shipment_id, status, event_at, notes, source)
                        VALUES (%s, 'booked', %s, 'Shipment booked', 'operator')
                        """,
                        (shipment_id, booked_at),
                    )
            return shipment_id
        except psycopg.errors.UniqueViolation as exc:
            self._raise_write_error(exc, conflict=True)
        except psycopg.errors.ForeignKeyViolation as exc:
            self._raise_write_error(exc, invalid=True)
        except psycopg.errors.CheckViolation as exc:
            self._raise_write_error(exc, invalid=True)

    def update_shipment(self, shipment_id: int, changes: dict[str, Any]) -> bool:
        columns = {
            "customer_id": "customer_id",
            "route_id": "route_id",
            "assigned_driver_id": "assigned_driver_id",
            "assigned_vehicle_id": "assigned_vehicle_id",
            "weight_kg": "weight_kg",
            "shipping_cost": "shipping_cost",
            "priority": "priority",
            "expected_delivery_at": "expected_delivery_at",
            "notes": "notes",
        }
        setters = [f"{columns[field]} = %s" for field in changes]
        parameters = list(changes.values())
        try:
            with self.connection.transaction():
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT customer_id, route_id, assigned_driver_id,
                               assigned_vehicle_id, weight_kg, booked_at
                        FROM shipments
                        WHERE shipment_id = %s
                        FOR UPDATE
                        """,
                        (shipment_id,),
                    )
                    current = cursor.fetchone()
                    if current is None:
                        return False
                    effective = {
                        field: changes.get(field, current[column])
                        for field, column in (
                            ("customer_id", "customer_id"),
                            ("route_id", "route_id"),
                            ("assigned_driver_id", "assigned_driver_id"),
                            ("assigned_vehicle_id", "assigned_vehicle_id"),
                            ("weight_kg", "weight_kg"),
                        )
                    }
                    expected_at = changes.get("expected_delivery_at")
                    if expected_at is not None and expected_at < current["booked_at"]:
                        raise InvalidRequestError(
                            "Expected delivery time cannot precede booking."
                        )
                    self._validate_shipment_references(
                        customer_id=effective["customer_id"],
                        route_id=effective["route_id"],
                        driver_id=effective["assigned_driver_id"],
                        vehicle_id=effective["assigned_vehicle_id"],
                        weight_kg=effective["weight_kg"],
                        allow_inactive_route="route_id" not in changes,
                        allow_inactive_driver="assigned_driver_id" not in changes,
                        allow_inactive_vehicle="assigned_vehicle_id" not in changes,
                    )
                    cursor.execute(
                        f"UPDATE shipments SET {', '.join(setters)} WHERE shipment_id = %s",
                        (*parameters, shipment_id),
                    )
            return True
        except psycopg.errors.ForeignKeyViolation as exc:
            self._raise_write_error(exc, invalid=True)
        except psycopg.errors.CheckViolation as exc:
            self._raise_write_error(exc, invalid=True)

    def add_status_event(
        self,
        shipment_id: int,
        *,
        status: str,
        hub_id: int | None,
        event_at: datetime,
        notes: str | None,
    ) -> bool:
        try:
            with self.connection.transaction():
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT status, booked_at
                        FROM shipments
                        WHERE shipment_id = %s
                        FOR UPDATE
                        """,
                        (shipment_id,),
                    )
                    shipment = cursor.fetchone()
                    if shipment is None:
                        return False
                    if event_at < shipment["booked_at"]:
                        raise InvalidRequestError(
                            "Operational event time cannot precede booking."
                        )
                    if shipment["status"] == "cancelled":
                        raise ConflictError(
                            "Cancelled shipments cannot receive additional status events."
                        )
                    if status in {
                        "booked",
                        "delivered",
                        "failed",
                        "out_for_delivery",
                        "exception",
                    }:
                        raise InvalidRequestError(
                            "Record booking and delivery outcomes through their dedicated operations."
                        )
                    if shipment["status"] == "returned":
                        raise ConflictError(
                            "Returned shipments cannot receive additional status events."
                        )
                    if shipment["status"] == "delivered" and status != "returned":
                        raise ConflictError(
                            "Only a return event may follow successful delivery."
                        )
                    if hub_id is not None:
                        cursor.execute(
                            "SELECT 1 FROM hubs WHERE hub_id = %s AND active",
                            (hub_id,),
                        )
                        if cursor.fetchone() is None:
                            raise InvalidRequestError("The selected active hub does not exist.")
                    cursor.execute(
                        """
                        INSERT INTO shipment_status_history
                            (shipment_id, status, hub_id, event_at, notes, source)
                        VALUES (%s, %s, %s, %s, %s, 'operator')
                        """,
                        (shipment_id, status, hub_id, event_at, notes),
                    )
            return True
        except psycopg.errors.ForeignKeyViolation as exc:
            self._raise_write_error(exc, invalid=True)
        except psycopg.errors.CheckViolation as exc:
            self._raise_write_error(exc, invalid=True)

    def create_delivery_attempt(
        self,
        shipment_id: int,
        *,
        delivery_status: str,
        attempted_at: datetime,
        recipient_name: str | None,
        failure_reason: str | None,
        notes: str | None,
    ) -> bool:
        try:
            with self.connection.transaction():
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT status, booked_at
                        FROM shipments
                        WHERE shipment_id = %s
                        FOR UPDATE
                        """,
                        (shipment_id,),
                    )
                    shipment = cursor.fetchone()
                    if shipment is None:
                        return False
                    if attempted_at < shipment["booked_at"]:
                        raise InvalidRequestError(
                            "Delivery attempt time cannot precede booking."
                        )
                    if shipment["status"] in {"delivered", "returned", "cancelled"}:
                        raise ConflictError(
                            "A terminal shipment cannot receive another delivery attempt."
                        )
                    cursor.execute(
                        """
                        SELECT COALESCE(MAX(attempt_no), 0)::int + 1 AS next_attempt
                        FROM deliveries
                        WHERE shipment_id = %s
                        """,
                        (shipment_id,),
                    )
                    attempt_no = cursor.fetchone()["next_attempt"]
                    cursor.execute(
                        """
                        INSERT INTO deliveries
                            (shipment_id, attempt_no, delivery_status, attempted_at,
                             recipient_name, failure_reason, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            shipment_id,
                            attempt_no,
                            delivery_status,
                            attempted_at,
                            recipient_name,
                            failure_reason,
                            notes,
                        ),
                    )
            return True
        except psycopg.errors.ForeignKeyViolation as exc:
            self._raise_write_error(exc, invalid=True)
        except psycopg.errors.CheckViolation as exc:
            self._raise_write_error(exc, invalid=True)
        except psycopg.errors.UniqueViolation as exc:
            self._raise_write_error(exc, conflict=True)

    def cancel_shipment(
        self,
        shipment_id: int,
        *,
        event_at: datetime,
        reason: str,
    ) -> bool:
        try:
            with self.connection.transaction():
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT status FROM shipments WHERE shipment_id = %s FOR UPDATE",
                        (shipment_id,),
                    )
                    shipment = cursor.fetchone()
                    if shipment is None:
                        return False
                    if shipment["status"] != "booked":
                        raise ConflictError(
                            "Only shipments that are still booked can be cancelled."
                        )
                    cursor.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM deliveries WHERE shipment_id = %s
                        ) OR EXISTS (
                            SELECT 1 FROM shipment_status_history
                            WHERE shipment_id = %s AND status <> 'booked'
                        ) AS has_dispatch_activity
                        """,
                        (shipment_id, shipment_id),
                    )
                    if cursor.fetchone()["has_dispatch_activity"]:
                        raise ConflictError(
                            "A shipment with dispatch or delivery activity cannot be cancelled."
                        )
                    cursor.execute(
                        """
                        INSERT INTO shipment_status_history
                            (shipment_id, status, event_at, notes, source)
                        VALUES (%s, 'cancelled', %s, %s, 'operator')
                        """,
                        (shipment_id, event_at, f"Cancellation reason: {reason}"),
                    )
            return True
        except psycopg.errors.ForeignKeyViolation as exc:
            self._raise_write_error(exc, invalid=True)
        except psycopg.errors.CheckViolation as exc:
            self._raise_write_error(exc, invalid=True)

    def _validate_shipment_references(
        self,
        *,
        customer_id: int,
        route_id: int,
        driver_id: int | None,
        vehicle_id: int | None,
        weight_kg: Decimal,
        allow_inactive_route: bool = False,
        allow_inactive_driver: bool = False,
        allow_inactive_vehicle: bool = False,
    ) -> None:
        query = """
            SELECT EXISTS (
                       SELECT 1 FROM customers WHERE customer_id = %s
                   ) AS customer_exists,
                   EXISTS (
                       SELECT 1
                       FROM routes r
                       JOIN hubs origin ON origin.hub_id = r.origin_hub_id
                       JOIN hubs destination ON destination.hub_id = r.destination_hub_id
                       WHERE r.route_id = %s
                         AND (%s OR (origin.active AND destination.active))
                   ) AS route_available,
                   (%s::bigint IS NULL OR EXISTS (
                       SELECT 1 FROM drivers
                       WHERE driver_id = %s AND (%s OR active)
                   )) AS driver_available,
                   (%s::bigint IS NULL OR EXISTS (
                       SELECT 1 FROM vehicles
                       WHERE vehicle_id = %s AND (%s OR active) AND capacity_kg >= %s
                   )) AS vehicle_available
        """
        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    customer_id,
                    route_id,
                    allow_inactive_route,
                    driver_id,
                    driver_id,
                    allow_inactive_driver,
                    vehicle_id,
                    vehicle_id,
                    allow_inactive_vehicle,
                    weight_kg,
                ),
            )
            availability = cursor.fetchone()
        if not all(availability.values()):
            raise InvalidRequestError(
                "A selected customer, route, driver or vehicle is unavailable or invalid."
            )

    @staticmethod
    def _raise_write_error(
        exc: psycopg.Error,
        *,
        invalid: bool = False,
        conflict: bool = False,
    ) -> NoReturn:
        logger.warning(
            "PostgreSQL shipment write rejected",
            extra={"event": "shipment_write_rejected", "error_type": type(exc).__name__},
        )
        if conflict:
            raise ConflictError("The shipment operation conflicts with current data.") from exc
        if invalid:
            raise InvalidRequestError("Shipment data or references are invalid.") from exc
        raise exc

    def _fetch_one(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> dict[str, Any]:
        row = self._fetch_optional_one(query, params)
        if row is None:
            raise RuntimeError("Aggregate query returned no row")
        return row

    def _fetch_optional_one(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> dict[str, Any] | None:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()
        except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
            logger.warning(
                "PostgreSQL query failed",
                extra={"event": "postgres_query_failed", "error_type": type(exc).__name__},
            )
            raise DependencyUnavailableError("postgresql") from exc

    def _fetch_all(
        self,
        query: str,
        params: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
            logger.warning(
                "PostgreSQL query failed",
                extra={"event": "postgres_query_failed", "error_type": type(exc).__name__},
            )
            raise DependencyUnavailableError("postgresql") from exc
