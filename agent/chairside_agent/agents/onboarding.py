"""Act 1: one prompt opens a salon."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from chairside_agent.agents.runtime import Runtime, now_iso
from chairside_agent.agents.signing import await_signature
from chairside_agent.agents.storefront import render_storefront
from chairside_agent.core.models import Extraction, Field_, Sku, SkuKind
from chairside_agent.core.price_policy import price_policy
from chairside_agent.core.quarantine_policy import quarantine_policy
from chairside_agent.events import Actor, ConsultationEvent, EventType

CONFIDENCE_THRESHOLD = 0.85
PRICE_ALERT_PCT = 15
FIXTURE_STATIC_HOST = "chairside-fixture.xano.app"
CONSENT_CLASSES = ("chemical", "heat", "injectable", "laser")
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}  # fmt: skip

PROMPT_RE = re.compile(
    r"""^\s*open\s+chairside\s+for\s+
        (?P<salon>[^,]+?),\s*
        (?P<address>[^,]+?),\s*
        (?P<postcode>[A-Za-z0-9][A-Za-z0-9 -]{2,9}?)\s+(?P<city>[^.,]+?)\.\s*
        (?P<services>[^.]+?)\.\s*
        (?P<chairs>[A-Za-z0-9]+)\s+chairs?\.\s*
        owner:\s*(?P<owner>[^,]+?),\s*(?P<email>[^\s,]+?@[^\s,]+?)\.?\s*$""",
    re.IGNORECASE | re.VERBOSE,
)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
ROW_FIELD_RE = re.compile(r"^rows?[\[._](\d+)\]?[._](\w+)$")


class PromptParseError(ValueError):
    pass


class OnboardingRequest(BaseModel):
    salon_name: str
    address: str
    postcode: str
    city: str
    services: list[str] = Field(min_length=1)
    chairs: int = Field(ge=1, le=50)
    owner_name: str
    owner_email: str

    @field_validator("owner_email")
    @classmethod
    def _email(cls, value: str) -> str:
        if not EMAIL_RE.match(value):
            raise ValueError(f"not an email: {value!r}")
        return value

    @property
    def slug(self) -> str:
        return re.sub(r"[^a-z0-9]", "", self.salon_name.lower())


def _chairs(raw: str) -> int:
    if raw.isdigit():
        return int(raw)
    if raw.lower() in NUMBER_WORDS:
        return NUMBER_WORDS[raw.lower()]
    raise PromptParseError(f"cannot read chair count {raw!r}")


def _services(raw: str) -> list[str]:
    parts = re.split(r",\s*|\s+and\s+|\s*&\s*", raw)
    return [p.strip().lower() for p in parts if p.strip()]


def parse_prompt(prompt: str) -> OnboardingRequest:
    match = PROMPT_RE.match(prompt)
    if not match:
        raise PromptParseError(
            "expected: Open Chairside for <name>, <address>, <postcode> <city>. <services>. "
            "<N> chairs. Owner: <name>, <email>."
        )
    return OnboardingRequest(
        salon_name=match["salon"].strip(),
        address=match["address"].strip(),
        postcode=match["postcode"].strip(),
        city=match["city"].strip(),
        services=_services(match["services"]),
        chairs=_chairs(match["chairs"]),
        owner_name=match["owner"].strip(),
        owner_email=match["email"].strip(),
    )


def static_host_target(xano_base_url: str) -> str:
    host = urlparse(xano_base_url).hostname if xano_base_url else None
    return host or FIXTURE_STATIC_HOST


def idempotency_key(salon_id: str, domain: str) -> str:
    return sha256(f"{salon_id}:{domain}".encode()).hexdigest()[:36]


def _cents(raw: str) -> int:
    text = re.sub(r"[^\d,.]", "", raw).replace(",", ".")
    if not text:
        raise ValueError(f"no amount in {raw!r}")
    if "." in text:
        return round(float(text) * 100)
    return int(text)


def _read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _rows(fields: list[Field_]) -> dict[int, dict[str, Field_]]:
    rows: dict[int, dict[str, Field_]] = {}
    for f in fields:
        match = ROW_FIELD_RE.match(f.name)
        if match:
            rows.setdefault(int(match[1]), {})[match[2]] = f
    return rows


def _kind(code: str, base: Sku | None) -> SkuKind:
    if base:
        return base.kind
    return "service" if code.startswith("SVC-") else "retail"


def skus_from_extraction(extraction: Extraction, seed: list[Sku]) -> list[Sku]:
    """The salon's price list is the catalog; the seed only fills in when nothing parsed."""
    by_code = {s.code: s for s in seed}
    parsed: list[Sku] = []
    for row in _rows(extraction.fields).values():
        if not {"code", "name", "price"} <= set(row):
            continue
        code = row["code"].value
        base = by_code.get(code)
        parsed.append(
            Sku(
                code=code,
                name=row["name"].value,
                brand=row["brand"].value if "brand" in row else (base.brand if base else ""),
                salon_price_cents=_cents(row["price"].value),
                shade_code=base.shade_code if base else None,
                kind=_kind(code, base),
            )
        )
    return parsed or list(seed)


