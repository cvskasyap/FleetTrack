from __future__ import annotations

from pydantic import BaseModel


class HubPerformance(BaseModel):
    hub_id: int
    hub_code: str
    hub_name: str
    city: str
    state: str
    daily_capacity: int
    shipments_handled: int
    scan_count: int
    delivered_shipments: int
    in_progress_shipments: int
    delivered_with_sla_count: int
    on_time_shipments: int
    on_time_pct: float | None
    average_transit_hours: float | None


class HubPerformanceResponse(BaseModel):
    items: list[HubPerformance]


class RoutePerformance(BaseModel):
    route_id: int
    route_code: str
    route_name: str
    origin_hub: str
    origin_city: str
    origin_state: str
    destination_hub: str
    destination_city: str
    destination_state: str
    distance_km: float
    shipment_count: int
    delivered_shipments: int
    in_progress_shipments: int
    delivered_with_sla_count: int
    on_time_shipments: int
    on_time_pct: float | None
    average_transit_hours: float | None


class RoutePerformanceResponse(BaseModel):
    items: list[RoutePerformance]
