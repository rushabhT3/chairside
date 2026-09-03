from pathlib import Path

import pytest

from chairside_agent.agents.consultation import ConsultationAgent, ConsultOptions
from chairside_agent.agents.runtime import Runtime
from chairside_agent.events import EventType
from chairside_agent.hashing import verify_chain

STEP_EVENTS = [
    EventType.CAPTURE_UPLOADED,
    EventType.COLOR_TONES_DONE,
    EventType.SKIN_HD_DONE,
    EventType.HAIR_DIAGNOSTICS_DONE,
    EventType.FACE_ATTRIBUTES_DONE,
    EventType.PLAN_RECOMMENDED,
    EventType.SIMULATION_RENDERED,
    EventType.PRICE_IDENTIFIED,
    EventType.PRICE_SNAPSHOT,
    EventType.NEWS_CHECKED,
    EventType.REVIEWS_FETCHED,
    EventType.CONSENT_TEMPLATE_SELECTED,
    EventType.CONSENT_GENERATED,
    EventType.INTAKE_EXTRACTED,
    EventType.ENVELOPE_REQUESTED,
    EventType.ENVELOPE_SENT,
    EventType.ENVELOPE_SIGNED,
    EventType.BUNDLE_SEALED,
    EventType.PLAN_ACCEPTED,
    EventType.ORDER_CREATED,
    EventType.BOOKING_CREATED,
]


def _types(rt: Runtime, consultation_id: str) -> list[EventType]:
    return [
        e.type
        for e in rt.ledger.read_events(consultation_id)
        if e.type is not EventType.TOOL_CALLED
    ]


def _first_seen(types: list[EventType]) -> list[EventType]:
    return list(dict.fromkeys(t for t in types if t in STEP_EVENTS))


async def test_consult_completes_and_orders(rt: Runtime) -> None:
    p = await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-01", chair=2, stylist="Léa"))

    assert p["state"] == "done"
    assert p["order"]["total_cents"] == 13200 < p["plan"]["total_cents"]
    assert p["order"]["stylist"] == "Léa" and p["order"]["chair"] == 2
    assert p["booking"]["when"]
    assert p["consent"]["envelope"]["state"] == "signed"
    assert p["consent"]["envelope"]["sealed_hash"]
    assert {s["tab"] for s in p["simulations"]} == {"hair", "skin", "style"}
    assert all(r["visibility"] == "staff" for r in p["reviews"]) and len(p["reviews"]) == 2
    assert _first_seen(_types(rt, p["id"])) == STEP_EVENTS
    states = [
        e.payload["to"] for e in rt.ledger.read_events(p["id"]) if e.type is EventType.STATE_CHANGED
    ]
    assert states[-1] == "done" and "needs_attention" not in states
    assert verify_chain([a.model_dump() for a in rt.ledger.read_audit()]).ok


async def test_second_visit_overlays_previous_scan(rt: Runtime) -> None:
    await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-01"))
    p = await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-01"))

    assert p["previous_scan"]["scan_id"] == "scan-cl-01-v1"
    assert set(p["deltas"]) == set(p["scan"]["skin"])


async def test_multi_face_scan_is_quarantined(rt: Runtime) -> None:
    p = await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-01", face_count=2))

    assert p["state"] == "needs_attention" and p["failing_step"] == "capture"
    assert p["quarantine"]["source"] == "scan"
    assert EventType.COLOR_TONES_DONE not in _types(rt, p["id"])


async def test_adversarial_intake_is_quarantined(rt: Runtime) -> None:
    intake = rt.settings.seed_dir / "intake" / "intake-03-adversarial.png"
    p = await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-01", intake=Path(intake)))

    assert p["state"] == "needs_attention" and p["failing_step"] == "consent"
    assert p["quarantine"]["file"] == "intake-03-adversarial.png"
    assert p["quarantine"]["reasons"]
    assert p["order"] is None
    assert EventType.ORDER_CREATED not in _types(rt, p["id"])


async def test_failing_step_halts_downstream(rt: Runtime, monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(*_args, **_kwargs):
        raise RuntimeError("vendor 503")

    monkeypatch.setattr(rt.youcam, "skin_hd", boom)

    p = await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-01"))

    assert p["state"] == "needs_attention" and p["failing_step"] == "skin_hd"
    types = _types(rt, p["id"])
    assert EventType.NEEDS_ATTENTION in types
    assert EventType.HAIR_DIAGNOSTICS_DONE not in types
    assert EventType.PLAN_RECOMMENDED not in types


async def test_renders_are_cached_by_image(rt: Runtime) -> None:
    first = await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-02", visit=0))
    second = await ConsultationAgent(rt).run(ConsultOptions(client_id="cl-02", visit=0))

    assert not any(s["cache_hit"] for s in first["simulations"])
    assert all(s["cache_hit"] for s in second["simulations"])
