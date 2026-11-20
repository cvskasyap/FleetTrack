from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from fleettrack_api.core.errors import (
    DependencyUnavailableError,
)
from fleettrack_api.dependencies import (
    get_mongo_health_check,
    get_mongo_repository,
    get_postgres_health_check,
    get_postgres_repository,
)
from fleettrack_api.dependencies_auth import (
    get_application_user,
    get_auth_repository,
    require_application_csrf,
)
from fleettrack_api.main import app
from fleettrack_api.repositories.postgres import PostgresRepository
from fleettrack_api.schemas.geospatial import GeospatialHub, GeospatialRoute


class FakePostgresRepository:
    def dashboard_summary(self):
        return {
            "total_shipments": 12,
            "delivered_shipments": 8,
            "in_progress_shipments": 3,
            "on_time_pct": 75.0,
            "average_transit_hours": 22.5,
        }

    def monthly_trends(self, from_month, to_month):
        return [
            {
                "month": date(2026, 11, 1),
                "booked_count": 12,
                "delivered_in_booking_cohort": 8,
                "delivered_at_count": 7,
            }
        ]

    def hub_performance(self, from_date, to_date):
        return [
            {
                "hub_id": 1,
                "hub_code": "H-1",
                "hub_name": "North Hub",
                "city": "North City",
                "state": "North State",
                "daily_capacity": 200,
                "shipments_handled": 4,
                "scan_count": 8,
                "delivered_shipments": 2,
                "in_progress_shipments": 2,
                "delivered_with_sla_count": 2,
                "on_time_shipments": 1,
                "on_time_pct": 50.0,
                "average_transit_hours": 24.5,
            }
        ]

    def route_performance(self, from_date, to_date):
        return [
            {
                "route_id": 1,
                "route_code": "R-1",
                "route_name": "North - South",
                "origin_hub": "North Hub",
                "origin_city": "North City",
                "origin_state": "North State",
                "destination_hub": "South Hub",
                "destination_city": "South City",
                "destination_state": "South State",
                "distance_km": 450.5,
                "shipment_count": 5,
                "delivered_shipments": 3,
                "in_progress_shipments": 2,
                "delivered_with_sla_count": 3,
                "on_time_shipments": 2,
                "on_time_pct": 66.67,
                "average_transit_hours": 42.5,
            }
        ]

    def list_shipments(self, **kwargs):
        return 0, []

    def get_shipment(self, shipment_id):
        if shipment_id == 404:
            return None
        return {
            "shipment_id": shipment_id,
            "tracking_number": "FT-TEST-1",
            "customer_name": "Synthetic Test Customer",
            "route_name": "Test Origin - Test Destination",
            "status": "in_transit",
            "priority": "standard",
            "booked_at": datetime(2026, 11, 1, tzinfo=timezone.utc),
            "expected_delivery_at": datetime(2026, 11, 3, tzinfo=timezone.utc),
            "delivered_at": None,
            "on_time": None,
            "transit_hours": None,
        }

    def get_shipment_detail(self, shipment_id):
        shipment = self.get_shipment(shipment_id)
        if shipment is None:
            return None
        return {
            **shipment,
            "customer_id": 1,
            "customer_code": "TEST",
            "route_id": 1,
            "origin_hub": "Test Origin",
            "destination_hub": "Test Destination",
            "assigned_driver_id": None,
            "driver_code": None,
            "driver_name": None,
            "assigned_vehicle_id": None,
            "registration_no": None,
            "weight_kg": Decimal("1.25"),
            "shipping_cost": Decimal("10.50"),
            "notes": None,
        }

    def get_tracking_history(self, shipment_id):
        return []

    def shipment_options(self):
        return {
            "customers": [],
            "routes": [],
            "drivers": [],
            "vehicles": [
                {
                    "vehicle_id": 1,
                    "registration_no": "TEST-1",
                    "vehicle_type": "van",
                    "capacity_kg": Decimal("12.50"),
                }
            ],
            "hubs": [],
        }

    def report_shipments(self):
        return [
            {
                "tracking_number": "FT-SYNTHETIC-1",
                "customer_name": "Synthetic Test Customer",
                "route_name": "Test Origin - Test Destination",
                "origin_hub": "Test Origin",
                "destination_hub": "Test Destination",
                "status": "delivered",
                "priority": "standard",
                "booked_at": datetime(2026, 11, 1, tzinfo=timezone.utc),
                "expected_delivery_at": datetime(2026, 11, 3, tzinfo=timezone.utc),
                "delivered_at": datetime(2026, 11, 2, tzinfo=timezone.utc),
                "on_time": True,
                "transit_hours": 24.0,
                "weight_kg": 1.5,
                "shipping_cost": 10,
            }
        ]


