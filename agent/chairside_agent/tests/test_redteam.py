import pytest

from chairside_agent import redteam
from chairside_agent.agents.runtime import Runtime
from chairside_agent.events import EventType


async def test_redteam_esign_is_denied_and_logged(rt: Runtime) -> None:
    status = await redteam.esign(rt)

    assert status == 401
    denied = [e for e in rt.ledger.read_events() if e.type is EventType.REDTEAM_ESIGN_DENIED]
    assert len(denied) == 1
    assert denied[0].payload["credential_presented"] == "pdf_services_client_id"
    assert denied[0].payload["http_status"] == 401
    assert denied[0].payload["denied"] is True


async def test_redteam_raises_if_boundary_leaks(
    rt: Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def leaked() -> int:
        return 200

    monkeypatch.setattr(rt.esign, "redteam_direct_esign_call", leaked)

    with pytest.raises(redteam.BoundaryLeakError):
        await redteam.esign(rt)
    assert any(e.type is EventType.NEEDS_ATTENTION for e in rt.ledger.read_events())
