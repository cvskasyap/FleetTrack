from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from fleettrack_api.core.config import Settings
from fleettrack_api.core.errors import AuthenticationRequiredError, RateLimitExceededError
from fleettrack_api.repositories.auth import AuthRepository

PASSWORD_HASHER = PasswordHasher(type=Type.ID)
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash(secrets.token_urlsafe(32))


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: int
    username: str
    display_name: str
    email: str | None
    roles: tuple[str, ...]
    must_change_password: bool
    session_id: UUID
    csrf_token_hash: bytes


@dataclass(frozen=True)
class NewSession:
    user: dict[str, Any]
    session_token: str
    csrf_token: str
    expires_at: datetime


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        if len(password) < 14:
            raise ValueError("Passwords must contain at least 14 characters.")
        if "\x00" in password:
            raise ValueError("Passwords must not contain null characters.")
        return PASSWORD_HASHER.hash(password)

    @staticmethod
    def _verify(password_hash: str, password: str) -> bool:
        try:
            return PASSWORD_HASHER.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError, VerificationError):
            return False

    def authenticate(
        self,
        repository: AuthRepository,
        *,
        username: str,
        password: str,
        remote_address: str | None,
        user_agent: str | None,
        settings: Settings,
    ) -> NewSession:
        normalized_username = username.lower()
        blocked = False
        created_session: NewSession | None = None
        now = datetime.now(timezone.utc)
        failure_since = now - timedelta(seconds=settings.login_failure_window_seconds)

        with repository.connection.transaction():
            repository.acquire_login_locks(normalized_username, remote_address)
            username_failures, address_failures = repository.recent_failure_counts(
                normalized_username,
                remote_address,
                failure_since,
            )
            blocked = (
                username_failures >= settings.login_failure_limit
                or address_failures >= settings.login_ip_failure_limit
            )
            user = repository.user_for_login(normalized_username)
            stored_hash = user["password_hash"] if user else DUMMY_PASSWORD_HASH
            password_matches = self._verify(stored_hash, password)
            authenticated = bool(
                not blocked
                and user
                and user["is_active"]
                and password_matches
            )
            repository.record_login_attempt(
                normalized_username,
                remote_address,
                authenticated,
            )

            if authenticated and user is not None:
                if PASSWORD_HASHER.check_needs_rehash(stored_hash):
                    repository.rehash_password(
                        user["user_id"],
                        PASSWORD_HASHER.hash(password),
                    )
                session_token = secrets.token_urlsafe(32)
                csrf_token = secrets.token_urlsafe(32)
                expires_at = now + timedelta(seconds=settings.session_lifetime_seconds)
                repository.create_session(
                    user_id=user["user_id"],
                    token_hash=self.token_hash(session_token),
                    csrf_token_hash=self.token_hash(csrf_token),
                    remote_address=remote_address,
                    user_agent=user_agent[:512] if user_agent else None,
                    expires_at=expires_at,
                )
                repository.update_last_login(user["user_id"])
                repository.write_audit(
                    actor_user_id=user["user_id"],
                    action="auth.login",
                    entity_type="user",
                    entity_id=str(user["user_id"]),
                    outcome="success",
                    remote_address=remote_address,
                )
                created_session = NewSession(
                    user=user,
                    session_token=session_token,
                    csrf_token=csrf_token,
                    expires_at=expires_at,
                )

        if blocked:
            raise RateLimitExceededError("Too many sign-in attempts. Try again later.")
        if created_session is None:
            raise AuthenticationRequiredError("Invalid username or password.")
        return created_session

    @staticmethod
    def token_hash(token: str) -> bytes:
        return hashlib.sha256(token.encode("utf-8")).digest()

    def principal_for_token(
        self,
        repository: AuthRepository,
        token: str | None,
    ) -> AuthenticatedPrincipal:
        if not token or len(token) > 256:
            raise AuthenticationRequiredError("Sign in is required.")
        row = repository.principal_for_token(self.token_hash(token))
        if row is None:
            raise AuthenticationRequiredError("Sign in is required.")
        return AuthenticatedPrincipal(
            user_id=row["user_id"],
            username=row["username"],
            display_name=row["display_name"],
            email=row["email"],
            roles=tuple(row["roles"]),
            must_change_password=row["must_change_password"],
            session_id=row["session_id"],
            csrf_token_hash=bytes(row["csrf_token_hash"]),
        )
