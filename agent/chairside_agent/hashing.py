"""Canonical JSON + SHA-256 hash chain. Mirrors web/src/lib/hashchain.ts byte for byte."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

GENESIS_HASH = "0" * 64


class NonCanonicalValueError(TypeError):
    """Floats are rejected: JS and Python print them differently."""


def _reject_floats(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise NonCanonicalValueError(f"float at {path}; audited payloads use integers")
    if isinstance(value, dict):
        for k, v in value.items():
            _reject_floats(v, f"{path}.{k}")
    elif isinstance(value, list | tuple):
        for i, v in enumerate(value):
            _reject_floats(v, f"{path}[{i}]")


def canonical(value: Any) -> str:
    _reject_floats(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str | bytes) -> str:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()


def payload_hash(payload: dict[str, Any]) -> str:
    return sha256_hex(canonical(payload))


def chain_hash(*, prev_hash: str, actor: str, action: str, payload_hash: str, ts: str) -> str:
    return sha256_hex(
        canonical(
            {
                "action": action,
                "actor": actor,
                "payload_hash": payload_hash,
                "prev_hash": prev_hash,
                "ts": ts,
            }
        )
    )


@dataclass(slots=True)
class VerifyResult:
    ok: bool
    checked: int
    first_bad_index: int | None = None
    reasons: list[str] = field(default_factory=list)


def verify_chain(rows: Iterable[dict[str, Any]]) -> VerifyResult:
    prev = GENESIS_HASH
    for i, row in enumerate(rows):
        if row["prev_hash"] != prev:
            return VerifyResult(False, i, i, [f"row {i}: prev_hash does not link"])
        expected = chain_hash(
            prev_hash=row["prev_hash"],
            actor=row["actor"],
            action=row["action"],
            payload_hash=row["payload_hash"],
            ts=row["ts"],
        )
        if row["hash"] != expected:
            return VerifyResult(False, i, i, [f"row {i}: hash mismatch"])
        prev = row["hash"]
    else:
        i = -1
    return VerifyResult(True, i + 1)
