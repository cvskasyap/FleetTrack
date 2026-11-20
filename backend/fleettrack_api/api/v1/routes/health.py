from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from fleettrack_api.dependencies import (
    HealthCheck,
    get_mongo_health_check,
    get_postgres_health_check,
)
from fleettrack_api.schemas.health import LivenessResponse, ReadinessResponse
from fleettrack_api.services.health import HealthService

router = APIRouter()


@router.get("/live", response_model=LivenessResponse, summary="Check API liveness")
def liveness() -> LivenessResponse:
    return LivenessResponse()


@router.get("/ready", response_model=ReadinessResponse, summary="Check database readiness")
def readiness(
    response: Response,
    postgres_check: HealthCheck = Depends(get_postgres_health_check),
    mongo_check: HealthCheck = Depends(get_mongo_health_check),
) -> ReadinessResponse:
    result = HealthService(postgres_check, mongo_check).readiness()
    if result.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
