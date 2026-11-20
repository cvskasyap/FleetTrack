from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Request, Response

from fleettrack_api.core.config import Settings, get_settings
from fleettrack_api.core.errors import (
    AuthenticationRequiredError,
    InvalidRequestError,
    PermissionDeniedError,
)
from fleettrack_api.dependencies_auth import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    get_auth_repository,
    get_current_user,
    require_csrf,
)
from fleettrack_api.repositories.auth import AuthRepository
from fleettrack_api.schemas.auth import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthUser,
    PasswordChangeRequest,
)
from fleettrack_api.services.auth import AuthenticatedPrincipal, AuthService

router = APIRouter()


def _client_address(request: Request) -> str | None:
    if request.client is None:
        return None
    try:
        return str(ipaddress.ip_address(request.client.host))
    except ValueError:
        return None


def _validate_login_origin(request: Request) -> None:
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise PermissionDeniedError("Cross-site sign-in requests are not accepted.")
    origin = request.headers.get("origin")
    if origin:
        parsed_origin = urlsplit(origin)
        expected_host = request.headers.get("host", "").lower()
        if (
            parsed_origin.netloc.lower() != expected_host
            or parsed_origin.scheme != request.url.scheme
            or parsed_origin.path not in {"", "/"}
        ):
            raise PermissionDeniedError("Sign-in must originate from the FleetTrack application.")


def _response_user(user: dict) -> AuthUser:
    return AuthUser(
        user_id=user["user_id"],
        username=user["username"],
        display_name=user["display_name"],
        email=user["email"],
        roles=user["roles"],
        must_change_password=user["must_change_password"],
    )


def _principal_user(principal: AuthenticatedPrincipal) -> AuthUser:
    return AuthUser(
        user_id=principal.user_id,
        username=principal.username,
        display_name=principal.display_name,
        email=principal.email,
        roles=list(principal.roles),
        must_change_password=principal.must_change_password,
    )


@router.post("/login", response_model=AuthLoginResponse, summary="Create a server-side session")
def login(
    payload: AuthLoginRequest,
    request: Request,
    response: Response,
    repository: AuthRepository = Depends(get_auth_repository),
    settings: Settings = Depends(get_settings),
) -> AuthLoginResponse:
    _validate_login_origin(request)
    session = AuthService().authenticate(
        repository,
        username=payload.username,
        password=payload.password.get_secret_value(),
        remote_address=_client_address(request),
        user_agent=request.headers.get("user-agent"),
        settings=settings,
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session.session_token,
        max_age=settings.session_lifetime_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/api/v1",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=session.csrf_token,
        max_age=settings.session_lifetime_seconds,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return AuthLoginResponse(user=_response_user(session.user))


@router.get("/me", response_model=AuthUser, summary="Read the current session user")
def current_session_user(
    response: Response,
    current_user: AuthenticatedPrincipal = Depends(get_current_user),
) -> AuthUser:
    response.headers["Cache-Control"] = "no-store"
    return _principal_user(current_user)


@router.post("/logout", status_code=204, summary="Revoke the current server-side session")
def logout(
    request: Request,
    response: Response,
    current_user: AuthenticatedPrincipal = Depends(require_csrf),
    repository: AuthRepository = Depends(get_auth_repository),
    settings: Settings = Depends(get_settings),
) -> Response:
    with repository.connection.transaction():
        repository.revoke_session(current_user.session_id)
        repository.write_audit(
            actor_user_id=current_user.user_id,
            action="auth.logout",
            entity_type="user",
            entity_id=str(current_user.user_id),
            outcome="success",
            remote_address=_client_address(request),
        )
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/api/v1",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path="/",
        secure=settings.session_cookie_secure,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    response.status_code = 204
    return response


@router.post("/password", status_code=204, summary="Change the current user's password")
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    current_user: AuthenticatedPrincipal = Depends(require_csrf),
    repository: AuthRepository = Depends(get_auth_repository),
    settings: Settings = Depends(get_settings),
) -> Response:
    stored_hash = repository.password_hash_for_user(current_user.user_id)
    service = AuthService()
    if stored_hash is None or not service._verify(
        stored_hash,
        payload.current_password.get_secret_value(),
    ):
        raise AuthenticationRequiredError("The current password is incorrect.")
    try:
        new_hash = service.hash_password(payload.new_password.get_secret_value())
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc

    with repository.connection.transaction():
        repository.change_password(current_user.user_id, new_hash)
        repository.write_audit(
            actor_user_id=current_user.user_id,
            action="auth.password_changed",
            entity_type="user",
            entity_id=str(current_user.user_id),
            outcome="success",
            remote_address=_client_address(request),
        )
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/api/v1",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path="/",
        secure=settings.session_cookie_secure,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    response.status_code = 204
    return response
