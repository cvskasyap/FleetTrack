from __future__ import annotations

from datetime import date

from fleettrack_api.core.errors import InvalidRequestError
from fleettrack_api.repositories.postgres import PostgresRepository


class LogisticsAnalyticsService:
    def __init__(self, repository: PostgresRepository):
        self.repository = repository

    def hub_performance(
        self,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict]:
        self._validate_range(from_date, to_date)
        return self.repository.hub_performance(from_date, to_date)

    def route_performance(
        self,
        from_date: date | None,
        to_date: date | None,
    ) -> list[dict]:
        self._validate_range(from_date, to_date)
        return self.repository.route_performance(from_date, to_date)

    @staticmethod
    def _validate_range(from_date: date | None, to_date: date | None) -> None:
        if from_date and to_date and from_date > to_date:
            raise InvalidRequestError("from_date must not be after to_date")
