"""CLI: open | consult | replay | redteam esign | reset | seed."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from chairside_agent import redteam
from chairside_agent.agents.consultation import ConsultationAgent, ConsultOptions
from chairside_agent.agents.onboarding import OnboardingAgent
from chairside_agent.agents.runtime import Runtime, build_runtime, reset_state
from chairside_agent.config import Settings
from chairside_agent.replay import diff, project


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chairside_agent")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("open").add_argument("prompt")
    consult = sub.add_parser("consult")
    consult.add_argument("client_id")
    consult.add_argument("--chair", type=int, default=1)
    consult.add_argument("--stylist", default="")
    consult.add_argument("--faces", type=int, default=1, help="on-device face count from Mirror")
    consult.add_argument("--aging", action="store_true")
    consult.add_argument("--image-url")
    consult.add_argument("--bottle-url", default=ConsultOptions.bottle_url)
    consult.add_argument("--intake", type=Path)
    consult.add_argument("--visit", type=int)
    consult.add_argument(
        "--retain", action="store_true", help="client opted into progress tracking"
    )
    sub.add_parser("replay").add_argument("consultation_id")
    sub.add_parser("redteam").add_argument("target", choices=["esign"])
    sub.add_parser("reset")
    sub.add_parser("seed")
    return parser


async def _open(rt: Runtime, prompt: str) -> int:
    try:
        projection = await OnboardingAgent(rt).run(prompt)
    except Exception as exc:
        print(f"needs_attention: {type(exc).__name__}: {exc}")
        return 1
    print(f"open: https://{projection['domain']['name']}/ · {projection['catalog']['skus']} SKUs")
    return 0


async def _consult(rt: Runtime, args: argparse.Namespace) -> int:
    opts = ConsultOptions(
        client_id=args.client_id,
        chair=args.chair,
        stylist=args.stylist,
        face_count=args.faces,
        aging=args.aging,
        image_url=args.image_url,
        bottle_url=args.bottle_url,
        intake=args.intake,
        visit=args.visit,
        retained=args.retain,
    )
    p = await ConsultationAgent(rt).run(opts)
    total = (p.get("order") or {}).get("total_cents")
    money = f" · €{total / 100:.2f}" if total is not None else ""
    print(f"consultation {p['id']} → {p['state']}{money}")
    if p["state"] == "needs_attention":
        print(f"failing step: {p['failing_step']}")
        return 1
    return 0


def replay(rt: Runtime, consultation_id: str) -> int:
    stored = rt.projections.load(consultation_id)
    events = rt.ledger.read_events(consultation_id)
    delta = diff(stored, project(consultation_id, events))
    if delta:
        print(delta)
        return 1
    print(f"replay {consultation_id}: {len(events)} events fold to the stored projection")
    return 0


async def _seed(rt: Runtime) -> int:
    await rt.xano.upsert_skus(rt.seed.skus)
    await rt.xano.put_shade_map(rt.seed.shade_map)
    print(
        f"seeded {len(rt.seed.skus)} SKUs · {len(rt.seed.shade_map)} shades · "
        f"{len(rt.seed.clients)} clients"
    )
    return 0


async def _dispatch(args: argparse.Namespace, settings: Settings) -> int:
    if args.command == "reset":
        reset_state(settings)
        print(f"reset {settings.state_dir}")
        return 0
    rt = build_runtime(settings)
    try:
        if args.command == "open":
            return await _open(rt, args.prompt)
        if args.command == "consult":
            return await _consult(rt, args)
        if args.command == "replay":
            return replay(rt, args.consultation_id)
        if args.command == "seed":
            return await _seed(rt)
        status = await redteam.esign(rt)
        print(f"redteam esign: HTTP {status} — the agent process holds no eSign credential")
        return 0
    finally:
        await rt.aclose()


def run() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parser().parse_args()
    raise SystemExit(asyncio.run(_dispatch(args, Settings.from_env())))


if __name__ == "__main__":
    run()
