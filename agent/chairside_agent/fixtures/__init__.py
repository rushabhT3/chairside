"""Recorded vendor responses. One JSON cassette per (vendor, primitive, variant)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class CassetteMissingError(FileNotFoundError):
    pass


class Cassette(BaseModel):
    vendor: str
    primitive: str
    variant: str = "default"
    recorded_at: str
    request: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
    units: int = 1
    latency_ms: int = 0


def cassette_path(fixtures_dir: Path, vendor: str, primitive: str, variant: str) -> Path:
    name = primitive if variant == "default" else f"{primitive}.{variant}"
    return fixtures_dir / vendor / f"{name}.json"


def load(fixtures_dir: Path, vendor: str, primitive: str, variant: str = "default") -> Cassette:
    path = cassette_path(fixtures_dir, vendor, primitive, variant)
    if not path.exists():
        raise CassetteMissingError(
            f"no cassette for {vendor}/{primitive}[{variant}] at {path}; "
            "run scripts/record_fixtures.py with RECORD=1 in live mode"
        )
    return Cassette.model_validate_json(path.read_text(encoding="utf-8"))


def save(fixtures_dir: Path, cassette: Cassette) -> Path:
    path = cassette_path(fixtures_dir, cassette.vendor, cassette.primitive, cassette.variant)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cassette.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path
