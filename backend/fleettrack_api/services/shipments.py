from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fleettrack_api.core.errors import (
    InvalidRequestError,
    ResourceNotFoundError,
)
from fleettrack_api.repositories.mongodb import MongoRepository
from fleettrack_api.repositories.postgres import PostgresRepository
from fleettrack_api.schemas.shipments import (
    DeliveryAttemptCreate,
    ShipmentCancellationRequest,
    ShipmentCreate,
    ShipmentUpdate,
    StatusEventCreate,
)


class ShipmentService:
    def __init__(
        self,
        postgres_repository: PostgresRepository,
        mongo_repository: MongoRepository | None = None,
    ):
        self.postgres_repository = postgres_repository
        self.mongo_repository = mongo_repository

    def list_shipments(
        self,
        *,
        status: str | None,
        tracking_number: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        total, items = self.postgres_repository.list_shipments(
            status=status,
            tracking_number=tracking_number,
            limit=limit,
            offset=offset,
        )
        return {"total": total, "limit": limit, "offset": offset, "items": items}

    def get_shipment(self, shipment_id: int) -> dict:
        shipment = self.postgres_repository.get_shipment(shipment_id)
        if shipment is None:
            raise ResourceNotFoundError("Shipment not found")
        return shipment

    def get_shipment_detail(self, shipment_id: int) -> dict[str, Any]:
        shipment = self.postgres_repository.get_shipment_detail(shipment_id)
        if shipment is None:
            raise ResourceNotFoundError("Shipment not found")
        return shipment

    def get_tracking(self, shipment_id: int) -> dict:
        if self.mongo_repository is None:
            raise RuntimeError("MongoDB repository is required for tracking")
        shipment = self.postgres_repository.get_shipment(shipment_id)
        if shipment is None:
            raise ResourceNotFoundError("Shipment not found")
        relational_events = self.postgres_repository.get_tracking_history(shipment_id)
        mongo_events = self.mongo_repository.get_tracking_events(shipment_id)
        return {
            "shipment_id": shipment_id,
            "tracking_number": shipment["tracking_number"],
            "relational_events": relational_events,
            "mongo_events": mongo_events,
            "delivery_attempts": self.postgres_repository.get_delivery_attempts(
                shipment_id
            ),
        }

    def shipment_options(self) -> dict[str, list[dict[str, Any]]]:
        return self.postgres_repository.shipment_options()

    def create_shipment(self, payload: ShipmentCreate) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        if payload.expected_delivery_at <= now:
            raise InvalidRequestError("Expected delivery time must be in the future.")
        values = payload.model_dump()
        values["priority"] = payload.priority.value
        shipment_id = self.postgres_repository.create_shipment(values)
        return self._get_written_shipment(shipment_id)

    def update_shipment(
        self,
        shipment_id: int,
        payload: ShipmentUpdate,
    ) -> dict[str, Any]:
        current = self.postgres_repository.get_shipment_detail(shipment_id)
        if current is None:
            raise ResourceNotFoundError("Shipment not found")
        changes = payload.model_dump(exclude_unset=True)
        if "priority" in changes:
            changes["priority"] = payload.priority.value
        if not self.postgres_repository.update_shipment(shipment_id, changes):
            raise ResourceNotFoundError("Shipment not found")
        return self._get_written_shipment(shipment_id)

    def add_status_event(
        self,
        shipment_id: int,
        payload: StatusEventCreate,
    ) -> dict[str, Any]:
        if payload.status.value == "delivered":
            raise InvalidRequestError(
                "Record delivery outcomes through the delivery-attempt operation."
            )
        event_at = payload.event_at or datetime.now(timezone.utc)
        self._validate_event_time(event_at)
        if not self.postgres_repository.add_status_event(
            shipment_id,
            status=payload.status.value,
            hub_id=payload.hub_id,
            event_at=event_at,
            notes=payload.notes,
        ):
            raise ResourceNotFoundError("Shipment not found")
        return self._get_written_shipment(shipment_id)

    def create_delivery_attempt(
        self,
        shipment_id: int,
        payload: DeliveryAttemptCreate,
    ) -> dict[str, Any]:
        attempted_at = payload.attempted_at or datetime.now(timezone.utc)
        self._validate_event_time(attempted_at)
        if not self.postgres_repository.create_delivery_attempt(
            shipment_id,
            delivery_status=payload.delivery_status.value,
            attempted_at=attempted_at,
            recipient_name=payload.recipient_name,
            failure_reason=payload.failure_reason,
            notes=payload.notes,
        ):
            raise ResourceNotFoundError("Shipment not found")
        return self._get_written_shipment(shipment_id)

    def cancel_shipment(
        self,
        shipment_id: int,
        payload: ShipmentCancellationRequest,
    ) -> dict[str, Any]:
        if not self.postgres_repository.cancel_shipment(
            shipment_id,
            event_at=datetime.now(timezone.utc),
            reason=payload.reason,
        ):
            raise ResourceNotFoundError("Shipment not found")
        return self._get_written_shipment(shipment_id)

    def _get_written_shipment(self, shipment_id: int) -> dict[str, Any]:
        shipment = self.postgres_repository.get_shipment_detail(shipment_id)
        if shipment is None:
            raise ResourceNotFoundError("Shipment not found")
        return shipment

    @staticmethod
    def _validate_event_time(event_at: datetime) -> None:
        if event_at > datetime.now(timezone.utc):
            raise InvalidRequestError("Operational event time cannot be in the future.")
