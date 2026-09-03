import pytest

from chairside_agent.agents.onboarding import OnboardingAgent
from chairside_agent.agents.runtime import Runtime
from chairside_agent.events import EventType
from chairside_agent.hashing import verify_chain
from chairside_agent.tests.conftest import DEMO_PROMPT

EXPECTED_ORDER = [
    EventType.ONBOARDING_PARSED,
    EventType.DOMAIN_SEARCHED,
    EventType.DOMAIN_AVAILABLE,
    EventType.DOMAIN_CREATED,
    EventType.DNS_CREATED,
    EventType.FORWARDING_CREATED,
    EventType.DOCUMENTS_GENERATED,
    EventType.AGREEMENT_REQUESTED,
    EventType.ENVELOPE_SENT,
    EventType.ENVELOPE_SIGNED,
    EventType.AGREEMENT_SIGNED,
    EventType.CATALOG_EXTRACTED,
    EventType.CATALOG_REVIEW_QUEUED,
    EventType.CATALOG_SEALED,
    EventType.PRICES_SEEDED,
    EventType.SHADE_MAP_SEEDED,
    EventType.STOREFRONT_DEPLOYED,
    EventType.ONBOARDING_DONE,
]


def _types(rt: Runtime) -> list[EventType]:
    return [e.type for e in rt.ledger.read_events() if e.type is not EventType.TOOL_CALLED]


async def test_open_completes_in_fixtures_mode(rt: Runtime) -> None:
    projection = await OnboardingAgent(rt).run(DEMO_PROMPT)

    assert projection["state"] == "done"
    assert projection["domain"]["name"]
    assert projection["catalog"]["skus"] == 42
    assert [s["status"] for s in projection["steps"]] == ["done"] * 9
    kept = [t for t in _types(rt) if t in EXPECTED_ORDER]
    assert kept == EXPECTED_ORDER
    assert EventType.ENVELOPE_SENT in _types(rt)
    sent = next(e for e in rt.ledger.read_events() if e.type is EventType.ENVELOPE_SENT)
    assert sent.actor == "owner"
    assert verify_chain([a.model_dump() for a in rt.ledger.read_audit()]).ok


async def test_bad_math_invoice_is_quarantined(rt: Runtime) -> None:
    projection = await OnboardingAgent(rt).run(DEMO_PROMPT)

    files = {q["file"] for q in projection["quarantine"]}
    assert "inv-0003-bad-math.pdf" in files
    quarantined = [e for e in rt.ledger.read_events() if e.type is EventType.QUARANTINED]
    assert any(e.payload["file"] == "inv-0003-bad-math.pdf" for e in quarantined)


async def test_failure_halts_downstream(rt: Runtime, monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(*_args, **_kwargs):
        raise RuntimeError("registrar down")

    monkeypatch.setattr(rt.namecom, "create_domain", boom)

    with pytest.raises(RuntimeError):
        await OnboardingAgent(rt).run(DEMO_PROMPT)

    types = _types(rt)
    assert EventType.NEEDS_ATTENTION in types
    assert EventType.DOCUMENTS_GENERATED not in types
    stored = rt.projections.load("onboarding")
    assert stored["state"] == "needs_attention"
    assert [s for s in stored["steps"] if s["name"] == "domain"][0]["status"] == "failed"
