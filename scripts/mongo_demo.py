from __future__ import annotations

from datetime import datetime, timezone

from fleettrack.config import MONGODB_DATABASE, MONGODB_URI
from pymongo import MongoClient


def main() -> None:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    collection = client[MONGODB_DATABASE]["crud_sandbox"]
    sample = {
        "tracking_number": "FT-DEMO-CRUD",
        "status": "in_transit",
        "event_at": datetime.now(timezone.utc),
        "note": "Temporary CRUD demonstration document",
    }
    inserted = collection.insert_one(sample)
    print("INSERT:", inserted.inserted_id)
    print("FIND:", collection.find_one({"_id": inserted.inserted_id}, {"_id": 0}))
    collection.update_one({"_id": inserted.inserted_id}, {"$set": {"status": "delivered"}})
    print("UPDATE:", collection.find_one({"_id": inserted.inserted_id}, {"_id": 0}))
    collection.delete_one({"_id": inserted.inserted_id})
    print("DELETE: remaining matching documents =", collection.count_documents({"tracking_number": "FT-DEMO-CRUD"}))
    client.close()


if __name__ == "__main__":
    main()
