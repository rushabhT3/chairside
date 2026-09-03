import json

import httpx
import pytest

from chairside_agent.adapters.xano import XanoAdapter
from chairside_agent.config import PACKAGE_DIR, Settings
from chairside_agent.core.models import ShadeEntry, Sku
from chairside_agent.events import EventType
from chairside_agent.hashing import GENESIS_HASH

SALON = "salon-atelier-noor"


@pytest.fixture
def xano(settings) -> XanoAdapter:
    return XanoAdapter(settings, SALON)


async def test_fixtures_mode_writes_local_store_with_deterministic_ids(xano: XanoAdapter) -> None:
    cons = await xano.create_consultation("client-01", 2, "Léa")
    await xano.set_state(cons, "plan")
    order = await xano.create_order(cons, [{"code": "OLA-3", "qty": 1}], 14700)
    booking = await xano.create_booking(cons, "2026-10-15T10:00:00Z", "SVC-COLOR")
    doc = await xano.create_document("consent", "https://x/consent.pdf", "ab" * 32)

    assert (cons, order, booking, doc) == ("cons-0001", "ord-0001", "bk-0001", "doc-0001")
    stored = json.loads((xano.settings.state_dir / "store.json").read_text("utf-8"))
    assert stored["consultations"]["cons-0001"]["state"] == "plan"
    assert stored["orders"]["ord-0001"]["total_cents"] == 14700


async def test_set_state_on_unknown_consultation_fails_fast(xano: XanoAdapter) -> None:
    with pytest.raises(KeyError):
        await xano.set_state("cons-9999", "done")


async def test_catalog_writes(xano: XanoAdapter) -> None:
    await xano.upsert_skus(
        [Sku(code="OLA-3", name="Olaplex No.3", brand="Olaplex", salon_price_cents=3200)]
    )
    await xano.put_shade_map(
        [
            ShadeEntry(
                line="Majirel",
                code="7.31",
                name="Medium Blonde Gold Ash",
                hex="#A8804F",
                undertone="warm",
                level=7,
            )
        ]
    )

    assert xano.snapshot()["skus"]["OLA-3"]["salon_price_cents"] == 3200
    assert xano.snapshot()["shade_map"]["7.31"]["hex"] == "#A8804F"


async def test_adapter_is_the_event_sink_and_ledger_verifies(xano: XanoAdapter) -> None:
    await xano.events.emit(EventType.ONBOARDING_PARSED, {"salon": "Atelier Noor", "chairs": 3})
    await xano.events.emit(EventType.DOMAIN_SEARCHED, {"keyword": "atelier noor"})

    ledger = await xano.get_ledger()
    assert ledger[0]["prev_hash"] == GENESIS_HASH
    assert ledger[1]["prev_hash"] == ledger[0]["hash"]
    assert (await xano.verify_ledger())["ok"] is True

    xano.reset()
    assert await xano.get_ledger() == []
    assert xano.snapshot()["consultations"] == {}


async def test_live_path_hits_contract_endpoints(tmp_path) -> None:
    calls: list[tuple[str, str, dict]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        path = request.url.path.removeprefix("/api:v1")
        calls.append((request.method, path, body))
        assert request.headers["Authorization"] == "Bearer agent-token"
        if path == "/agent/events":
            audit = [
                {
                    "id": e["id"],
                    "prev_hash": GENESIS_HASH,
                    "hash": "f" * 64,
                    "actor": e["actor"],
                    "action": e["type"],
                    "payload_hash": "e" * 64,
                    "ts": e["ts"],
                }
                for e in body["events"]
            ]
            return httpx.Response(200, json={"audit": audit})
        if path == "/floor/ledger/verify":
            return httpx.Response(200, json={"ok": True, "checked": 3})
        return httpx.Response(200, json={"id": "cons-live-1", "state": "plan"})

    settings = Settings.from_env(
        {
            "CHAIRSIDE_MODE": "live",
            "XANO_BASE_URL": "https://xano.example/api:v1",
            "XANO_AGENT_TOKEN": "agent-token",
            "CHAIRSIDE_STATE_DIR": str(tmp_path / "state"),
            "CHAIRSIDE_FIXTURES_DIR": str(PACKAGE_DIR / "fixtures"),
        }
    )
    xano = XanoAdapter(
        settings, SALON, http=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )

    cons = await xano.create_consultation("client-01", 1, "Marc")
    await xano.set_state(cons, "plan")
    verified = await xano.verify_ledger()

    assert cons == "cons-live-1"
    assert verified["ok"] is True
    paths = [(m, p) for m, p, _ in calls]
    assert ("POST", "/agent/consultations") in paths
    assert ("PATCH", "/agent/consultations/cons-live-1/state") in paths
    assert ("POST", "/agent/events") in paths
    assert ("GET", "/floor/ledger/verify") in paths
