from fastapi import APIRouter

from fleettrack_api.api.v1.routes.analytics import router as analytics_router
from fleettrack_api.api.v1.routes.auth import router as auth_router
from fleettrack_api.api.v1.routes.admin import router as admin_router
from fleettrack_api.api.v1.routes.dashboard import router as dashboard_router
from fleettrack_api.api.v1.routes.geospatial import router as geospatial_router
from fleettrack_api.api.v1.routes.health import router as health_router
from fleettrack_api.api.v1.routes.reports import router as reports_router
from fleettrack_api.api.v1.routes.shipments import router as shipments_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(admin_router, prefix="/admin", tags=["administration"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["logistics analytics"])
api_router.include_router(geospatial_router, prefix="/geospatial", tags=["geospatial"])
api_router.include_router(shipments_router, prefix="/shipments", tags=["shipments"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
