"""Reusable MongoDB aggregation pipelines for scan analytics."""


def hub_dwell_pipeline() -> list[dict]:
    return [
        {"$match": {"hub_id": {"$ne": None}, "dwell_minutes": {"$gte": 0}}},
        {"$group": {
            "_id": "$hub_id",
            "hub_code": {"$first": "$hub_code"},
            "hub_name": {"$first": "$hub_name"},
            "city": {"$first": "$hub_city"},
            "scan_count": {"$sum": 1},
            "avg_dwell_minutes": {"$avg": "$dwell_minutes"},
            "total_dwell_minutes": {"$sum": "$dwell_minutes"},
            "delay_scans": {"$sum": {"$cond": ["$delay_flag", 1, 0]}},
        }},
        {"$sort": {"avg_dwell_minutes": -1}},
    ]


def delay_hotspots_pipeline() -> list[dict]:
    return [
        {"$match": {"delay_flag": True, "hub_id": {"$ne": None}}},
        {"$group": {
            "_id": {"hub_id": "$hub_id", "status": "$status"},
            "hub_code": {"$first": "$hub_code"},
            "hub_name": {"$first": "$hub_name"},
            "city": {"$first": "$hub_city"},
            "delay_event_count": {"$sum": 1},
            "avg_dwell_minutes": {"$avg": "$dwell_minutes"},
        }},
        {"$sort": {"delay_event_count": -1, "avg_dwell_minutes": -1}},
    ]
