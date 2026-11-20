from __future__ import annotations

from collections.abc import Callable

from fleettrack_api.schemas.health import DependencyHealth, ReadinessResponse


class HealthService:
    def __init__(
        self,
        postgres_check: Callable[[], bool],
        mongo_check: Callable[[], bool],
    ):
        self.postgres_check = postgres_check
        self.mongo_check = mongo_check

    def readiness(self) -> ReadinessResponse:
        postgres_ok = self.postgres_check()
        mongodb_ok = self.mongo_check()
        ready = postgres_ok and mongodb_ok
        return ReadinessResponse(
            status="ready" if ready else "not_ready",
            postgres=DependencyHealth(status="ok" if postgres_ok else "unavailable"),
            mongodb=DependencyHealth(status="ok" if mongodb_ok else "unavailable"),
        )
