from datetime import UTC, datetime

import pytest

from chairside_agent.adapters.serpapi import (
    SerpApiAdapter,
    is_flagged,
    median_cents,
    recent_results,
    split_title,
    to_cents,
)
from chairside_agent.config import Settings
from chairside_agent.events import EventType, EventWriter, LocalLedger

KAYA = "ChIJ2Y7xMfBv5kcRk3YV8jXbQ5o"
MARAIS = "ChIJq0dXt-9v5kcR3aH1oXkq6Lw"
SEQUENCE = "ChIJa20AB-tx5kcR9O2MelhIe1c"
ANISSA = "ChIJv3trOO9v5kcREWHQz42jTC4"
NOW = datetime(2026, 9, 3, 9, 0, tzinfo=UTC)


@pytest.fixture
def ledger(tmp_path) -> LocalLedger:
    return LocalLedger(tmp_path)


@pytest.fixture
async def adapter(ledger, tmp_path):
    settings = Settings.from_env(
        {"CHAIRSIDE_MODE": "fixtures", "CHAIRSIDE_STATE_DIR": str(tmp_path)}
    )
    serp = SerpApiAdapter(settings, EventWriter(ledger, "salon_noor"))
    yield serp
    await serp.aclose()


def tool_calls(ledger: LocalLedger) -> list[dict]:
    return [e.payload for e in ledger.read_events() if e.type == EventType.TOOL_CALLED]


async def test_lens_identifies_bottle_in_hand(adapter, ledger) -> None:
    result = await adapter.lens("https://fixture.chairside.local/scans/olaplex-in-hand.jpg")

    assert result.brand == "OLAPLEX"
    assert "OLAPLEX" in result.product
    assert len(result.visual_matches) == 59
    assert result.visual_matches[0].price_cents is None
    assert result.visual_matches[4].price_cents == 2400
    (call,) = tool_calls(ledger)
    assert call["server"] == "rest/serpapi"
    assert call["tool"] == "google_lens"
    assert call["units"] == 1


async def test_shopping_builds_snapshot_from_offers(adapter, ledger) -> None:
    result = await adapter.shopping("Olaplex No. 3 Hair Perfector 100ml", "OLX-03")

    snapshot = result.snapshot
    assert snapshot.sku_code == "OLX-03"
    assert (snapshot.min_cents, snapshot.median_cents, snapshot.max_cents) == (1212, 7316, 33175)
    assert snapshot.source == "google_shopping"
    assert len(result.offers) == 29
    assert tool_calls(ledger)[0]["tool"] == "google_shopping"


async def test_shopping_falls_back_to_seed_cassette_for_unknown_sku(adapter, ledger) -> None:
    result = await adapter.shopping("Davines OI Oil 135ml", "DAV-OI")

    assert result.snapshot.sku_code == "DAV-OI"
    assert result.snapshot.min_cents == 1890
    assert len(tool_calls(ledger)) == 1


async def test_news_is_clean_within_window(adapter, ledger) -> None:
    result = await adapter.news("Olaplex No. 3 recall", now=NOW)

    assert result.clean is True
    assert result.flags == []
    assert result.as_of == "2026-09-03T09:00:00+00:00"
    assert tool_calls(ledger)[0]["tool"] == "google_news"


def test_news_flag_detection_and_window() -> None:
    assert is_flagged("Olaplex : rappel de lots en Europe")
    assert not is_flagged("Olaplex lance une recharge")
    results = [
        {"title": "old", "iso_date": "2026-02-11T10:20:00Z"},
        {"title": "new", "iso_date": "2026-08-14T09:12:00Z"},
        {"title": "undated"},
    ]
    kept = recent_results(results, datetime(2026, 6, 5, tzinfo=UTC))
    assert [r["title"] for r in kept] == ["new"]


async def test_maps_nearby_returns_two_nearest(adapter, ledger) -> None:
    competitors = await adapter.maps_nearby()

    assert [c.place_id for c in competitors] == [SEQUENCE, ANISSA]
    assert competitors[0].name == "Sequence Paris International Hair Salon"
    assert competitors[0].rating == 4.6
    assert tool_calls(ledger)[0]["tool"] == "google_maps"


async def test_maps_reviews_summarises_topic_deterministically(adapter, ledger) -> None:
    kaya = await adapter.maps_reviews(KAYA, "balayage")
    marais = await adapter.maps_reviews(MARAIS, "balayage")

    assert kaya.summary == (
        "Maison Kaya Coiffure: 4 of 6 recent reviews mention balayage; those average 4.0/5."
    )
    assert len(kaya.quotes) == 3
    assert marais.summary.startswith("Studio Marais Hair: 2 of 5 recent reviews mention balayage")
    calls = tool_calls(ledger)
    assert len(calls) == 2
    assert {c["tool"] for c in calls} == {"google_maps_reviews"}


def test_money_helpers() -> None:
    assert to_cents(29.9) == 2990
    assert to_cents("24.995") == 2500
    assert median_cents([100, 200]) == 150
    assert median_cents([100, 201]) == 151
    assert split_title("OLAPLEX N°3 Hair Perfector 100ml | Nocibé") == (
        "OLAPLEX",
        "OLAPLEX N°3 Hair Perfector 100ml",
    )
