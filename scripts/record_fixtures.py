"""One real call per primitive per vendor, recorded as cassettes.

Run from agent/: `RECORD=1 CHAIRSIDE_MODE=live uv run python ../scripts/record_fixtures.py`.
Vendors whose credentials are missing are skipped and listed. Set RECORD_IMAGE_URL to a public
selfie and RECORD_BOTTLE_URL to a public product photo for the YouCam and Lens primitives.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from chairside_agent.agents.runtime import Runtime, build_runtime
from chairside_agent.config import Settings

REPO = Path(__file__).resolve().parents[1]
SEED = REPO / "seed"
CREDENTIALS = {
    "serpapi": ["serpapi_api_key"],
    "namecom": ["namecom_username", "namecom_token"],
    "nutrient": ["nutrient_api_key"],
    "youcam": ["perfectcorp_api_key"],
    "foxit_pdf": ["foxit_client_id", "foxit_client_secret"],
    "doctavian": ["doctavian_base_url", "doctavian_api_key"],
    "xano": ["xano_base_url", "xano_agent_token"],
}


def _url(name: str) -> str | None:
    return os.environ.get(name) or None


async def record_serpapi(rt: Runtime) -> None:
    sku = next(s for s in rt.seed.skus if "olaplex" in s.brand.lower())
    if bottle := _url("RECORD_BOTTLE_URL"):
        await rt.serpapi.lens(bottle)
    await rt.serpapi.shopping(f"{sku.brand} {sku.name}", sku.code)
    await rt.serpapi.news(f"{sku.brand} {sku.name}", 90)
    nearby = await rt.serpapi.maps_nearby(rt.salon["ll"], "hair salon", 2)
    if nearby:
        await rt.serpapi.maps_reviews(nearby[0].place_id, "colour")


async def record_namecom(rt: Runtime) -> None:
    slug = "ateliernoor"
    suggestions = await rt.namecom.search(slug)
    names = [f"{slug}.com", *(s.domain_name for s in suggestions[:2])]
    availability = await rt.namecom.check_availability(names)
    domain = next((a.domain_name for a in availability if a.purchasable), None)
    if domain:
        created = await rt.namecom.create_domain(domain, f"record-{slug}")
        await rt.namecom.create_dns_record(
            created.domain_name, "www", "CNAME", "chairside.xano.app"
        )
        await rt.namecom.create_url_forwarding(created.domain_name, "www", f"https://{domain}")
        await rt.namecom.create_email_forwarding(
            created.domain_name, "hello", rt.salon["owner"]["email"]
        )


async def record_nutrient(rt: Runtime) -> None:
    price_list = (SEED / "price_list.pdf").read_bytes()
    invoice = (SEED / "invoices" / "inv-0001-loreal.pdf").read_bytes()
    intake = (SEED / "intake" / "intake-01-amira.png").read_bytes()
    await rt.nutrient.extract(price_list, "price_list", "price_list.pdf")
    await rt.nutrient.extract(invoice, "invoice", "inv-0001-loreal.pdf")
    await rt.nutrient.extract(intake, "intake", "intake-01-amira.png")
    merged = await rt.nutrient.build([price_list, invoice], pdfa=True)
    await rt.nutrient.sign_cades(merged)


async def record_youcam(rt: Runtime) -> None:
    image = _url("RECORD_IMAGE_URL")
    if not image:
        print("skip youcam: set RECORD_IMAGE_URL to a public selfie URL")
        return
    await rt.youcam.list_tools()
    await rt.youcam.color_tones(image)
    await rt.youcam.skin_hd(image)
    await rt.youcam.hair_diagnostics(image)
    await rt.youcam.face_attributes(image)
    await rt.youcam.hair_color_tryon(image, rt.seed.shade_map[0].hex)
    await rt.youcam.skin_simulation(image, "hydration")
    await rt.youcam.hairstyle_tryon(image, "long_layers")
    await rt.youcam.aging_simulation(image, 10)


async def record_foxit(rt: Runtime) -> None:
    invoice = (SEED / "invoices" / "inv-0002-olaplex-scanned.pdf").read_bytes()
    price_list = (SEED / "price_list.pdf").read_bytes()
    await rt.foxit_pdf.list_tools()
    merged = await rt.foxit_pdf.merge([price_list, invoice])
    await rt.foxit_pdf.compress(merged)
    await rt.foxit_pdf.ocr(invoice)
    await rt.foxit_pdf.convert_to_pdf(
        b"<html><body><h1>Atelier Noor</h1></body></html>", "index.html"
    )


async def record_doctavian(rt: Runtime) -> None:
    templates = rt.seed.templates
    data = {
        "salon": {"name": rt.salon["name"], "address": rt.salon["address"]},
        "jurisdiction": "FR",
        "treatment_classes": ["chemical"],
        "allergens": ["ppd"],
        "client": {"name": "Amira Benali"},
    }
    await rt.doctavian.generate(templates["consent"]["chemical"], data)
    await rt.doctavian.clickwrap(templates["client_terms"], data)


async def record_xano(rt: Runtime) -> None:
    consultation_id = await rt.xano.create_consultation("cl-01", 1, rt.salon["stylists"][0]["name"])
    await rt.xano.set_state(consultation_id, "capture")
    document_id = await rt.xano.create_document("consent", "fixture://consent", "")
    await rt.esign.request_envelope(
        document_id, {"name": "Amira Benali", "email": "amira@example.com"}, consultation_id
    )
    await rt.esign.redteam_direct_esign_call()


RECORDERS: dict[str, Callable[[Runtime], Awaitable[None]]] = {
    "serpapi": record_serpapi,
    "namecom": record_namecom,
    "nutrient": record_nutrient,
    "youcam": record_youcam,
    "foxit_pdf": record_foxit,
    "doctavian": record_doctavian,
    "xano": record_xano,
}


async def main() -> int:
    env = {**os.environ, "CHAIRSIDE_MODE": "live", "RECORD": "1"}
    settings = Settings.from_env(env)
    rt = build_runtime(settings, printer=None)
    try:
        for vendor, keys in CREDENTIALS.items():
            missing = [k for k in keys if not getattr(settings, k)]
            if missing:
                print(f"skip {vendor}: missing {', '.join(k.upper() for k in missing)}")
                continue
            await RECORDERS[vendor](rt)
            print(f"recorded {vendor}")
    finally:
        await rt.aclose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
