from __future__ import annotations

import ipaddress

from fastapi import APIRouter, Depends, Path, Query, Request, Response, status

from fleettrack_api.dependencies_auth import (
    get_administrator,
    get_auth_repository,
    require_administrator_csrf,
)
from fleettrack_api.repositories.auth import AuthRepository
from fleettrack_api.schemas.auth import (
    AdminUserCreate,
    AdminUserList,
    AdminUserUpdate,
    AdminUserView,
    AuditLogView,
    LoginAttemptView,
    TemporaryPasswordResponse,
)
from fleettrack_api.services.admin import AdminService
from fleettrack_api.services.auth import AuthenticatedPrincipal

router = APIRouter()


def _client_address(request: Request) -> str | None:
    if request.client is None:
        return None
    try:
        return str(ipaddress.ip_address(request.client.host))
    except ValueError:
        return None


def _user_view(user: dict) -> AdminUserView:
    return AdminUserView(**user)


@router.get("/users", response_model=AdminUserList, summary="List user accounts")
def list_users(
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repository: AuthRepository = Depends(get_auth_repository),
    _administrator: AuthenticatedPrincipal = Depends(get_administrator),
) -> AdminUserList:
    response.headers["Cache-Control"] = "no-store"
    total, rows = repository.list_users(limit=limit, offset=offset)
    return AdminUserList(total=total, items=[_user_view(row) for row in rows])


@router.post(
    "/users",
    response_model=TemporaryPasswordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account with a one-time password",
)
def create_user(
    payload: AdminUserCreate,
    request: Request,
    response: Response,
    repository: AuthRepository = Depends(get_auth_repository),
    administrator: AuthenticatedPrincipal = Depends(require_administrator_csrf),
) -> TemporaryPasswordResponse:
    user, temporary_password = AdminService().create_user(
        repository,
        actor=administrator,
        username=payload.username,
        display_name=payload.display_name,
        email=payload.email,
        roles=payload.roles,
        remote_address=_client_address(request),
    )
    response.headers["Cache-Control"] = "no-store"
    return TemporaryPasswordResponse(
        user=_user_view(user),
        temporary_password=temporary_password,
    )


@router.patch("/users/{user_id}", response_model=AdminUserView, summary="Update a user account")
def update_user(
    request: Request,
    response: Response,
    payload: AdminUserUpdate,
    user_id: int = Path(gt=0),
    repository: AuthRepository = Depends(get_auth_repository),
    administrator: AuthenticatedPrincipal = Depends(require_administrator_csrf),
) -> AdminUserView:
    changes = payload.model_dump(exclude_unset=True)
    result = AdminService().update_user(
        repository,
        actor=administrator,
        user_id=user_id,
        changes=changes,
        remote_address=_client_address(request),
    )
    response.headers["Cache-Control"] = "no-store"
    return _user_view(result)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=TemporaryPasswordResponse,
    summary="Reset a user's password and revoke existing sessions",
)
def reset_password(
    request: Request,
    response: Response,
    user_id: int = Path(gt=0),
    repository: AuthRepository = Depends(get_auth_repository),
    administrator: AuthenticatedPrincipal = Depends(require_administrator_csrf),
) -> TemporaryPasswordResponse:
    user, temporary_password = AdminService().reset_password(
        repository,
        actor=administrator,
        user_id=user_id,
        remote_address=_client_address(request),
    )
    response.headers["Cache-Control"] = "no-store"
    return TemporaryPasswordResponse(
        user=_user_view(user),
        temporary_password=temporary_password,
    )


@router.get("/login-attempts", response_model=list[LoginAttemptView], summary="Review login activity")
def login_activity(
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repository: AuthRepository = Depends(get_auth_repository),
    _administrator: AuthenticatedPrincipal = Depends(get_administrator),
) -> list[LoginAttemptView]:
    response.headers["Cache-Control"] = "no-store"
    _, rows = repository.list_login_attempts(limit=limit, offset=offset)
    return [LoginAttemptView(**row) for row in rows]


@router.get("/audit-logs", response_model=list[AuditLogView], summary="Review administrative audit events")
def audit_events(
    response: Response,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repository: AuthRepository = Depends(get_auth_repository),
    _administrator: AuthenticatedPrincipal = Depends(get_administrator),
) -> list[AuditLogView]:
    response.headers["Cache-Control"] = "no-store"
    _, rows = repository.list_audit_logs(limit=limit, offset=offset)
    return [AuditLogView(**row) for row in rows]
