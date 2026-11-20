import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import mean

import pytest

from fleettrack.demo_data import build_timeline, is_on_time
from scripts.seed_data import (
    DEFAULT_SEED_ANCHOR,
    booking_age_days,
    get_seed_anchor,
    weighted_status,
)


def test_timeline_uses_expected_status_order_and_chronology():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    timeline = build_timeline("delivered", start, [0, 30, 180, 360, 420, 480])
    assert [status for status, _ in timeline] == [
        "booked", "picked_up", "in_transit", "at_hub", "out_for_delivery", "delivered"
    ]
    assert timeline[0][1] == start
    assert all(timeline[i][1] <= timeline[i + 1][1] for i in range(len(timeline) - 1))


def test_timeline_rejects_unknown_status():
    with pytest.raises(ValueError):
        build_timeline("lost", datetime.now(timezone.utc), [0])


def test_timeline_rejects_wrong_number_of_offsets():
    with pytest.raises(ValueError):
        build_timeline("booked", datetime.now(timezone.utc), [0, 10])


def test_timeline_rejects_non_chronological_offsets():
    with pytest.raises(ValueError):
        build_timeline("in_transit", datetime.now(timezone.utc), [0, 200, 100])


def test_sla_logic_handles_delivered_and_undelivered_shipments():
    expected = datetime(2026, 2, 1, tzinfo=timezone.utc)
    assert is_on_time(expected, expected - timedelta(minutes=1)) is True
    assert is_on_time(expected, expected + timedelta(minutes=1)) is False
    assert is_on_time(expected, None) is None


def test_seed_anchor_is_fixed_and_requires_an_explicit_timezone(monkeypatch):
    monkeypatch.delenv("FLEETTRACK_SEED_ANCHOR", raising=False)
    assert get_seed_anchor() == DEFAULT_SEED_ANCHOR

    monkeypatch.setenv("FLEETTRACK_SEED_ANCHOR", "2026-11-19T00:00:00")
    with pytest.raises(ValueError, match="UTC offset"):
        get_seed_anchor()


def test_seed_booking_age_spreads_recent_nonterminal_shipments():
    rng = random.Random(17)
    ages = [booking_age_days("in_transit", rng) for _ in range(2_000)]

    assert min(ages) == 0
    assert max(ages) <= 60


def test_seed_booking_cohorts_do_not_concentrate_in_the_anchor_month():
    rng = random.Random(20261119)
    month_counts = Counter()
    for _ in range(1_500):
        status = weighted_status(rng)
        age_days = booking_age_days(status, rng)
        booked_at = DEFAULT_SEED_ANCHOR - timedelta(
            days=age_days,
            hours=rng.randint(0, 23),
        )
        month_counts[(booked_at.year, booked_at.month)] += 1

    prior_month_average = mean(month_counts[(2026, month)] for month in range(6, 11))
    assert month_counts[(2026, 11)] <= prior_month_average * 1.5
