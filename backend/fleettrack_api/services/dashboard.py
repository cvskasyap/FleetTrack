from __future__ import annotations

from datetime import date

from fleettrack_api.core.errors import InvalidRequestError
from fleettrack_api.repositories.postgres import PostgresRepository


class DashboardService:
    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def summary(self) -> dict:
        return self.repository.dashboard_summary()

    def monthly_trends(
        self,
        from_month: date | None,
        to_month: date | None,
    ) -> list[dict]:
        if from_month and to_month and from_month.replace(day=1) > to_month.replace(day=1):
            raise InvalidRequestError("from_month must not be after to_month")
        return self.repository.monthly_trends(from_month, to_month)
