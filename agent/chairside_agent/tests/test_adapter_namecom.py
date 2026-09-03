import pytest

from chairside_agent.adapters.namecom import NameComAdapter, backoff_seconds, dns_variant
from chairside_agent.config import Settings
from chairside_agent.events import EventType, EventWriter, LocalLedger

DOMAIN = "ateliernoor.com"


@pytest.fixture
def ledger(tmp_path) -> LocalLedger:
    return LocalLedger(tmp_path)


@pytest.fixture
async def adapter(ledger, tmp_path):
    settings = Settings.from_env(
        {"CHAIRSIDE_MODE": "fixtures", "CHAIRSIDE_STATE_DIR": str(tmp_path)}
    )
    namecom = NameComAdapter(settings, EventWriter(ledger, "salon_noor"))
    yield namecom
    await namecom.aclose()


def tool_calls(ledger: LocalLedger) -> list[dict]:
    return [e.payload for e in ledger.read_events() if e.type == EventType.TOOL_CALLED]


async def test_search_returns_purchasable_suggestions(adapter, ledger) -> None:
    suggestions = await adapter.search("atelier noor")

    assert suggestions[0].domain_name == DOMAIN
    assert suggestions[0].purchasable is True
    assert suggestions[0].purchase_price_cents == 1299
    assert {s.domain_name for s in suggestions} >= {"ateliernoor.fr", "ateliernoor.paris"}
    (call,) = tool_calls(ledger)
    assert call["server"] == "rest/namecom"
    assert call["tool"] == "domains:search"
    assert call["units"] == 0


async def test_check_availability(adapter, ledger) -> None:
    results = await adapter.check_availability([DOMAIN, "ateliernoor.fr", "ateliernoor.paris"])

    assert [r.domain_name for r in results] == [DOMAIN, "ateliernoor.fr", "ateliernoor.paris"]
    assert all(r.purchasable and not r.premium for r in results)
    assert results[2].purchase_price_cents == 4499
    assert tool_calls(ledger)[0]["tool"] == "domains:checkAvailability"


async def test_check_availability_rejects_bad_batch(adapter) -> None:
    with pytest.raises(ValueError):
        await adapter.check_availability([])
    with pytest.raises(ValueError):
        await adapter.check_availability([f"d{i}.com" for i in range(51)])


async def test_create_domain_is_idempotent_call(adapter, ledger) -> None:
    record = await adapter.create_domain(DOMAIN, "chairside-open-atelier-noor-ateliernoor.com")

    assert record.domain_name == DOMAIN
    assert record.expire_date == "2027-09-03T08:31:04Z"
    assert record.order_id == 4471023
    assert tool_calls(ledger)[0]["tool"] == "domains.create"


async def test_dns_records_for_apex_and_www(adapter, ledger) -> None:
    apex = await adapter.create_dns_record(DOMAIN, "@", "A", "34.120.203.11")
    www = await adapter.create_dns_record(DOMAIN, "www", "CNAME", "x8ke-lq7p-vxdr.static.xano.io")

    assert (apex.host, apex.type, apex.answer, apex.ttl) == ("", "A", "34.120.203.11", 300)
    assert (www.host, www.type) == ("www", "CNAME")
    assert www.answer.endswith(".static.xano.io")
    assert [c["tool"] for c in tool_calls(ledger)] == ["records.create", "records.create"]


def test_dns_variant_and_backoff() -> None:
    assert dns_variant("@", "A") == "apex_a"
    assert dns_variant("", "A") == "apex_a"
    assert dns_variant("www", "CNAME") == "www_cname"
    assert 0.5 <= backoff_seconds(1) <= 0.75
    assert 4.0 <= backoff_seconds(4) <= 4.25


async def test_forwarding(adapter, ledger) -> None:
    url = await adapter.create_url_forwarding(DOMAIN, "www", "https://ateliernoor.com")
    email = await adapter.create_email_forwarding(DOMAIN, "hello", "noor@example.com")

    assert (url.host, url.forwards_to) == ("www", "https://ateliernoor.com")
    assert (email.alias, email.forwards_to) == ("hello", "noor@example.com")
    assert email.domain_name == DOMAIN
    assert [c["tool"] for c in tool_calls(ledger)] == [
        "urlForwarding.create",
        "emailForwarding.create",
    ]
