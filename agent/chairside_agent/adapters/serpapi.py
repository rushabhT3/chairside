from __future__ import annotations

import statistics
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx
from pydantic import BaseModel

from chairside_agent.adapters.base import VendorAdapter
from chairside_agent.config import Settings
from chairside_agent.core.models import PriceSnapshot
from chairside_agent.events import EventWriter
from chairside_agent.fixtures import CassetteMissingError

SEARCH_URL = "https://serpapi.com/search"
PARIS_LL = "@48.8590,2.3640,15z"
DEFAULT_MAPS_ZOOM = "15z"
SEED_VARIANT = "seed"
FLAG_WORDS = (
    "recall",
    "rappel",
    "controvers",
    "toxic",
    "toxique",
    "ban",
    "interdit",
    "retrait",
    "lawsuit",
    "warning",
)
TITLE_SEPARATORS = (" - ", " | ", " – ", " — ")


class NoOffersError(RuntimeError):
    pass


class VisualMatch(BaseModel):
    title: str
    price_cents: int | None = None
    currency: str | None = None
    in_stock: bool | None = None
    source: str
    link: str


class LensResult(BaseModel):
    brand: str
    product: str
    visual_matches: list[VisualMatch]
    as_of: str


class Offer(BaseModel):
    title: str
    price_cents: int
    source: str
    link: str


class ShoppingResult(BaseModel):
    snapshot: PriceSnapshot
    offers: list[Offer]


class NewsFlag(BaseModel):
    title: str
    source: str
    date: str
    link: str


class NewsResult(BaseModel):
    flags: list[NewsFlag]
    clean: bool
    as_of: str


class Competitor(BaseModel):
    place_id: str
    name: str
    rating: float | None = None
    address: str


class ReviewSummary(BaseModel):
    place_id: str
    summary: str
    quotes: list[str]
    as_of: str


