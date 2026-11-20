from __future__ import annotations

import hashlib
import hmac

from fastapi import Depends, Request

from fleettrack_api.core.errors import PermissionDeniedError
from fleettrack_api.dependencies import get_postgres_repository
from fleettrack_api.repositories.auth import AuthRepository
from fleettrack_api.repositories.postgres import PostgresRepository
from fleettrack_api.services.auth import AuthenticatedPrincipal, AuthService

SESSION_COOKIE_NAME = "fleettrack_session"
CSRF_COOKIE_NAME = "fleettrack_csrf"


def get_auth_repository(
    postgres_repository: PostgresRepository = Depends(get_postgres_repository),
) -> AuthRepository:
    return AuthRepository(postgres_repository.connection)


def get_current_user(
    request: Request,
    repository: AuthRepository = Depends(get_auth_repository),
) -> AuthenticatedPrincipal:
    return AuthService().principal_for_token(
        repository,
        request.cookies.get(SESSION_COOKIE_NAME),
    )


def get_application_user(
    current_user: AuthenticatedPrincipal = Depends(get_current_user),
) -> AuthenticatedPrincipal:
    if current_user.must_change_password:
        raise PermissionDeniedError("Change your temporary password before continuing.")
    return current_user


def get_administrator(
    current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> AuthenticatedPrincipal:
    if "ADMIN" not in current_user.roles:
        raise PermissionDeniedError("Administrator access is required.")
    return current_user


def require_csrf(
    request: Request,
    current_user: AuthenticatedPrincipal = Depends(get_current_user),
) -> AuthenticatedPrincipal:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get("X-CSRF-Token")
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise PermissionDeniedError("The request could not be verified.")
    digest = hashlib.sha256(cookie_token.encode("utf-8")).digest()
    if not hmac.compare_digest(digest, current_user.csrf_token_hash):
        raise PermissionDeniedError("The request could not be verified.")
    return current_user


def require_application_csrf(
    current_user: AuthenticatedPrincipal = Depends(require_csrf),
) -> AuthenticatedPrincipal:
    if current_user.must_change_password:
        raise PermissionDeniedError("Change your temporary password before continuing.")
    return current_user


def require_administrator_csrf(
    current_user: AuthenticatedPrincipal = Depends(require_csrf),
) -> AuthenticatedPrincipal:
    if current_user.must_change_password:
        raise PermissionDeniedError("Change your temporary password before continuing.")
    if "ADMIN" not in current_user.roles:
        raise PermissionDeniedError("Administrator access is required.")
    return current_user
