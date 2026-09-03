import json

import pytest

from chairside_agent.adapters.doctavian import DoctavianAdapter, cassette_variant
from chairside_agent.config import REPO_DIR
from chairside_agent.events import EventType, LocalLedger


@pytest.fixture
def doctavian(settings, events) -> DoctavianAdapter:
    return DoctavianAdapter(settings, events)


def test_variant_strips_fixture_prefix() -> None:
    assert cassette_variant("tpl_fixture_consent_chemical") == "consent_chemical"
    assert cassette_variant("tpl_Consent Combined") == "consent_combined"


async def test_generate_consent_returns_pdf(
    doctavian: DoctavianAdapter, ledger: LocalLedger
) -> None:
    doc = await doctavian.generate(
        "tpl_fixture_consent_chemical",
        {"treatment_classes": ["chemical"], "allergens": ["PPD"], "jurisdiction": "FR"},
    )

    assert doc.pdf.startswith(b"%PDF")
    assert doc.document_id
    assert doc.url.endswith("consent_chemical.pdf")
    last = [e for e in ledger.read_events() if e.type == EventType.TOOL_CALLED][-1]
    assert last.payload["server"] == "rest/doctavian"


async def test_every_seed_template_has_a_cassette(doctavian: DoctavianAdapter) -> None:
    templates = json.loads((REPO_DIR / "seed" / "doctavian_templates.json").read_text("utf-8"))
    ids: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        else:
            ids.add(str(node))

    walk(templates)
    for template_id in sorted(ids - {templates["client_terms"]}):
        assert (await doctavian.generate(template_id, {})).pdf.startswith(b"%PDF")


async def test_clickwrap(doctavian: DoctavianAdapter) -> None:
    accepted = await doctavian.clickwrap(
        "tpl_fixture_client_terms", {"client": {"name": "Camille"}}
    )

    assert accepted.acceptance_id == "cw-000001"
    assert accepted.url.startswith("https://")
