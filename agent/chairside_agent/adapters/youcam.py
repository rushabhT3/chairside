"""Perfect Corp YouCam via MCP (streamable HTTP) with the task-based REST API as fallback.

Tool names come from https://docs.perfectcorp.com/develop/mcp and are re-confirmed from each
server's tools/list at runtime; the beauty server hosts analysis, skin simulation, aging and
every hair tool, the fashion server hosts clothing and accessories. Routing therefore follows
what tools/list reports rather than a fixed table.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client
from pydantic import BaseModel

from chairside_agent.adapters.base import VendorAdapter
from chairside_agent.core.models import (
    INVERTED_CONCERNS,
    SKIN_CONCERNS,
    ColorTones,
    Density,
    FaceAttributes,
    FaceShape,
    HairDiagnostics,
    HairType,
    SkinScores,
    Undertone,
)

MCP_SERVERS: dict[str, str] = {
    "mcp/beauty": "https://mcp-api-01.makeupar.com/mcp/beauty",
    "mcp/fashion": "https://mcp-api-01.makeupar.com/mcp/fashion",
}
REST_BASE = "https://yce-api-01.makeupar.com"

TOOL_COLOR_TONES = "AI_Facial_Color_Tones_Analyzer"
TOOL_SKIN_ANALYSIS = "AI_Skin_Analysis"
TOOL_SKIN_SIMULATION = "AI_Skin_simulation"
TOOL_FACE_ATTRIBUTES = "AI_Face_Attributes_and_Ratio_Analyzer"
TOOL_AGING = "AI_Aging_Simulation"
TOOL_HAIR_TYPE = "AI_Hair_Type_Detection"
TOOL_HAIR_DENSITY = "AI_Hair_Density_Detection"
TOOL_HAIR_FRIZZ = "AI_Hair_Frizziness_Detection"
TOOL_HAIR_COLOR = "AI_Hair_Color_Virtual_Try_On"
TOOL_HAIRSTYLE = "AI_Hair_Style_Virtual_Try_On"
TOOL_BANGS = "AI_Bangs_Filter_Virtual_Try_On"
TOOL_HAIR_VOLUME = "AI_Hair_Volume_Virtual_Try_On"

REST_FEATURE: dict[str, tuple[str, str]] = {
    TOOL_COLOR_TONES: ("v2.0", "skin-tone-analysis"),
    TOOL_SKIN_ANALYSIS: ("v2.1", "skin-analysis"),
    TOOL_SKIN_SIMULATION: ("v2.0", "skin-simulation"),
    TOOL_FACE_ATTRIBUTES: ("v2.0", "face-attr-analysis"),
    TOOL_AGING: ("v2.0", "aging"),
    TOOL_HAIR_TYPE: ("v2.0", "hair-type-detection"),
    TOOL_HAIR_DENSITY: ("v2.0", "hair-density-detection"),
    TOOL_HAIR_FRIZZ: ("v2.0", "hair-frizziness-detection"),
    TOOL_HAIR_COLOR: ("v2.0", "hair-color"),
    TOOL_HAIRSTYLE: ("v2.1", "hair-transfer"),
    TOOL_BANGS: ("v2.0", "hair-bang"),
    TOOL_HAIR_VOLUME: ("v2.0", "hair-vol"),
}

FACE_FEATURES: tuple[str, ...] = ("faceShape", "horizontalThird", "faceAspectRatio")

HD_ACTIONS: tuple[str, ...] = tuple(f"hd_{c}" for c in SKIN_CONCERNS if c != "spot") + (
    "hd_age_spot",
)
HD_TYPE_TO_CONCERN: dict[str, str] = {f"hd_{c}": c for c in SKIN_CONCERNS} | {"hd_age_spot": "spot"}

SKIN_TREATMENTS: dict[str, dict[str, float]] = {
    "brightening": {"radiance": 1.0, "spots": 0.8},
    "resurfacing": {"texture": 1.0, "pores": 0.8},
    "calming": {"redness": 1.0},
    "anti_aging": {"wrinkle": 1.0},
    "eye_refresh": {"dark_circle": 1.0, "eye_bag": 1.0},
    "clarifying": {"oiliness": 1.0, "pores": 0.6},
}

FACE_SHAPE_MAP: dict[str, FaceShape] = {
    "Oval": "oval",
    "Round": "round",
    "Square": "square",
    "Heart": "heart",
    "Oblong": "oblong",
    "Diamond": "diamond",
    "Triangle": "square",
    "InvTriangle": "heart",
    "Unknown": "oval",
}
HAIR_TYPE_MAP: dict[str, HairType] = {
    "1 to 2a": "straight",
    "2a to 2b": "wavy",
    "2b to 2c": "wavy",
    "2c to 3a": "wavy",
    "3a to 3b": "curly",
    "3b to 3c": "curly",
    "3c to 4a": "curly",
    "4a to 4b": "coily",
    "4b to 4c": "coily",
}
DENSITY_MAP: dict[str, Density] = {
    "Extremely Low Density": "low",
    "Low Density": "low",
    "Medium Density": "medium",
    "High Density": "high",
}
FRIZZ_SCORE: dict[int, int] = {0: 0, 1: 33, 2: 67, 3: 100}

POLL_INITIAL_SECONDS = 1.0
POLL_MAX_SECONDS = 8.0
POLL_ATTEMPTS = 40


class RenderResult(BaseModel):
    image_url: str
    tool: str
    server: str
    as_of: str


class YouCamError(RuntimeError):
    pass


def undertone_from_hex(skin_hex: str) -> Undertone:
    value = skin_hex.lstrip("#")
    r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    warmth = (r - b) - (g - b) // 2
    if warmth > 40:
        return "warm"
    if warmth < 25:
        return "cool"
    return "neutral"


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def _mcp_payload(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structured_content", None)
    if structured:
        return structured
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            return json.loads(text)
    raise YouCamError("MCP tool returned no JSON payload")


def _results(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", payload)
    if data.get("task_status", "success") == "error":
        raise YouCamError(data.get("error_message") or data.get("error") or "task failed")
    return data.get("results", data)


def _first_url(results: dict[str, Any]) -> str:
    if isinstance(results.get("url"), str):
        return results["url"]
    output = results.get("output") or results.get("results") or []
    if isinstance(output, dict) and isinstance(output.get("url"), str):
        return output["url"]
    if isinstance(output, list) and output and isinstance(output[0].get("url"), str):
        return output[0]["url"]
    raise YouCamError("render result carries no image url")


def parse_color_tones(payload: dict[str, Any]) -> ColorTones:
    color = _results(payload)["color"]
    return ColorTones(
        skin_tone=color["skin_color"],
        undertone=undertone_from_hex(color["skin_color"]),
        eye_color=color.get("eye_color_name") or color["eye_color"],
        hair_color_hex=color.get("hair_color") or color["eyebrow_color"],
    )


def parse_skin_scores(payload: dict[str, Any]) -> SkinScores:
    scores = dict.fromkeys(SKIN_CONCERNS, 0)
    for row in _results(payload)["output"]:
        concern = HD_TYPE_TO_CONCERN.get(row.get("type", ""))
        if concern is None or row.get("region", "whole") != "whole":
            continue
        healthy = _clamp(row["ui_score"])
        scores[concern] = healthy if concern in INVERTED_CONCERNS else 100 - healthy
    return SkinScores(scores=scores)


def parse_face_attributes(payload: dict[str, Any]) -> FaceAttributes:
    results = _results(payload)
    ratio = results.get("facialratio", {})
    ratios: dict[str, int] = {}
    thirds = ratio.get("horizontal_third")
    if thirds:
        ratios["third_top"], ratios["third_mid"], ratios["third_bottom"] = (
            _clamp(v) for v in thirds
        )
    aspect = ratio.get("face_aspect_ratio")
    if aspect:
        ratios["face_aspect_pct"] = round(aspect[1] * 100)
    return FaceAttributes(shape=FACE_SHAPE_MAP[results["faceshape"]], ratios=ratios)


def parse_hair_diagnostics(
    type_payload: dict[str, Any], density_payload: dict[str, Any], frizz_payload: dict[str, Any]
) -> HairDiagnostics:
    mapping = _results(type_payload)["hair_type"]["mapping"]
    density_term = _results(density_payload)["hair_density"]["term"]
    frizz_level = int(_results(frizz_payload)["hair_frizziness"]["mapping"])
    return HairDiagnostics(
        type=HAIR_TYPE_MAP[mapping],
        frizz=FRIZZ_SCORE[frizz_level],
        density=DENSITY_MAP[density_term],
    )


def closest_aging_url(payload: dict[str, Any], years: int) -> str:
    results = _results(payload)
    target = int(results.get("age", 0)) + years
    outputs = results["output"]
    best = min(outputs, key=lambda o: abs(int(o["res_age"]) - target))
    return best["url"]


class YouCamAdapter(VendorAdapter):
    vendor = "youcam"
    server = "mcp/beauty"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._tools_by_server: dict[str, list[str]] | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.settings.perfectcorp_api_key}"}

    async def _with_session(
        self, server: str, fn: Callable[[ClientSession], Awaitable[Any]]
    ) -> Any:
        self.settings.require("perfectcorp_api_key")
        async with create_mcp_http_client(headers=self._headers()) as http:
            async with streamable_http_client(MCP_SERVERS[server], http_client=http) as (
                read,
                write,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await fn(session)

    async def _mcp_list(self, server: str) -> list[str]:
        async def run(session: ClientSession) -> list[str]:
            listed = await session.list_tools()
            return [tool.name for tool in listed.tools]

        return await self._with_session(server, run)

    async def _mcp_call(self, server: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        async def run(session: ClientSession) -> dict[str, Any]:
            return _mcp_payload(await session.call_tool(tool, args))

        return await self._with_session(server, run)

    async def _rest_task(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        version, feature = REST_FEATURE[tool]
        base = f"{REST_BASE}/s2s/{version}/task/{feature}"
        created = await self.http.post(base, json=payload, headers=self._headers())
        created.raise_for_status()
        task_id = created.json()["data"]["task_id"]
        delay = POLL_INITIAL_SECONDS
        for _ in range(POLL_ATTEMPTS):
            await asyncio.sleep(delay)
            polled = await self.http.get(f"{base}/{task_id}", headers=self._headers())
            polled.raise_for_status()
            body = polled.json()
            if body["data"]["task_status"] != "running":
                return body
            delay = min(delay * 2, POLL_MAX_SECONDS)
        raise YouCamError(f"task {task_id} still running after {POLL_ATTEMPTS} polls")

    async def _ensure_tools(self) -> dict[str, list[str]]:
        if self._tools_by_server is None:
            self._tools_by_server = {}
            for server in MCP_SERVERS:
                self._tools_by_server[server] = list(
                    (
                        await self.call(
                            "tools_list",
                            {"server": server},
                            lambda req: self._list_as_dict(req["server"]),
                            variant=server.split("/")[1],
                            units=0,
                            tool="tools/list",
                            server=server,
                        )
                    )["tools"]
                )
        return self._tools_by_server

    async def _list_as_dict(self, server: str) -> dict[str, Any]:
        return {"tools": await self._mcp_list(server)}

    def _server_for(self, tool: str) -> str | None:
        for server, tools in (self._tools_by_server or {}).items():
            if tool in tools:
                return server
        return None

    async def list_tools(self) -> list[str]:
        tools = await self._ensure_tools()
        return sorted({name for names in tools.values() for name in names})

    async def _invoke(
        self, primitive: str, tool: str, args: dict[str, Any], *, units: int, variant: str
    ) -> tuple[dict[str, Any], str]:
        await self._ensure_tools()
        server = self._server_for(tool)

        async def live(req: dict[str, Any]) -> dict[str, Any]:
            if server is not None:
                return await self._mcp_call(server, tool, req)
            return await self._rest_task(tool, req)

        label = server or "mcp/beauty"
        response = await self.call(
            primitive, args, live, variant=variant, units=units, tool=tool, server=label
        )
        return response, label

    async def color_tones(self, image_url: str, *, variant: str = "default") -> ColorTones:
        payload, _ = await self._invoke(
            "color_tones", TOOL_COLOR_TONES, {"src_file_url": image_url}, units=20, variant=variant
        )
        return parse_color_tones(payload)

    async def skin_hd(self, image_url: str, *, variant: str = "default") -> SkinScores:
        payload, _ = await self._invoke(
            "skin_hd",
            TOOL_SKIN_ANALYSIS,
            {"src_file_url": image_url, "dst_actions": list(HD_ACTIONS), "format": "json"},
            units=10,
            variant=variant,
        )
        return parse_skin_scores(payload)

    async def hair_diagnostics(
        self, image_url: str, *, variant: str = "default"
    ) -> HairDiagnostics:
        # Type and frizziness take front, right, and left views; one selfie stands in for all three.
        three_views = {"src_file_urls": [image_url, image_url, image_url]}
        hair_type, _ = await self._invoke(
            "hair_type", TOOL_HAIR_TYPE, three_views, units=2, variant=variant
        )
        density, _ = await self._invoke(
            "hair_density", TOOL_HAIR_DENSITY, {"src_file_url": image_url}, units=2, variant=variant
        )
        frizz, _ = await self._invoke(
            "hair_frizziness", TOOL_HAIR_FRIZZ, three_views, units=2, variant=variant
        )
        return parse_hair_diagnostics(hair_type, density, frizz)

    async def face_attributes(self, image_url: str, *, variant: str = "default") -> FaceAttributes:
        payload, _ = await self._invoke(
            "face_attributes",
            TOOL_FACE_ATTRIBUTES,
            {"src_file_url": image_url, "features": list(FACE_FEATURES)},
            units=20,
            variant=variant,
        )
        return parse_face_attributes(payload)

    async def _render(
        self,
        primitive: str,
        tool: str,
        args: dict[str, Any],
        *,
        units: int,
        variant: str,
        pick: Callable[[dict[str, Any]], str] | None = None,
    ) -> RenderResult:
        payload, server = await self._invoke(primitive, tool, args, units=units, variant=variant)
        url = pick(payload) if pick else _first_url(_results(payload))
        return RenderResult(
            image_url=url,
            tool=tool,
            server=server,
            as_of=datetime.now(UTC).isoformat(timespec="seconds"),
        )

    async def hair_color_tryon(
        self, image_url: str, hex: str, *, variant: str = "default"
    ) -> RenderResult:
        return await self._render(
            "hair_color",
            TOOL_HAIR_COLOR,
            {
                "src_file_url": image_url,
                "pattern": {"name": "full"},
                "palettes": [
                    {"color": hex.upper(), "color_intensity": 100, "shine_intensity": 100}
                ],
            },
            units=1,
            variant=variant,
        )

    async def hairstyle_tryon(
        self, image_url: str, style_id: str, *, variant: str = "default"
    ) -> RenderResult:
        return await self._render(
            "hairstyle",
            TOOL_HAIRSTYLE,
            {"src_file_url": image_url, "template_id": style_id},
            units=2,
            variant=variant,
        )

    async def bangs_tryon(
        self, image_url: str, bangs_id: str, *, variant: str = "default"
    ) -> RenderResult:
        return await self._render(
            "bangs",
            TOOL_BANGS,
            {"src_file_url": image_url, "template_id": bangs_id},
            units=1,
            variant=variant,
        )

    async def hair_volume_tryon(
        self, image_url: str, level: str, *, variant: str = "default"
    ) -> RenderResult:
        return await self._render(
            "hair_volume",
            TOOL_HAIR_VOLUME,
            {"src_file_url": image_url, "template_id": level},
            units=1,
            variant=variant,
        )

    async def skin_simulation(
        self, image_url: str, treatment: str, *, variant: str = "default"
    ) -> RenderResult:
        if treatment not in SKIN_TREATMENTS:
            raise ValueError(f"unknown skin treatment {treatment!r}")
        return await self._render(
            "skin_simulation",
            TOOL_SKIN_SIMULATION,
            {"src_file_url": image_url, **SKIN_TREATMENTS[treatment]},
            units=4,
            variant=variant,
        )

    async def aging_simulation(
        self, image_url: str, years: int, *, variant: str = "default"
    ) -> RenderResult:
        return await self._render(
            "aging",
            TOOL_AGING,
            {"src_file_url": image_url},
            units=2,
            variant=variant,
            pick=lambda payload: closest_aging_url(payload, years),
        )
