"""Units per consultation, per onboarding, and the weekly refresh, from the local ledger.

Run from agent/: `uv run python ../scripts/cost_report.py`. Writes docs/cost-report.md.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVER_VENDOR = {
    "mcp/beauty": ("Perfect Corp", "YouCam unit"),
    "mcp/fashion": ("Perfect Corp", "YouCam unit"),
    "mcp/foxit": ("Foxit", "credit"),
    "rest/serpapi": ("SerpApi", "search"),
    "rest/namecom": ("name.com", "call"),
    "rest/doctavian": ("Doctavian", "generation"),
    "rest/nutrient": ("Nutrient", "operation"),
    "rest/xano": ("Xano", "request"),
    "commit/xano": ("Xano", "request"),
}


def load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def tool_calls(events: list[dict]) -> list[dict]:
    return [e for e in events if e["type"] == "tool.called"]


def units_by_server(calls: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(lambda: {"calls": 0, "units": 0})
    for call in calls:
        server = call["payload"]["server"]
        out[server]["calls"] += 1
        out[server]["units"] += int(call["payload"]["units"])
    return dict(sorted(out.items()))


def completed_ids(events: list[dict]) -> set[str]:
    return {
        e["consultation_id"]
        for e in events
        if e["type"] == "state.changed" and e["payload"].get("to") == "done"
    }


def per_consultation(events: list[dict]) -> tuple[dict[str, dict[str, int]], int]:
    done = completed_ids(events)
    by_id: dict[str, list[dict]] = defaultdict(list)
    for call in tool_calls(events):
        if call["consultation_id"] in done:
            by_id[call["consultation_id"]].append(call)
    if not by_id:
        return {}, 0
    totals = units_by_server([c for calls in by_id.values() for c in calls])
    n = len(by_id)
    return {s: {k: round(v / n) for k, v in row.items()} for s, row in totals.items()}, n


def per_onboarding(events: list[dict]) -> dict[str, dict[str, int]]:
    return units_by_server([c for c in tool_calls(events) if not c["consultation_id"]])


def weekly_refresh(seed_dir: Path) -> int:
    skus = json.loads((seed_dir / "skus.json").read_text(encoding="utf-8"))
    return sum(1 for s in skus if s["kind"] != "service")


def rows(units: dict[str, dict[str, int]]) -> list[dict]:
    return [
        {
            "vendor": SERVER_VENDOR[s][0],
            "server": s,
            "unit": SERVER_VENDOR[s][1],
            "calls": r["calls"],
            "units": r["units"],
        }
        for s, r in units.items()
    ]


def table(title: str, units: dict[str, dict[str, int]]) -> str:
    lines = [
        f"### {title}",
        "",
        "| Vendor | Server | Calls | Units | Unit |",
        "|---|---|---:|---:|---|",
    ]
    for r in rows(units):
        lines.append(
            f"| {r['vendor']} | `{r['server']}` | {r['calls']} | {r['units']} | {r['unit']} |"
        )
    return "\n".join(lines) + "\n"


def report(events: list[dict], seed_dir: Path) -> str:
    consult, n = per_consultation(events)
    refresh = weekly_refresh(seed_dir)
    parts = [
        "# Cost report",
        "",
        f"Generated from the local ledger ({len(tool_calls(events))} tool calls, "
        f"{n} completed consultations).",
        "",
        table(f"Per consultation (mean over {n} completed)", consult),
        table("Per onboarding", per_onboarding(events)),
        "### Weekly refresh",
        "",
        f"{refresh} priced SKUs × 1 `google_shopping` search when the snapshot is older than "
        "7 days "
        f"= {refresh} searches/week (≈{refresh / 7:.1f}/night).",
        "",
    ]
    return "\n".join(parts)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    state_dir = Path(argv[1]) if len(argv) > 1 else REPO / ".chairside"
    text = report(load_events(state_dir / "events.jsonl"), REPO / "seed")
    (REPO / "docs" / "cost-report.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
