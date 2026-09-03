"""The LLM narrates; code decides.

`narrate()` turns a deterministic Plan into one paragraph in the stylist's voice. In fixtures
mode, or when no model key is configured, it is a template over `plan.facts` and makes no call.
In live mode it runs a google-adk 2.8 `LlmAgent` whose instruction forbids adding facts.

`build_agent()` is the live tool-using agent: `MCPToolset` mounts for the Foxit PDF MCP server
(stdio) and both YouCam MCP servers (streamable HTTP), plus `FunctionTool`s over the
deterministic core so the model can only *ask* for a plan, never invent one. The state machines
in `agents/` drive the fixed call order; this agent is what the ADK web UI and the live film use.
"""

from __future__ import annotations

from typing import Any

from chairside_agent.config import Settings
from chairside_agent.core.models import Plan

GEMINI_MODEL = "gemini-2.5-flash"
ANTHROPIC_MODEL = "anthropic/claude-sonnet-5"
APP_NAME = "chairside"

NARRATOR_INSTRUCTION = (
    "You are a senior stylist speaking to a client at the chair. Rewrite the facts you are given "
    "into one warm paragraph of at most four sentences. Use only the facts provided. Do not add "
    "products, services, prices, timings, or claims. Say 'readings' and 'concerns', never "
    "'diagnosis'."
)


def _facts_block(plan: Plan, scan: dict[str, Any]) -> str:
    tones = scan.get("color_tones") or {}
    lines = [f"- {fact}" for fact in plan.facts]
    if tones:
        lines.append(f"- Undertone reads {tones.get('undertone')} on {tones.get('skin_tone')} skin")
    lines.append(f"- Plan total €{plan.total_cents / 100:.2f}; return in {plan.rebook_weeks} weeks")
    return "\n".join(lines)


def template_narration(plan: Plan, scan: dict[str, Any]) -> str:
    tones = scan.get("color_tones") or {}
    opener = (
        f"Your undertone reads {tones['undertone']} today, so we work with it, not against it. "
        if tones
        else ""
    )
    facts = " ".join(f.rstrip(".") + "." for f in plan.facts[:4])
    closer = f" We'll see you again in about {plan.rebook_weeks} weeks to check the readings."
    return f"{opener}{facts}{closer}"


def _has_model_key(settings: Settings) -> bool:
    key = (
        settings.gemini_api_key if settings.llm_provider == "gemini" else settings.anthropic_api_key
    )
    return bool(key)


def _model(settings: Settings) -> Any:
    if settings.llm_provider == "gemini":
        return GEMINI_MODEL
    from google.adk.models.lite_llm import LiteLlm

    return LiteLlm(model=ANTHROPIC_MODEL)


async def narrate(settings: Settings, plan: Plan, scan: dict[str, Any]) -> str:
    if not settings.is_live or not _has_model_key(settings):
        return template_narration(plan, scan)
    return await _narrate_live(settings, _facts_block(plan, scan))


async def _narrate_live(settings: Settings, facts: str) -> str:
    from google.adk.agents import LlmAgent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    agent = LlmAgent(name="narrator", model=_model(settings), instruction=NARRATOR_INSTRUCTION)
    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session = await runner.session_service.create_session(app_name=APP_NAME, user_id="stylist")
    message = types.Content(role="user", parts=[types.Part(text=facts)])
    text = ""
    async for event in runner.run_async(
        user_id="stylist", session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            text = "".join(part.text or "" for part in event.content.parts)
    return text or facts


def build_agent(settings: Settings) -> Any:
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
    from google.adk.tools.mcp_tool import (
        MCPToolset,
        StdioConnectionParams,
        StreamableHTTPConnectionParams,
    )
    from mcp import StdioServerParameters

    from chairside_agent.core.consent_template_select import consent_template_select
    from chairside_agent.core.price_policy import price_policy
    from chairside_agent.core.recommend_plan import recommend_plan
    from chairside_agent.core.sku_shade_map import sku_shade_map

    settings.require("perfectcorp_api_key", "foxit_client_id", "foxit_client_secret")
    youcam_headers = {"Authorization": f"Bearer {settings.perfectcorp_api_key}"}
    foxit_env = {
        "FOXIT_CLOUD_API_HOST": settings.foxit_host,
        "FOXIT_CLOUD_API_CLIENT_ID": settings.foxit_client_id,
        "FOXIT_CLOUD_API_CLIENT_SECRET": settings.foxit_client_secret,
    }
    tools = [
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url="https://mcp-api-01.makeupar.com/mcp/beauty", headers=youcam_headers
            ),
            tool_name_prefix="beauty",
        ),
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url="https://mcp-api-01.makeupar.com/mcp/fashion", headers=youcam_headers
            ),
            tool_name_prefix="fashion",
        ),
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="uvx", args=["foxit-pdf-api-mcp-server"], env=foxit_env
                )
            ),
            tool_name_prefix="foxit",
        ),
        FunctionTool(recommend_plan),
        FunctionTool(price_policy),
        FunctionTool(consent_template_select),
        FunctionTool(sku_shade_map),
    ]
    return LlmAgent(
        name="chairside",
        model=_model(settings),
        instruction=(
            "You run salon consultations. Diagnose and simulate with the beauty and fashion tools, "
            "prepare documents with the foxit tools, and ask the plan/price/consent functions for "
            "every decision. You have no signing tool: a person signs."
        ),
        tools=tools,
    )
