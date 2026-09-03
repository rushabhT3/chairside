"""Event fold. The consultation projection is `project(events)`; replay re-folds and diffs."""

from __future__ import annotations

import copy
import difflib
import json
from collections.abc import Iterable
from typing import Any

from chairside_agent.events import ConsultationEvent, EventType


def _without(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if k not in keys}


def empty_projection(consultation_id: str) -> dict[str, Any]:
    return {
        "id": consultation_id,
        "client": None,
        "stylist": None,
        "chair": None,
        "state": "capture",
        "failing_step": None,
        "started_at": None,
        "scan": None,
        "previous_scan": None,
        "deltas": None,
        "plan": None,
        "simulations": [],
        "identified": None,
        "prices": [],
        "news": None,
        "reviews": [],
        "consent": None,
        "order": None,
        "booking": None,
        "quarantine": None,
    }


def _apply_capture(p: dict[str, Any], ev: ConsultationEvent) -> None:
    pl = ev.payload
    p["client"] = {"id": pl["client_id"], "name": pl["client_name"]}
    p["stylist"] = pl["stylist"]
    p["chair"] = pl["chair"]
    p["started_at"] = ev.ts
    p["scan"] = {
        "scan_id": pl["scan_id"],
        "ts": pl["as_of"],
        "image_sha256": pl["image_sha256"],
        "image_url": pl["image_url"],
        "retained": pl["retained"],
        "color_tones": None,
        "skin": None,
        "hair": None,
        "face": None,
    }


def _apply_consent(p: dict[str, Any], ev: ConsultationEvent) -> None:
    pl = ev.payload
    t = ev.type
    if t is EventType.CONSENT_TEMPLATE_SELECTED:
        p["consent"] = {**_without(pl, "as_of"), "document": None, "intake": None, "envelope": None}
        return
    consent = p["consent"]
    if t is EventType.CONSENT_GENERATED:
        consent["document"] = _without(pl, "as_of")
    elif t is EventType.INTAKE_EXTRACTED:
        consent["intake"] = _without(pl, "as_of")
    elif t is EventType.ENVELOPE_REQUESTED:
        consent["envelope"] = {
            "envelope_id": pl["envelope_id"],
            "state": "draft",
            "session_url": None,
            "expires_at": None,
            "sealed_hash": None,
        }
    elif t is EventType.ENVELOPE_SENT:
        consent["envelope"].update(state="sent", session_url=pl.get("session_url"))
    elif t is EventType.ENVELOPE_SIGNED:
        consent["envelope"].update(state="signed", signed_at=pl["signed_at"])
    elif t is EventType.BUNDLE_SEALED:
        consent["envelope"]["sealed_hash"] = pl["sha256"]


_SCAN_FIELDS = {
    EventType.COLOR_TONES_DONE: "color_tones",
    EventType.HAIR_DIAGNOSTICS_DONE: "hair",
    EventType.FACE_ATTRIBUTES_DONE: "face",
}

_CONSENT_TYPES = {
    EventType.CONSENT_TEMPLATE_SELECTED,
    EventType.CONSENT_GENERATED,
    EventType.INTAKE_EXTRACTED,
    EventType.ENVELOPE_REQUESTED,
    EventType.ENVELOPE_SENT,
    EventType.ENVELOPE_SIGNED,
    EventType.BUNDLE_SEALED,
}


def apply(projection: dict[str, Any], ev: ConsultationEvent) -> dict[str, Any]:
    p = copy.deepcopy(projection)
    pl = ev.payload
    t = ev.type
    if t is EventType.STATE_CHANGED:
        p["state"] = pl["to"]
    elif t is EventType.CAPTURE_UPLOADED:
        _apply_capture(p, ev)
    elif t in _SCAN_FIELDS:
        p["scan"][_SCAN_FIELDS[t]] = _without(pl, "as_of")
    elif t is EventType.SKIN_HD_DONE:
        p["scan"]["skin"] = pl["scores"]
        p["previous_scan"] = pl["previous"]
        p["deltas"] = pl["deltas"]
    elif t is EventType.PLAN_RECOMMENDED:
        p["plan"] = _without(pl, "as_of")
    elif t is EventType.SIMULATION_RENDERED:
        p["simulations"].append(dict(pl))
    elif t is EventType.PRICE_IDENTIFIED:
        p["identified"] = dict(pl)
    elif t is EventType.PRICE_SNAPSHOT:
        p["prices"].append(dict(pl))
    elif t is EventType.NEWS_CHECKED:
        p["news"] = dict(pl)
    elif t is EventType.REVIEWS_FETCHED:
        p["reviews"].append(dict(pl))
    elif t in _CONSENT_TYPES:
        _apply_consent(p, ev)
    elif t is EventType.ORDER_CREATED:
        p["order"] = dict(pl)
    elif t is EventType.BOOKING_CREATED:
        p["booking"] = dict(pl)
    elif t is EventType.QUARANTINED:
        p["quarantine"] = dict(pl)
    elif t is EventType.NEEDS_ATTENTION:
        p["failing_step"] = pl["step"]
    return p


def project(consultation_id: str, events: Iterable[ConsultationEvent]) -> dict[str, Any]:
    p = empty_projection(consultation_id)
    for ev in events:
        p = apply(p, ev)
    return p


def diff(stored: dict[str, Any], rebuilt: dict[str, Any]) -> str:
    a = json.dumps(stored, indent=2, sort_keys=True, ensure_ascii=False).splitlines()
    b = json.dumps(rebuilt, indent=2, sort_keys=True, ensure_ascii=False).splitlines()
    return "\n".join(difflib.unified_diff(a, b, "stored", "rebuilt", lineterm=""))
