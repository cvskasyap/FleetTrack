from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

STATUS_STAGES: dict[str, tuple[str, ...]] = {
    "delivered": ("booked", "picked_up", "in_transit", "at_hub", "out_for_delivery", "delivered"),
    "failed": ("booked", "picked_up", "in_transit", "at_hub", "out_for_delivery", "failed"),
    "exception": ("booked", "picked_up", "in_transit", "exception"),
    "returned": ("booked", "picked_up", "in_transit", "at_hub", "out_for_delivery", "failed", "returned"),
    "out_for_delivery": ("booked", "picked_up", "in_transit", "at_hub", "out_for_delivery"),
    "at_hub": ("booked", "picked_up", "in_transit", "at_hub"),
    "in_transit": ("booked", "picked_up", "in_transit"),
    "booked": ("booked",),
}


def build_timeline(final_status: str, booked_at: datetime, step_minutes: Iterable[int]) -> list[tuple[str, datetime]]:
    """Create a deterministic, ordered status sequence for a shipment."""
    if final_status not in STATUS_STAGES:
        raise ValueError(f"Unsupported final status: {final_status}")
    stages = STATUS_STAGES[final_status]
    offsets = list(step_minutes)
    if len(offsets) != len(stages):
        raise ValueError("step_minutes must contain one offset per status stage")
    events = [(status, booked_at + timedelta(minutes=offset))
              for status, offset in zip(stages, offsets)]
    if any(events[i][1] > events[i + 1][1] for i in range(len(events) - 1)):
        raise ValueError("Timeline timestamps must be chronological")
    return events


def is_on_time(expected_at: datetime, delivered_at: datetime | None) -> bool | None:
    """Return SLA outcome; None represents an undelivered shipment."""
    if delivered_at is None:
        return None
    return delivered_at <= expected_at
