from pathlib import Path

import pytest

from chairside_agent.adapters import foxit_esign_proxy
from chairside_agent.adapters.foxit_esign_proxy import EsignProxy, esign_gateway
from chairside_agent.events import EventType, LocalLedger


@pytest.fixture
def proxy(settings, events) -> EsignProxy:
    return EsignProxy(settings, events)


def test_module_never_names_an_esign_credential() -> None:
    source = Path(foxit_esign_proxy.__file__).read_text("utf-8")

    assert "FOXIT_ESIGN" not in source
    assert "esign_client" not in source.lower()


def test_gateway_derived_from_pdf_services_host() -> None:
    assert (
        esign_gateway("https://na1.fusion.foxit.com/pdf-services") == "https://na1.fusion.foxit.com"
    )


async def test_request_envelope_goes_through_xano(proxy: EsignProxy, ledger: LocalLedger) -> None:
    handle = await proxy.request_envelope(
        "doc-0001", {"name": "Noor Haddad", "email": "noor@example.com"}
    )

    assert handle.envelope_id == "env-0001"
    assert handle.state == "draft"
    tool_events = [e for e in ledger.read_events() if e.type == EventType.TOOL_CALLED]
    assert tool_events[-1].payload["server"] == "commit/xano"


async def test_status_is_free_and_human_reviewed(proxy: EsignProxy, ledger: LocalLedger) -> None:
    status = await proxy.status("env-0001")

    assert status.state == "human_reviewed"
    assert status.session_url is None
    assert [e for e in ledger.read_events() if e.type == EventType.TOOL_CALLED][-1].payload[
        "units"
    ] == 0


async def test_redteam_records_denial(proxy: EsignProxy, ledger: LocalLedger) -> None:
    status = await proxy.redteam_direct_esign_call()

    assert status == 401
    denied = [e for e in ledger.read_events() if e.type == EventType.REDTEAM_ESIGN_DENIED]
    assert len(denied) == 1
    assert denied[0].payload["denied"] is True
    assert denied[0].payload["credential_presented"] == "pdf_services_client_id"
    assert denied[0].payload["endpoint"].endswith("/esign/api/v1/folders/createfolder")
