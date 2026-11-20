from __future__ import annotations

import secrets
from typing import Any

import psycopg

from fleettrack_api.core.errors import ConflictError, ResourceNotFoundError
from fleettrack_api.repositories.auth import (
    AuthRepository,
    DuplicateAccountError,
    LastAdministratorError,
)
from fleettrack_api.services.auth import AuthService, AuthenticatedPrincipal


class AdminService:
    def create_user(
        self,
        repository: AuthRepository,
        *,
        actor: AuthenticatedPrincipal,
        username: str,
        display_name: str,
        email: str | None,
        roles: list[str],
        remote_address: str | None,
    ) -> tuple[dict[str, Any], str]:
        temporary_password = secrets.token_urlsafe(18)
        password_hash = AuthService.hash_password(temporary_password)
        try:
            with repository.connection.transaction():
                user = repository.create_user(
                    username=username,
                    display_name=display_name,
                    email=email,
                    password_hash=password_hash,
                    roles=roles,
                )
                repository.write_audit(
                    actor_user_id=actor.user_id,
                    action="admin.user_created",
                    entity_type="user",
                    entity_id=str(user["user_id"]),
                    outcome="success",
                    details={"roles": roles},
                    remote_address=remote_address,
                )
        except psycopg.errors.UniqueViolation as exc:
            raise ConflictError("The username or email address is already in use.") from exc
        return user, temporary_password

    def update_user(
        self,
        repository: AuthRepository,
        *,
        actor: AuthenticatedPrincipal,
        user_id: int,
        changes: dict[str, Any],
        remote_address: str | None,
    ) -> dict[str, Any]:
        if not changes:
            raise ConflictError("Provide at least one account field to update.")
        try:
            with repository.connection.transaction():
                user = repository.update_user(
                    user_id,
                    display_name=changes.get("display_name"),
                    email=changes.get("email"),
                    email_supplied="email" in changes,
                    is_active=changes.get("is_active"),
                    roles=changes.get("roles"),
                )
                if user is None:
                    raise ResourceNotFoundError("User account not found.")
                repository.write_audit(
                    actor_user_id=actor.user_id,
                    action="admin.user_updated",
                    entity_type="user",
                    entity_id=str(user_id),
                    outcome="success",
                    details={"changed_fields": sorted(changes)},
                    remote_address=remote_address,
                )
        except LastAdministratorError as exc:
            raise ConflictError(str(exc)) from exc
        except psycopg.errors.UniqueViolation as exc:
            raise ConflictError("The email address is already in use.") from exc
        return user

    def reset_password(
        self,
        repository: AuthRepository,
        *,
        actor: AuthenticatedPrincipal,
        user_id: int,
        remote_address: str | None,
    ) -> tuple[dict[str, Any], str]:
        temporary_password = secrets.token_urlsafe(18)
        password_hash = AuthService.hash_password(temporary_password)
        with repository.connection.transaction():
            if not repository.set_password(user_id, password_hash):
                raise ResourceNotFoundError("User account not found.")
            user = repository.get_user(user_id)
            if user is None:
                raise ResourceNotFoundError("User account not found.")
            repository.write_audit(
                actor_user_id=actor.user_id,
                action="admin.user_password_reset",
                entity_type="user",
                entity_id=str(user_id),
                outcome="success",
                remote_address=remote_address,
            )
        return user, temporary_password

