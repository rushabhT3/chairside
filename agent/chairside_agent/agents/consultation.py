"""Act 2: one selfie runs the consultation. Fixed order; any failure halts downstream."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any

from chairside_agent.agents.runtime import RenderCache, Runtime, now_iso
from chairside_agent.agents.signing import await_signature
from chairside_agent.core.consent_template_select import (
    NoConsentRequiredError,
    consent_template_select,
)
from chairside_agent.core.models import (
    ColorTones,
    ConsentSelection,
    Extraction,
    FaceAttributes,
    HairDiagnostics,
    Plan,
    PriceVerdict,
    ShadeEntry,
    SkinScores,
    Sku,
)
from chairside_agent.core.price_policy import price_policy
from chairside_agent.core.quarantine_policy import quarantine_policy
from chairside_agent.core.recommend_plan import recommend_plan
from chairside_agent.core.sku_shade_map import shade_for_sku
from chairside_agent.events import Actor, ConsultationEvent, EventType
from chairside_agent.llm import narrate
from chairside_agent.replay import apply, empty_projection

STEPS = (
    "capture",
    "color_tones",
    "skin_hd",
    "hair_diagnostics",
    "face_attributes",
    "plan",
    "simulations",
    "price",
    "consent",
    "commit",
)
STYLE_BY_FACE_SHAPE = {
    "oval": "long_layers",
    "round": "textured_lob",
    "square": "soft_waves",
    "heart": "side_swept_bangs",
    "oblong": "chin_length_bob",
    "diamond": "curtain_bangs",
}
CONFIDENCE_THRESHOLD = 0.85
DEFAULT_BOTTLE_URL = "fixture://bottle/olaplex-no3"
AGING_YEARS = 10
REVIEW_COMPETITORS = 2
NEWS_DAYS = 90
MIN_MATCH_TOKENS = 2


class QuarantineHalt(RuntimeError):
    def __init__(self, source: str, file: str, reasons: list[str]) -> None:
        super().__init__(f"{source} {file} quarantined: {'; '.join(reasons)}")
        self.source = source
        self.file = file
        self.reasons = reasons


@dataclass(slots=True)
class ConsultOptions:
    client_id: str
    chair: int = 1
    stylist: str = ""
    face_count: int = 1
    aging: bool = False
    image_url: str | None = None
    bottle_url: str = DEFAULT_BOTTLE_URL
    intake: Path | None = None
    visit: int | None = None
    retained: bool = False


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 1}


def match_sku(brand: str, product: str, catalog: list[Sku]) -> Sku | None:
    want = _tokens(f"{brand} {product}")
    best: Sku | None = None
    score = 0
    for sku in catalog:
        if sku.kind == "service":
            continue
        shared = len(want & _tokens(f"{sku.brand} {sku.name}"))
        if shared > score:
            best, score = sku, shared
    return best if score >= MIN_MATCH_TOKENS else None


def fallback_shade(undertone: str, shade_map: list[ShadeEntry]) -> ShadeEntry:
    matches = sorted(
        [e for e in shade_map if e.undertone == undertone] or shade_map, key=lambda e: e.level
    )
    return matches[len(matches) // 2]


SKIN_TREATMENT_BY_SERVICE = {
    "SVC-CLARIFY": "clarifying",
    "SVC-COLLAGEN": "anti_aging",
    "SVC-SOOTHE": "calming",
    "SVC-BRIGHT": "brightening",
}
SKIN_TREATMENT_BY_CONCERN = {
    "redness": "calming",
    "wrinkle": "anti_aging",
    "spot": "brightening",
    "texture": "resurfacing",
    "pore": "resurfacing",
    "oiliness": "clarifying",
    "dark_circle": "eye_refresh",
    "eye_bag": "eye_refresh",
}


def skin_treatment(plan: Plan, scores: dict[str, int]) -> str:
    """The plan's skin service decides; without one, the highest skin concern does."""
    for item in plan.services:
        if item.code in SKIN_TREATMENT_BY_SERVICE:
            return SKIN_TREATMENT_BY_SERVICE[item.code]
    concern = max(SKIN_TREATMENT_BY_CONCERN, key=lambda k: (scores.get(k, 0), k))
    return SKIN_TREATMENT_BY_CONCERN[concern]