def to_cents(value: float | int | str) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def median_cents(cents: list[int]) -> int:
    return int(Decimal(statistics.median(cents)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def is_flagged(title: str) -> bool:
    lowered = title.lower()
    return any(word in lowered for word in FLAG_WORDS)


def split_title(title: str) -> tuple[str, str]:
    product = title
    for separator in TITLE_SEPARATORS:
        product = product.split(separator, 1)[0]
    brand = product.split()[0].strip(",.:;") if product.split() else product
    return brand, product.strip()


def recent_results(results: list[dict[str, Any]], cutoff: datetime) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for result in results:
        iso = result.get("iso_date")
        if iso and datetime.fromisoformat(iso) >= cutoff:
            kept.append(result)
    return kept


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _visual_match(raw: dict[str, Any]) -> VisualMatch:
    price = raw.get("price") or {}
    extracted = price.get("extracted_value")
    return VisualMatch(
        title=raw["title"],
        price_cents=to_cents(extracted) if extracted is not None else None,
        currency=price.get("currency"),
        in_stock=raw.get("in_stock"),
        source=raw.get("source", ""),
        link=raw.get("link", ""),
    )


def maps_ll(value: str) -> str:
    """Google Maps rejects a bare "lat,lng"; it wants "@lat,lng,<zoom>z"."""
    return value if value.startswith("@") else f"@{value},{DEFAULT_MAPS_ZOOM}"


class SerpApiAdapter(VendorAdapter):
    vendor = "serpapi"
    server = "rest/serpapi"

    def __init__(
        self,
        settings: Settings,
        events: EventWriter,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(settings, events, http)

    async def _search(self, params: dict[str, Any]) -> dict[str, Any]:
        self.settings.require("serpapi_api_key")
        response = await self.http.get(
            SEARCH_URL, params={**params, "api_key": self.settings.serpapi_api_key}
        )
        response.raise_for_status()
        return response.json()

    async def lens(self, image_url: str) -> LensResult:
        request = {
            "engine": "google_lens",
            "url": image_url,
            "type": "products",
            "hl": "fr",
            "country": "fr",
        }
        raw = await self.call("lens", request, self._search, tool="google_lens")
        matches = [_visual_match(m) for m in raw.get("visual_matches", [])]
        priced = [m for m in matches if m.price_cents is not None]
        top = priced[0] if priced else (matches[0] if matches else None)
        if top is None:
            raise NoOffersError("google_lens returned no visual matches")
        brand, product = split_title(top.title)
        return LensResult(brand=brand, product=product, visual_matches=matches, as_of=_now_iso())

    async def shopping(self, query: str, sku_code: str) -> ShoppingResult:
        request = {"engine": "google_shopping", "q": query, "gl": "fr", "hl": "fr"}
        try:
            raw = await self.call(
                "shopping", request, self._search, variant=sku_code, tool="google_shopping"
            )
        except CassetteMissingError:
            raw = await self.call(
                "shopping", request, self._search, variant=SEED_VARIANT, tool="google_shopping"
            )
        offers = [
            Offer(
                title=r["title"],
                price_cents=to_cents(r["extracted_price"]),
                source=r.get("source", ""),
                link=r.get("product_link") or r.get("link", ""),
            )
            for r in raw.get("shopping_results", [])
            if r.get("extracted_price") is not None
        ]
        if not offers:
            raise NoOffersError(f"google_shopping returned no priced offers for {query!r}")
        cents = sorted(o.price_cents for o in offers)
        snapshot = PriceSnapshot(
            sku_code=sku_code,
            min_cents=cents[0],
            median_cents=median_cents(cents),
            max_cents=cents[-1],
            as_of=_now_iso(),
        )
        return ShoppingResult(snapshot=snapshot, offers=offers)

    async def news(self, query: str, days: int = 90, *, now: datetime | None = None) -> NewsResult:
        request = {"engine": "google_news", "q": query, "gl": "fr", "hl": "fr"}
        raw = await self.call("news", request, self._search, tool="google_news")
        as_of = now or datetime.now(UTC)
        recent = recent_results(raw.get("news_results", []), as_of - timedelta(days=days))
        flags = [
            NewsFlag(
                title=r["title"],
                source=(r.get("source") or {}).get("name", ""),
                date=r["iso_date"],
                link=r.get("link", ""),
            )
            for r in recent
            if is_flagged(r["title"])
        ]
        return NewsResult(flags=flags, clean=not flags, as_of=as_of.isoformat(timespec="seconds"))

    async def maps_nearby(
        self, ll: str = PARIS_LL, query: str = "salon de coiffure", limit: int = 2
    ) -> list[Competitor]:
        request = {
            "engine": "google_maps",
            "q": query,
            "ll": maps_ll(ll),
            "type": "search",
            "hl": "fr",
        }
        raw = await self.call("maps_nearby", request, self._search, tool="google_maps")
        return [
            Competitor(
                place_id=r["place_id"],
                name=r["title"],
                rating=r.get("rating"),
                address=r.get("address", ""),
            )
            for r in raw.get("local_results", [])[:limit]
        ]

    async def maps_reviews(self, place_id: str, topic: str) -> ReviewSummary:
        request = {
            "engine": "google_maps_reviews",
            "place_id": place_id,
            "hl": "fr",
            "sort_by": "qualityScore",
        }
        raw = await self.call(
            "maps_reviews", request, self._search, variant=place_id, tool="google_maps_reviews"
        )
        reviews = raw.get("reviews", [])
        mentions = [r for r in reviews if topic.lower() in (r.get("snippet") or "").lower()]
        name = (raw.get("place_info") or {}).get("title", place_id)
        if mentions:
            average = statistics.mean(r["rating"] for r in mentions)
            summary = (
                f"{name}: {len(mentions)} of {len(reviews)} recent reviews mention {topic}; "
                f"those average {average:.1f}/5."
            )
        else:
            summary = f"{name}: none of {len(reviews)} recent reviews mention {topic}."
        return ReviewSummary(
            place_id=place_id,
            summary=summary,
            quotes=[r["snippet"] for r in mentions[:3]],
            as_of=_now_iso(),
        )
