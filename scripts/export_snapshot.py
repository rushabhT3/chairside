"""Build web/src/fixtures/snapshot.json from the local ledger and stored projections.

Run from agent/: `uv run python ../scripts/export_snapshot.py [--force]`. The shape is
web/src/lib/snapshot.ts. Writes only when the file is missing or --force is given.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cost_report import (  # noqa: E402
    load_events,
    per_consultation,
    per_onboarding,
    rows,
    weekly_refresh,
)

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "web" / "src" / "fixtures" / "snapshot.json"
SCAN_KEYS = ("scan_id", "ts", "color_tones", "skin", "hair", "face")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _projections(state_dir: Path) -> dict[str, dict[str, Any]]:
    folder = state_dir / "projections"
    if not folder.exists():
        return {}
    return {p.stem: _read(p) for p in sorted(folder.glob("*.json"))}


def _seed_scan(clients: list[dict[str, Any]], scan_id: str | None) -> dict[str, Any] | None:
    for client in clients:
        for visit in client["visits"]:
            if visit["scan_id"] == scan_id:
                return {k: visit[k] for k in SCAN_KEYS}
    return None


def _scan(p: dict[str, Any]) -> dict[str, Any] | None:
    scan = p.get("scan")
    if not scan:
        return None
    return {k: scan.get(k) for k in SCAN_KEYS}


def _previous(p: dict[str, Any], clients: list[dict[str, Any]]) -> dict[str, Any] | None:
    prev = p.get("previous_scan")
    return _seed_scan(clients, prev["scan_id"]) if prev else None


def _consent(p: dict[str, Any]) -> dict[str, Any] | None:
    c = p.get("consent")
    if not c or not c.get("template_id"):
        return None
    envelope = c.get("envelope") or {
        "envelope_id": "",
        "state": "draft",
        "session_url": None,
        "expires_at": None,
        "sealed_hash": None,
    }
    return {
        "template_id": c["template_id"],
        "treatment_classes": c["treatment_classes"],
        "envelope": envelope,
    }


def _order(p: dict[str, Any]) -> dict[str, Any] | None:
    order = p.get("order")
    plan = p.get("plan") or {}
    if not order:
        return None
    return {
        "id": order["order_id"],
        "total_cents": order["total_cents"],
        "items": plan.get("services", []) + plan.get("products", []),
    }


def _booking(p: dict[str, Any]) -> dict[str, Any] | None:
    booking = p.get("booking")
    if not booking:
        return None
    return {"id": booking["booking_id"], "when": booking["when"], "service": booking["service"]}


def _consultation(
    p: dict[str, Any], events: list[dict[str, Any]], clients: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "id": p["id"],
        "client": p["client"],
        "stylist": p["stylist"],
        "chair": p["chair"],
        "state": p["state"],
        "failing_step": p["failing_step"],
        "started_at": p["started_at"],
        "events": events,
        "scan": _scan(p),
        "previous_scan": _previous(p, clients),
        "plan": p["plan"],
        "simulations": p["simulations"],
        "prices": p["prices"],
        "news": p["news"],
        "reviews": p["reviews"],
        "consent": _consent(p),
        "order": _order(p),
        "booking": _booking(p),
    }


def _chairs(
    salon: dict[str, Any], consultations: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    latest: dict[int, dict[str, Any]] = {}
    for c in consultations.values():
        if c["chair"] not in latest or c["started_at"] > latest[c["chair"]]["started_at"]:
            latest[c["chair"]] = c
    stylists = salon["stylists"]
    out = []
    for chair in range(1, salon["chairs"] + 1):
        c = latest.get(chair)
        stylist = c["stylist"] if c else stylists[(chair - 1) % len(stylists)]["name"]
        out.append(
            {
                "chair": chair,
                "stylist": stylist,
                "client": c["client"] if c else None,
                "consultation_id": c["id"] if c else None,
                "state": c["state"] if c else "free",
                "time": c["started_at"][11:16] if c else "",
            }
        )
    return out


def _attribution(consultations: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    agg: dict[tuple[str, int], dict[str, int]] = defaultdict(
        lambda: {"consultations": 0, "orders": 0, "revenue_cents": 0}
    )
    for c in consultations.values():
        row = agg[(c["stylist"], c["chair"])]
        row["consultations"] += 1
        if c["order"]:
            row["orders"] += 1
            row["revenue_cents"] += c["order"]["total_cents"]
    return [{"stylist": s, "chair": ch, **r} for (s, ch), r in sorted(agg.items())]


def _price_watch(onboarding: dict[str, Any]) -> list[dict[str, Any]]:
    keys = ("sku_code", "name", "salon_price_cents", "median_cents", "delta_pct", "alert", "as_of")
    return [{k: r[k] for k in keys} for r in onboarding.get("prices", [])]


def _cost(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    consult, _ = per_consultation(events)
    refresh = weekly_refresh(REPO / "seed")

    def cost_rows(units: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
        return [
            {"vendor": r["vendor"], "unit": f"{r['unit']} ({r['server']})", "count": r["units"]}
            for r in rows(units)
        ]

    return {
        "per_consultation": cost_rows(consult),
        "per_onboarding": cost_rows(per_onboarding(events)),
        "weekly_refresh": [
            {"vendor": "SerpApi", "unit": "google_shopping search", "count": refresh}
        ],
    }


def _quarantine(
    onboarding: dict[str, Any],
    consultations: dict[str, dict[str, Any]],
    projections: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    out = list(onboarding.get("quarantine", []))
    for key, p in projections.items():
        q = p.get("quarantine")
        if q:
            out.append(
                {
                    "id": f"q-{key}",
                    "source": q["source"],
                    "file": q["file"],
                    "reasons": q["reasons"],
                    "ts": q["as_of"],
                }
            )
    return out


def build(state_dir: Path, seed_dir: Path) -> dict[str, Any]:
    salon = _read(seed_dir / "salon.json")
    clients = _read(seed_dir / "clients.json")
    events = load_events(state_dir / "events.jsonl")
    projections = _projections(state_dir)
    onboarding = projections.pop("onboarding", {})
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in events:
        if e["consultation_id"]:
            by_id[e["consultation_id"]].append(e)
    consultations = {k: _consultation(p, by_id.get(k, []), clients) for k, p in projections.items()}
    domain = (onboarding.get("domain") or {}).get("name") or salon["domain"]
    audit = load_events(state_dir / "audit.jsonl")
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "salon": {**salon, "domain": domain},
        "shade_map": _read(seed_dir / "shade_map.json"),
        "skus": onboarding.get("skus") or _read(seed_dir / "skus.json"),
        "chairs": _chairs(salon, consultations),
        "consultations": consultations,
        "audit": audit,
        "extractions": onboarding.get("extractions", []),
        "onboarding": onboarding.get("steps", []),
        "price_watch": _price_watch(onboarding),
        "attribution": _attribution(consultations),
        "cost": _cost(events),
        "quarantine": _quarantine(onboarding, consultations, projections),
    }


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    force = "--force" in argv
    if OUT.exists() and not force:
        print(f"{OUT} exists; pass --force to overwrite")
        return 0
    snapshot = build(REPO / ".chairside", REPO / "seed")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT}: {len(snapshot['consultations'])} consultations, "
        f"{len(snapshot['audit'])} audit rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
