from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from chairside_agent.adapters.base import VendorAdapter
from chairside_agent.config import Settings
from chairside_agent.core.models import Extraction, ExtractionSource, Field_
from chairside_agent.events import EventWriter
from chairside_agent.hashing import sha256_hex

BASE_URL = "https://api.nutrient.io"
# DWS Processor forces SHA-256 + CAdES B-LT on /sign; the level is not a request option.
CADES_LEVEL = "b-lt"
OCR_LANGUAGE = "french"
PDFA_CONFORMANCE = "pdfa-2a"

PRICE_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rows": {
            "type": "array",
            "description": "One row per product or service on the price list",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "SKU or reference code"},
                    "name": {"type": "string", "description": "Product or service name"},
                    "brand": {"type": "string", "description": "Brand or manufacturer"},
                    "price": {"type": "number", "description": "Price in EUR including VAT"},
                },
                "required": ["name", "price"],
            },
        }
    },
    "required": ["rows"],
}

INVOICE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": "string", "description": "Invoice identifier"},
        "supplier_name": {"type": "string", "description": "Issuing supplier"},
        "invoice_date": {"type": "string", "description": "Invoice date, ISO 8601"},
        "subtotal": {"type": "number", "description": "Total before VAT"},
        "vat_rate": {"type": "number", "description": "VAT rate as a percentage"},
        "vat_amount": {"type": "number", "description": "VAT amount"},
        "total": {"type": "number", "description": "Total including VAT"},
        "lines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "qty": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "amount": {"type": "number"},
                },
                "required": ["description", "qty", "unit_price", "amount"],
            },
        },
    },
    "required": ["invoice_number", "supplier_name", "total", "lines"],
}

INTAKE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Client full name"},
        "date": {"type": "string", "description": "Form date, ISO 8601"},
        "allergies": {"type": "string", "description": "Declared allergies, comma separated"},
        "medications": {"type": "string", "description": "Current medications"},
        "previous_chemical_services": {
            "type": "string",
            "description": "Chemical services in the last 12 months",
        },
        "pregnancy": {"type": "string", "description": "Pregnant or breastfeeding: yes/no"},
        "photo_consent": {"type": "string", "description": "Consent to photos: yes/no"},
        "notes": {"type": "string", "description": "Any free-text notes on the form"},
    },
    "required": ["name", "allergies"],
}

SCHEMAS: dict[str, dict[str, Any]] = {
    "price_list": PRICE_LIST_SCHEMA,
    "invoice": INVOICE_SCHEMA,
    "intake": INTAKE_SCHEMA,
}
LIST_PREFIXES = {"rows": "row", "lines": "line"}


class SealResult(BaseModel):
    pdf: bytes
    sha256: str
    cades_level: str = CADES_LEVEL


def variant_for(schema_name: str, filename: str) -> str:
    if schema_name == "price_list":
        return "price_list"
    stem = Path(filename).stem.lower()
    digits = re.search(r"\d+", stem)
    number = int(digits.group(0)) if digits else 1
    if schema_name == "invoice":
        return f"invoice_{number:04d}"
    suffix = "_adversarial" if "adversarial" in stem else ""
    return f"intake_{number:02d}{suffix}"


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(_text(v) for v in value)
    return str(value)


def _bbox(raw: dict[str, Any] | None) -> list[float]:
    if not raw:
        return []
    return [float(raw["x"]), float(raw["y"]), float(raw["width"]), float(raw["height"])]


def _field(name: str, value: Any, meta: dict[str, Any]) -> Field_:
    return Field_(
        name=name,
        value=_text(value),
        confidence=float(meta.get("confidence") or 0.0),
        page=int(meta.get("pageNumber") or 1),
        bbox=_bbox(meta.get("bbox")),
    )


def _meta_at(meta: dict[str, Any], key: str, index: int, sub_key: str) -> dict[str, Any]:
    items = meta.get(key) or []
    item = items[index] if index < len(items) else {}
    return item.get(sub_key) or {}


