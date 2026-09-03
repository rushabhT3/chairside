import json
from pathlib import Path

from chairside_agent.core.models import ShadeEntry, Sku

SEED_DIR = Path(__file__).resolve().parents[3] / "seed"


def load_json(name: str):
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


def seed_catalog() -> list[Sku]:
    return [Sku.model_validate(row) for row in load_json("skus.json")]


def seed_shade_map() -> list[ShadeEntry]:
    return [ShadeEntry.model_validate(row) for row in load_json("shade_map.json")]


def seed_client(client_id: str) -> dict:
    return next(c for c in load_json("clients.json") if c["id"] == client_id)