class FakeMongoRepository:
    def get_tracking_events(self, shipment_id):
        return []


class CapturingCursor:
    def __init__(self):
        self.calls = []
        self.last_query = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params):
        self.last_query = query
        self.calls.append((query, params))

    def fetchone(self):
        return {"total": 1}

    def fetchall(self):
        return []


class CapturingConnection:
    def __init__(self):
        self.cursor_instance = CapturingCursor()

    def cursor(self):
        return self.cursor_instance


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_postgres_repository] = FakePostgresRepository
    app.dependency_overrides[get_mongo_repository] = FakeMongoRepository
    app.dependency_overrides[get_application_user] = lambda: object()
    app.dependency_overrides[require_application_csrf] = lambda: object()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_liveness_and_openapi_are_available(client):
    live = client.get("/api/v1/health/live")
    openapi = client.get("/openapi.json")

    assert live.status_code == 200
    assert live.json() == {"status": "alive"}
    assert openapi.status_code == 200
    assert "/api/v1/dashboard/summary" in openapi.json()["paths"]
    assert "/api/v1/geospatial/network" in openapi.json()["paths"]
    assert "/api/v1/shipments/{shipment_id}/tracking" in openapi.json()["paths"]
    assert "/api/v1/shipments/{shipment_id}/status" in openapi.json()["paths"]
    assert "/api/v1/shipments/{shipment_id}/deliveries" in openapi.json()["paths"]
    assert "/api/v1/shipments/{shipment_id}/cancel" in openapi.json()["paths"]
    assert "/api/v1/auth/login" in openapi.json()["paths"]
    assert "/api/v1/admin/users" in openapi.json()["paths"]


def test_data_routes_require_a_server_side_session(client):
    app.dependency_overrides.pop(get_application_user)
    app.dependency_overrides[get_auth_repository] = lambda: None

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.headers["cache-control"] == "no-store"


def test_shipment_read_routes_still_require_a_server_side_session(client):
    app.dependency_overrides.pop(get_application_user)
    app.dependency_overrides[get_auth_repository] = lambda: None

    responses = [
        client.get("/api/v1/shipments?limit=50&offset=0"),
        client.get("/api/v1/shipments/1306"),
        client.get("/api/v1/shipments/options"),
    ]

    assert [response.status_code for response in responses] == [401, 401, 401]


def test_dashboard_responses_are_typed_and_include_event_months(client):
    summary = client.get("/api/v1/dashboard/summary")
    trends = client.get("/api/v1/dashboard/monthly-trends?from_month=2026-11-15")

    assert summary.status_code == 200
    assert summary.json()["total_shipments"] == 12
    assert trends.status_code == 200
    assert trends.json()["items"][0]["delivered_at_count"] == 7


