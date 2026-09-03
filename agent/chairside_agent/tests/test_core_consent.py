import pytest

from chairside_agent.core.consent_template_select import (
    MissingTemplateError,
    NoConsentRequiredError,
    UnknownJurisdictionError,
    consent_template_select,
)
from chairside_agent.core.models import Plan
from chairside_agent.tests.seed_helpers import load_json

SALON = {"name": "Atelier Noor", "address": "14 Rue de Turenne, 75003 Paris", "chairs": 3}
CLIENT = {"name": "Amira Benali", "email": "amira.benali@example.com"}


def _plan(*classes: str) -> Plan:
    return Plan(
        treatment_classes=list(classes),
        services=[],
        products=[],
        total_cents=0,
        rebook_weeks=6,
        facts=[],
    )


def _templates() -> dict:
    return load_json("doctavian_templates.json")


def test_single_class_selects_that_template() -> None:
    selection = consent_template_select(_plan("chemical"), [], "FR", SALON, CLIENT, _templates())

    assert selection.template_id == "tpl_fixture_consent_chemical"
    assert selection.variables["treatment_classes"] == ["chemical"]


def test_two_classes_select_combined_template() -> None:
    selection = consent_template_select(
        _plan("heat", "chemical"), [], "FR", SALON, CLIENT, _templates()
    )

    assert selection.template_id == "tpl_fixture_consent_combined"
    assert selection.variables["treatment_classes"] == ["chemical", "heat"]


def test_none_class_is_ignored_for_selection() -> None:
    selection = consent_template_select(
        _plan("laser", "none"), [], "US", SALON, CLIENT, _templates()
    )

    assert selection.template_id == "tpl_fixture_consent_laser"


def test_plan_without_consenting_class_raises() -> None:
    with pytest.raises(NoConsentRequiredError):
        consent_template_select(_plan("none"), [], "FR", SALON, CLIENT, _templates())


def test_unknown_jurisdiction_raises() -> None:
    with pytest.raises(UnknownJurisdictionError):
        consent_template_select(_plan("chemical"), [], "DE", SALON, CLIENT, _templates())


def test_allergens_are_deduped_sorted_and_lowercased() -> None:
    selection = consent_template_select(
        _plan("chemical"), ["PPD", " nickel", "ppd", ""], "FR", SALON, CLIENT, _templates()
    )

    assert selection.variables["allergens"] == ["nickel", "ppd"]


def test_variables_carry_salon_identity_and_client_name_only() -> None:
    selection = consent_template_select(_plan("chemical"), [], "FR", SALON, CLIENT, _templates())

    assert selection.variables["salon"] == {"name": SALON["name"], "address": SALON["address"]}
    assert selection.variables["client"] == {"name": "Amira Benali"}
    assert selection.variables["jurisdiction"] == "FR"


def test_missing_template_raises() -> None:
    with pytest.raises(MissingTemplateError):
        consent_template_select(_plan("chemical"), [], "FR", SALON, CLIENT, {"consent": {}})
