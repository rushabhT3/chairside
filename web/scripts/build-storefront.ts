import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Snapshot } from "../src/lib/snapshot";
import { generateStorefront } from "../src/storefront/generate";

const here = dirname(fileURLToPath(import.meta.url));
const web = resolve(here, "..");
const MAX_BYTES = 50 * 1024;
const LOOKS = 3;

const snapshot = JSON.parse(readFileSync(resolve(web, "src", "fixtures", "snapshot.json"), "utf-8")) as Snapshot;
const looks = Object.values(snapshot.consultations)
  .flatMap((c) => c.simulations)
  .slice(0, LOOKS)
  .map((s) => ({ label: s.label, image_url: s.after_url }));
const services = snapshot.skus.filter((s) => s.kind === "service").map((s) => ({ name: s.name, price_cents: s.salon_price_cents }));

const html = generateStorefront(snapshot.salon, looks, "/mirror/", services);
const bytes = new TextEncoder().encode(html).byteLength;
if (bytes > MAX_BYTES) throw new Error(`storefront is ${bytes} bytes; limit is ${MAX_BYTES}`);

const out = resolve(web, "dist", "storefront", "index.html");
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, html, "utf-8");
process.stdout.write(`storefront: ${bytes} bytes → ${out}\n`);
