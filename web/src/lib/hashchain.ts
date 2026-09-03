// Mirrors agent/chairside_agent/hashing.py byte for byte. Vectors: docs/hash-vectors.json.

export const GENESIS_HASH = "0".repeat(64);

export interface AuditRow {
  id: string;
  prev_hash: string;
  hash: string;
  actor: string;
  action: string;
  payload_hash: string;
  ts: string;
}

export interface VerifyResult {
  ok: boolean;
  checked: number;
  firstBadIndex: number | null;
  reasons: string[];
}

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

function assertNoFloat(value: Json, path: string): void {
  if (typeof value === "number" && !Number.isInteger(value)) {
    throw new TypeError(`float at ${path}; audited payloads use integers`);
  }
  if (Array.isArray(value)) value.forEach((v, i) => assertNoFloat(v, `${path}[${i}]`));
  else if (value !== null && typeof value === "object") {
    for (const [k, v] of Object.entries(value)) assertNoFloat(v, `${path}.${k}`);
  }
}

function sortKeys(value: Json): Json {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value !== null && typeof value === "object") {
    const out: { [key: string]: Json } = {};
    for (const key of Object.keys(value).sort()) out[key] = sortKeys(value[key]);
    return out;
  }
  return value;
}

export function canonical(value: Json): string {
  assertNoFloat(value, "$");
  return JSON.stringify(sortKeys(value));
}

export async function sha256Hex(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

export async function payloadHash(payload: Json): Promise<string> {
  return sha256Hex(canonical(payload));
}

export async function chainHash(row: Omit<AuditRow, "id" | "hash">): Promise<string> {
  return sha256Hex(
    canonical({
      action: row.action,
      actor: row.actor,
      payload_hash: row.payload_hash,
      prev_hash: row.prev_hash,
      ts: row.ts,
    }),
  );
}

export async function verifyChain(rows: AuditRow[]): Promise<VerifyResult> {
  let prev = GENESIS_HASH;
  for (let i = 0; i < rows.length; i += 1) {
    const row = rows[i];
    if (row.prev_hash !== prev) {
      return { ok: false, checked: i, firstBadIndex: i, reasons: [`row ${i}: prev_hash does not link`] };
    }
    const expected = await chainHash(row);
    if (row.hash !== expected) {
      return { ok: false, checked: i, firstBadIndex: i, reasons: [`row ${i}: hash mismatch`] };
    }
    prev = row.hash;
  }
  return { ok: true, checked: rows.length, firstBadIndex: null, reasons: [] };
}
