from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


CoordinateStatus = Literal["verified", "missing", "invalid"]
GeometryStatus = Literal["verified", "missing", "invalid"]


class GeospatialHub(BaseModel):
    hub_id: int
    hub_code: str
    hub_name: str
    city: str
    state: str
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    coordinate_status: CoordinateStatus
    shipments_handled: int
    delivered_shipments: int
    in_progress_shipments: int
    scan_count: int
    on_time_pct: float | None

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> "GeospatialHub":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be supplied together.")
        if self.coordinate_status == "verified" and self.latitude is None:
            raise ValueError("Verified coordinates must include latitude and longitude.")
        if self.coordinate_status != "verified" and self.latitude is not None:
            raise ValueError("Only verified coordinates may be returned.")
        return self


class GeospatialEndpoint(BaseModel):
    hub_name: str
    city: str
    state: str


class GeospatialRoute(BaseModel):
    route_id: int
    route_code: str
    route_name: str
    origin: GeospatialEndpoint
    destination: GeospatialEndpoint
    distance_km: float
    route_geometry: list[tuple[float, float]] | None = None
    geometry_status: GeometryStatus
    shipment_count: int
    delivered_shipments: int
    in_progress_shipments: int
    on_time_pct: float | None
    average_transit_hours: float | None

    @model_validator(mode="after")
    def validate_route_geometry(self) -> "GeospatialRoute":
        if self.geometry_status == "verified":
            if self.route_geometry is None or len(self.route_geometry) < 2:
                raise ValueError("Verified route geometry must contain at least two points.")
            if any(
                not -180 <= longitude <= 180 or not -90 <= latitude <= 90
                for longitude, latitude in self.route_geometry
            ):
                raise ValueError("Route geometry coordinates are outside valid ranges.")
        elif self.route_geometry is not None:
            raise ValueError("Unverified route geometry must not be returned.")
        return self


class GeospatialDataQuality(BaseModel):
    total_hubs: int
    hubs_with_verified_coordinates: int
    hubs_missing_coordinates: int
    hubs_with_invalid_coordinates: int
    total_routes: int
    routes_with_verified_geometry: int
    routes_missing_geometry: int
    routes_with_invalid_geometry: int
    spatial_map_available: bool


class GeospatialNetworkResponse(BaseModel):
    hubs: list[GeospatialHub]
    routes: list[GeospatialRoute]
    data_quality: GeospatialDataQuality
