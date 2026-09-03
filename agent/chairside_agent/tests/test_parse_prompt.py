import pytest

from chairside_agent.agents.onboarding import PromptParseError, parse_prompt
from chairside_agent.tests.conftest import DEMO_PROMPT


def test_parses_demo_prompt() -> None:
    req = parse_prompt(DEMO_PROMPT)
    assert req.salon_name == "Atelier Noor"
    assert req.address == "14 Rue de Turenne"
    assert req.postcode == "75003"
    assert req.city == "Paris"
    assert req.services == ["hair", "skin", "brows"]
    assert req.chairs == 3
    assert req.owner_name == "Noor Haddad"
    assert req.owner_email == "noor@example.com"
    assert req.slug == "ateliernoor"


def test_accepts_digits_and_conjunctions() -> None:
    req = parse_prompt(
        "Open Chairside for Salon Marc, 2 Rue Oberkampf, 75011 Paris. Hair and brows. "
        "2 chairs. Owner: Marc Dupont, marc@example.com"
    )
    assert req.chairs == 2
    assert req.services == ["hair", "brows"]


def test_rejects_prompt_without_owner() -> None:
    with pytest.raises(PromptParseError):
        parse_prompt("Open Chairside for X, 1 Rue Y, 75001 Paris. Hair. Two chairs.")


def test_rejects_bad_chair_count() -> None:
    with pytest.raises(PromptParseError):
        parse_prompt(DEMO_PROMPT.replace("Three chairs", "Several chairs"))


def test_rejects_bad_email() -> None:
    with pytest.raises(ValueError):
        parse_prompt(DEMO_PROMPT.replace("noor@example.com", "noor-at-example"))
