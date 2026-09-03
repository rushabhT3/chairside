import pytest

from chairside_agent.adapters._pdf import minimal_pdf
from chairside_agent.adapters.foxit_pdf import (
    FOXIT_MCP_COMMAND,
    TOOL_MERGE,
    TOOL_OCR,
    FoxitPdfAdapter,
)
from chairside_agent.events import EventType, LocalLedger


@pytest.fixture
def foxit(settings, events) -> FoxitPdfAdapter:
    return FoxitPdfAdapter(settings, events)


def _tool_events(ledger: LocalLedger) -> list[dict]:
    return [e.payload for e in ledger.read_events() if e.type == EventType.TOOL_CALLED]


def test_command_matches_readme() -> None:
    assert FOXIT_MCP_COMMAND[0] == "uv"
    assert FOXIT_MCP_COMMAND[-1] == "foxit-pdf-api-mcp-server"


async def test_list_tools_includes_reversible_operations(foxit: FoxitPdfAdapter) -> None:
    tools = await foxit.list_tools()

    assert {"pdf_merge", "pdf_compress", "pdf_ocr", "pdf_from_word", "upload_document"} <= set(
        tools
    )


async def test_merge_returns_pdf_and_logs_mcp_foxit(
    foxit: FoxitPdfAdapter, ledger: LocalLedger
) -> None:
    merged = await foxit.merge([minimal_pdf(["a"]), minimal_pdf(["b"])])

    assert merged.startswith(b"%PDF-1.4")
    last = _tool_events(ledger)[-1]
    assert last["server"] == "mcp/foxit"
    assert last["tool"] == TOOL_MERGE
    assert last["units"] == 1


async def test_merge_rejects_empty_input(foxit: FoxitPdfAdapter) -> None:
    with pytest.raises(ValueError):
        await foxit.merge([])


async def test_compress_and_convert(foxit: FoxitPdfAdapter) -> None:
    assert (await foxit.compress(minimal_pdf(["x"]))).startswith(b"%PDF")
    assert (await foxit.convert_to_pdf(b"docx-bytes", "consent.docx")).startswith(b"%PDF")
    with pytest.raises(ValueError):
        await foxit.convert_to_pdf(b"?", "notes.xyz")


async def test_ocr_default_and_adversarial(foxit: FoxitPdfAdapter, ledger: LocalLedger) -> None:
    clean = await foxit.ocr(minimal_pdf(["scan"]))
    adversarial = await foxit.ocr(minimal_pdf(["scan"]), variant="adversarial")

    assert "Camille Roux" in clean.text
    assert "Ignore previous instructions" in adversarial.text
    assert clean.pdf.startswith(b"%PDF")
    assert _tool_events(ledger)[-1]["tool"] == TOOL_OCR
