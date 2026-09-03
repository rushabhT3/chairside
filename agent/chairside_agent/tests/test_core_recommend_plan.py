from chairside_agent.core.models import FaceAttributes, HairDiagnostics, SkinScores, Sku
from chairside_agent.core.recommend_plan import (
    BRIGHTENING_SERVICE,
    INJECTABLE_SERVICE,
    LASER_SERVICE,
    recommend_plan,
)
from chairside_agent.tests.seed_helpers import seed_catalog, seed_client

CALM_SKIN = SkinScores(
    scores={
        "wrinkle": 20,
        "spot": 20,
        "pore": 20,
        "texture": 20,
        "acne": 20,
        "redness": 20,
        "oiliness": 20,
        "dark_circle": 20,
        "eye_bag": 20,
        "droopy_upper_eyelid": 20,
        "droopy_lower_eyelid": 20,
        "firmness": 70,
        "radiance": 70,
        "moisture": 70,
    }
)
TAME_HAIR = HairDiagnostics(type="straight", frizz=10, density="medium")
OVAL = FaceAttributes(shape="oval", ratios={})


def _skin(**overrides: int) -> SkinScores:
    return SkinScores(scores={**CALM_SKIN.scores, **overrides})


def _amira_inputs() -> tuple[SkinScores, HairDiagnostics, FaceAttributes]:
    visit = seed_client("cl-01")["visits"][0]
    return (
        SkinScores(scores=visit["skin"]),
        HairDiagnostics.model_validate(visit["hair"]),
        FaceAttributes.model_validate(visit["face"]),
    )


def test_demo_client_plan_products_total_147_eur() -> None:
    skin, hair, face = _amira_inputs()

    plan = recommend_plan(skin, hair, face, seed_catalog())

    assert sum(p.price_cents * p.qty for p in plan.products) == 14700
    assert plan.treatment_classes == ["chemical", "heat"]
    assert plan.rebook_weeks == 6


def test_calm_client_gets_colour_only_and_six_week_rebook() -> None:
    plan = recommend_plan(CALM_SKIN, TAME_HAIR, OVAL, seed_catalog())

    assert [s.code for s in plan.services] == ["SVC-COLOR"]
    assert [p.code for p in plan.products] == ["OLX-03"]
    assert plan.treatment_classes == ["chemical"]
    assert plan.rebook_weeks == 6
    assert plan.total_cents == 8500 + 2800


def test_low_density_adds_volume_cut_and_product() -> None:
    hair = HairDiagnostics(type="straight", frizz=10, density="low")

    plan = recommend_plan(CALM_SKIN, hair, OVAL, seed_catalog())

    assert "SVC-VOLCUT" in [s.code for s in plan.services]
    assert "KER-VOL" in [p.code for p in plan.products]


def test_coily_hair_adds_curl_care_product() -> None:
    hair = HairDiagnostics(type="coily", frizz=10, density="high")

    plan = recommend_plan(CALM_SKIN, hair, OVAL, seed_catalog())

    assert "KER-CURL" in [p.code for p in plan.products]


def test_missing_catalog_item_is_skipped_and_explained() -> None:
    catalog = [s for s in seed_catalog() if s.code != "SVC-SMOOTH"]
    hair = HairDiagnostics(type="wavy", frizz=80, density="medium")

    plan = recommend_plan(CALM_SKIN, hair, OVAL, catalog)

    assert "SVC-SMOOTH" not in [s.code for s in plan.services]
    assert any("not carried: SVC-SMOOTH" in f for f in plan.facts)


def test_spot_reading_uses_laser_when_salon_carries_it() -> None:
    plan = recommend_plan(_skin(spot=70), TAME_HAIR, OVAL, seed_catalog())

    assert LASER_SERVICE in [s.code for s in plan.services]
    assert "laser" in plan.treatment_classes


def test_spot_reading_falls_back_to_brightening_without_laser() -> None:
    catalog = [s for s in seed_catalog() if s.code != LASER_SERVICE]

    plan = recommend_plan(_skin(spot=70), TAME_HAIR, OVAL, catalog)

    codes = [s.code for s in plan.services]
    assert BRIGHTENING_SERVICE in codes
    assert LASER_SERVICE not in codes
    assert "laser" not in plan.treatment_classes


def test_injectable_never_appears_without_catalog_code() -> None:
    plan = recommend_plan(_skin(wrinkle=75, firmness=30), TAME_HAIR, OVAL, seed_catalog())

    assert "injectable" not in plan.treatment_classes


def test_injectable_appears_only_when_catalog_carries_it() -> None:
    injectable = Sku(
        code=INJECTABLE_SERVICE,
        name="Injectable consult",
        brand="Atelier Noor",
        salon_price_cents=15000,
        kind="service",
    )

    plan = recommend_plan(
        _skin(wrinkle=75, firmness=30), TAME_HAIR, OVAL, [*seed_catalog(), injectable]
    )

    assert "injectable" in plan.treatment_classes
    assert plan.treatment_classes == ["chemical", "heat", "injectable"]


def test_products_only_plan_rebooks_in_eight_weeks() -> None:
    catalog = [s for s in seed_catalog() if s.kind != "service"]
    hair = HairDiagnostics(type="curly", frizz=10, density="medium")

    plan = recommend_plan(CALM_SKIN, hair, OVAL, catalog)

    assert plan.services == []
    assert plan.rebook_weeks == 8
    assert plan.treatment_classes == ["none"]


def test_redness_adds_soothing_facial_and_barrier_product() -> None:
    plan = recommend_plan(_skin(redness=65), TAME_HAIR, OVAL, seed_catalog())

    assert "SVC-SOOTHE" in [s.code for s in plan.services]
    assert "LRP-CICA" in [p.code for p in plan.products]


def test_face_shape_fact_present() -> None:
    plan = recommend_plan(CALM_SKIN, TAME_HAIR, FaceAttributes(shape="round"), seed_catalog())

    assert any(f.startswith("Round face") for f in plan.facts)


def test_same_input_gives_identical_plan() -> None:
    skin, hair, face = _amira_inputs()

    first = recommend_plan(skin, hair, face, seed_catalog())
    second = recommend_plan(skin, hair, face, seed_catalog())

    assert first == second
