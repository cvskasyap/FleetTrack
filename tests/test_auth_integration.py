from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from fleettrack_api.api.v1.routes.auth import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME
from fleettrack_api.core.config import Settings, get_settings
from fleettrack_api.dependencies_auth import get_auth_repository
from fleettrack_api.main import app
from fleettrack_api.repositories.auth import AuthRepository


@pytest.fixture(scope="module")
def auth_test_accounts(disposable_database_url):
    accounts = {
        "admin": secrets.token_urlsafe(24),
        "user": secrets.token_urlsafe(24),
    }
    with psycopg.connect(disposable_database_url, row_factory=dict_row) as connection:
        AuthRepository(connection).create_bootstrap_users(
            [
                {
                    "username": "admin",
                    "display_name": "Integration Administrator",
                    "password_hash": _hash_password(accounts["admin"]),
                    "role": "ADMIN",
                },
                {
                    "username": "user",
                    "display_name": "Integration User",
                    "password_hash": _hash_password(accounts["user"]),
                    "role": "USER",
                },
            ]
        )
    return accounts


def _hash_password(password: str) -> str:
    from fleettrack_api.services.auth import AuthService

    return AuthService.hash_password(password)


@pytest.fixture
def auth_client(disposable_database_url):
    settings = Settings(
        database_url=disposable_database_url,
        session_cookie_secure=False,
        login_failure_limit=3,
        login_ip_failure_limit=100,
        login_failure_window_seconds=900,
    )

    def provide_auth_repository():
        with psycopg.connect(disposable_database_url, row_factory=dict_row) as connection:
            yield AuthRepository(connection)

    app.dependency_overrides.clear()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_auth_repository] = provide_auth_repository
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


def _login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


def test_login_uses_httponly_session_cookie_and_logout_revokes_it(
    auth_client,
    auth_test_accounts,
):
    response = _login(auth_client, "admin", auth_test_accounts["admin"])

    assert response.status_code == 200
    assert response.json()["user"]["roles"] == ["ADMIN"]
    set_cookies = response.headers.get_list("set-cookie")
    session_cookie = next(value for value in set_cookies if value.startswith(f"{SESSION_COOKIE_NAME}="))
    csrf_cookie = next(value for value in set_cookies if value.startswith(f"{CSRF_COOKIE_NAME}="))
    assert "httponly" in session_cookie.lower()
    assert "httponly" not in csrf_cookie.lower()
    assert "samesite=strict" in session_cookie.lower()
    current_user = auth_client.get("/api/v1/auth/me")
    assert current_user.json()["username"] == "admin"
    assert current_user.headers["cache-control"] == "no-store"

    csrf_token = auth_client.cookies.get(CSRF_COOKIE_NAME)
    logout = auth_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert logout.status_code == 204
    assert auth_client.get("/api/v1/auth/me").status_code == 401


def test_csrf_is_required_for_session_mutations(auth_client, auth_test_accounts):
    assert _login(auth_client, "user", auth_test_accounts["user"]).status_code == 200

    response = auth_client.post("/api/v1/auth/logout")

    assert response.status_code == 403
    assert auth_client.get("/api/v1/auth/me").status_code == 200


