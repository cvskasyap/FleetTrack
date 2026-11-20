from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response

from fleettrack_api.dependencies import get_postgres_repository
from fleettrack_api.dependencies_auth import get_application_user
from fleettrack_api.repositories.postgres import PostgresRepository
from fleettrack_api.schemas.analytics import (
    HubPerformanceResponse,
    RoutePerformanceResponse,
)
from fleettrack_api.services.analytics import LogisticsAnalyticsService
from fleettrack_api.services.auth import AuthenticatedPrincipal

router = APIRouter()


@router.get(
    "/hubs",
    response_model=HubPerformanceResponse,
    summary="Compare shipment and delivery performance by hub",
)
def hub_performance(
    response: Response,
    from_date: date | None = Query(
        default=None,
        description="Inclusive shipment booking date range start.",
    ),
    to_date: date | None = Query(
        default=None,
        description="Inclusive shipment booking date range end.",
    ),
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> HubPerformanceResponse:
    response.headers["Cache-Control"] = "no-store"
    items = LogisticsAnalyticsService(repository).hub_performance(from_date, to_date)
    return HubPerformanceResponse(items=items)


@router.get(
    "/routes",
    response_model=RoutePerformanceResponse,
    summary="Compare shipment and delivery performance by route",
)
def route_performance(
    response: Response,
    from_date: date | None = Query(
        default=None,
        description="Inclusive shipment booking date range start.",
    ),
    to_date: date | None = Query(
        default=None,
        description="Inclusive shipment booking date range end.",
    ),
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> RoutePerformanceResponse:
    response.headers["Cache-Control"] = "no-store"
    items = LogisticsAnalyticsService(repository).route_performance(from_date, to_date)
    return RoutePerformanceResponse(items=items)
