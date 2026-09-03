"""Event-sourced consultations: every step is a ConsultationEvent; the ledger is a projection."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from chairside_agent.hashing import GENESIS_HASH, chain_hash, payload_hash

Actor = Literal["agent", "owner", "stylist", "client", "system"]


class EventType(StrEnum):
    CAPTURE_UPLOADED = "capture.uploaded"
    COLOR_TONES_DONE = "color_tones.done"
    SKIN_HD_DONE = "skin_hd.done"
    HAIR_DIAGNOSTICS_DONE = "hair_diagnostics.done"
    FACE_ATTRIBUTES_DONE = "face_attributes.done"
    PLAN_RECOMMENDED = "plan.recommended"
    SIMULATION_RENDERED = "simulation.rendered"
    PRICE_IDENTIFIED = "price.identified"
    PRICE_SNAPSHOT = "price.snapshot"
    NEWS_CHECKED = "news.checked"
    REVIEWS_FETCHED = "reviews.fetched"
    CONSENT_TEMPLATE_SELECTED = "consent.template_selected"
    CONSENT_GENERATED = "consent.generated"
    INTAKE_EXTRACTED = "intake.extracted"
    ENVELOPE_REQUESTED = "envelope.requested"
    ENVELOPE_SENT = "envelope.sent"
    ENVELOPE_SIGNED = "envelope.signed"
    BUNDLE_SEALED = "bundle.sealed"
    PLAN_ACCEPTED = "plan.accepted"
    ORDER_CREATED = "order.created"
    BOOKING_CREATED = "booking.created"
    STATE_CHANGED = "state.changed"
    NEEDS_ATTENTION = "needs_attention"
    QUARANTINED = "quarantined"
    REDTEAM_ESIGN_DENIED = "redteam.esign_denied"
    DATA_TOMBSTONED = "data.tombstoned"
    TOOL_CALLED = "tool.called"
    ONBOARDING_PARSED = "onboarding.parsed"
    DOMAIN_SEARCHED = "domain.searched"
    DOMAIN_AVAILABLE = "domain.available"
    DOMAIN_CREATED = "domain.created"
    DNS_CREATED = "dns.created"
    FORWARDING_CREATED = "forwarding.created"
    DOCUMENTS_GENERATED = "documents.generated"
    AGREEMENT_REQUESTED = "agreement.requested"
    AGREEMENT_SIGNED = "agreement.signed"
    CATALOG_EXTRACTED = "catalog.extracted"
    CATALOG_REVIEW_QUEUED = "catalog.review_queued"
    CATALOG_SEALED = "catalog.sealed"
    PRICES_SEEDED = "prices.seeded"
    SHADE_MAP_SEEDED = "shade_map.seeded"
    STOREFRONT_DEPLOYED = "storefront.deployed"
    ONBOARDING_DONE = "onboarding.done"


def now_iso() -> str:
    t = datetime.now(UTC)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


class ConsultationEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    consultation_id: str | None = None
    salon_id: str
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    ts: str = Field(default_factory=now_iso)
    actor: Actor = "agent"


class AuditEvent(BaseModel):
    id: str
    prev_hash: str
    hash: str
    actor: Actor
    action: str
    payload_hash: str
    ts: str


def audit_for(event: ConsultationEvent, prev_hash: str) -> AuditEvent:
    ph = payload_hash(event.payload)
    return AuditEvent(
        id=event.id,
        prev_hash=prev_hash,
        hash=chain_hash(
            prev_hash=prev_hash,
            actor=event.actor,
            action=event.type.value,
            payload_hash=ph,
            ts=event.ts,
        ),
        actor=event.actor,
        action=event.type.value,
        payload_hash=ph,
        ts=event.ts,
    )


class EventSink(Protocol):
    async def append(self, events: list[ConsultationEvent]) -> list[AuditEvent]: ...


class LocalLedger:
    """Fixtures-mode sink: JSONL files under the state dir, hash chain computed locally."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.events_path = state_dir / "events.jsonl"
        self.audit_path = state_dir / "audit.jsonl"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.events_path.touch()
        self.audit_path.touch()

    def _last_hash(self) -> str:
        last = GENESIS_HASH
        with self.audit_path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    last = json.loads(line)["hash"]
        return last

    async def append(self, events: list[ConsultationEvent]) -> list[AuditEvent]:
        prev = self._last_hash()
        audits: list[AuditEvent] = []
        with (
            self.events_path.open("a", encoding="utf-8") as ef,
            self.audit_path.open("a", encoding="utf-8") as af,
        ):
            for ev in events:
                audit = audit_for(ev, prev)
                ef.write(ev.model_dump_json() + "\n")
                af.write(audit.model_dump_json() + "\n")
                prev = audit.hash
                audits.append(audit)
        return audits

    def read_events(self, consultation_id: str | None = None) -> list[ConsultationEvent]:
        out: list[ConsultationEvent] = []
        with self.events_path.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                ev = ConsultationEvent.model_validate_json(line)
                if consultation_id is None or ev.consultation_id == consultation_id:
                    out.append(ev)
        return out

    def read_audit(self) -> list[AuditEvent]:
        with self.audit_path.open(encoding="utf-8") as fh:
            return [AuditEvent.model_validate_json(line) for line in fh if line.strip()]


class EventWriter:
    def __init__(self, sink: EventSink, salon_id: str) -> None:
        self.sink = sink
        self.salon_id = salon_id
        self.consultation_id: str | None = None

    async def emit(
        self,
        type_: EventType,
        payload: dict[str, Any] | None = None,
        *,
        actor: Actor = "agent",
        consultation_id: str | None = None,
    ) -> ConsultationEvent:
        ev = ConsultationEvent(
            consultation_id=consultation_id or self.consultation_id,
            salon_id=self.salon_id,
            type=type_,
            payload=payload or {},
            actor=actor,
        )
        await self.sink.append([ev])
        return ev
