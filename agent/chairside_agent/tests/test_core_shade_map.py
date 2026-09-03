import pytest

from chairside_agent.core.models import Sku
from chairside_agent.core.sku_shade_map import UnknownShadeError, shade_for_sku, sku_shade_map
from chairside_agent.tests.seed_helpers import load_json, seed_catalog, seed_shade_map


def test_known_code_returns_entry() -> None:
    entry = sku_shade_map("7.31", seed_shade_map())

    assert entry.name == "Medium Blonde Gold Ash"
    assert entry.hex == "#A88A5F"
    assert entry.level == 7


def test_unknown_code_raises_with_code() -> None:
    with pytest.raises(UnknownShadeError) as excinfo:
        sku_shade_map("99.99", seed_shade_map())

    assert excinfo.value.shade_code == "99.99"


def test_shade_for_sku_resolves_backbar_tube() -> None:
    sku = next(s for s in seed_catalog() if s.code == "MAJ-7.31")

    entry = shade_for_sku(sku, seed_shade_map())

    assert entry.code == "7.31"


def test_shade_for_sku_without_shade_raises() -> None:
    sku = Sku(code="OLX-03", name="Olaplex No. 3", brand="Olaplex", salon_price_cents=2800)

    with pytest.raises(UnknownShadeError):
        shade_for_sku(sku, seed_shade_map())


def test_seed_catalog_has_42_unique_skus() -> None:
    catalog = seed_catalog()

    assert len(catalog) == 42
    assert len({s.code for s in catalog}) == 42


def test_every_sku_shade_code_exists_in_shade_map() -> None:
    shade_map = seed_shade_map()

    for sku in seed_catalog():
        if sku.shade_code is not None:
            assert sku_shade_map(sku.shade_code, shade_map).code == sku.shade_code


def test_shade_map_levels_match_code_integer_part() -> None:
    shade_map = seed_shade_map()

    assert len(shade_map) >= 16
    assert len({e.code for e in shade_map}) == len(shade_map)
    for entry in shade_map:
        assert entry.level == int(entry.code.split(".")[0])


def test_seed_json_files_parse_with_expected_shapes() -> None:
    salon = load_json("salon.json")
    clients = load_json("clients.json")
    templates = load_json("doctavian_templates.json")

    assert salon["name"] == "Atelier Noor" and salon["domain"] == "ateliernoor.com"
    assert len(clients) == 12 and all(len(c["visits"]) == 2 for c in clients)
    assert all(len(v["skin"]) == 14 for c in clients for v in c["visits"])
    assert set(templates["consent"]) == {"chemical", "heat", "injectable", "laser", "combined"}
