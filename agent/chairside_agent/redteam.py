"""Force the agent process to call eSign with the only Foxit credential it holds. Expect 401."""

from __future__ import annotations

from chairside_agent.agents.runtime import Runtime, now_iso
from chairside_agent.events import EventType

EXPECTED_STATUS = 401


class BoundaryLeakError(RuntimeError):
    pass


async def esign(rt: Runtime) -> int:
    """The proxy writes `redteam.esign_denied` itself; this only enforces the expected answer."""
    status = await rt.esign.redteam_direct_esign_call()
    if status != EXPECTED_STATUS:
        await rt.events.emit(
            EventType.NEEDS_ATTENTION,
            {
                "step": "redteam.esign",
                "error": f"eSign answered HTTP {status} to the PDF Services token",
                "as_of": now_iso(),
            },
        )
        raise BoundaryLeakError(
            f"eSign answered {status} to the agent's PDF Services token; expected {EXPECTED_STATUS}"
        )
    return status
