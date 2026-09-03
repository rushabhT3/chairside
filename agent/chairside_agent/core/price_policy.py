from __future__ import annotations

from datetime import datetime

from chairside_agent.core.models import PriceSnapshot, PriceVerdict

MATCH_BAND_PERCENT = 10
BUNDLE_BAND_PERCENT = 25
STALE_AFTER_DAYS = 7

REASON_MATCH = "within 10% of market median"
REASON_BUNDLE = "above median; bundle with a service"
REASON_HOLD_HIGH = "more than 25% above median; review price"
REASON_HOLD_LOW = "below market minimum; check the snapshot"
REASON_STALE_SUFFIX = "; snapshot stale"


class InvalidSnapshotError(ValueError):
    pass


def _is_stale(as_of: str, now: str) -> bool:
    age = datetime.fromisoformat(now) - datetime.fromisoformat(as_of)
    return age.days >= STALE_AFTER_DAYS


def _decide(salon_price_cents: int, snapshot: PriceSnapshot) -> PriceVerdict:
    median = snapshot.median_cents
    if salon_price_cents < snapshot.min_cents:
        return PriceVerdict(action="hold", reason=REASON_HOLD_LOW)
    delta_scaled = 100 * (salon_price_cents - median)
    if abs(delta_scaled) <= MATCH_BAND_PERCENT * median:
        return PriceVerdict(action="match", reason=REASON_MATCH)
    if delta_scaled <= BUNDLE_BAND_PERCENT * median:
        return PriceVerdict(action="bundle", reason=REASON_BUNDLE)
    return PriceVerdict(action="hold", reason=REASON_HOLD_HIGH)


def price_policy(
    salon_price_cents: int, snapshot: PriceSnapshot, now: str | None = None
) -> PriceVerdict:
    if snapshot.median_cents <= 0 or snapshot.min_cents > snapshot.max_cents:
        raise InvalidSnapshotError(f"unusable snapshot for {snapshot.sku_code}")
    if salon_price_cents < 0:
        raise ValueError("salon price must be non-negative")
    verdict = _decide(salon_price_cents, snapshot)
    if now is not None and _is_stale(snapshot.as_of, now):
        return PriceVerdict(action=verdict.action, reason=verdict.reason + REASON_STALE_SUFFIX)
    return verdict