def review_rows(extraction: Extraction, file: str, prefix: str) -> list[dict[str, Any]]:
    rows = _rows(extraction.fields) or {i: {f.name: f} for i, f in enumerate(extraction.fields)}
    out = []
    for index, row in sorted(rows.items()):
        low = any(f.confidence < CONFIDENCE_THRESHOLD for f in row.values())
        out.append(
            {
                "id": f"{prefix}-{index}",
                "source": extraction.source,
                "file": file,
                "needs_review": low,
                "status": "pending" if low else "confirmed",
                "fields": [f.model_dump() for f in row.values()],
            }
        )
    return out


Step = Callable[[], Awaitable[str]]


@dataclass(slots=True)
class OnboardingAgent:
    rt: Runtime
    request: OnboardingRequest | None = None
    projection: dict[str, Any] = field(default_factory=dict)
    documents: dict[str, Path] = field(default_factory=dict)

    @property
    def salon(self) -> dict[str, Any]:
        return self.rt.salon

    @property
    def docs_dir(self) -> Path:
        path = self.rt.settings.state_dir / "documents"
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def _emit(
        self, type_: EventType, payload: dict[str, Any], *, actor: Actor = "agent"
    ) -> ConsultationEvent:
        return await self.rt.events.emit(type_, payload, actor=actor, consultation_id=None)

    def _mark(self, name: str, status: str, detail: str = "") -> None:
        steps = self.projection["steps"]
        for step in steps:
            if step["name"] == name:
                step.update(status=status, detail=detail, ts=now_iso())
                return
        steps.append({"name": name, "status": status, "detail": detail, "ts": now_iso()})

    async def _step(self, name: str, fn: Step) -> None:
        self._mark(name, "running")
        try:
            detail = await fn()
        except Exception as exc:
            self._mark(name, "failed", f"{type(exc).__name__}: {exc}")
            self.projection["state"] = "needs_attention"
            await self._emit(
                EventType.NEEDS_ATTENTION,
                {"step": name, "error": f"{type(exc).__name__}: {exc}", "as_of": now_iso()},
            )
            self.rt.projections.save("onboarding", self.projection)
            raise
        self._mark(name, "done", detail)
        self.rt.projections.save("onboarding", self.projection)

    async def run(self, prompt: str) -> dict[str, Any]:
        self.projection = {"salon_id": self.salon["id"], "state": "running", "steps": []}
        await self._step("parse_prompt", lambda: self._parse(prompt))
        await self._step("domain", self._domain)
        await self._step("documents", self._documents)
        await self._step("platform_agreement", self._platform_agreement)
        await self._step("catalog", self._catalog)
        await self._step("prices", self._prices)
        await self._step("shade_map", self._shade_map)
        await self._step("storefront", self._storefront)
        await self._step("done", self._done)
        return self.projection

    async def _parse(self, prompt: str) -> str:
        self.request = parse_prompt(prompt)
        self.projection["request"] = self.request.model_dump()
        await self._emit(
            EventType.ONBOARDING_PARSED, {**self.request.model_dump(), "as_of": now_iso()}
        )
        return f"{self.request.salon_name} · {self.request.chairs} chairs"

    async def _domain(self) -> str:
        req = self.request
        assert req is not None
        suggestions = await self.rt.namecom.search(req.slug)
        await self._emit(
            EventType.DOMAIN_SEARCHED,
            {
                "keyword": req.slug,
                "suggestions": [s.domain_name for s in suggestions[:5]],
                "as_of": now_iso(),
            },
        )
        candidates = [
            f"{req.slug}.com",
            f"{req.slug}.fr",
            *(s.domain_name for s in suggestions[:3]),
        ]
        availability = await self.rt.namecom.check_availability(list(dict.fromkeys(candidates)))
        purchasable = [a for a in availability if a.purchasable]
        if not purchasable:
            raise RuntimeError(f"no purchasable domain among {candidates}")
        preferred = next(
            (a for a in purchasable if a.domain_name == self.salon.get("domain")), purchasable[0]
        )
        await self._emit(
            EventType.DOMAIN_AVAILABLE,
            {
                "domain": preferred.domain_name,
                "price_cents": preferred.purchase_price_cents,
                "as_of": now_iso(),
            },
        )
        key = idempotency_key(self.salon["id"], preferred.domain_name)
        created = await self.rt.namecom.create_domain(preferred.domain_name, key)
        await self._emit(
            EventType.DOMAIN_CREATED,
            {
                "domain": created.domain_name,
                "order_id": created.order_id,
                "expire_date": created.expire_date,
                "idempotency_key": key,
                "as_of": now_iso(),
            },
        )
        await self._dns_and_forwarding(created.domain_name)
        self.projection["domain"] = {"name": created.domain_name, "order_id": created.order_id}
        return created.domain_name

    async def _dns_and_forwarding(self, domain: str) -> None:
        target = static_host_target(self.rt.settings.xano_base_url)
        apex = await self.rt.namecom.create_dns_record(domain, "", "A", target)
        www = await self.rt.namecom.create_dns_record(domain, "www", "CNAME", target)
        await self._emit(
            EventType.DNS_CREATED,
            {
                "domain": domain,
                "records": [r.model_dump() for r in (apex, www)],
                "target": target,
                "as_of": now_iso(),
            },
        )
        url = await self.rt.namecom.create_url_forwarding(domain, "www", f"https://{domain}")
        email = await self.rt.namecom.create_email_forwarding(
            domain, "hello", self.salon["owner"]["email"]
        )
        await self._emit(
            EventType.FORWARDING_CREATED,
            {
                "domain": domain,
                "url": url.model_dump(),
                "email": email.model_dump(),
                "as_of": now_iso(),
            },
        )

    def _salon_address(self) -> str:
        s = self.salon
        return f"{s['address']}, {s['postcode']} {s['city']}"

    def _template_data(self, extra: dict[str, Any]) -> dict[str, Any]:
        return {
            "salon": {
                "name": self.salon["name"],
                "address": self._salon_address(),
            },
            "jurisdiction": self.salon["jurisdiction"],
            "owner": self.salon["owner"],
            **extra,
        }

    async def _generate(self, kind: str, template_id: str, data: dict[str, Any]) -> str:
        doc = await self.rt.doctavian.generate(template_id, self._template_data(data))
        path = self.docs_dir / f"{kind}.pdf"
        path.write_bytes(doc.pdf)
        self.documents[kind] = path
        document_id = await self.rt.xano.create_document(kind, doc.url, "")
        self.projection.setdefault("documents", []).append(
            {"kind": kind, "template_id": template_id, "document_id": document_id, "url": doc.url}
        )
        return document_id

    async def _documents(self) -> str:
        templates = self.rt.seed.templates
        services = [s for s in self.rt.seed.skus if s.kind == "service"]
        for cls in CONSENT_CLASSES:
            await self._generate(
                f"consent_{cls}",
                templates["consent"][cls],
                {"treatment_classes": [cls], "allergens": [], "client": {"name": ""}},
            )
        await self._generate(
            "price_list",
            templates["price_list"],
            {
                "services": [s.model_dump() for s in services],
                "retail": [s.model_dump() for s in self.rt.seed.skus if s.kind == "retail"],
            },
        )
        primary = services[0]
        await self._generate(
            "aftercare", templates["aftercare"][primary.code], {"service": primary.model_dump()}
        )
        terms = await self.rt.doctavian.clickwrap(
            templates["client_terms"], self._template_data({})
        )
        self.projection["client_terms"] = terms.model_dump()
        kinds = list(self.documents)
        await self._emit(
            EventType.DOCUMENTS_GENERATED,
            {"count": len(kinds), "kinds": kinds, "clickwrap": terms.url, "as_of": now_iso()},
        )
        return f"{len(kinds)} generated · clickwrap live"

    async def _platform_agreement(self) -> str:
        templates = self.rt.seed.templates
        document_id = await self._generate(
            "platform_agreement", templates["platform_agreement"], {}
        )
        packet = await self.rt.foxit_pdf.merge([p.read_bytes() for p in self.documents.values()])
        packet = await self.rt.foxit_pdf.compress(packet)
        (self.docs_dir / "salon_packet.pdf").write_bytes(packet)
        envelope = await self.rt.esign.request_envelope(
            document_id,
            {"name": self.salon["owner"]["name"], "email": self.salon["owner"]["email"]},
        )
        await self._emit(
            EventType.AGREEMENT_REQUESTED,
            {
                "envelope_id": envelope.envelope_id,
                "document_id": document_id,
                "signer": "owner",
                "packet_bytes": len(packet),
                "as_of": now_iso(),
            },
        )
        signed_at = await await_signature(
            self.rt,
            self._emit,
            envelope.envelope_id,
            signer="owner",
            gatekeeper="owner",
            gate_check="docs_reviewed",
        )
        await self._emit(
            EventType.AGREEMENT_SIGNED,
            {"envelope_id": envelope.envelope_id, "signed_at": signed_at},
        )
        self.projection["agreement"] = {"envelope_id": envelope.envelope_id, "signed_at": signed_at}
        return f"signed by owner {signed_at}"

    async def _extract_invoice(
        self, path: Path, seen: set[tuple[str, str]]
    ) -> tuple[Extraction, list[str]]:
        raw = _read_bytes(path)
        if "scanned" in path.name:
            ocr = await self.rt.foxit_pdf.ocr(raw)
            raw = ocr.pdf
        extraction = await self.rt.nutrient.extract(raw, "invoice", path.name)
        verdict = quarantine_policy(extraction, known_invoice_numbers=seen)
        fields = {f.name: f.value for f in extraction.fields}
        if not verdict.quarantined and fields.get("supplier_name") and fields.get("invoice_number"):
            seen.add((fields["supplier_name"], fields["invoice_number"]))
        return extraction, verdict.reasons

    async def _catalog(self) -> str:
        seed_dir = self.rt.settings.seed_dir
        price_list = await self.rt.nutrient.extract(
            (seed_dir / "price_list.pdf").read_bytes(), "price_list", "price_list.pdf"
        )
        rows = review_rows(price_list, "price_list.pdf", "pl")
        quarantine: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        invoices = sorted((seed_dir / "invoices").glob("*.pdf"))
        for path in invoices:
            extraction, reasons = await self._extract_invoice(path, seen)
            if reasons:
                quarantine.append(
                    {
                        "id": f"q-{path.stem}",
                        "source": "invoice",
                        "file": path.name,
                        "reasons": reasons,
                        "ts": now_iso(),
                    }
                )
                await self._emit(
                    EventType.QUARANTINED,
                    {
                        "source": "invoice",
                        "file": path.name,
                        "reasons": reasons,
                        "as_of": now_iso(),
                    },
                )
            rows += review_rows(extraction, path.name, path.stem)
        low = [r for r in rows if r["needs_review"]]
        await self._emit(
            EventType.CATALOG_EXTRACTED,
            {
                "sources": 1 + len(invoices),
                "rows": len(rows),
                "low_confidence": len(low),
                "as_of": now_iso(),
            },
        )
        await self._emit(
            EventType.CATALOG_REVIEW_QUEUED, {"count": len(low), "rows": [r["id"] for r in low]}
        )
        skus = skus_from_extraction(price_list, self.rt.seed.skus)
        await self.rt.xano.upsert_skus(skus)
        sealed = await self.rt.nutrient.sign_cades(
            await self.rt.nutrient.build(
                [(seed_dir / "price_list.pdf").read_bytes(), *(p.read_bytes() for p in invoices)],
                ocr=True,
                pdfa=True,
            )
        )
        (self.docs_dir / "catalog_sealed.pdf").write_bytes(sealed.pdf)
        await self.rt.xano.create_document("catalog", "documents/catalog_sealed.pdf", sealed.sha256)
        await self._emit(
            EventType.CATALOG_SEALED,
            {
                "sha256": sealed.sha256,
                "skus": len(skus),
                "signature": "CAdES B-LT",
                "as_of": now_iso(),
            },
        )
        self.projection.update(
            extractions=rows,
            quarantine=quarantine,
            catalog={"skus": len(skus), "sealed_hash": sealed.sha256, "review": len(low)},
        )
        self.projection["skus"] = [s.model_dump() for s in skus]
        return f"{len(skus)} SKUs ({len(low)} to review) · {len(quarantine)} quarantined"

    async def _prices(self) -> str:
        rows = []
        for sku in [s for s in self.rt.seed.skus if s.kind != "service"]:
            result = await self.rt.serpapi.shopping(f"{sku.brand} {sku.name}", sku.code)
            snap = result.snapshot
            verdict = price_policy(sku.salon_price_cents, snap)
            delta_pct = round((sku.salon_price_cents - snap.median_cents) * 100 / snap.median_cents)
            rows.append(
                {
                    "sku_code": sku.code,
                    "name": sku.name,
                    "salon_price_cents": sku.salon_price_cents,
                    "min_cents": snap.min_cents,
                    "median_cents": snap.median_cents,
                    "max_cents": snap.max_cents,
                    "delta_pct": delta_pct,
                    "alert": abs(delta_pct) > PRICE_ALERT_PCT,
                    "action": verdict.action,
                    "reason": verdict.reason,
                    "as_of": snap.as_of,
                }
            )
        alerts = sum(1 for r in rows if r["alert"])
        await self._emit(
            EventType.PRICES_SEEDED, {"count": len(rows), "alerts": alerts, "as_of": now_iso()}
        )
        self.projection["prices"] = rows
        return f"{len(rows)} snapshots · {alerts} alerts"

    async def _shade_map(self) -> str:
        entries = self.rt.seed.shade_map
        await self.rt.xano.put_shade_map(entries)
        await self._emit(
            EventType.SHADE_MAP_SEEDED, {"line": self.salon["color_line"], "count": len(entries)}
        )
        self.projection["shade_map"] = {"line": self.salon["color_line"], "count": len(entries)}
        return f"{len(entries)} shades · {self.salon['color_line']}"

    async def _storefront(self) -> str:
        domain = self.projection["domain"]["name"]
        html = render_storefront(self.salon, domain, self.rt.seed.skus, self.rt.seed.shade_map)
        out = self.rt.settings.state_dir / "storefront"
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(html, encoding="utf-8")
        print_copy = await self.rt.foxit_pdf.convert_to_pdf(html.encode("utf-8"), "index.html")
        (out / "index.pdf").write_bytes(print_copy)
        via = (
            "xano static host (run: xano static host deploy)"
            if self.rt.settings.is_live
            else "fixtures"
        )
        payload = {
            "domain": domain,
            "url": f"https://{domain}/",
            "bytes": len(html.encode("utf-8")),
            "deployed_via": via,
            "as_of": now_iso(),
        }
        await self._emit(EventType.STOREFRONT_DEPLOYED, payload)
        self.projection["storefront"] = payload
        return f"https://{domain}/ · {payload['bytes']} bytes"

    async def _done(self) -> str:
        self.projection["state"] = "done"
        await self._emit(
            EventType.ONBOARDING_DONE,
            {
                "domain": self.projection["domain"]["name"],
                "skus": self.projection["catalog"]["skus"],
                "review": self.projection["catalog"]["review"],
                "documents": len(self.projection["documents"]),
                "as_of": now_iso(),
            },
        )
        return "open"
