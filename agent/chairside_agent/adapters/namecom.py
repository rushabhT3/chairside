from __future__ import annotations

import asyncio
import random
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx
from pydantic import BaseModel

from chairside_agent.adapters.base import VendorAdapter
from chairside_agent.config import Settings
from chairside_agent.events import EventWriter

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 5
MAX_AVAILABILITY_NAMES = 50
DEFAULT_TLDS = ["com", "fr", "paris"]
APEX_HOSTS = frozenset({"", "@"})


class DomainSuggestion(BaseModel):
    domain_name: str
    purchasable: bool
    purchase_price_cents: int | None = None


class DomainAvailability(BaseModel):
    domain_name: str
    purchasable: bool
    premium: bool = False
    purchase_price_cents: int | None = None


class DomainRecord(BaseModel):
    domain_name: str
    expire_date: str
    order_id: int


class DnsRecord(BaseModel):
    id: int
    host: str
    type: str
    answer: str
    ttl: int


class Forwarding(BaseModel):
    domain_name: str
    host: str
    forwards_to: str


class EmailForwarding(BaseModel):
    domain_name: str
    alias: str
    forwards_to: str


def _cents_or_none(value: float | None) -> int | None:
    if value is None:
        return None
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def backoff_seconds(attempt: int) -> float:
    return 0.5 * 2 ** (attempt - 1) + random.uniform(0, 0.25)


def dns_variant(host: str, record_type: str) -> str:
    label = "apex" if host in APEX_HOSTS else host
    return f"{label}_{record_type.lower()}"


class NameComAdapter(VendorAdapter):
    vendor = "namecom"
    server = "rest/namecom"

    def __init__(
        self,
        settings: Settings,
        events: EventWriter,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(settings, events, http)
        settings.require("namecom_username", "namecom_token")

    async def _send(self, request: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.namecom_base_url}{request['path']}"
        auth = httpx.BasicAuth(self.settings.namecom_username, self.settings.namecom_token)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            response = await self.http.request(
                request["method"],
                url,
                json=request.get("body"),
                headers=request.get("headers"),
                auth=auth,
            )
            if response.status_code not in RETRY_STATUSES or attempt == MAX_ATTEMPTS:
                response.raise_for_status()
                return response.json()
            await asyncio.sleep(backoff_seconds(attempt))
        raise httpx.HTTPError("name.com retry loop exhausted")

    async def search(self, keyword: str) -> list[DomainSuggestion]:
        request = {
            "method": "POST",
            "path": "/core/v1/domains:search",
            "body": {"keyword": keyword, "tldFilter": DEFAULT_TLDS, "purchaseType": "registration"},
        }
        raw = await self.call("search", request, self._send, units=0, tool="domains:search")
        return [
            DomainSuggestion(
                domain_name=r["domainName"],
                purchasable=r["purchasable"],
                purchase_price_cents=_cents_or_none(r.get("purchasePrice")),
            )
            for r in raw.get("results", [])
        ]

    async def check_availability(self, names: list[str]) -> list[DomainAvailability]:
        if not names or len(names) > MAX_AVAILABILITY_NAMES:
            raise ValueError(f"checkAvailability takes 1-{MAX_AVAILABILITY_NAMES} names")
        request = {
            "method": "POST",
            "path": "/core/v1/domains:checkAvailability",
            "body": {"domainNames": names, "purchaseType": "registration"},
        }
        raw = await self.call(
            "check_availability", request, self._send, units=0, tool="domains:checkAvailability"
        )
        return [
            DomainAvailability(
                domain_name=r["domainName"],
                purchasable=r["purchasable"],
                premium=bool(r.get("premium", False)),
                purchase_price_cents=_cents_or_none(r.get("purchasePrice")),
            )
            for r in raw.get("results", [])
        ]

    async def create_domain(self, domain_name: str, idempotency_key: str) -> DomainRecord:
        request = {
            "method": "POST",
            "path": "/core/v1/domains",
            "headers": {"X-Idempotency-Key": idempotency_key},
            "body": {
                "domain": {
                    "domainName": domain_name,
                    "autorenewEnabled": True,
                    "locked": True,
                    "privacyEnabled": True,
                },
                "years": 1,
            },
        }
        raw = await self.call("create_domain", request, self._send, units=0, tool="domains.create")
        domain = raw["domain"]
        return DomainRecord(
            domain_name=domain["domainName"],
            expire_date=domain["expireDate"],
            order_id=int(raw["order"]),
        )

    async def create_dns_record(
        self, domain_name: str, host: str, type: str, answer: str, ttl: int = 300
    ) -> DnsRecord:
        request = {
            "method": "POST",
            "path": f"/core/v1/domains/{domain_name}/records",
            "body": {
                "host": "" if host in APEX_HOSTS else host,
                "type": type,
                "answer": answer,
                "ttl": ttl,
            },
        }
        raw = await self.call(
            "dns_record",
            request,
            self._send,
            variant=dns_variant(host, type),
            units=0,
            tool="records.create",
        )
        return DnsRecord(
            id=int(raw["id"]),
            host=raw.get("host") or "",
            type=raw["type"],
            answer=raw["answer"],
            ttl=int(raw["ttl"]),
        )

    async def create_url_forwarding(
        self, domain_name: str, host: str, forwards_to: str
    ) -> Forwarding:
        request = {
            "method": "POST",
            "path": f"/core/v1/domains/{domain_name}/url/forwarding",
            "body": {"host": host, "forwardsTo": forwards_to, "type": "redirect"},
        }
        raw = await self.call(
            "url_forwarding", request, self._send, units=0, tool="urlForwarding.create"
        )
        return Forwarding(
            domain_name=raw.get("domainName", domain_name),
            host=raw["host"],
            forwards_to=raw["forwardsTo"],
        )

    async def create_email_forwarding(
        self, domain_name: str, alias: str, forwards_to: str
    ) -> EmailForwarding:
        request = {
            "method": "POST",
            "path": f"/core/v1/domains/{domain_name}/email/forwarding",
            "body": {"emailBox": alias, "emailTo": forwards_to},
        }
        raw = await self.call(
            "email_forwarding", request, self._send, units=0, tool="emailForwarding.create"
        )
        return EmailForwarding(
            domain_name=raw["domainName"], alias=raw["emailBox"], forwards_to=raw["emailTo"]
        )
