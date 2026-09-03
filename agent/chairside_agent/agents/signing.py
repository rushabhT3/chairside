"""The two signatures are a human's: the agent requests an envelope and waits, never sends."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

from chairside_agent.adapters.foxit_esign_proxy import EnvelopeStatus
from chairside_agent.agents.runtime import Runtime, now_iso
from chairside_agent.events import ConsultationEvent, EventType

POLL_SECONDS = 5
POLL_LIMIT = 360

HumanRole = Literal["owner", "stylist", "client"]
Emit = Callable[..., Awaitable[ConsultationEvent]]


class SignatureTimeoutError(TimeoutError):
    pass


async def await_signature(
    rt: Runtime,
    emit: Emit,
    envelope_id: str,
    *,
    signer: HumanRole,
    gatekeeper: HumanRole,
    gate_check: str,
) -> str:
    if rt.settings.is_live:
        return await _poll_live(rt, emit, envelope_id, signer=signer, gatekeeper=gatekeeper)
    status = await rt.esign.status(envelope_id)
    return await _simulate_human(
        emit, envelope_id, status, signer=signer, gatekeeper=gatekeeper, check=gate_check
    )


async def _poll_live(
    rt: Runtime, emit: Emit, envelope_id: str, *, signer: HumanRole, gatekeeper: HumanRole
) -> str:
    shown = False
    for _ in range(POLL_LIMIT):
        status = await rt.esign.status(envelope_id)
        if status.state == "sent" and not shown and status.session_url:
            await emit(
                EventType.ENVELOPE_SENT,
                {"envelope_id": envelope_id, "session_url": status.session_url, "as_of": now_iso()},
                actor=gatekeeper,
            )
            shown = True
        if status.state == "signed":
            return await _signed(emit, envelope_id, signer)
        await asyncio.sleep(POLL_SECONDS)
    raise SignatureTimeoutError(
        f"envelope {envelope_id} unsigned after {POLL_LIMIT * POLL_SECONDS}s"
    )


async def _simulate_human(
    emit: Emit,
    envelope_id: str,
    status: EnvelopeStatus,
    *,
    signer: HumanRole,
    gatekeeper: HumanRole,
    check: str,
) -> str:
    await emit(
        EventType.ENVELOPE_SENT,
        {
            "envelope_id": envelope_id,
            "gate": "commit/xano",
            "role": gatekeeper,
            "checks": ["role_allowed", "state_human_reviewed", check],
            "session_url": status.session_url or f"fixture://esign/{envelope_id}",
            "as_of": now_iso(),
        },
        actor=gatekeeper,
    )
    return await _signed(emit, envelope_id, signer)


async def _signed(emit: Emit, envelope_id: str, signer: HumanRole) -> str:
    signed_at = now_iso()
    await emit(
        EventType.ENVELOPE_SIGNED,
        {"envelope_id": envelope_id, "signed_at": signed_at, "session": "embedded"},
        actor=signer,
    )
    return signed_at
