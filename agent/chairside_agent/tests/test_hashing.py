import json
from pathlib import Path

import pytest

from chairside_agent.hashing import (
    GENESIS_HASH,
    NonCanonicalValueError,
    canonical,
    chain_hash,
    payload_hash,
    verify_chain,
)

VECTORS = json.loads(
    (Path(__file__).resolve().parents[3] / "docs" / "hash-vectors.json").read_text("utf-8")
)


def test_canonical_matches_shared_vectors() -> None:
    for v in VECTORS["canonical"]:
        assert canonical(v["in"]) == v["out"]


def test_canonical_rejects_floats() -> None:
    with pytest.raises(NonCanonicalValueError):
        canonical({"price": 1.5})


def _build_rows() -> list[dict]:
    prev = GENESIS_HASH
    rows = []
    for i, v in enumerate(VECTORS["chain"]):
        ph = payload_hash(v["payload"])
        h = chain_hash(
            prev_hash=prev, actor=v["actor"], action=v["action"], payload_hash=ph, ts=v["ts"]
        )
        rows.append(
            {
                "id": str(i),
                "prev_hash": prev,
                "hash": h,
                "actor": v["actor"],
                "action": v["action"],
                "payload_hash": ph,
                "ts": v["ts"],
            }
        )
        prev = h
    return rows


def test_verify_chain_ok_and_detects_tamper() -> None:
    rows = _build_rows()
    assert verify_chain(rows).ok
    rows[0]["action"] = "tampered"
    result = verify_chain(rows)
    assert not result.ok
    assert result.first_bad_index == 0
