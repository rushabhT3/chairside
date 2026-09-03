from __future__ import annotations

from dataclasses import dataclass

from chairside_agent.core.models import (
    INVERTED_CONCERNS,
    FaceAttributes,
    HairDiagnostics,
    Plan,
    PlanItem,
    SkinScores,
    Sku,
    TreatmentClass,
)

CONCERN_THRESHOLD = 60
INVERTED_THRESHOLD = 40
FRIZZ_THRESHOLD = 60

COLOR_SERVICE = "SVC-COLOR"
COLOR_AFTERCARE_PRODUCT = "OLX-03"
SMOOTHING_SERVICE = "SVC-SMOOTH"
ANTI_FRIZZ_PRODUCT = "KER-DISC-MASK"
VOLUME_SERVICE = "SVC-VOLCUT"
VOLUME_PRODUCT = "KER-VOL"
CURL_PRODUCT = "KER-CURL"
CLARIFYING_SERVICE = "SVC-CLARIFY"
COLLAGEN_SERVICE = "SVC-COLLAGEN"
SOOTHING_SERVICE = "SVC-SOOTHE"
BARRIER_PRODUCT = "LRP-CICA"
BRIGHTENING_SERVICE = "SVC-BRIGHT"
LASER_SERVICE = "SVC-LASER"
INJECTABLE_SERVICE = "SVC-INJECT"

CLASS_ORDER: tuple[TreatmentClass, ...] = ("chemical", "heat", "injectable", "laser", "none")

HAIRSTYLE_BY_FACE_SHAPE: dict[str, str] = {
    "oval": "Oval face: any length and parting works",
    "round": "Round face: layered lengths past the chin",
    "square": "Square face: soft waves around the jaw",
    "heart": "Heart face: chin-length shapes",
    "oblong": "Oblong face: bangs to shorten the length",
    "diamond": "Diamond face: side-swept layers at the temples",
}

REBOOK_DEFAULT_WEEKS = 6
REBOOK_PRODUCTS_ONLY_WEEKS = 8


@dataclass(frozen=True, slots=True)
class _Pick:
    code: str
    treatment_class: TreatmentClass
    fact: str


def _flagged(scores: dict[str, int], concern: str) -> bool:
    score = scores.get(concern)
    if score is None:
        return False
    if concern in INVERTED_CONCERNS:
        return score <= INVERTED_THRESHOLD
    return score >= CONCERN_THRESHOLD


def _color_picks(codes: set[str]) -> list[_Pick]:
    if not any(sku_code.startswith("MAJ-") for sku_code in codes):
        return []
    return [
        _Pick(COLOR_SERVICE, "chemical", "Colour service in the salon's own shade line"),
        _Pick(COLOR_AFTERCARE_PRODUCT, "none", "Bond builder to take home after colour"),
    ]


def _hair_picks(hair: HairDiagnostics) -> list[_Pick]:
    picks: list[_Pick] = []
    if hair.frizz >= FRIZZ_THRESHOLD:
        picks.append(_Pick(SMOOTHING_SERVICE, "heat", f"Frizz {hair.frizz}: smoothing treatment"))
        picks.append(_Pick(ANTI_FRIZZ_PRODUCT, "none", "Anti-frizz mask between visits"))
    if hair.density == "low":
        picks.append(_Pick(VOLUME_SERVICE, "none", "Low density: volume cut"))
        picks.append(_Pick(VOLUME_PRODUCT, "none", "Volumising shampoo at home"))
    if hair.type in ("curly", "coily"):
        picks.append(_Pick(CURL_PRODUCT, "none", f"{hair.type.title()} hair: curl-care cream"))
    return picks


def _skin_picks(scores: dict[str, int], codes: set[str]) -> list[_Pick]:
    picks: list[_Pick] = []
    if _flagged(scores, "acne") or _flagged(scores, "oiliness"):
        picks.append(
            _Pick(CLARIFYING_SERVICE, "none", "Acne or oiliness reading: clarifying facial")
        )
    wrinkle, firmness = _flagged(scores, "wrinkle"), _flagged(scores, "firmness")
    if wrinkle or firmness:
        picks.append(_Pick(COLLAGEN_SERVICE, "heat", "Wrinkle or firmness reading: collagen LED"))
    if wrinkle and firmness and INJECTABLE_SERVICE in codes:
        picks.append(_Pick(INJECTABLE_SERVICE, "injectable", "Deep lines: injectable consult"))
    if _flagged(scores, "redness"):
        picks.append(_Pick(SOOTHING_SERVICE, "none", "Redness reading: soothing facial"))
        picks.append(_Pick(BARRIER_PRODUCT, "none", "Barrier balm for redness"))
    if _flagged(scores, "spot"):
        picks.append(_spot_pick(codes))
    return picks


def _spot_pick(codes: set[str]) -> _Pick:
    if LASER_SERVICE in codes:
        return _Pick(LASER_SERVICE, "laser", "Spot reading: laser pigment session")
    return _Pick(BRIGHTENING_SERVICE, "none", "Spot reading: brightening facial")


def _resolve(picks: list[_Pick], catalog: dict[str, Sku]) -> tuple[list[PlanItem], list[str]]:
    items: list[PlanItem] = []
    facts: list[str] = []
    seen: set[str] = set()
    for pick in picks:
        if pick.code in seen:
            continue
        seen.add(pick.code)
        sku = catalog.get(pick.code)
        if sku is None:
            facts.append(f"{pick.fact} (not carried: {pick.code})")
            continue
        facts.append(pick.fact)
        items.append(_item(sku, pick.treatment_class))
    return items, facts


def _item(sku: Sku, treatment_class: TreatmentClass) -> PlanItem:
    return PlanItem(
        code=sku.code,
        name=sku.name,
        price_cents=sku.salon_price_cents,
        qty=1,
        treatment_class=treatment_class,
    )


def _treatment_classes(items: list[PlanItem]) -> list[TreatmentClass]:
    present = {item.treatment_class for item in items}
    ordered = [cls for cls in CLASS_ORDER if cls in present]
    if len(ordered) > 1 and "none" in ordered:
        ordered.remove("none")
    return ordered


def _rebook_weeks(services: list[PlanItem]) -> int:
    if not services:
        return REBOOK_PRODUCTS_ONLY_WEEKS
    return REBOOK_DEFAULT_WEEKS


def recommend_plan(
    skin: SkinScores, hair: HairDiagnostics, face: FaceAttributes, catalog: list[Sku]
) -> Plan:
    by_code = {sku.code: sku for sku in catalog}
    codes = set(by_code)
    picks = _color_picks(codes) + _hair_picks(hair) + _skin_picks(skin.scores, codes)
    items, facts = _resolve(picks, by_code)
    services = [item for item in items if by_code[item.code].kind == "service"]
    products = [item for item in items if by_code[item.code].kind != "service"]
    facts.append(HAIRSTYLE_BY_FACE_SHAPE[face.shape])
    classes = _treatment_classes(items)
    return Plan(
        treatment_classes=classes or ["none"],
        services=services,
        products=products,
        total_cents=sum(item.price_cents * item.qty for item in items),
        rebook_weeks=_rebook_weeks(services),
        facts=facts,
    )
