"""Reaches Foxit eSign only through Xano's Commit Service.

Rule: this process never reads an eSign credential. The only secrets in scope are the Xano
agent token and the PDF Services client id/secret. `redteam_direct_esign_call` proves it by
presenting the PDF Services credential to the eSign gateway and recording the rejection.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel

from chairside_agent import fixtures
from chairside_agent.adapters.base import VendorAdapter
from chairside_agent.adapters.xano import live_path
from chairside_agent.events import EventType

ESIGN_CREATE_ENVELOPE_PATH = "/esign/api/v1/folders/createfolder"


class EnvelopeHandle(BaseModel):
    envelope_id: str
    state: str


class EnvelopeStatus(BaseModel):
    state: str
    session_url: str | None = None
    expires_at: str | None = None


def esign_gateway(pdf_services_host: str) -> str:
    return pdf_services_host.removesuffix("/pdf-services")


class EsignProxy(VendorAdapter):
    vendor = "foxit"
    server = "commit/xano"

    def _xano_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.xano_agent_token}",
            "Content-Type": "application/json",
        }

    async def _xano(self, method: str, path: str, body: dict[str, Any] | None) -> dict[str, Any]:
        self.settings.require("xano_base_url", "xano_agent_token")
        response = await self.http.request(
            method,
            f"{self.settings.xano_base_url}{live_path(path)}",
            json=body,
            headers=self._xano_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def request_envelope(
        self,
        document_id: str,
        signer: dict[str, str],
        consultation_id: str | None = None,
    ) -> EnvelopeHandle:
        request = {
            "document_id": document_id,
            "signer": {"name": signer["name"], "email": signer["email"]},
            "consultation_id": consultation_id,
        }
        response = await self.call(
            "request_envelope",
            request,
            lambda req: self._xano("POST", "/agent/envelopes", req),
            tool="agent.envelopes.create",
        )
        return EnvelopeHandle(envelope_id=response["envelope_id"], state=response["state"])

    async def status(self, envelope_id: str) -> EnvelopeStatus:
        response = await self.call(
            "envelope_status",
            {"envelope_id": envelope_id},
            lambda req: self._xano("GET", f"/commit/envelopes/{req['envelope_id']}/status", None),
            units=0,
            tool="commit.envelopes.status",
        )
        return EnvelopeStatus.model_validate(response)

    async def redteam_direct_esign_call(self) -> int:
        endpoint = esign_gateway(self.settings.foxit_host) + ESIGN_CREATE_ENVELOPE_PATH
        if self.settings.is_live:
            self.settings.require("foxit_client_id", "foxit_client_secret")
            try:
                response = await self.http.post(
                    endpoint,
                    json={"folderName": "chairside redteam", "inputType": "base64"},
                    headers={
                        "client_id": self.settings.foxit_client_id,
                        "client_secret": self.settings.foxit_client_secret,
                    },
                )
                status = response.status_code
            except httpx.HTTPError:
                status = 0
        else:
            status = int(
                fixtures.load(self.settings.fixtures_dir, self.vendor, "redteam_esign").response[
                    "status"
                ]
            )
        await self.events.emit(
            EventType.REDTEAM_ESIGN_DENIED,
            {
                "endpoint": endpoint,
                "credential_presented": "pdf_services_client_id",
                "http_status": status,
                "denied": status in (401, 403),
                "as_of": datetime.now(UTC).isoformat(timespec="seconds"),
            },
        )
        return status
