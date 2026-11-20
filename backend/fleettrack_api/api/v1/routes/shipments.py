from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Response, status

from fleettrack_api.core.errors import ResourceNotFoundError
from fleettrack_api.dependencies import (
    get_mongo_repository,
    get_postgres_repository,
)
from fleettrack_api.dependencies_auth import (
    get_application_user,
    require_application_csrf,
)
from fleettrack_api.repositories.mongodb import MongoRepository
from fleettrack_api.repositories.postgres import PostgresRepository
from fleettrack_api.schemas.shipments import (
    DeliveryAttemptCreate,
    ShipmentCancellationRequest,
    ShipmentCreate,
    ShipmentDetail,
    ShipmentListResponse,
    ShipmentOptions,
    ShipmentStatus,
    ShipmentSummary,
    ShipmentTrackingResponse,
    ShipmentUpdate,
    StatusEventCreate,
)
from fleettrack_api.services.shipments import ShipmentService
from fleettrack_api.services.auth import AuthenticatedPrincipal

router = APIRouter()


@router.get("", response_model=ShipmentListResponse, summary="List shipments")
def list_shipments(
    response: Response,
    status_filter: ShipmentStatus | None = Query(default=None, alias="status"),
    tracking_number: str | None = Query(default=None, min_length=1, max_length=32),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> ShipmentListResponse:
    response.headers["Cache-Control"] = "no-store"
    result = ShipmentService(repository).list_shipments(
        status=status_filter.value if status_filter else None,
        tracking_number=tracking_number,
        limit=limit,
        offset=offset,
    )
    return ShipmentListResponse(**result)


@router.get(
    "/options",
    response_model=ShipmentOptions,
    summary="Read active shipment reference options",
)
def get_shipment_options(
    response: Response,
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> ShipmentOptions:
    response.headers["Cache-Control"] = "no-store"
    return ShipmentOptions(**ShipmentService(repository).shipment_options())


@router.post(
    "",
    response_model=ShipmentDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shipment",
)
def create_shipment(
    payload: ShipmentCreate,
    response: Response,
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(require_application_csrf),
) -> ShipmentDetail:
    response.headers["Cache-Control"] = "no-store"
    shipment = ShipmentService(repository).create_shipment(payload)
    return ShipmentDetail(**shipment)


@router.get(
    "/{shipment_id}",
    response_model=ShipmentDetail,
    summary="Read a shipment",
)
def get_shipment(
    response: Response,
    shipment_id: int = Path(gt=0),
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> ShipmentDetail:
    response.headers["Cache-Control"] = "no-store"
    shipment = ShipmentService(repository).get_shipment_detail(shipment_id)
    return ShipmentDetail(**shipment)


@router.patch(
    "/{shipment_id}",
    response_model=ShipmentDetail,
    summary="Update shipment booking details",
)
def update_shipment(
    payload: ShipmentUpdate,
    response: Response,
    shipment_id: int = Path(gt=0),
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(require_application_csrf),
) -> ShipmentDetail:
    response.headers["Cache-Control"] = "no-store"
    shipment = ShipmentService(repository).update_shipment(shipment_id, payload)
    return ShipmentDetail(**shipment)


@router.post(
    "/{shipment_id}/status",
    response_model=ShipmentDetail,
    summary="Record an operational status event",
)
def add_shipment_status_event(
    payload: StatusEventCreate,
    response: Response,
    shipment_id: int = Path(gt=0),
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(require_application_csrf),
) -> ShipmentDetail:
    response.headers["Cache-Control"] = "no-store"
    shipment = ShipmentService(repository).add_status_event(shipment_id, payload)
    return ShipmentDetail(**shipment)


@router.post(
    "/{shipment_id}/deliveries",
    response_model=ShipmentDetail,
    summary="Record a delivery attempt",
)
def add_delivery_attempt(
    payload: DeliveryAttemptCreate,
    response: Response,
    shipment_id: int = Path(gt=0),
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(require_application_csrf),
) -> ShipmentDetail:
    response.headers["Cache-Control"] = "no-store"
    shipment = ShipmentService(repository).create_delivery_attempt(shipment_id, payload)
    return ShipmentDetail(**shipment)


@router.post(
    "/{shipment_id}/cancel",
    response_model=ShipmentDetail,
    summary="Cancel a booked shipment",
)
def cancel_shipment(
    payload: ShipmentCancellationRequest,
    response: Response,
    shipment_id: int = Path(gt=0),
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(require_application_csrf),
) -> ShipmentDetail:
    response.headers["Cache-Control"] = "no-store"
    shipment = ShipmentService(repository).cancel_shipment(shipment_id, payload)
    return ShipmentDetail(**shipment)


@router.get(
    "/{shipment_id}/tracking",
    response_model=ShipmentTrackingResponse,
    summary="Read relational and document tracking events",
)
def get_shipment_tracking(
    response: Response,
    shipment_id: int = Path(gt=0),
    postgres_repository: PostgresRepository = Depends(get_postgres_repository),
    mongo_repository: MongoRepository = Depends(get_mongo_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> ShipmentTrackingResponse:
    response.headers["Cache-Control"] = "no-store"
    tracking = ShipmentService(postgres_repository, mongo_repository).get_tracking(
        shipment_id
    )
    return ShipmentTrackingResponse(**tracking)
