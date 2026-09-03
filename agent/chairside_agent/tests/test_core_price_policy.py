import pytest

from chairside_agent.core.models import PriceSnapshot
from chairside_agent.core.price_policy import InvalidSnapshotError, price_policy


def _snapshot(min_cents=2000, median_cents=2600, max_cents=3400, as_of="2026-09-01T10:00:00Z"):
    return PriceSnapshot(
        sku_code="OLX-03",
        min_cents=min_cents,
        median_cents=median_cents,
        max_cents=max_cents,
        as_of=as_of,
    )


def test_within_ten_percent_matches() -> None:
    verdict = price_policy(2800, _snapshot())

    assert verdict.action == "match"
    assert verdict.reason == "within 10% of market median"


def test_exactly_ten_percent_above_still_matches() -> None:
    verdict = price_policy(2860, _snapshot())

    assert verdict.action == "match"


def test_between_ten_and_twenty_five_percent_bundles() -> None:
    verdict = price_policy(3100, _snapshot())

    assert verdict.action == "bundle"
    assert verdict.reason == "above median; bundle with a service"


def test_more_than_twenty_five_percent_above_holds() -> None:
    verdict = price_policy(3400, _snapshot())

    assert verdict.action == "hold"
    assert verdict.reason == "more than 25% above median; review price"


def test_below_market_minimum_holds() -> None:
    verdict = price_policy(1500, _snapshot())

    assert verdict.action == "hold"
    assert verdict.reason == "below market minimum; check the snapshot"


def test_stale_snapshot_keeps_decision_and_flags_it() -> None:
    verdict = price_policy(
        2800, _snapshot(as_of="2026-08-01T10:00:00Z"), now="2026-09-01T10:00:00Z"
    )

    assert verdict.action == "match"
    assert verdict.reason.endswith("; snapshot stale")


def test_fresh_snapshot_not_flagged() -> None:
    verdict = price_policy(
        2800, _snapshot(as_of="2026-08-30T10:00:00Z"), now="2026-09-01T10:00:00Z"
    )

    assert "stale" not in verdict.reason


def test_zero_median_is_rejected() -> None:
    with pytest.raises(InvalidSnapshotError):
        price_policy(2800, _snapshot(median_cents=0))


def test_negative_salon_price_is_rejected() -> None:
    with pytest.raises(ValueError):
        price_policy(-1, _snapshot())
