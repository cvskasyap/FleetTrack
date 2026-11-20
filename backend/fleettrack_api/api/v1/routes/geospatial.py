from fastapi import APIRouter, Depends, Response

from fleettrack_api.dependencies import get_postgres_repository
from fleettrack_api.dependencies_auth import get_application_user
from fleettrack_api.repositories.postgres import PostgresRepository
from fleettrack_api.schemas.geospatial import GeospatialNetworkResponse
from fleettrack_api.services.auth import AuthenticatedPrincipal
from fleettrack_api.services.geospatial import GeospatialService

router = APIRouter()


@router.get(
    "/network",
    response_model=GeospatialNetworkResponse,
    summary="Read verified hub locations and route relationships",
)
def get_geospatial_network(
    response: Response,
    repository: PostgresRepository = Depends(get_postgres_repository),
    _current_user: AuthenticatedPrincipal = Depends(get_application_user),
) -> GeospatialNetworkResponse:
    response.headers["Cache-Control"] = "no-store"
    return GeospatialService(repository).network()
