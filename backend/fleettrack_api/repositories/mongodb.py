from __future__ import annotations

import logging
from typing import Any

from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure

from fleettrack_api.core.errors import DependencyUnavailableError

logger = logging.getLogger(__name__)


class MongoRepository:
    def __init__(self, collection: Collection[Any]):
        self.collection = collection

    def get_tracking_events(self, shipment_id: int) -> list[dict[str, Any]]:
        projection = {
            "_id": 0,
            "tracking_number": 1,
            "status": 1,
            "event_at": 1,
            "hub_id": 1,
            "hub_name": 1,
            "hub_city": 1,
            "dwell_minutes": 1,
            "delay_flag": 1,
            "event_source": 1,
            "notes": 1,
        }
        try:
            return list(
                self.collection.find(
                    {"shipment_id": shipment_id},
                    projection,
                ).sort([("event_at", 1), ("_id", 1)])
            )
        except ConnectionFailure as exc:
            logger.warning(
                "MongoDB query failed",
                extra={"event": "mongodb_query_failed", "error_type": type(exc).__name__},
            )
            raise DependencyUnavailableError("mongodb") from exc
