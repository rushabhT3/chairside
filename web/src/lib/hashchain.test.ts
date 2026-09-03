import { describe, expect, it } from "vitest";
import vectors from "../../../docs/hash-vectors.json";
import { GENESIS_HASH, canonical, chainHash, payloadHash, verifyChain } from "./hashchain";

describe("canonical", () => {
  it("matches the shared vectors", () => {
    for (const v of vectors.canonical) expect(canonical(v.in as never)).toBe(v.out);
  });
  it("rejects floats", () => {
    expect(() => canonical({ price: 1.5 })).toThrow(/float/);
  });
});

describe("verifyChain", () => {
  it("verifies a chain built from the shared vectors and detects tampering", async () => {
    let prev = GENESIS_HASH;
    const rows = [];
    for (const [i, v] of vectors.chain.entries()) {
      const payload_hash = await payloadHash(v.payload as never);
      const partial = { prev_hash: prev, actor: v.actor, action: v.action, payload_hash, ts: v.ts };
      const hash = await chainHash(partial);
      rows.push({ id: String(i), hash, ...partial });
      prev = hash;
    }
    expect((await verifyChain(rows)).ok).toBe(true);
    rows[0].action = "tampered";
    const bad = await verifyChain(rows);
    expect(bad.ok).toBe(false);
    expect(bad.firstBadIndex).toBe(0);
  });
});
