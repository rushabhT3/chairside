"""Foxit PDF Services through the open-source MCP server (stdio).

Server: https://github.com/foxitsoftware/foxit-pdf-api-mcp-server (python build). The README
runs it with `uv --directory <checkout> run foxit-pdf-api-mcp-server`; the checkout path comes
from FOXIT_MCP_SERVER_DIR. Every operation is upload -> tool -> download, so one adapter call
records one cassette even though the server sees three tool calls.
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

from chairside_agent.adapters.base import VendorAdapter
from chairside_agent.config import REPO_DIR
from chairside_agent.hashing import sha256_hex

FOXIT_MCP_SERVER_DIR = Path(
    os.environ.get(
        "FOXIT_MCP_SERVER_DIR",
        str(
            REPO_DIR / "vendor" / "foxit-pdf-api-mcp-server" / "python" / "foxit-pdf-api-mcp-server"
        ),
    )
)
FOXIT_MCP_COMMAND: tuple[str, ...] = (
    "uv",
    "--directory",
    str(FOXIT_MCP_SERVER_DIR),
    "run",
    "foxit-pdf-api-mcp-server",
)

TOOL_UPLOAD = "upload_document"
TOOL_DOWNLOAD = "download_document"
TOOL_MERGE = "pdf_merge"
TOOL_COMPRESS = "pdf_compress"
TOOL_OCR = "pdf_ocr"
TOOL_TO_TEXT = "pdf_to_text"
TOOL_FROM_WORD = "pdf_from_word"
TOOL_FROM_IMAGE = "pdf_from_image"
TOOL_FROM_TEXT = "pdf_from_text"
TOOL_FROM_HTML = "pdf_from_html"

CONVERTERS: dict[str, str] = {
    ".docx": TOOL_FROM_WORD,
    ".doc": TOOL_FROM_WORD,
    ".png": TOOL_FROM_IMAGE,
    ".jpg": TOOL_FROM_IMAGE,
    ".jpeg": TOOL_FROM_IMAGE,
    ".txt": TOOL_FROM_TEXT,
    ".html": TOOL_FROM_HTML,
}


class OcrResult(BaseModel):
    text: str
    pdf: bytes


class FoxitError(RuntimeError):
    pass


def _tool_json(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structured_content", None)
    if structured:
        return structured
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            return json.loads(text)
    raise FoxitError("Foxit tool returned no JSON payload")


def _ok(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("success", True):
        raise FoxitError(payload.get("message") or payload.get("error") or "Foxit tool failed")
    return payload


class FoxitPdfAdapter(VendorAdapter):
    vendor = "foxit"
    server = "mcp/foxit"

    def _server_params(self) -> StdioServerParameters:
        self.settings.require("foxit_client_id", "foxit_client_secret")
        return StdioServerParameters(
            command=FOXIT_MCP_COMMAND[0],
            args=list(FOXIT_MCP_COMMAND[1:]),
            env={
                **os.environ,
                "FOXIT_CLOUD_API_HOST": self.settings.foxit_host,
                "FOXIT_CLOUD_API_CLIENT_ID": self.settings.foxit_client_id,
                "FOXIT_CLOUD_API_CLIENT_SECRET": self.settings.foxit_client_secret,
            },
        )

    async def _with_session(self, fn: Callable[[ClientSession], Awaitable[Any]]) -> Any:
        async with stdio_client(self._server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await fn(session)

    async def _upload(self, session: ClientSession, data: bytes, filename: str) -> str:
        payload = _ok(
            _tool_json(
                await session.call_tool(
                    TOOL_UPLOAD,
                    {"fileContent": base64.b64encode(data).decode(), "fileName": filename},
                )
            )
        )
        return payload["documentId"]

    async def _download(self, session: ClientSession, document_id: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / f"{document_id}.bin"
            _ok(
                _tool_json(
                    await session.call_tool(
                        TOOL_DOWNLOAD, {"documentId": document_id, "outputPath": str(target)}
                    )
                )
            )
            return target.read_bytes()

    async def _run_tool(
        self, session: ClientSession, tool: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        return _ok(_tool_json(await session.call_tool(tool, args)))

    async def list_tools(self) -> list[str]:
        async def live(_: dict[str, Any]) -> dict[str, Any]:
            async def run(session: ClientSession) -> dict[str, Any]:
                listed = await session.list_tools()
                return {"tools": [tool.name for tool in listed.tools]}

            return await self._with_session(run)

        response = await self.call("tools_list", {}, live, units=0, tool="tools/list")
        return list(response["tools"])

    async def merge(self, pdfs: list[bytes], *, variant: str = "default") -> bytes:
        if not pdfs:
            raise ValueError("merge needs at least one PDF")
        request = {"parts": [sha256_hex(p) for p in pdfs]}

        async def live(_: dict[str, Any]) -> dict[str, Any]:
            async def run(session: ClientSession) -> dict[str, Any]:
                ids = [await self._upload(session, p, f"part-{i}.pdf") for i, p in enumerate(pdfs)]
                merged = await self._run_tool(
                    session, TOOL_MERGE, {"documents": [{"documentId": i} for i in ids]}
                )
                result_id = merged["resultDocumentId"]
                data = await self._download(session, result_id)
                return {"resultDocumentId": result_id, "_base64": base64.b64encode(data).decode()}

            return await self._with_session(run)

        response = await self.call("merge", request, live, variant=variant, tool=TOOL_MERGE)
        return base64.b64decode(response["_base64"])

    async def compress(self, pdf: bytes, *, variant: str = "default") -> bytes:
        request = {"sha256": sha256_hex(pdf), "compressionLevel": "MEDIUM"}

        async def live(req: dict[str, Any]) -> dict[str, Any]:
            async def run(session: ClientSession) -> dict[str, Any]:
                doc_id = await self._upload(session, pdf, "input.pdf")
                done = await self._run_tool(
                    session,
                    TOOL_COMPRESS,
                    {"documentId": doc_id, "compressionLevel": req["compressionLevel"]},
                )
                result_id = done["resultDocumentId"]
                data = await self._download(session, result_id)
                return {"resultDocumentId": result_id, "_base64": base64.b64encode(data).decode()}

            return await self._with_session(run)

        response = await self.call("compress", request, live, variant=variant, tool=TOOL_COMPRESS)
        return base64.b64decode(response["_base64"])

    async def ocr(self, document: bytes, *, variant: str = "default") -> OcrResult:
        request = {"sha256": sha256_hex(document)}

        async def live(_: dict[str, Any]) -> dict[str, Any]:
            async def run(session: ClientSession) -> dict[str, Any]:
                doc_id = await self._upload(session, document, "scan.pdf")
                searchable = await self._run_tool(session, TOOL_OCR, {"documentId": doc_id})
                pdf_id = searchable["resultDocumentId"]
                pdf = await self._download(session, pdf_id)
                text_id = (await self._run_tool(session, TOOL_TO_TEXT, {"documentId": pdf_id}))[
                    "resultDocumentId"
                ]
                text = (await self._download(session, text_id)).decode("utf-8", "replace")
                return {
                    "resultDocumentId": pdf_id,
                    "text": text,
                    "_base64": base64.b64encode(pdf).decode(),
                }

            return await self._with_session(run)

        response = await self.call("ocr", request, live, variant=variant, tool=TOOL_OCR)
        return OcrResult(text=response["text"], pdf=base64.b64decode(response["_base64"]))

    async def convert_to_pdf(
        self, document: bytes, filename: str, *, variant: str = "default"
    ) -> bytes:
        suffix = Path(filename).suffix.lower()
        if suffix not in CONVERTERS:
            raise ValueError(f"no Foxit converter for {suffix or 'files without extension'}")
        tool = CONVERTERS[suffix]
        request = {"sha256": sha256_hex(document), "filename": filename, "tool": tool}

        async def live(_: dict[str, Any]) -> dict[str, Any]:
            async def run(session: ClientSession) -> dict[str, Any]:
                doc_id = await self._upload(session, document, filename)
                done = await self._run_tool(session, tool, {"documentId": doc_id})
                result_id = done["resultDocumentId"]
                data = await self._download(session, result_id)
                return {"resultDocumentId": result_id, "_base64": base64.b64encode(data).decode()}

            return await self._with_session(run)

        response = await self.call("convert", request, live, variant=variant, tool=tool)
        return base64.b64decode(response["_base64"])