def test_hub_performance_returns_database_aggregates_and_location(client):
    response = client.get(
        "/api/v1/analytics/hubs?from_date=2026-11-01&to_date=2026-11-30"
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["items"][0] == {
        "hub_id": 1,
        "hub_code": "H-1",
        "hub_name": "North Hub",
        "city": "North City",
        "state": "North State",
        "daily_capacity": 200,
        "shipments_handled": 4,
        "scan_count": 8,
        "delivered_shipments": 2,
        "in_progress_shipments": 2,
        "delivered_with_sla_count": 2,
        "on_time_shipments": 1,
        "on_time_pct": 50.0,
        "average_transit_hours": 24.5,
    }


def test_route_performance_returns_delivery_and_transit_metrics(client):
    response = client.get("/api/v1/analytics/routes")

    assert response.status_code == 200
    assert response.json()["items"][0]["route_code"] == "R-1"
    assert response.json()["items"][0]["shipment_count"] == 5
    assert response.json()["items"][0]["on_time_pct"] == 66.67
    assert response.json()["items"][0]["average_transit_hours"] == 42.5


def test_analytics_rejects_reversed_date_ranges(client):
    response = client.get(
        "/api/v1/analytics/routes?from_date=2026-11-30&to_date=2026-11-01"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_analytics_read_routes_require_a_server_side_session(client):
    app.dependency_overrides.pop(get_application_user)
    app.dependency_overrides[get_auth_repository] = lambda: None

    responses = [
        client.get("/api/v1/analytics/hubs"),
        client.get("/api/v1/analytics/routes"),
    ]

    assert [response.status_code for response in responses] == [401, 401]


def test_geospatial_network_exposes_missing_coordinates_and_real_relationships(client):
    response = client.get("/api/v1/geospatial/network")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["hubs"][0]["hub_id"] == 1
    assert payload["hubs"][0]["latitude"] is None
    assert payload["hubs"][0]["longitude"] is None
    assert payload["hubs"][0]["coordinate_status"] == "missing"
    assert payload["hubs"][0]["shipments_handled"] == 4
    assert payload["routes"][0]["origin"] == {
        "hub_name": "North Hub",
        "city": "North City",
        "state": "North State",
    }
    assert payload["routes"][0]["destination"]["hub_name"] == "South Hub"
    assert payload["routes"][0]["route_geometry"] is None
    assert payload["routes"][0]["geometry_status"] == "missing"
    assert payload["routes"][0]["shipment_count"] == 5
    assert payload["data_quality"] == {
        "total_hubs": 1,
        "hubs_with_verified_coordinates": 0,
        "hubs_missing_coordinates": 1,
        "hubs_with_invalid_coordinates": 0,
        "total_routes": 1,
        "routes_with_verified_geometry": 0,
        "routes_missing_geometry": 1,
        "routes_with_invalid_geometry": 0,
        "spatial_map_available": False,
    }


def test_geospatial_network_requires_a_server_side_session(client):
    app.dependency_overrides.pop(get_application_user)
    app.dependency_overrides[get_auth_repository] = lambda: None

    response = client.get("/api/v1/geospatial/network")

    assert response.status_code == 401


def test_geospatial_hub_rejects_invalid_or_partial_coordinates():
    valid_fields = {
        "hub_id": 1,
        "hub_code": "H-1",
        "hub_name": "Test Hub",
        "city": "Test City",
        "state": "Test State",
        "coordinate_status": "verified",
        "shipments_handled": 0,
        "delivered_shipments": 0,
        "in_progress_shipments": 0,
        "scan_count": 0,
        "on_time_pct": None,
    }

    with pytest.raises(ValidationError):
        GeospatialHub(**valid_fields, latitude=91, longitude=0)
    with pytest.raises(ValidationError):
        GeospatialHub(**valid_fields, latitude=10)


def test_geospatial_route_rejects_out_of_range_geometry():
    with pytest.raises(ValidationError):
        GeospatialRoute(
            route_id=1,
            route_code="R-1",
            route_name="Origin - Destination",
            origin={"hub_name": "Origin", "city": "Origin City", "state": "State"},
            destination={
                "hub_name": "Destination",
                "city": "Destination City",
                "state": "State",
            },
            distance_km=10,
            route_geometry=[(0, 0), (181, 0)],
            geometry_status="verified",
            shipment_count=0,
            delivered_shipments=0,
            in_progress_shipments=0,
            on_time_pct=None,
            average_transit_hours=None,
        )


@pytest.mark.parametrize(
    ("postgres_ok", "mongo_ok", "expected_status", "expected_body"),
    [
        (False, True, 503, {"postgres": "unavailable", "mongodb": "ok"}),
        (True, False, 503, {"postgres": "ok", "mongodb": "unavailable"}),
    ],
)
def test_readiness_checks_both_services_independently(
    client,
    postgres_ok,
    mongo_ok,
    expected_status,
    expected_body,
):
    checked = []

    def postgres_check():
        checked.append("postgres")
        return postgres_ok

    def mongo_check():
        checked.append("mongodb")
        return mongo_ok

    app.dependency_overrides[get_postgres_health_check] = lambda: postgres_check
    app.dependency_overrides[get_mongo_health_check] = lambda: mongo_check

    response = client.get("/api/v1/health/ready")

    assert response.status_code == expected_status
    assert response.json()["postgres"]["status"] == expected_body["postgres"]
    assert response.json()["mongodb"]["status"] == expected_body["mongodb"]
    assert checked == ["postgres", "mongodb"]


def test_invalid_path_and_query_parameters_return_validation_error(client):
    invalid_path = client.get("/api/v1/shipments/0")
    invalid_limit = client.get("/api/v1/shipments?limit=0")
    invalid_status = client.get("/api/v1/shipments?status=unknown")

    assert invalid_path.status_code == 422
    assert invalid_limit.status_code == 422
    assert invalid_status.status_code == 422
    assert invalid_path.json()["error"]["code"] == "validation_error"
    assert invalid_path.headers["x-request-id"]


def test_reversed_month_range_returns_a_typed_client_error(client):
    response = client.get(
        "/api/v1/dashboard/monthly-trends"
        "?from_month=2026-12-01&to_month=2026-11-01"
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_missing_shipment_returns_not_found(client):
    response = client.get("/api/v1/shipments/404")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_shipment_options_are_typed_and_non_cacheable(client):
    response = client.get("/api/v1/shipments/options")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "customers": [],
        "routes": [],
        "drivers": [],
        "vehicles": [
            {
                "vehicle_id": 1,
                "registration_no": "TEST-1",
                "vehicle_type": "van",
                "capacity_kg": 12.5,
            }
        ],
        "hubs": [],
    }
    assert isinstance(response.json()["vehicles"][0]["capacity_kg"], (int, float))


def test_shipment_detail_serializes_decimal_fields_as_json_numbers(client):
    response = client.get("/api/v1/shipments/1306")

    assert response.status_code == 200
    assert response.json()["weight_kg"] == 1.25
    assert response.json()["shipping_cost"] == 10.5
    assert isinstance(response.json()["weight_kg"], (int, float))
    assert isinstance(response.json()["shipping_cost"], (int, float))


def test_shipment_csv_export_uses_database_rows(client):
    response = client.get("/api/v1/reports/shipments.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"].endswith(
        'filename="fleettrack_shipments.csv"'
    )
    assert response.headers["cache-control"] == "no-store"
    assert "FT-SYNTHETIC-1,Synthetic Test Customer" in response.text


@pytest.mark.parametrize(
    "status",
    ["booked", "delivered", "failed", "out_for_delivery", "exception", "cancelled"],
)
def test_booking_and_delivery_outcomes_cannot_bypass_their_operations(client, status):
    response = client.post(
        "/api/v1/shipments/1/status",
        json={"status": status},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_shipment_requires_timezone_aware_sla(client):
    response = client.post(
        "/api/v1/shipments",
        json={
            "customer_id": 1,
            "route_id": 1,
            "weight_kg": 1,
            "shipping_cost": 10,
            "expected_delivery_at": "2026-12-01T10:00:00",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_postgres_unavailable_returns_sanitized_503(client):
    def unavailable_repository():
        try:
            raise RuntimeError("postgresql://user:private@host/db")
        except RuntimeError as exc:
            raise DependencyUnavailableError("postgresql") from exc

    app.dependency_overrides[get_postgres_repository] = unavailable_repository
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 503
    assert "private" not in response.text
    assert response.json()["error"]["dependency"] == "postgresql"


def test_mongodb_unavailable_returns_503_for_tracking(client):
    def unavailable_repository():
        raise DependencyUnavailableError("mongodb")

    app.dependency_overrides[get_mongo_repository] = unavailable_repository
    response = client.get("/api/v1/shipments/1/tracking")

    assert response.status_code == 503
    assert response.json()["error"]["dependency"] == "mongodb"


def test_shipment_filter_values_are_passed_as_dbapi_parameters():
    connection = CapturingConnection()
    repository = PostgresRepository(connection)
    tracking_filter = "' OR 1=1 --"

    repository.list_shipments(
        status="in_transit",
        tracking_number=tracking_filter,
        limit=10,
        offset=0,
    )

    assert len(connection.cursor_instance.calls) == 2
    for query, params in connection.cursor_instance.calls:
        assert tracking_filter not in query
        assert tracking_filter in params


def test_analytics_booking_date_ranges_are_parameterized():
    connection = CapturingConnection()
    repository = PostgresRepository(connection)
    from_date = date(2026, 11, 1)
    to_date = date(2026, 11, 30)

    repository.hub_performance(from_date, to_date)
    hub_query, hub_params = connection.cursor_instance.calls[-1]
    repository.route_performance(from_date, to_date)
    route_query, route_params = connection.cursor_instance.calls[-1]

    assert hub_params == (from_date, from_date, to_date, to_date)
    assert route_params == hub_params
    assert "shipment_status_history" in hub_query
    assert "vw_delivery_performance" in hub_query
    assert "vw_delivery_performance" in route_query
    assert "2026-11-01" not in hub_query + route_query


def test_analytics_date_filters_are_parameterized():
    connection = CapturingConnection()
    repository = PostgresRepository(connection)
    from_date = date(2026, 11, 1)
    to_date = date(2026, 11, 30)

    repository.hub_performance(from_date, to_date)
    hub_query, hub_params = connection.cursor_instance.calls[-1]
    repository.route_performance(from_date, to_date)
    route_query, route_params = connection.cursor_instance.calls[-1]

    assert hub_params == (from_date, from_date, to_date, to_date)
    assert route_params == hub_params
    assert "shipment_status_history" in hub_query
    assert "vw_delivery_performance" in hub_query
    assert "vw_delivery_performance" in route_query
    assert "2026-11-01" not in hub_query + route_query


def test_unexpected_error_response_and_logs_do_not_expose_exception_text(client, caplog):
    secret_like_text = "postgresql://user:private@host/database"

    def broken_repository():
        raise RuntimeError(secret_like_text)

    app.dependency_overrides[get_postgres_repository] = broken_repository
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 500
    assert secret_like_text not in response.text
    assert secret_like_text not in caplog.text
