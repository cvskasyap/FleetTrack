from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from fleettrack_api.dependencies_auth import get_application_user
from fleettrack_api.dependencies import get_postgres_repository
from fleettrack_api.repositories.postgres import PostgresRepository
from fleettrack_api.schemas.dashboard import (
    DashboardSummary,
    MonthlyTrendsResponse,
)
from fleettrack_api.services.dashboard import DashboardService
from fleettrack_api.services.auth import AuthenticatedPrincipal

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary, summary="Read dashboard summary")
def dashboard_summary(
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> DashboardSummary:
    return DashboardService(repository).summary()


@router.get(
    "/monthly-trends",
    response_model=MonthlyTrendsResponse,
    summary="Read booking cohorts and delivery-event trends",
)
def monthly_trends(
    from_month: date | None = Query(
        default=None,
        description="Inclusive month selector; any day in the month is accepted.",
    ),
    to_month: date | None = Query(
        default=None,
        description="Inclusive month selector; any day in the month is accepted.",
    ),
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> MonthlyTrendsResponse:
    items = DashboardService(repository).monthly_trends(from_month, to_month)
    return MonthlyTrendsResponse(items=items)
