import { describe, expect, it } from "vitest";
import snapshot from "../fixtures/snapshot.json";
import type { Snapshot } from "../lib/snapshot";
import { generateStorefront } from "./generate";

const MAX_BYTES = 50 * 1024;
const data = snapshot as unknown as Snapshot;

const looks = Object.values(data.consultations)
  .flatMap((c) => c.simulations)
  .slice(0, 3)
  .map((s) => ({ label: s.label, image_url: s.after_url }));
const services = data.skus.filter((s) => s.kind === "service").map((s) => ({ name: s.name, price_cents: s.salon_price_cents }));

describe("generateStorefront", () => {
  const html = generateStorefront(data.salon, looks, "/mirror/", services);

  it("stays under 50 KB", () => {
    expect(new TextEncoder().encode(html).byteLength).toBeLessThanOrEqual(MAX_BYTES);
  });

  it("ships no script", () => {
    expect(html).not.toMatch(/<script/i);
  });

  it("carries the salon, three looks, services and the Book link", () => {
    expect(html).toContain("Atelier Noor");
    expect(html.match(/<figure>/g)).toHaveLength(3);
    expect(html).toContain('href="/mirror/"');
    expect(html).toContain("Colour service");
  });

  it("escapes markup in salon data", () => {
    const evil = { ...data.salon, name: "<b>x</b>" };
    expect(generateStorefront(evil, [], "/mirror/")).toContain("&lt;b&gt;x&lt;/b&gt;");
  });
});
