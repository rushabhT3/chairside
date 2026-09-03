from __future__ import annotations

import os
from pathlib import Path

import pytest

from chairside_agent.agents.runtime import Runtime, build_runtime
from chairside_agent.config import Settings
from chairside_agent.events import EventWriter, LocalLedger

SALON_ID = "salon-atelier-noor"
DEMO_PROMPT = (
    "Open Chairside for Atelier Noor, 14 Rue de Turenne, 75003 Paris. Hair, skin, brows. "
    "Three chairs. Owner: Noor Haddad, noor@example.com."
)


def fixtures_settings(state_dir: Path) -> Settings:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CHAIRSIDE_")}
    env["CHAIRSIDE_MODE"] = "fixtures"
    env["CHAIRSIDE_STATE_DIR"] = str(state_dir)
    return Settings.from_env(env)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return fixtures_settings(tmp_path / "state")


@pytest.fixture
def ledger(settings: Settings) -> LocalLedger:
    return LocalLedger(settings.state_dir)


@pytest.fixture
def events(ledger: LocalLedger) -> EventWriter:
    return EventWriter(ledger, salon_id=SALON_ID)


@pytest.fixture
async def rt(settings: Settings) -> Runtime:
    runtime = build_runtime(settings, printer=None)
    yield runtime
    await runtime.aclose()