def intake_for(client: dict[str, Any], intake_dir: Path) -> Path:
    first = client["name"].split()[0].lower()
    files = sorted(intake_dir.glob("*.png"))
    for path in files:
        if first in path.stem.lower():
            return path
    if not files:
        raise FileNotFoundError(f"no intake scans under {intake_dir}")
    return files[0]


def ocr_variant(filename: str) -> str:
    return "adversarial" if "adversarial" in filename.lower() else "default"


def image_digest(repo_dir: Path, image_ref: str, fallback: str) -> str:
    path = repo_dir / image_ref
    if path.exists():
        return sha256(path.read_bytes()).hexdigest()
    return sha256(fallback.encode()).hexdigest()


@dataclass(slots=True)
class ConsultationAgent:
    rt: Runtime
    opts: ConsultOptions = field(default_factory=lambda: ConsultOptions(client_id=""))
    id: str = ""
    projection: dict[str, Any] = field(default_factory=dict)
    client: dict[str, Any] = field(default_factory=dict)
    visit: dict[str, Any] = field(default_factory=dict)
    visit_index: int = 0
    stylist: str = ""
    image_url: str = ""
    image_sha256: str = ""
    tones: ColorTones | None = None
    skin: SkinScores | None = None
    hair: HairDiagnostics | None = None
    face: FaceAttributes | None = None
    plan: Plan | None = None
    selection: ConsentSelection | None = None

    async def _emit(
        self, type_: EventType, payload: dict[str, Any], *, actor: Actor = "agent"
    ) -> ConsultationEvent:
        ev = await self.rt.events.emit(type_, payload, actor=actor, consultation_id=self.id)
        self.projection = apply(self.projection, ev)
        return ev

    async def _transition(self, to: str, failing_step: str | None = None) -> None:
        await self._emit(EventType.STATE_CHANGED, {"from": self.projection["state"], "to": to})
        await self.rt.xano.set_state(self.id, to, failing_step)

    async def run(self, opts: ConsultOptions) -> dict[str, Any]:
        self.opts = opts
        self.client = self.rt.seed.client(opts.client_id)
        self.stylist = opts.stylist or self.rt.salon["stylists"][0]["name"]
        self.id = await self.rt.xano.create_consultation(opts.client_id, opts.chair, self.stylist)
        self.rt.events.consultation_id = self.id
        self.projection = empty_projection(self.id)
        steps: dict[str, Callable[[], Awaitable[None]]] = {
            name: getattr(self, f"_{name}") for name in STEPS
        }
        for name in STEPS:
            if not await self._run_step(name, steps[name]):
                break
        else:
            await self._transition("done")
        self.rt.projections.save(self.id, self.projection)
        return self.projection

    async def _run_step(self, name: str, step: Callable[[], Awaitable[None]]) -> bool:
        try:
            if name != STEPS[0]:
                await self._transition(name)
            await step()
        except QuarantineHalt as halt:
            await self._emit(
                EventType.QUARANTINED,
                {
                    "source": halt.source,
                    "file": halt.file,
                    "reasons": halt.reasons,
                    "as_of": now_iso(),
                },
            )
            await self._fail(name, halt)
            return False
        except Exception as exc:
            await self._fail(name, exc)
            return False
        return True

    async def _fail(self, step: str, exc: Exception) -> None:
        await self._emit(
            EventType.NEEDS_ATTENTION,
            {"step": step, "error": f"{type(exc).__name__}: {exc}", "as_of": now_iso()},
        )
        await self._transition("needs_attention", failing_step=step)

    def _previous_count(self) -> int:
        count = 0
        for key in self.rt.projections.keys():
            if key == "onboarding":
                continue
            stored = self.rt.projections.load(key)
            if (stored.get("client") or {}).get("id") == self.opts.client_id:
                count += 1
        return count

    async def _capture(self) -> None:
        visits = self.client["visits"]
        self.visit_index = (
            self.opts.visit
            if self.opts.visit is not None
            else min(self._previous_count(), len(visits) - 1)
        )
        self.visit = visits[self.visit_index]
        scan_id = self.visit["scan_id"]
        self.image_sha256 = image_digest(
            self.rt.settings.seed_dir.parent,
            self.visit["image_ref"],
            f"{self.opts.client_id}:{scan_id}",
        )
        self.image_url = self.opts.image_url or f"fixture://{scan_id}"
        await self._emit(
            EventType.CAPTURE_UPLOADED,
            {
                "client_id": self.opts.client_id,
                "client_name": self.client["name"],
                "stylist": self.stylist,
                "chair": self.opts.chair,
                "scan_id": scan_id,
                "image_sha256": self.image_sha256,
                "image_url": self.image_url,
                "retained": self.opts.retained,
                "face_count": self.opts.face_count,
                "as_of": now_iso(),
            },
        )
        guard = quarantine_policy(
            Extraction(source="intake", fields=[], text=""), face_count=self.opts.face_count
        )
        if guard.quarantined:
            raise QuarantineHalt("scan", scan_id, guard.reasons)

    async def _color_tones(self) -> None:
        self.tones = await self.rt.youcam.color_tones(self.image_url)
        await self._emit(
            EventType.COLOR_TONES_DONE, {**self.tones.model_dump(), "as_of": now_iso()}
        )

    def _previous_skin(self) -> dict[str, Any] | None:
        if self.visit_index == 0:
            return None
        prior = self.client["visits"][self.visit_index - 1]
        return {"scan_id": prior["scan_id"], "ts": prior["ts"], "skin": prior["skin"]}

    async def _skin_hd(self) -> None:
        self.skin = await self.rt.youcam.skin_hd(self.image_url)
        previous = self._previous_skin()
        deltas = (
            {
                k: v - previous["skin"][k]
                for k, v in self.skin.scores.items()
                if k in previous["skin"]
            }
            if previous
            else None
        )
        await self._emit(
            EventType.SKIN_HD_DONE,
            {
                "scores": self.skin.scores,
                "previous": previous,
                "deltas": deltas,
                "as_of": now_iso(),
            },
        )

    async def _hair_diagnostics(self) -> None:
        self.hair = await self.rt.youcam.hair_diagnostics(self.image_url)
        await self._emit(
            EventType.HAIR_DIAGNOSTICS_DONE, {**self.hair.model_dump(), "as_of": now_iso()}
        )

    async def _face_attributes(self) -> None:
        self.face = await self.rt.youcam.face_attributes(self.image_url)
        await self._emit(
            EventType.FACE_ATTRIBUTES_DONE, {**self.face.model_dump(), "as_of": now_iso()}
        )

    async def _plan(self) -> None:
        assert self.skin and self.hair and self.face
        self.plan = recommend_plan(self.skin, self.hair, self.face, self.rt.seed.skus)
        prose = await narrate(self.rt.settings, self.plan, self.projection["scan"])
        await self._emit(
            EventType.PLAN_RECOMMENDED,
            {**self.plan.model_dump(), "prose": prose, "as_of": now_iso()},
        )

    def _shade(self) -> tuple[Sku | None, ShadeEntry]:
        assert self.plan and self.tones
        by_code = {s.code: s for s in self.rt.seed.skus}
        for item in self.plan.products + self.plan.services:
            sku = by_code.get(item.code)
            if sku and sku.shade_code:
                return sku, shade_for_sku(sku, self.rt.seed.shade_map)
        shade = fallback_shade(self.tones.undertone, self.rt.seed.shade_map)
        carrier = next((s for s in self.rt.seed.skus if s.shade_code == shade.code), None)
        return carrier, shade

    async def _render(
        self,
        tab: str,
        tool: str,
        sku_code: str | None,
        hex_: str | None,
        label: str,
        call: Callable[[], Awaitable[Any]],
    ) -> dict[str, Any]:
        key = RenderCache.key(self.opts.client_id, sku_code, tool, self.image_sha256)
        cached = self.rt.renders.get(key)
        if cached:
            return {**cached, "cache_hit": True}
        result = await call()
        payload = {
            "tool": result.tool,
            "server": result.server,
            "tab": tab,
            "sku_code": sku_code,
            "hex": hex_,
            "label": label,
            "before_url": self.image_url,
            "after_url": result.image_url,
            "as_of": result.as_of,
            "cache_hit": False,
        }
        self.rt.renders.put(key, payload)
        return payload

    async def _simulations(self) -> None:
        assert self.plan and self.face and self.skin
        sku, shade = self._shade()
        treatment = skin_treatment(self.plan, self.skin.scores)
        style = STYLE_BY_FACE_SHAPE[self.face.shape]
        url = self.image_url
        jobs = [
            self._render(
                "hair",
                "hair_color_tryon",
                sku.code if sku else None,
                shade.hex,
                f"{shade.code} {shade.name}",
                lambda: self.rt.youcam.hair_color_tryon(url, shade.hex),
            ),
            self._render(
                "skin",
                "skin_simulation",
                None,
                None,
                treatment,
                lambda: self.rt.youcam.skin_simulation(url, treatment),
            ),
            self._render(
                "style",
                "hairstyle_tryon",
                None,
                None,
                style,
                lambda: self.rt.youcam.hairstyle_tryon(url, style),
            ),
        ]
        if self.opts.aging:
            jobs.append(
                self._render(
                    "skin",
                    "aging_simulation",
                    None,
                    None,
                    f"+{AGING_YEARS} years",
                    lambda: self.rt.youcam.aging_simulation(url, AGING_YEARS),
                )
            )
        for payload in await asyncio.gather(*jobs):
            await self._emit(EventType.SIMULATION_RENDERED, payload)

    async def _price(self) -> None:
        lens = await self.rt.serpapi.lens(self.opts.bottle_url)
        sku = match_sku(lens.brand, lens.product, self.rt.seed.skus)
        query = f"{lens.brand} {lens.product}".strip()
        await self._emit(
            EventType.PRICE_IDENTIFIED,
            {
                "sku_code": sku.code if sku else None,
                "brand": lens.brand,
                "product": lens.product,
                "matches": len(lens.visual_matches),
                "carried": sku is not None,
                "as_of": lens.as_of,
            },
        )
        shopping = await self.rt.serpapi.shopping(query, sku.code if sku else "unlisted")
        snap = shopping.snapshot
        verdict = (
            price_policy(sku.salon_price_cents, snap)
            if sku
            else PriceVerdict(action="hold", reason="not carried by the salon")
        )
        await self._emit(
            EventType.PRICE_SNAPSHOT,
            {
                "sku_code": sku.code if sku else None,
                "name": sku.name if sku else query,
                "salon_price_cents": sku.salon_price_cents if sku else None,
                "min_cents": snap.min_cents,
                "median_cents": snap.median_cents,
                "max_cents": snap.max_cents,
                "action": verdict.action,
                "reason": verdict.reason,
                "as_of": snap.as_of,
            },
        )
        news = await self.rt.serpapi.news(query, NEWS_DAYS)
        await self._emit(
            EventType.NEWS_CHECKED,
            {
                "query": query,
                "days": NEWS_DAYS,
                "clean": news.clean,
                "flags": [f.model_dump() for f in news.flags],
                "as_of": news.as_of,
            },
        )
        await self._competitor_reviews()

    async def _competitor_reviews(self) -> None:
        assert self.plan
        topic = self.plan.services[0].name if self.plan.services else "consultation"
        competitors = await self.rt.serpapi.maps_nearby(
            self.rt.salon["ll"], "hair salon", REVIEW_COMPETITORS
        )
        for competitor in competitors[:REVIEW_COMPETITORS]:
            review = await self.rt.serpapi.maps_reviews(competitor.place_id, topic)
            await self._emit(
                EventType.REVIEWS_FETCHED,
                {
                    "place_id": competitor.place_id,
                    "competitor": competitor.name,
                    "topic": topic,
                    "summary": review.summary,
                    "quotes": review.quotes,
                    "visibility": "staff",
                    "as_of": review.as_of,
                },
            )

    async def _consent(self) -> None:
        assert self.plan
        salon = self.rt.salon
        try:
            self.selection = consent_template_select(
                self.plan,
                self.client.get("allergens", []),
                salon["jurisdiction"],
                salon,
                self.client,
                self.rt.seed.templates,
            )
        except NoConsentRequiredError:
            await self._emit(
                EventType.CONSENT_TEMPLATE_SELECTED,
                {
                    "template_id": None,
                    "treatment_classes": [],
                    "allergens": [],
                    "jurisdiction": salon["jurisdiction"],
                    "as_of": now_iso(),
                },
            )
            return
        variables = self.selection.variables
        await self._emit(
            EventType.CONSENT_TEMPLATE_SELECTED,
            {
                "template_id": self.selection.template_id,
                "treatment_classes": variables["treatment_classes"],
                "allergens": variables["allergens"],
                "jurisdiction": variables["jurisdiction"],
                "as_of": now_iso(),
            },
        )
        doc = await self.rt.doctavian.generate(self.selection.template_id, variables)
        await self._emit(
            EventType.CONSENT_GENERATED,
            {"document_id": doc.document_id, "url": doc.url, "as_of": doc.as_of},
        )
        intake_pdf = await self._intake(set(variables["treatment_classes"]))
        document_id = await self.rt.xano.create_document("consent", doc.url, "")
        envelope = await self.rt.esign.request_envelope(
            document_id,
            {"name": self.client["name"], "email": self.client["email"]},
            consultation_id=self.id,
        )
        await self._emit(
            EventType.ENVELOPE_REQUESTED,
            {
                "envelope_id": envelope.envelope_id,
                "document_id": document_id,
                "signer": "client",
                "as_of": now_iso(),
            },
        )
        await await_signature(
            self.rt,
            self._emit,
            envelope.envelope_id,
            signer="client",
            gatekeeper="stylist",
            gate_check="consent_ready",
        )
        await self._seal(envelope.envelope_id, [doc.pdf, intake_pdf])

    async def _intake(self, consented: set[str]) -> bytes:
        assert self.plan
        path = self.opts.intake or intake_for(self.client, self.rt.settings.seed_dir / "intake")
        raw = path.read_bytes()
        ocr = await self.rt.foxit_pdf.ocr(raw, variant=ocr_variant(path.name))
        extraction = await self.rt.nutrient.extract(raw, "intake", path.name)
        text = "\n".join(t for t in (extraction.text, ocr.text) if t)
        extraction = extraction.model_copy(update={"text": text})
        low = sum(1 for f in extraction.fields if f.confidence < CONFIDENCE_THRESHOLD)
        await self._emit(
            EventType.INTAKE_EXTRACTED,
            {
                "file": path.name,
                "fields": len(extraction.fields),
                "low_confidence": low,
                "as_of": now_iso(),
            },
        )
        verdict = quarantine_policy(extraction, plan=self.plan, consented_classes=consented)
        if verdict.quarantined:
            raise QuarantineHalt("intake", path.name, verdict.reasons)
        return ocr.pdf

    async def _seal(self, envelope_id: str, parts: list[bytes]) -> None:
        packet = await self.rt.foxit_pdf.merge(parts)
        seal = await self.rt.nutrient.sign_cades(packet)
        out = self.rt.settings.state_dir / "documents"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{self.id}-bundle.pdf").write_bytes(seal.pdf)
        await self.rt.xano.create_document(
            "consent_bundle", f"documents/{self.id}-bundle.pdf", seal.sha256
        )
        await self._emit(
            EventType.BUNDLE_SEALED,
            {
                "sha256": seal.sha256,
                "parts": len(parts),
                "envelope_id": envelope_id,
                "signature": "CAdES B-LT",
                "as_of": now_iso(),
            },
        )

    async def _commit(self) -> None:
        assert self.plan
        await self._emit(
            EventType.PLAN_ACCEPTED,
            {"total_cents": self.plan.total_cents, "as_of": now_iso()},
            actor="client",
        )
        items = [i.model_dump() for i in self.plan.products]
        order_total = sum(i.price_cents * i.qty for i in self.plan.products)
        order_id = await self.rt.xano.create_order(self.id, items, order_total)
        await self._emit(
            EventType.ORDER_CREATED,
            {
                "order_id": order_id,
                "total_cents": order_total,
                "items": len(items),
                "stylist": self.stylist,
                "chair": self.opts.chair,
                "as_of": now_iso(),
            },
        )
        when = (datetime.now(UTC) + timedelta(weeks=self.plan.rebook_weeks)).date().isoformat()
        service = self.plan.services[0].name if self.plan.services else "check-in"
        booking_id = await self.rt.xano.create_booking(self.id, when, service)
        await self._emit(
            EventType.BOOKING_CREATED,
            {
                "booking_id": booking_id,
                "when": when,
                "service": service,
                "weeks": self.plan.rebook_weeks,
                "as_of": now_iso(),
            },
        )
