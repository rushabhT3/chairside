from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Undertone = Literal["warm", "cool", "neutral"]
HairType = Literal["straight", "wavy", "curly", "coily"]
Density = Literal["low", "medium", "high"]
FaceShape = Literal["oval", "round", "square", "heart", "oblong", "diamond"]
TreatmentClass = Literal["chemical", "heat", "injectable", "laser", "none"]
SkuKind = Literal["retail", "backbar", "service"]
Jurisdiction = Literal["FR", "US"]
PriceAction = Literal["match", "bundle", "hold"]
ExtractionSource = Literal["price_list", "invoice", "intake"]

SKIN_CONCERNS: tuple[str, ...] = (
    "wrinkle",
    "spot",
    "pore",
    "texture",
    "acne",
    "redness",
    "oiliness",
    "dark_circle",
    "eye_bag",
    "droopy_upper_eyelid",
    "droopy_lower_eyelid",
    "firmness",
    "radiance",
    "moisture",
)
INVERTED_CONCERNS: frozenset[str] = frozenset({"firmness", "radiance", "moisture"})


class ColorTones(BaseModel):
    skin_tone: str
    undertone: Undertone
    eye_color: str
    hair_color_hex: str


class SkinScores(BaseModel):
    scores: dict[str, int]


class HairDiagnostics(BaseModel):
    type: HairType
    frizz: int = Field(ge=0, le=100)
    density: Density


class FaceAttributes(BaseModel):
    shape: FaceShape
    ratios: dict[str, int] = Field(default_factory=dict)


class Sku(BaseModel):
    code: str
    name: str
    brand: str
    salon_price_cents: int = Field(ge=0)
    shade_code: str | None = None
    kind: SkuKind = "retail"


class ShadeEntry(BaseModel):
    line: str
    code: str
    name: str
    hex: str
    undertone: Undertone
    level: int = Field(ge=1, le=10)


class PlanItem(BaseModel):
    code: str
    name: str
    price_cents: int = Field(ge=0)
    qty: int = Field(ge=1, default=1)
    treatment_class: TreatmentClass = "none"


class Plan(BaseModel):
    treatment_classes: list[TreatmentClass]
    services: list[PlanItem]
    products: list[PlanItem]
    total_cents: int
    rebook_weeks: int
    facts: list[str]


class PriceSnapshot(BaseModel):
    sku_code: str
    min_cents: int
    median_cents: int
    max_cents: int
    as_of: str
    source: Literal["google_shopping"] = "google_shopping"


class PriceVerdict(BaseModel):
    action: PriceAction
    reason: str


class ConsentSelection(BaseModel):
    template_id: str
    variables: dict


class Field_(BaseModel):
    name: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    page: int = 1
    bbox: list[float] = Field(default_factory=list)


class Extraction(BaseModel):
    source: ExtractionSource
    fields: list[Field_]
    text: str = ""


class QuarantineVerdict(BaseModel):
    quarantined: bool
    reasons: list[str]
