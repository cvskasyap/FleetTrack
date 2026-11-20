from __future__ import annotations

from fleettrack_api.repositories.postgres import PostgresRepository
from fleettrack_api.schemas.geospatial import (
    GeospatialDataQuality,
    GeospatialHub,
    GeospatialNetworkResponse,
    GeospatialRoute,
    GeospatialEndpoint,
)


class GeospatialService:
    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def network(self) -> GeospatialNetworkResponse:
        hub_rows = self.repository.hub_performance(None, None)
        route_rows = self.repository.route_performance(None, None)

        hubs = [
            GeospatialHub(
                hub_id=row["hub_id"],
                hub_code=row["hub_code"],
                hub_name=row["hub_name"],
                city=row["city"],
                state=row["state"],
                latitude=None,
                longitude=None,
                coordinate_status="missing",
                shipments_handled=row["shipments_handled"],
                delivered_shipments=row["delivered_shipments"],
                in_progress_shipments=row["in_progress_shipments"],
                scan_count=row["scan_count"],
                on_time_pct=row["on_time_pct"],
            )
            for row in hub_rows
        ]
        routes = [
            GeospatialRoute(
                route_id=row["route_id"],
                route_code=row["route_code"],
                route_name=row["route_name"],
                origin=GeospatialEndpoint(
                    hub_name=row["origin_hub"],
                    city=row["origin_city"],
                    state=row["origin_state"],
                ),
                destination=GeospatialEndpoint(
                    hub_name=row["destination_hub"],
                    city=row["destination_city"],
                    state=row["destination_state"],
                ),
                distance_km=row["distance_km"],
                route_geometry=None,
                geometry_status="missing",
                shipment_count=row["shipment_count"],
                delivered_shipments=row["delivered_shipments"],
                in_progress_shipments=row["in_progress_shipments"],
                on_time_pct=row["on_time_pct"],
                average_transit_hours=row["average_transit_hours"],
            )
            for row in route_rows
        ]

        hubs_with_coordinates = sum(
            hub.coordinate_status == "verified" for hub in hubs
        )
        hubs_missing_coordinates = sum(
            hub.coordinate_status == "missing" for hub in hubs
        )
        hubs_with_invalid_coordinates = sum(
            hub.coordinate_status == "invalid" for hub in hubs
        )
        routes_with_geometry = sum(
            route.geometry_status == "verified" for route in routes
        )
        routes_missing_geometry = sum(
            route.geometry_status == "missing" for route in routes
        )
        routes_with_invalid_geometry = sum(
            route.geometry_status == "invalid" for route in routes
        )

        return GeospatialNetworkResponse(
            hubs=hubs,
            routes=routes,
            data_quality=GeospatialDataQuality(
                total_hubs=len(hubs),
                hubs_with_verified_coordinates=hubs_with_coordinates,
                hubs_missing_coordinates=hubs_missing_coordinates,
                hubs_with_invalid_coordinates=hubs_with_invalid_coordinates,
                total_routes=len(routes),
                routes_with_verified_geometry=routes_with_geometry,
                routes_missing_geometry=routes_missing_geometry,
                routes_with_invalid_geometry=routes_with_invalid_geometry,
                spatial_map_available=hubs_with_coordinates > 0,
            ),
        )