def to_extraction(schema_name: ExtractionSource, raw: dict[str, Any]) -> Extraction:
    output = raw["output"]
    data: dict[str, Any] = output["data"]
    meta: dict[str, Any] = output.get("metadata") or {}
    fields: list[Field_] = []
    for key, value in data.items():
        if isinstance(value, list) and key in LIST_PREFIXES:
            prefix = LIST_PREFIXES[key]
            for index, item in enumerate(value):
                for sub_key, sub_value in item.items():
                    fields.append(
                        _field(
                            f"{prefix}_{index + 1}_{sub_key}",
                            sub_value,
                            _meta_at(meta, key, index, sub_key),
                        )
                    )
        else:
            fields.append(_field(key, value, meta.get(key) or {}))
    text = output.get("text") or "\n".join(f.value for f in fields if f.value)
    return Extraction(source=schema_name, fields=fields, text=text)


def _binary_response(response: httpx.Response) -> dict[str, Any]:
    return {
        "_base64": base64.b64encode(response.content).decode("ascii"),
        "content_type": response.headers.get("content-type", "application/pdf"),
    }


class NutrientAdapter(VendorAdapter):
    vendor = "nutrient"
    server = "rest/nutrient"

    def __init__(
        self,
        settings: Settings,
        events: EventWriter,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(settings, events, http)

    def _headers(self) -> dict[str, str]:
        self.settings.require("nutrient_api_key")
        return {"Authorization": f"Bearer {self.settings.nutrient_api_key}"}

    async def extract(
        self,
        document: bytes,
        schema_name: ExtractionSource,
        filename: str,
        *,
        variant: str | None = None,
    ) -> Extraction:
        if schema_name not in SCHEMAS:
            raise ValueError(f"unknown extraction schema {schema_name!r}")
        instructions = {
            "schema": SCHEMAS[schema_name],
            "parseConfig": {"mode": "understand"},
            "options": {"includeCitations": True},
        }
        request = {
            "endpoint": "/extraction/extract",
            "filename": filename,
            "schema_name": schema_name,
            "document_sha256": sha256_hex(document),
            "instructions": instructions,
        }

        async def live(req: dict[str, Any]) -> dict[str, Any]:
            response = await self.http.post(
                BASE_URL + req["endpoint"],
                headers=self._headers(),
                files={"file": (req["filename"], document)},
                data={"instructions": json.dumps(req["instructions"])},
            )
            response.raise_for_status()
            return response.json()

        raw = await self.call(
            "extract",
            request,
            live,
            variant=variant or variant_for(schema_name, filename),
            tool="extraction/extract",
        )
        return to_extraction(schema_name, raw)

    async def build(self, parts: list[bytes], *, ocr: bool = False, pdfa: bool = False) -> bytes:
        if not parts:
            raise ValueError("build needs at least one part")
        names = [f"part{i}" for i in range(len(parts))]
        instructions: dict[str, Any] = {"parts": [{"file": n} for n in names]}
        if ocr:
            instructions["actions"] = [{"type": "ocr", "language": OCR_LANGUAGE}]
        if pdfa:
            instructions["output"] = {"type": "pdfa", "conformance": PDFA_CONFORMANCE}
        request = {
            "endpoint": "/build",
            "instructions": instructions,
            "part_sha256": [sha256_hex(p) for p in parts],
        }

        async def live(req: dict[str, Any]) -> dict[str, Any]:
            files = {
                name: (f"{name}.pdf", part, "application/pdf")
                for name, part in zip(names, parts, strict=True)
            }
            response = await self.http.post(
                BASE_URL + req["endpoint"],
                headers=self._headers(),
                files=files,
                data={"instructions": json.dumps(req["instructions"])},
            )
            response.raise_for_status()
            return _binary_response(response)

        flags = [flag for flag, on in (("ocr", ocr), ("pdfa", pdfa)) if on]
        raw = await self.call(
            "build", request, live, variant="_".join(flags) or "default", tool="build"
        )
        return base64.b64decode(raw["_base64"])

    async def sign_cades(self, pdf: bytes) -> SealResult:
        request = {
            "endpoint": "/sign",
            "document_sha256": sha256_hex(pdf),
            "data": {"flatten": False},
        }

        async def live(req: dict[str, Any]) -> dict[str, Any]:
            response = await self.http.post(
                BASE_URL + req["endpoint"],
                headers=self._headers(),
                files={
                    "file": ("document.pdf", pdf, "application/pdf"),
                    "data": (None, json.dumps(req["data"]), "application/json"),
                },
            )
            response.raise_for_status()
            return _binary_response(response)

        raw = await self.call("sign", request, live, tool="sign")
        signed = base64.b64decode(raw["_base64"])
        return SealResult(pdf=signed, sha256=sha256_hex(signed))
