"""Xano: system of record. Live = REST per docs/contracts.md section 5 with the agent token.
Fixtures = LocalLedger for events plus a JSON store, so the agent runs with no network."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from chairside_agent.adapters.base import VendorAdapter
from chairside_agent.config import Settings
from chairside_agent.core.models import ShadeEntry, Sku
from chairside_agent.events import AuditEvent, ConsultationEvent, EventWriter, LocalLedger
from chairside_agent.hashing import verify_chain

COLLECTIONS: tuple[str, ...] = (
    "consultations",
    "skus",
    "shade_map",
    "documents",
    "envelopes",
    "orders",
    "bookings",
)
ID_PREFIX: dict[str, str] = {
    "consultations": "cons",
    "documents": "doc",
    "envelopes": "env",
    "orders": "ord",
    "bookings": "bk",
}


def empty_store() -> dict[str, Any]:
    return {name: {} for name in COLLECTIONS} | {"counters": {}}


class LocalStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = empty_store()
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), "utf-8")

    def next_id(self, collection: str) -> str:
        counter = self.data["counters"].get(collection, 0) + 1
        self.data["counters"][collection] = counter
        return f"{ID_PREFIX[collection]}-{counter:04d}"

    def put(self, collection: str, key: str, row: dict[str, Any]) -> None:
        self.data[collection][key] = row
        self.save()


class XanoAdapter(VendorAdapter):
    vendor = "xano"
    server = "rest/xano"

    def __init__(
        self,
        settings: Settings,
        salon_id: str,
        events: EventWriter | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.salon_id = salon_id
        self.ledger = LocalLedger(settings.state_dir)
        self.store = LocalStore(settings.state_dir / "store.json")
        super().__init__(settings, events or EventWriter(self, salon_id), http)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.xano_agent_token}",
            "Content-Type": "application/json",
        }

    async def _rest(self, method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        self.settings.require("xano_base_url", "xano_agent_token")
        response = await self.http.request(
            method, f"{self.settings.xano_base_url}{path}", json=body, headers=self._headers()
        )
        response.raise_for_status()
        return response.json() if response.content else {}

    async def append(self, events: list[ConsultationEvent]) -> list[AuditEvent]:
        if not self.settings.is_live:
            return await self.ledger.append(events)
        body = {"events": [e.model_dump(mode="json") for e in events]}
        response = await self._rest("POST", "/agent/events", body)
        return [AuditEvent.model_validate(row) for row in response["audit"]]

    async def _write(
        self, primitive: str, method: str, path: str, body: dict[str, Any] | None
    ) -> dict[str, Any]:
        return await self.call(
            primitive,
            {"method": method, "path": path, "body": body},
            lambda req: self._rest(req["method"], req["path"], req["body"]),
            tool=primitive,
        )

    async def set_state(
        self, consultation_id: str, state: str, failing_step: str | None = None
    ) -> None:
        body = {"state": state, "failing_step": failing_step}
        if self.settings.is_live:
            await self._write(
                "set_state", "PATCH", f"/agent/consultations/{consultation_id}/state", body
            )
            return
        row = self.store.data["consultations"].get(consultation_id)
        if row is None:
            raise KeyError(f"unknown consultation {consultation_id}")
        self.store.put("consultations", consultation_id, row | body)

    async def upsert_skus(self, skus: list[Sku]) -> None:
        rows = [s.model_dump() for s in skus]
        if self.settings.is_live:
            await self._write("upsert_skus", "POST", "/agent/skus", {"skus": rows})
            return
        for row in rows:
            self.store.data["skus"][row["code"]] = row
        self.store.save()

    async def put_shade_map(self, entries: list[ShadeEntry]) -> None:
        rows = [e.model_dump() for e in entries]
        if self.settings.is_live:
            await self._write("put_shade_map", "POST", "/floor/shade_map", {"entries": rows})
            return
        self.store.data["shade_map"] = {row["code"]: row for row in rows}
        self.store.save()

    async def create_document(self, kind: str, url: str, sealed_hash: str) -> str:
        body = {"kind": kind, "url": url, "sealed_hash": sealed_hash}
        if self.settings.is_live:
            return (await self._write("create_document", "POST", "/agent/documents", body))["id"]
        doc_id = self.store.next_id("documents")
        self.store.put("documents", doc_id, {"id": doc_id, **body})
        return doc_id

    async def create_consultation(self, client_id: str, chair: int, stylist: str) -> str:
        body = {"client_id": client_id, "chair": chair, "stylist": stylist, "state": "capture"}
        if self.settings.is_live:
            return (await self._write("create_consultation", "POST", "/agent/consultations", body))[
                "id"
            ]
        cons_id = self.store.next_id("consultations")
        self.store.put("consultations", cons_id, {"id": cons_id, "failing_step": None, **body})
        return cons_id

    async def create_order(
        self, consultation_id: str, items: list[dict[str, Any]], total_cents: int
    ) -> str:
        body = {"consultation_id": consultation_id, "items": items, "total_cents": total_cents}
        if self.settings.is_live:
            return (await self._write("create_order", "POST", "/agent/orders", body))["id"]
        order_id = self.store.next_id("orders")
        self.store.put("orders", order_id, {"id": order_id, **body})
        return order_id

    async def create_booking(self, consultation_id: str, when: str, service: str) -> str:
        body = {"consultation_id": consultation_id, "when": when, "service": service}
        if self.settings.is_live:
            return (await self._write("create_booking", "POST", "/agent/bookings", body))["id"]
        booking_id = self.store.next_id("bookings")
        self.store.put("bookings", booking_id, {"id": booking_id, **body})
        return booking_id

    async def get_ledger(self) -> list[dict[str, Any]]:
        if self.settings.is_live:
            return list((await self._rest("GET", "/floor/ledger", None))["audit"])
        return [row.model_dump() for row in self.ledger.read_audit()]

    async def verify_ledger(self) -> dict[str, Any]:
        if self.settings.is_live:
            return await self._rest("GET", "/floor/ledger/verify", None)
        result = verify_chain(await self.get_ledger())
        return {
            "ok": result.ok,
            "checked": result.checked,
            "first_bad_index": result.first_bad_index,
            "reasons": result.reasons,
        }

    def snapshot(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.store.data))

    def reset(self) -> None:
        self.store.data = empty_store()
        self.store.save()
        self.ledger.events_path.write_text("", encoding="utf-8")
        self.ledger.audit_path.write_text("", encoding="utf-8")
