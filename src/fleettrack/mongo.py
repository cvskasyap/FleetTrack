from __future__ import annotations

from pymongo import MongoClient
from pymongo.collection import Collection

from .config import MONGODB_COLLECTION, MONGODB_DATABASE, MONGODB_URI


def get_client() -> MongoClient:
    return MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)


def get_tracking_collection() -> Collection:
    client = get_client()
    return client[MONGODB_DATABASE][MONGODB_COLLECTION]


def ensure_indexes() -> None:
    collection = get_tracking_collection()
    collection.create_index([("tracking_number", 1)])
    collection.create_index([("shipment_id", 1), ("event_at", 1)])
    collection.create_index([("hub_id", 1), ("event_at", -1)])
    collection.create_index([("delay_flag", 1), ("hub_id", 1)])
