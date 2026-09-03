import { describe, expect, it } from "vitest";
import snapshot from "../fixtures/snapshot.json";
import { verifyChain, type AuditRow } from "../lib/hashchain";

const audit = snapshot.audit as AuditRow[];
const TAMPER_INDEX = 17;

describe("snapshot ledger", () => {
  it("has a chain that verifies end to end", async () => {
    const result = await verifyChain(audit);
    expect(result.ok).toBe(true);
    expect(result.checked).toBe(audit.length);
  });

  it("fails at the tampered row", async () => {
    const rows = audit.map((r) => ({ ...r }));
    rows[TAMPER_INDEX].action = "envelope.signed";
    const result = await verifyChain(rows);
    expect(result.ok).toBe(false);
    expect(result.firstBadIndex).toBe(TAMPER_INDEX);
  });

  it("carries the red-team denial and the quarantine", () => {
    expect(audit.some((r) => r.action === "redteam.esign_denied")).toBe(true);
    expect(audit.filter((r) => r.action === "quarantined")).toHaveLength(2);
  });
});
