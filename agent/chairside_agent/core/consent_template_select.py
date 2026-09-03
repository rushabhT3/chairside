from __future__ import annotations

from typing import Any

from chairside_agent.core.models import ConsentSelection, Plan

JURISDICTIONS = frozenset({"FR", "US"})
COMBINED_TEMPLATE_KEY = "combined"


class NoConsentRequiredError(ValueError):
    pass


class UnknownJurisdictionError(ValueError):
    pass


class MissingTemplateError(KeyError):
    pass


def _consenting_classes(plan: Plan) -> list[str]:
    return sorted({cls for cls in plan.treatment_classes if cls != "none"})


def _template_id(classes: list[str], templates: dict[str, Any]) -> str:
    key = classes[0] if len(classes) == 1 else COMBINED_TEMPLATE_KEY
    try:
        return templates["consent"][key]
    except KeyError as exc:
        raise MissingTemplateError(f"no consent template for {key}") from exc


def consent_template_select(
    plan: Plan,
    allergens: list[str],
    jurisdiction: str,
    salon: dict[str, Any],
    client: dict[str, Any],
    templates: dict[str, Any],
) -> ConsentSelection:
    classes = _consenting_classes(plan)
    if not classes:
        raise NoConsentRequiredError("plan has no treatment class that needs consent")
    if jurisdiction not in JURISDICTIONS:
        raise UnknownJurisdictionError(f"jurisdiction must be FR or US, got {jurisdiction!r}")
    return ConsentSelection(
        template_id=_template_id(classes, templates),
        variables={
            "treatment_classes": classes,
            "allergens": sorted({a.strip().lower() for a in allergens if a.strip()}),
            "jurisdiction": jurisdiction,
            "salon": {"name": salon["name"], "address": salon["address"]},
            "client": {"name": client["name"]},
        },
    )
