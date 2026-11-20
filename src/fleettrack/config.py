from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fleettrack:change_this_local_password@localhost:5432/fleettrack",
)
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://fleettrack:change_this_mongo_password@localhost:27017/?authSource=admin",
)
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "fleettrack")
MONGODB_COLLECTION = "tracking_events"
