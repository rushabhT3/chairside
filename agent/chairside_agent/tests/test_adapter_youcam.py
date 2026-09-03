import pytest

from chairside_agent.adapters.youcam import (
    TOOL_HAIR_COLOR,
    TOOL_SKIN_ANALYSIS,
    YouCamAdapter,
    undertone_from_hex,
)
from chairside_agent.core.models import SKIN_CONCERNS
from chairside_agent.events import EventType, EventWriter, LocalLedger

SELFIE = "https://fixtures.chairside.local/uploads/scan-camille-01.jpg"


@pytest.fixture
def youcam(settings, events: EventWriter) -> YouCamAdapter:
    return YouCamAdapter(settings, events)


def _tool_events(ledger: LocalLedger) -> list[dict]:
    return [e.payload for e in ledger.read_events() if e.type == EventType.TOOL_CALLED]


async def test_list_tools_reports_both_servers(youcam: YouCamAdapter, ledger: LocalLedger) -> None:
    tools = await youcam.list_tools()

    assert TOOL_SKIN_ANALYSIS in tools
    assert "AI_Clothes_Virtual_Try_On" in tools
    assert {e["server"] for e in _tool_events(ledger)} == {"mcp/beauty", "mcp/fashion"}


async def test_color_tones_parses_hex_and_undertone(
    youcam: YouCamAdapter, ledger: LocalLedger
) -> None:
    tones = await youcam.color_tones(SELFIE)

    assert tones.skin_tone == "#C9A27E"
    assert tones.undertone == "warm"
    assert tones.hair_color_hex == "#42280E"
    last = _tool_events(ledger)[-1]
    assert last["server"] == "mcp/beauty"
    assert last["units"] == 20


async def test_skin_hd_has_all_fourteen_concerns_as_ints(youcam: YouCamAdapter) -> None:
    scores = await youcam.skin_hd(SELFIE)

    assert set(scores.scores) == set(SKIN_CONCERNS)
    assert all(isinstance(v, int) and 0 <= v <= 100 for v in scores.scores.values())
    assert scores.scores["oiliness"] == 45
    assert scores.scores["moisture"] == 48


async def test_hair_diagnostics_combines_three_tools(
    youcam: YouCamAdapter, ledger: LocalLedger
) -> None:
    hair = await youcam.hair_diagnostics(SELFIE)

    assert hair.type == "curly"
    assert hair.density == "medium"
    assert hair.frizz == 67
    assert [e["tool"] for e in _tool_events(ledger)][-3:] == [
        "AI_Hair_Type_Detection",
        "AI_Hair_Density_Detection",
        "AI_Hair_Frizziness_Detection",
    ]


async def test_face_attributes_maps_shape(youcam: YouCamAdapter) -> None:
    face = await youcam.face_attributes(SELFIE)

    assert face.shape == "oval"
    assert face.ratios["face_aspect_pct"] == 142


async def test_hair_color_render_carries_tool_server_and_time(youcam: YouCamAdapter) -> None:
    render = await youcam.hair_color_tryon(SELFIE, "#a8804f")

    assert render.image_url.endswith("hair-color-7.31.jpg")
    assert render.tool == TOOL_HAIR_COLOR
    assert render.server == "mcp/beauty"
    assert render.as_of


async def test_other_renders(youcam: YouCamAdapter) -> None:
    assert (await youcam.hairstyle_tryon(SELFIE, "oval_long_layers")).image_url.endswith(
        "long-layers.jpg"
    )
    assert (await youcam.bangs_tryon(SELFIE, "curtain")).image_url.endswith("bangs-curtain.jpg")
    assert (await youcam.hair_volume_tryon(SELFIE, "medium")).image_url.endswith(
        "volume-medium.jpg"
    )
    assert (await youcam.skin_simulation(SELFIE, "brightening")).image_url.endswith(
        "brightening.jpg"
    )


async def test_aging_picks_closest_age(youcam: YouCamAdapter) -> None:
    render = await youcam.aging_simulation(SELFIE, 20)

    assert render.image_url.endswith("aging-50.jpg")


async def test_unknown_treatment_fails_fast(youcam: YouCamAdapter) -> None:
    with pytest.raises(ValueError):
        await youcam.skin_simulation(SELFIE, "lasers")


def test_undertone_is_deterministic() -> None:
    assert undertone_from_hex("#C9A27E") == "warm"
    assert undertone_from_hex("#B9A8A0") == "cool"
    assert undertone_from_hex("#B49A80") == "neutral"
