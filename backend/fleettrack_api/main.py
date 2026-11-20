from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from fleettrack_api.api.v1.router import api_router
from fleettrack_api.core.config import get_settings
from fleettrack_api.core.errors import (
    AuthenticationRequiredError,
    ConflictError,
    DependencyUnavailableError,
    InvalidRequestError,
    PermissionDeniedError,
    RateLimitExceededError,
    ResourceNotFoundError,
)
from fleettrack_api.core.logging import configure_logging

logger = logging.getLogger(__name__)
API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(
        title="FleetTrack API",
        description=(
            "Typed read and shipment-operations API for the FleetTrack PostgreSQL "
            "operational database and MongoDB tracking events."
        ),
        version="1.0.0",
    )
    application.include_router(api_router, prefix=API_PREFIX)

    @application.middleware("http")
    async def request_logging(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "event": "http_request_completed",
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response

    @application.exception_handler(DependencyUnavailableError)
    async def dependency_unavailable(
        request: Request,
        exc: DependencyUnavailableError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "dependency_unavailable",
                    "message": "A required data service is unavailable.",
                    "dependency": exc.dependency,
                }
            },
            headers={"X-Request-ID": getattr(request.state, "request_id", "")},
        )

    @application.exception_handler(ResourceNotFoundError)
    async def resource_not_found(
        request: Request,
        exc: ResourceNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "not_found",
                    "message": str(exc),
                }
            },
            headers={"X-Request-ID": getattr(request.state, "request_id", "")},
        )

    @application.exception_handler(AuthenticationRequiredError)
    async def authentication_required(
        request: Request,
        exc: AuthenticationRequiredError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "authentication_required",
                    "message": str(exc),
                }
            },
            headers={
                "X-Request-ID": getattr(request.state, "request_id", ""),
                "WWW-Authenticate": "Session",
                "Cache-Control": "no-store",
            },
        )

    @application.exception_handler(PermissionDeniedError)
    async def permission_denied(
        request: Request,
        exc: PermissionDeniedError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "permission_denied",
                    "message": str(exc),
                }
            },
            headers={
                "X-Request-ID": getattr(request.state, "request_id", ""),
                "Cache-Control": "no-store",
            },
        )

    @application.exception_handler(RateLimitExceededError)
    async def rate_limited(
        request: Request,
        exc: RateLimitExceededError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limited",
                    "message": str(exc),
                }
            },
            headers={
                "X-Request-ID": getattr(request.state, "request_id", ""),
                "Retry-After": str(get_settings().login_failure_window_seconds),
                "Cache-Control": "no-store",
            },
        )

    @application.exception_handler(ConflictError)
    async def conflict(
        request: Request,
        exc: ConflictError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "conflict",
                    "message": str(exc),
                }
            },
            headers={"X-Request-ID": getattr(request.state, "request_id", "")},
        )

    @application.exception_handler(InvalidRequestError)
    async def invalid_request(
        request: Request,
        exc: InvalidRequestError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": str(exc),
                }
            },
            headers={"X-Request-ID": getattr(request.state, "request_id", "")},
        )

    @application.exception_handler(RequestValidationError)
    async def request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = [
            {
                "location": [str(part) for part in error["loc"]],
                "message": error["msg"],
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": errors,
                }
            },
            headers={"X-Request-ID": getattr(request.state, "request_id", "")},
        )

    @application.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled API error",
            extra={
                "event": "unhandled_api_error",
                "request_id": getattr(request.state, "request_id", ""),
                "error_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "The request could not be completed.",
                }
            },
            headers={"X-Request-ID": getattr(request.state, "request_id", "")},
        )

    return application


app = create_app()
