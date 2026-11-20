from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ShipmentStatus(str, Enum):
    booked = "booked"
    picked_up = "picked_up"
    in_transit = "in_transit"
    at_hub = "at_hub"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    failed = "failed"
    exception = "exception"
    returned = "returned"
    cancelled = "cancelled"


class ShipmentPriority(str, Enum):
    standard = "standard"
    express = "express"
    same_day = "same_day"


class DeliveryStatus(str, Enum):
    delivered = "delivered"
    failed = "failed"
    out_for_delivery = "out_for_delivery"
    exception = "exception"


class ShipmentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shipment_id: int
    tracking_number: str
    customer_name: str
    route_name: str
    status: ShipmentStatus
    priority: ShipmentPriority
    booked_at: datetime
    expected_delivery_at: datetime
    delivered_at: datetime | None
    on_time: bool | None
    transit_hours: float | None


class ShipmentDetail(ShipmentSummary):
    customer_id: int
    customer_code: str
    route_id: int
    origin_hub: str
    destination_hub: str
    assigned_driver_id: int | None
    driver_code: str | None
    driver_name: str | None
    assigned_vehicle_id: int | None
    registration_no: str | None
    weight_kg: float
    shipping_cost: float
    notes: str | None


class ShipmentListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ShipmentSummary]


class RelationalTrackingEvent(BaseModel):
    status: ShipmentStatus
    event_at: datetime
    hub_id: int | None
    hub_name: str | None
    notes: str | None
    source: str


class DeliveryAttemptView(BaseModel):
    delivery_id: int
    attempt_no: int
    delivery_status: DeliveryStatus
    attempted_at: datetime
    recipient_name: str | None
    failure_reason: str | None
    notes: str | None


class MongoTrackingEvent(BaseModel):
    tracking_number: str
    status: ShipmentStatus
    event_at: datetime
    hub_id: int | None = None
    hub_name: str | None = None
    hub_city: str | None = None
    dwell_minutes: int | None = None
    delay_flag: bool = False
    event_source: str | None = None
    notes: str | None = None


class ShipmentTrackingResponse(BaseModel):
    shipment_id: int
    tracking_number: str
    relational_events: list[RelationalTrackingEvent]
    mongo_events: list[MongoTrackingEvent]
    delivery_attempts: list[DeliveryAttemptView] = Field(default_factory=list)


class CustomerOption(BaseModel):
    customer_id: int
    customer_code: str
    full_name: str


class RouteOption(BaseModel):
    route_id: int
    route_code: str
    route_name: str
    origin_hub: str
    destination_hub: str


class DriverOption(BaseModel):
    driver_id: int
    driver_code: str
    full_name: str


class VehicleOption(BaseModel):
    vehicle_id: int
    registration_no: str
    vehicle_type: str
    capacity_kg: float


class HubOption(BaseModel):
    hub_id: int
    hub_code: str
    hub_name: str


class ShipmentOptions(BaseModel):
    customers: list[CustomerOption]
    routes: list[RouteOption]
    drivers: list[DriverOption]
    vehicles: list[VehicleOption]
    hubs: list[HubOption]


class ShipmentCreate(BaseModel):
    customer_id: int = Field(gt=0)
    route_id: int = Field(gt=0)
    assigned_vehicle_id: int | None = Field(default=None, gt=0)
    assigned_driver_id: int | None = Field(default=None, gt=0)
    weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    shipping_cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    priority: ShipmentPriority = ShipmentPriority.standard
    expected_delivery_at: datetime
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("expected_delivery_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Expected delivery time must include a timezone.")
        return value


class ShipmentUpdate(BaseModel):
    customer_id: int | None = Field(default=None, gt=0)
    route_id: int | None = Field(default=None, gt=0)
    assigned_vehicle_id: int | None = Field(default=None, gt=0)
    assigned_driver_id: int | None = Field(default=None, gt=0)
    weight_kg: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )
    shipping_cost: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    priority: ShipmentPriority | None = None
    expected_delivery_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("expected_delivery_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Expected delivery time must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_changes(self) -> "ShipmentUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one shipment field to update.")
        non_nullable = {
            "customer_id",
            "route_id",
            "weight_kg",
            "shipping_cost",
            "priority",
            "expected_delivery_at",
        }
        if any(name in self.model_fields_set and getattr(self, name) is None for name in non_nullable):
            raise ValueError("Required shipment fields cannot be cleared.")
        return self


class StatusEventCreate(BaseModel):
    status: ShipmentStatus
    hub_id: int | None = Field(default=None, gt=0)
    event_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("event_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Event time must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_status_event_source(self) -> "StatusEventCreate":
        if self.status is ShipmentStatus.cancelled:
            raise ValueError("Use the cancellation operation for booked shipments.")
        if self.status is ShipmentStatus.booked:
            raise ValueError("The booked event is created with the shipment.")
        if self.status in {
            ShipmentStatus.delivered,
            ShipmentStatus.failed,
            ShipmentStatus.out_for_delivery,
            ShipmentStatus.exception,
        }:
            raise ValueError("Record delivery outcomes through delivery attempts.")
        return self


class DeliveryAttemptCreate(BaseModel):
    delivery_status: DeliveryStatus
    attempted_at: datetime | None = None
    recipient_name: str | None = Field(default=None, max_length=120)
    failure_reason: str | None = Field(default=None, max_length=240)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("recipient_name")
    @classmethod
    def normalize_recipient_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("attempted_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Attempt time must include a timezone.")
        return value

    @model_validator(mode="after")
    def delivered_attempt_requires_recipient(self) -> "DeliveryAttemptCreate":
        if self.delivery_status is DeliveryStatus.delivered and not self.recipient_name:
            raise ValueError("A delivered attempt requires a recipient name.")
        return self


class ShipmentCancellationRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=240)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Cancellation reason must contain at least 3 characters.")
        return normalized