def test_admin_creates_temporary_account_and_last_admin_is_protected(
    auth_client,
    auth_test_accounts,
    disposable_database_url,
):
    assert _login(auth_client, "admin", auth_test_accounts["admin"]).status_code == 200
    csrf_token = auth_client.cookies.get(CSRF_COOKIE_NAME)
    users = auth_client.get("/api/v1/admin/users")
    assert users.status_code == 200
    assert users.headers["cache-control"] == "no-store"
    admin_id = next(item["user_id"] for item in users.json()["items"] if item["username"] == "admin")

    demote_last_admin = auth_client.patch(
        f"/api/v1/admin/users/{admin_id}",
        json={"roles": ["USER"]},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert demote_last_admin.status_code == 409

    create = auth_client.post(
        "/api/v1/admin/users",
        json={
            "username": "temporary.user",
            "display_name": "Temporary User",
            "email": None,
            "roles": ["USER"],
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert create.status_code == 201
    assert create.headers["cache-control"] == "no-store"
    created = create.json()
    assert created["user"]["must_change_password"] is True
    assert len(created["temporary_password"]) >= 14
    with psycopg.connect(disposable_database_url) as connection:
        stored_hash = connection.execute(
            "SELECT password_hash FROM users WHERE username = 'temporary.user'"
        ).fetchone()[0]
    assert stored_hash != created["temporary_password"]
    assert stored_hash.startswith("$argon2id$")

    updated = auth_client.patch(
        f"/api/v1/admin/users/{created['user']['user_id']}",
        json={"display_name": "Updated Temporary User"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert updated.status_code == 200
    assert updated.headers["cache-control"] == "no-store"

    temporary_password = created["temporary_password"]
    assert _login(auth_client, "temporary.user", temporary_password).status_code == 200
    assert auth_client.get("/api/v1/admin/users").status_code == 403
    csrf_token = auth_client.cookies.get(CSRF_COOKIE_NAME)
    changed_password = secrets.token_urlsafe(24)
    changed = auth_client.post(
        "/api/v1/auth/password",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "current_password": temporary_password,
            "new_password": changed_password,
            "confirm_password": changed_password,
        },
    )
    assert changed.status_code == 204
    assert auth_client.get("/api/v1/auth/me").status_code == 401
    assert _login(auth_client, "temporary.user", changed_password).status_code == 200


def test_admin_mutations_require_csrf(auth_client, auth_test_accounts):
    assert _login(auth_client, "admin", auth_test_accounts["admin"]).status_code == 200

    response = auth_client.post(
        "/api/v1/admin/users",
        json={
            "username": "csrf.protected",
            "display_name": "Must Not Be Created",
            "roles": ["USER"],
        },
    )

    assert response.status_code == 403
    assert auth_client.get("/api/v1/admin/users").status_code == 200


def test_shipment_operations_require_csrf(auth_client, auth_test_accounts):
    assert _login(auth_client, "user", auth_test_accounts["user"]).status_code == 200

    response = auth_client.post(
        "/api/v1/shipments/999/status",
        json={"status": "in_transit"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_authenticated_shipment_lifecycle_uses_history_triggers(
    auth_client,
    auth_test_accounts,
    disposable_database_url,
):
    assert _login(auth_client, "user", auth_test_accounts["user"]).status_code == 200
    csrf_token = auth_client.cookies.get(CSRF_COOKIE_NAME)
    suffix = secrets.token_hex(6)
    with psycopg.connect(disposable_database_url) as connection:
        customer_id = connection.execute(
            """
            INSERT INTO customers (customer_code, full_name, email, city, state)
            VALUES (%s, 'API Operations Customer', %s, 'Test City', 'Test State')
            RETURNING customer_id
            """,
            (f"API-{suffix}", f"api-{suffix}@example.test"),
        ).fetchone()[0]
        origin_id = connection.execute(
            """
            INSERT INTO hubs (hub_code, hub_name, city, state, daily_capacity)
            VALUES (%s, %s, 'Test City', 'Test State', 100)
            RETURNING hub_id
            """,
            (f"X{suffix[:11]}", f"API Origin {suffix}"),
        ).fetchone()[0]
        destination_id = connection.execute(
            """
            INSERT INTO hubs (hub_code, hub_name, city, state, daily_capacity)
            VALUES (%s, %s, 'Other City', 'Other State', 100)
            RETURNING hub_id
            """,
            (f"Y{suffix[:11]}", f"API Destination {suffix}"),
        ).fetchone()[0]
        route_id = connection.execute(
            """
            INSERT INTO routes
                (route_code, route_name, origin_hub_id, destination_hub_id, distance_km)
            VALUES (%s, %s, %s, %s, 100)
            RETURNING route_id
            """,
            (f"API-{suffix}", f"API Route {suffix}", origin_id, destination_id),
        ).fetchone()[0]

    def create_booking():
        return auth_client.post(
            "/api/v1/shipments",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "customer_id": customer_id,
                "route_id": route_id,
                "weight_kg": 2,
                "shipping_cost": 12,
                "priority": "standard",
                "expected_delivery_at": (
                    datetime.now(timezone.utc) + timedelta(days=2)
                ).isoformat(),
                "notes": "API lifecycle test",
            },
        )

    active_booking = create_booking()
    assert active_booking.status_code == 201
    assert active_booking.headers["cache-control"] == "no-store"
    active_id = active_booking.json()["shipment_id"]

    updated = auth_client.patch(
        f"/api/v1/shipments/{active_id}",
        headers={"X-CSRF-Token": csrf_token},
        json={"notes": "Metadata update only"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "booked"

    recorded_status = auth_client.post(
        f"/api/v1/shipments/{active_id}/status",
        headers={"X-CSRF-Token": csrf_token},
        json={"status": "in_transit"},
    )
    assert recorded_status.status_code == 200
    assert recorded_status.json()["status"] == "in_transit"

    rejected_cancel = auth_client.post(
        f"/api/v1/shipments/{active_id}/cancel",
        headers={"X-CSRF-Token": csrf_token},
        json={"reason": "Too late to cancel"},
    )
    assert rejected_cancel.status_code == 409

    delivered = auth_client.post(
        f"/api/v1/shipments/{active_id}/deliveries",
        headers={"X-CSRF-Token": csrf_token},
        json={
            "delivery_status": "delivered",
            "recipient_name": "API Test Recipient",
            "notes": "Delivered through attempt record",
        },
    )
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "delivered"

    cancelable = create_booking()
    assert cancelable.status_code == 201
    cancelable_id = cancelable.json()["shipment_id"]
    cancelled = auth_client.post(
        f"/api/v1/shipments/{cancelable_id}/cancel",
        headers={"X-CSRF-Token": csrf_token},
        json={"reason": "Customer requested cancellation"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    with psycopg.connect(disposable_database_url) as connection:
        active_status, delivered_events = connection.execute(
            """
            SELECT s.status,
                   COUNT(*) FILTER (WHERE h.status = 'delivered')
            FROM shipments s
            JOIN shipment_status_history h USING (shipment_id)
            WHERE s.shipment_id = %s
            GROUP BY s.status
            """,
            (active_id,),
        ).fetchone()
        cancelled_status = connection.execute(
            "SELECT status FROM shipments WHERE shipment_id = %s",
            (cancelable_id,),
        ).fetchone()[0]

    assert active_status == "delivered"
    assert delivered_events == 1
    assert cancelled_status == "cancelled"


def test_failed_login_rate_limit_is_enforced(auth_client):
    for _ in range(3):
        response = _login(auth_client, "nobody", secrets.token_urlsafe(18))
        assert response.status_code == 401

    limited = _login(auth_client, "nobody", secrets.token_urlsafe(18))
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "900"


def test_expired_or_revoked_session_is_rejected(
    auth_client,
    auth_test_accounts,
    disposable_database_url,
):
    assert _login(auth_client, "user", auth_test_accounts["user"]).status_code == 200
    token = auth_client.cookies.get(SESSION_COOKIE_NAME)
    token_hash = hashlib.sha256(token.encode("utf-8")).digest()
    with psycopg.connect(disposable_database_url) as connection:
        connection.execute(
            """
            UPDATE user_sessions
            SET created_at = NOW() - INTERVAL '2 minutes',
                expires_at = NOW() - INTERVAL '1 minute'
            WHERE token_hash = %s
            """,
            (token_hash,),
        )

    assert auth_client.get("/api/v1/auth/me").status_code == 401


def test_production_settings_require_secure_session_cookies():
    with pytest.raises(ValueError, match="SESSION_COOKIE_SECURE"):
        Settings(app_env="production", session_cookie_secure=False)
