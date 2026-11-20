from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


class DuplicateAccountError(Exception):
    pass


class LastAdministratorError(Exception):
    pass


class AuthRepository:
    def __init__(self, connection: psycopg.Connection[Any]):
        self.connection = connection

    def bootstrap_state(self) -> tuple[int, dict[str, list[str]]]:
        count = self.connection.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()["total"]
        rows = self.connection.execute(
            """
            SELECT u.username, COALESCE(array_agg(r.role_name) FILTER (WHERE r.role_name IS NOT NULL), '{}') AS roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.user_id
            LEFT JOIN roles r ON r.role_id = ur.role_id
            WHERE u.username IN ('admin', 'user')
            GROUP BY u.username
            """
        ).fetchall()
        return count, {row["username"]: row["roles"] for row in rows}

    def create_bootstrap_users(
        self,
        accounts: list[dict[str, Any]],
    ) -> None:
        with self.connection.transaction():
            self.connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended('fleettrack:bootstrap-users', 0))"
            )
            for account in accounts:
                exists = self.connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM users WHERE username = %s) AS account_exists",
                    (account["username"],),
                ).fetchone()["account_exists"]
                if exists:
                    raise DuplicateAccountError(
                        f"The bootstrap account {account['username']} already exists."
                    )
                self._create_user(
                    username=account["username"],
                    display_name=account["display_name"],
                    email=None,
                    password_hash=account["password_hash"],
                    must_change_password=False,
                    roles=[account["role"]],
                )

    def acquire_login_locks(self, username: str, remote_address: str | None) -> None:
        scopes = [f"username:{username}"]
        if remote_address:
            scopes.append(f"ip:{remote_address}")
        for scope in sorted(scopes):
            self.connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (scope,),
            )

    def recent_failure_counts(
        self,
        username: str,
        remote_address: str | None,
        since: datetime,
    ) -> tuple[int, int]:
        row = self.connection.execute(
            """
            SELECT COUNT(*) FILTER (WHERE username = %s)::int AS username_failures,
                   COUNT(*) FILTER (WHERE remote_address = %s::inet)::int AS address_failures
            FROM login_attempts
            WHERE succeeded = FALSE AND attempted_at >= %s
            """,
            (username, remote_address, since),
        ).fetchone()
        return row["username_failures"], row["address_failures"]

    def user_for_login(self, username: str) -> dict[str, Any] | None:
        return self.connection.execute(
            """
            SELECT u.user_id, u.username, u.display_name, u.email, u.password_hash,
                   u.is_active, u.must_change_password,
                   COALESCE(
                       array_agg(r.role_name) FILTER (WHERE r.role_name IS NOT NULL),
                       '{}'
                   ) AS roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.user_id
            LEFT JOIN roles r ON r.role_id = ur.role_id
            WHERE u.username = %s
            GROUP BY u.user_id
            """,
            (username,),
        ).fetchone()

    def record_login_attempt(
        self,
        username: str,
        remote_address: str | None,
        succeeded: bool,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO login_attempts (username, remote_address, succeeded)
            VALUES (%s, %s, %s)
            """,
            (username, remote_address, succeeded),
        )

    def update_last_login(self, user_id: int) -> None:
        self.connection.execute(
            "UPDATE users SET last_login_at = NOW(), updated_at = NOW() WHERE user_id = %s",
            (user_id,),
        )

    def create_session(
        self,
        *,
        user_id: int,
        token_hash: bytes,
        csrf_token_hash: bytes,
        remote_address: str | None,
        user_agent: str | None,
        expires_at: datetime,
    ) -> UUID:
        row = self.connection.execute(
            """
            INSERT INTO user_sessions
                (user_id, token_hash, csrf_token_hash, remote_address, user_agent, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING session_id
            """,
            (user_id, token_hash, csrf_token_hash, remote_address, user_agent, expires_at),
        ).fetchone()
        return row["session_id"]

    def principal_for_token(self, token_hash: bytes) -> dict[str, Any] | None:
        with self.connection.transaction():
            row = self.connection.execute(
                """
                SELECT s.session_id, s.user_id, s.csrf_token_hash, s.last_seen_at,
                       u.username, u.display_name, u.email, u.is_active, u.must_change_password,
                       COALESCE(
                           array_agg(r.role_name) FILTER (WHERE r.role_name IS NOT NULL),
                           '{}'
                       ) AS roles
                FROM user_sessions s
                JOIN users u ON u.user_id = s.user_id
                LEFT JOIN user_roles ur ON ur.user_id = u.user_id
                LEFT JOIN roles r ON r.role_id = ur.role_id
                WHERE s.token_hash = %s
                  AND s.revoked_at IS NULL
                  AND s.expires_at > NOW()
                  AND u.is_active = TRUE
                GROUP BY s.session_id, u.user_id
                """,
                (token_hash,),
            ).fetchone()
            if row:
                self.connection.execute(
                    """
                    UPDATE user_sessions
                    SET last_seen_at = NOW()
                    WHERE session_id = %s AND last_seen_at < NOW() - INTERVAL '5 minutes'
                    """,
                    (row["session_id"],),
                )
            return row

    def touch_session(self, session_id: UUID) -> None:
        with self.connection.transaction():
            self.connection.execute(
                """
                UPDATE user_sessions
                SET last_seen_at = NOW()
                WHERE session_id = %s AND last_seen_at < NOW() - INTERVAL '5 minutes'
                """,
                (session_id,),
            )

    def revoke_session(self, session_id: UUID) -> None:
        self.connection.execute(
            "UPDATE user_sessions SET revoked_at = NOW() WHERE session_id = %s AND revoked_at IS NULL",
            (session_id,),
        )

    def revoke_user_sessions(self, user_id: int) -> None:
        self.connection.execute(
            "UPDATE user_sessions SET revoked_at = NOW() WHERE user_id = %s AND revoked_at IS NULL",
            (user_id,),
        )

    def password_hash_for_user(self, user_id: int) -> str | None:
        row = self.connection.execute(
            "SELECT password_hash FROM users WHERE user_id = %s AND is_active = TRUE",
            (user_id,),
        ).fetchone()
        return row["password_hash"] if row else None

    def change_password(self, user_id: int, password_hash: str) -> None:
        self.connection.execute(
            """
            UPDATE users
            SET password_hash = %s, must_change_password = FALSE, updated_at = NOW()
            WHERE user_id = %s AND is_active = TRUE
            """,
            (password_hash, user_id),
        )
        self.revoke_user_sessions(user_id)

    def rehash_password(self, user_id: int, password_hash: str) -> None:
        self.connection.execute(
            "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE user_id = %s",
            (password_hash, user_id),
        )

    def list_users(self, *, limit: int, offset: int) -> tuple[int, list[dict[str, Any]]]:
        total = self.connection.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()["total"]
        rows = self.connection.execute(
            """
            SELECT u.user_id, u.username, u.display_name, u.email, u.is_active,
                   u.must_change_password, u.created_at, u.last_login_at,
                   COALESCE(
                       array_agg(r.role_name) FILTER (WHERE r.role_name IS NOT NULL),
                       '{}'
                   ) AS roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.user_id
            LEFT JOIN roles r ON r.role_id = ur.role_id
            GROUP BY u.user_id
            ORDER BY u.username
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
        return total, rows

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        return self.connection.execute(
            """
            SELECT u.user_id, u.username, u.display_name, u.email, u.is_active,
                   u.must_change_password, u.created_at, u.last_login_at,
                   COALESCE(
                       array_agg(r.role_name) FILTER (WHERE r.role_name IS NOT NULL),
                       '{}'
                   ) AS roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.user_id
            LEFT JOIN roles r ON r.role_id = ur.role_id
            WHERE u.user_id = %s
            GROUP BY u.user_id
            """,
            (user_id,),
        ).fetchone()

    def create_user(
        self,
        *,
        username: str,
        display_name: str,
        email: str | None,
        password_hash: str,
        roles: list[str],
    ) -> dict[str, Any]:
        with self.connection.transaction():
            user_id = self._create_user(
                username=username,
                display_name=display_name,
                email=email,
                password_hash=password_hash,
                must_change_password=True,
                roles=roles,
            )
            result = self.get_user(user_id)
            if result is None:
                raise RuntimeError("Created account could not be read.")
            return result

    def update_user(
        self,
        user_id: int,
        *,
        display_name: str | None,
        email: str | None,
        email_supplied: bool,
        is_active: bool | None,
        roles: list[str] | None,
    ) -> dict[str, Any] | None:
        with self.connection.transaction():
            active_admins = self._lock_active_administrators()
            current = self.connection.execute(
                "SELECT user_id, is_active FROM users WHERE user_id = %s FOR UPDATE",
                (user_id,),
            ).fetchone()
            if current is None:
                return None

            if is_active is not None or roles is not None:
                current_roles = self._get_roles(user_id)
                removes_admin = (
                    "ADMIN" in current_roles
                    and (
                        is_active is False
                        or (roles is not None and "ADMIN" not in roles)
                    )
                )
                if current["is_active"] and removes_admin and len(active_admins) <= 1:
                    raise LastAdministratorError("At least one active administrator must remain.")

            if display_name is not None or email_supplied or is_active is not None:
                self.connection.execute(
                    """
                    UPDATE users
                    SET display_name = COALESCE(%s, display_name),
                        email = CASE WHEN %s THEN %s ELSE email END,
                        is_active = COALESCE(%s, is_active),
                        updated_at = NOW()
                    WHERE user_id = %s
                    """,
                    (
                        display_name,
                        email_supplied,
                        email,
                        is_active,
                        user_id,
                    ),
                )
            if roles is not None:
                self._set_roles(user_id, roles)
            if is_active is False:
                self.revoke_user_sessions(user_id)
            result = self.get_user(user_id)
            if result is None:
                raise RuntimeError("Updated account could not be read.")
            return result

    def set_password(self, user_id: int, password_hash: str) -> bool:
        with self.connection.transaction():
            result = self.connection.execute(
                """
                UPDATE users
                SET password_hash = %s, must_change_password = TRUE, updated_at = NOW()
                WHERE user_id = %s
                RETURNING user_id
                """,
                (password_hash, user_id),
            ).fetchone()
            if result is None:
                return False
            self.revoke_user_sessions(user_id)
            return True

    def list_login_attempts(self, *, limit: int, offset: int) -> tuple[int, list[dict[str, Any]]]:
        total = self.connection.execute(
            "SELECT COUNT(*) AS total FROM login_attempts"
        ).fetchone()["total"]
        rows = self.connection.execute(
            """
            SELECT login_attempt_id, username, host(remote_address) AS remote_address,
                   succeeded, attempted_at
            FROM login_attempts
            ORDER BY attempted_at DESC, login_attempt_id DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
        return total, rows

    def list_audit_logs(self, *, limit: int, offset: int) -> tuple[int, list[dict[str, Any]]]:
        total = self.connection.execute(
            "SELECT COUNT(*) AS total FROM audit_logs"
        ).fetchone()["total"]
        rows = self.connection.execute(
            """
            SELECT a.audit_log_id, u.username AS actor_username, a.action, a.entity_type,
                   a.entity_id, a.outcome, a.details, host(a.remote_address) AS remote_address,
                   a.created_at
            FROM audit_logs a
            LEFT JOIN users u ON u.user_id = a.actor_user_id
            ORDER BY a.created_at DESC, a.audit_log_id DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
        return total, rows

    def write_audit(
        self,
        *,
        actor_user_id: int | None,
        action: str,
        entity_type: str,
        entity_id: str | None,
        outcome: str,
        details: dict[str, Any] | None = None,
        remote_address: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO audit_logs
                (actor_user_id, action, entity_type, entity_id, outcome, details, remote_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                outcome,
                Jsonb(details or {}),
                remote_address,
            ),
        )

    def _create_user(
        self,
        *,
        username: str,
        display_name: str,
        email: str | None,
        password_hash: str,
        must_change_password: bool,
        roles: list[str],
    ) -> int:
        row = self.connection.execute(
            """
            INSERT INTO users
                (username, display_name, email, password_hash, must_change_password)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id
            """,
            (username, display_name, email, password_hash, must_change_password),
        ).fetchone()
        user_id = row["user_id"]
        role_rows = self.connection.execute(
            "SELECT role_id, role_name FROM roles WHERE role_name = ANY(%s)",
            (roles,),
        ).fetchall()
        if {role["role_name"] for role in role_rows} != set(roles):
            raise ValueError("An account role is not configured.")
        with self.connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                [(user_id, role["role_id"]) for role in role_rows],
            )
        return user_id

    def _get_roles(self, user_id: int) -> set[str]:
        rows = self.connection.execute(
            """
            SELECT r.role_name
            FROM user_roles ur
            JOIN roles r ON r.role_id = ur.role_id
            WHERE ur.user_id = %s
            """,
            (user_id,),
        ).fetchall()
        return {row["role_name"] for row in rows}

    def _set_roles(self, user_id: int, roles: list[str]) -> None:
        role_rows = self.connection.execute(
            "SELECT role_id, role_name FROM roles WHERE role_name = ANY(%s)",
            (roles,),
        ).fetchall()
        if {row["role_name"] for row in role_rows} != set(roles):
            raise ValueError("An account role is not configured.")
        self.connection.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
        with self.connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                [(user_id, row["role_id"]) for row in role_rows],
            )

    def _lock_active_administrators(self) -> list[int]:
        rows = self.connection.execute(
            """
            SELECT u.user_id
            FROM users u
            JOIN user_roles ur ON ur.user_id = u.user_id
            JOIN roles r ON r.role_id = ur.role_id
            WHERE u.is_active = TRUE AND r.role_name = 'ADMIN'
            ORDER BY u.user_id
            FOR UPDATE OF u
            """
        ).fetchall()
        return [row["user_id"] for row in rows]
