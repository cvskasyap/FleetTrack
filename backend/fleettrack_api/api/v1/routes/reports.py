from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from fleettrack_api.dependencies import get_postgres_repository
from fleettrack_api.dependencies_auth import get_application_user
from fleettrack_api.repositories.postgres import PostgresRepository
from fleettrack_api.services.auth import AuthenticatedPrincipal

router = APIRouter()

CSV_COLUMNS = (
    "tracking_number",
    "customer_name",
    "route_name",
    "origin_hub",
    "destination_hub",
    "status",
    "priority",
    "booked_at",
    "expected_delivery_at",
    "delivered_at",
    "on_time",
    "transit_hours",
    "weight_kg",
    "shipping_cost",
)


@router.get(
    "/shipments.csv",
    response_class=Response,
    summary="Export current shipment records as CSV",
)
def export_shipments_csv(
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> Response:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(repository.report_shipments())
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="fleettrack_shipments.csv"',
            "Cache-Control": "no-store",
        },
    )
