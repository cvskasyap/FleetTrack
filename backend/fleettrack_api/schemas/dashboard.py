from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_shipments: int
    delivered_shipments: int
    in_progress_shipments: int
    on_time_pct: float | None
    average_transit_hours: float | None


class MonthlyTrend(BaseModel):
    month: date
    booked_count: int
    delivered_in_booking_cohort: int
    delivered_at_count: int


class MonthlyTrendsResponse(BaseModel):
    items: list[MonthlyTrend]
