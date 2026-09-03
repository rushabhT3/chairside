"""Doctavian document generation.

Endpoint paths follow the shape documented with the credentials; adjust here only.
Credentials are issued by email, so the live path is a bearer-token REST client against
DOCTAVIAN_BASE_URL with `POST /generate` and `POST /clickwrap`; the fixtures path replays
FIXTURE-labelled cassettes whose PDFs were built locally.
"""

from __future__ import annotations

import base64
import re
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from chairside_agent.adapters.base import VendorAdapter


class GeneratedDocument(BaseModel):
    document_id: str
    pdf: bytes
    url: str
    as_of: str


class Clickwrap(BaseModel):
    url: str
    acceptance_id: str
    as_of: str


def cassette_variant(template_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", template_id.lower()).strip("_")
    return re.sub(r"^tpl_(fixture_)?", "", slug)


class DoctavianAdapter(VendorAdapter):
    vendor = "doctavian"
    server = "rest/doctavian"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.doctavian_api_key}",
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        self.settings.require("doctavian_base_url", "doctavian_api_key")
        response = await self.http.post(
            f"{self.settings.doctavian_base_url}{path}", json=body, headers=self._headers()
        )
        response.raise_for_status()
        return response.json()

    async def generate(
        self, template_id: str, data: dict[str, Any], *, variant: str | None = None
    ) -> GeneratedDocument:
        request = {"template_id": template_id, "data": data}
        response = await self.call(
            "generate",
            request,
            lambda req: self._post("/generate", req),
            variant=variant or cassette_variant(template_id),
            tool="generate",
        )
        return GeneratedDocument(
            document_id=response["document_id"],
            pdf=base64.b64decode(response["pdf_base64"]),
            url=response["url"],
            as_of=datetime.now(UTC).isoformat(timespec="seconds"),
        )

    async def clickwrap(
        self, template_id: str, data: dict[str, Any], *, variant: str | None = None
    ) -> Clickwrap:
        request = {"template_id": template_id, "data": data}
        response = await self.call(
            "clickwrap",
            request,
            lambda req: self._post("/clickwrap", req),
            variant=variant or cassette_variant(template_id),
            tool="clickwrap",
        )
        return Clickwrap(
            url=response["url"],
            acceptance_id=response["acceptance_id"],
            as_of=datetime.now(UTC).isoformat(timespec="seconds"),
        )
