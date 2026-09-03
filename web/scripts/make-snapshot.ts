import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { GENESIS_HASH, chainHash, payloadHash, type AuditRow } from "../src/lib/hashchain";
import type { Actor, ConsultationEvent, EventType, ToolServer } from "../src/lib/events";
import type {
  AttributionRow,
  Chair,
  Consultation,
  CostRow,
  ExtractionRow,
  OnboardingStep,
  Plan,
  PriceRow,
  PriceWatchRow,
  QuarantineRow,
  Salon,
  Scan,
  ShadeEntry,
  Simulation,
  Sku,
  Snapshot,
} from "../src/lib/snapshot";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..", "..");
const readJson = <T>(path: string): T => JSON.parse(readFileSync(resolve(root, path), "utf-8")) as T;

const salon = readJson<Salon>("seed/salon.json");
const shadeMap = readJson<ShadeEntry[]>("seed/shade_map.json");
const skus = readJson<Sku[]>("seed/skus.json");
const skuByCode = new Map(skus.map((s) => [s.code, s]));
const sku = (code: string): Sku => {
  const found = skuByCode.get(code);
  if (!found) throw new Error(`seed sku missing: ${code}`);
  return found;
};

const SALON_ID = salon.id;
const DAY = "2026-09-03";
const PREVIOUS_DAY = "2026-07-23";
const RETURN_DAY = "2026-10-15";

type Json = Record<string, unknown>;

class Clock {
  private ms: number;
  constructor(iso: string) {
    this.ms = Date.parse(iso);
  }
  tick(seconds: number): string {
    this.ms += seconds * 1000;
    return new Date(this.ms).toISOString();
  }
  now(): string {
    return new Date(this.ms).toISOString();
  }
}

let eventCounter = 0;
const eventId = (): string => `ev-${String((eventCounter += 1)).padStart(4, "0")}`;

const RENDER_LATENCY = { analysis: 1840, render: 3120, rest: 640, mcpFoxit: 1210, commit: 310 };

const sha = (seed: string): string => {
  let h1 = 0x811c9dc5;
  let out = "";
  for (let i = 0; i < 64; i += 1) {
    h1 ^= seed.charCodeAt(i % seed.length) + i;
    h1 = Math.imul(h1, 0x01000193) >>> 0;
    out += (h1 & 0xf).toString(16);
  }
  return out;
};

interface EmitOptions {
  actor?: Actor;
  consultationId?: string | null;
}

function makeEmitter(clock: Clock, events: ConsultationEvent[], consultationId: string | null) {
  return (type: EventType, payload: Json, seconds: number, opts: EmitOptions = {}): ConsultationEvent => {
    const ev: ConsultationEvent = {
      id: eventId(),
      consultation_id: opts.consultationId === undefined ? consultationId : opts.consultationId,
      salon_id: SALON_ID,
      type,
      payload,
      ts: clock.tick(seconds),
      actor: opts.actor ?? "agent",
    };
    events.push(ev);
    return ev;
  };
}

type Emit = ReturnType<typeof makeEmitter>;

function toolCalled(emit: Emit, tool: string, server: ToolServer, latency: number, units: number, seedKey: string) {
  const ts = emit(
    "tool.called",
    { tool, server, latency_ms: latency, units, result_sha256: sha(seedKey), as_of: "" },
    Math.max(1, Math.round(latency / 1000)),
  );
  ts.payload = { ...ts.payload, as_of: ts.ts };
  return ts;
}

const amiraPrevious: Scan = {
  scan_id: "scan-0007",
  ts: `${PREVIOUS_DAY}T12:41:12.000Z`,
  color_tones: { skin_tone: "medium olive", undertone: "warm", eye_color: "brown", hair_color_hex: "#4A2C1A" },
  skin: {
    wrinkle: 24, spot: 51, pore: 66, texture: 49, acne: 22, redness: 38, oiliness: 70,
    dark_circle: 55, eye_bag: 33, droopy_upper_eyelid: 21, droopy_lower_eyelid: 16,
    firmness: 74, radiance: 48, moisture: 41,
  },
  hair: { type: "curly", frizz: 72, density: "medium" },
  face: { shape: "oval", ratios: { length_to_width: 142, jaw_to_forehead: 96, eye_spacing: 100 } },
};

const amiraToday: Scan = {
  scan_id: "scan-0031",
  ts: `${DAY}T12:31:44.000Z`,
  color_tones: { skin_tone: "medium olive", undertone: "warm", eye_color: "brown", hair_color_hex: "#4A2C1A" },
  skin: {
    wrinkle: 22, spot: 48, pore: 61, texture: 44, acne: 18, redness: 35, oiliness: 63,
    dark_circle: 52, eye_bag: 30, droopy_upper_eyelid: 20, droopy_lower_eyelid: 15,
    firmness: 78, radiance: 55, moisture: 47,
  },
  hair: { type: "curly", frizz: 66, density: "medium" },
  face: { shape: "oval", ratios: { length_to_width: 142, jaw_to_forehead: 96, eye_spacing: 100 } },
};

const julesScan: Scan = {
  scan_id: "scan-0032",
  ts: `${DAY}T12:07:10.000Z`,
  color_tones: { skin_tone: "light", undertone: "cool", eye_color: "grey", hair_color_hex: "#8C7A66" },
  skin: {
    wrinkle: 31, spot: 27, pore: 42, texture: 38, acne: 12, redness: 62, oiliness: 35,
    dark_circle: 44, eye_bag: 28, droopy_upper_eyelid: 18, droopy_lower_eyelid: 12,
    firmness: 71, radiance: 52, moisture: 39,
  },
  hair: { type: "straight", frizz: 22, density: "low" },
  face: { shape: "oblong", ratios: { length_to_width: 158, jaw_to_forehead: 91, eye_spacing: 98 } },
};

const camilleScan: Scan = {
  scan_id: "scan-0029",
  ts: `${DAY}T09:04:51.000Z`,
  color_tones: { skin_tone: "fair", undertone: "neutral", eye_color: "green", hair_color_hex: "#B5A58E" },
  skin: {
    wrinkle: 19, spot: 33, pore: 47, texture: 41, acne: 64, redness: 46, oiliness: 68,
    dark_circle: 39, eye_bag: 22, droopy_upper_eyelid: 14, droopy_lower_eyelid: 10,
    firmness: 82, radiance: 50, moisture: 44,
  },
  hair: { type: "curly", frizz: 71, density: "high" },
  face: { shape: "heart", ratios: { length_to_width: 139, jaw_to_forehead: 84, eye_spacing: 102 } },
};

const item = (code: string, treatment_class: Plan["services"][number]["treatment_class"], qty = 1) => {
  const s = sku(code);
  return { code: s.code, name: s.name, price_cents: s.salon_price_cents, qty, treatment_class };
};

const amiraPlan: Plan = {
  treatment_classes: ["chemical", "heat"],
  services: [item("SVC-COLOR", "chemical"), item("SVC-SMOOTH", "heat"), item("SVC-SOOTHE", "none")],
  products: [item("OLX-03", "none"), item("KER-DISC-MASK", "none"), item("KER-CURL", "none"), item("LRP-CICA", "none")],
  total_cents: 42200,
  rebook_weeks: 6,
  facts: [
    "Current hair level 5 warm; target 7.31 Medium Blonde Gold Ash is two levels of lift on a warm undertone",
    "Frizz 66 on curly hair; smoothing treatment today, Discipline mask and curl cream at home",
    "Redness 35 today from 38; soothing facial and Cicaplast balm keep the barrier calm",
    "Pores 61 and oiliness 63 improved since 23 July (66 and 70)",
    "Oval face shape; any length works, keep movement around the cheekbone",
    "Rebook in 6 weeks for root refresh and gloss",
  ],
  prose:
    "Amira, your hair is sitting at a warm level five, so 7.31 is two gentle levels up and keeps the gold you already have. We do the colour and the smoothing treatment today; at home, Olaplex No. 3 once a week, the Discipline mask, and the curl cream keep your curls defined and strong until we see you again in six weeks. Your skin readings moved in the right direction since July: pores and shine both came down, and a soothing facial today with the Cicaplast balm at home keeps the redness calm. Oval face, so we keep the length and add movement at the cheekbone.",
};

const shade731 = shadeMap.find((s) => s.code === "7.31");
if (!shade731) throw new Error("shade 7.31 missing from seed");

const amiraSimulations: Simulation[] = [
  {
    tool: "AI_Hair_Color_Virtual_Try_On", server: "mcp/beauty", tab: "hair", sku_code: "MAJ-7.31", hex: shade731.hex,
    label: "7.31 Medium Blonde Gold Ash", before_url: "/renders/amira-before.svg",
    after_url: "/renders/amira-hair-731.svg", as_of: `${DAY}T12:34:06.000Z`,
  },
  {
    tool: "AI_Skin_simulation", server: "mcp/beauty", tab: "skin", sku_code: null, hex: null,
    label: "Skin plan · pores and oil balance", before_url: "/renders/amira-before.svg",
    after_url: "/renders/amira-skin-plan.svg", as_of: `${DAY}T12:34:12.000Z`,
  },
  {
    tool: "AI_Hair_Style_Virtual_Try_On", server: "mcp/beauty", tab: "style", sku_code: null, hex: null,
    label: "Long layers · oval face", before_url: "/renders/amira-before.svg",
    after_url: "/renders/amira-style-layers.svg", as_of: `${DAY}T12:34:09.000Z`,
  },
];

const priceRow = (code: string, min: number, median: number, max: number, action: PriceRow["action"], reason: string, asOf: string): PriceRow => {
  const s = sku(code);
  return { sku_code: code, name: s.name, salon_price_cents: s.salon_price_cents, min_cents: min, median_cents: median, max_cents: max, as_of: asOf, action, reason };
};

const amiraPrices: PriceRow[] = [
  priceRow("OLX-03", 2490, 2790, 3200, "match", "within 10% of market median", `${DAY}T12:36:02.000Z`),
  priceRow("RED-ABC", 2590, 2890, 3390, "bundle", "above median; bundle with a service", `${DAY}T12:36:02.000Z`),
  priceRow("KER-DISC-MASK", 4990, 5600, 6900, "hold", "more than 25% above median; review price", `${DAY}T12:36:02.000Z`),
];

function buildOnboarding(clock: Clock, events: ConsultationEvent[]) {
  const emit = makeEmitter(clock, events, null);
  emit("onboarding.parsed", { salon: salon.name, address: salon.address, postcode: salon.postcode, city: salon.city, services: ["hair", "skin", "brows"], chairs: 3, owner_email: salon.owner.email }, 2);
  toolCalled(emit, "domains:search", "rest/namecom", RENDER_LATENCY.rest, 0, "namecom-search");
  emit("domain.searched", { keyword: "atelier noor", suggestions: 12, as_of: clock.now() }, 1);
  toolCalled(emit, "domains:checkAvailability", "rest/namecom", RENDER_LATENCY.rest, 0, "namecom-avail");
  emit("domain.available", { domain: salon.domain, purchasable: true, price_cents: 1299, as_of: clock.now() }, 1);
  toolCalled(emit, "domains:create", "rest/namecom", 1420, 0, "namecom-create");
  emit("domain.created", { domain: salon.domain, idempotency_key: "atelier-noor-2026-09-03", order_id: 48211, as_of: clock.now() }, 1);
  toolCalled(emit, "dnsRecords:create", "rest/namecom", RENDER_LATENCY.rest, 0, "namecom-dns-a");
  emit("dns.created", { domain: salon.domain, host: "@", type: "A", answer: "76.76.21.21", ttl: 300 }, 1);
  toolCalled(emit, "dnsRecords:create", "rest/namecom", RENDER_LATENCY.rest, 0, "namecom-dns-cname");
  emit("dns.created", { domain: salon.domain, host: "www", type: "CNAME", answer: "static.xano.io", ttl: 300 }, 1);
  toolCalled(emit, "urlForwarding:create", "rest/namecom", RENDER_LATENCY.rest, 0, "namecom-fwd");
  emit("forwarding.created", { kind: "url", host: "www", forwards_to: `https://${salon.domain}` }, 1);
  toolCalled(emit, "emailForwarding:create", "rest/namecom", RENDER_LATENCY.rest, 0, "namecom-mail");
  emit("forwarding.created", { kind: "email", alias: "hello", forwards_to: salon.owner.email }, 1);

  const templates = ["consent_chemical", "consent_heat", "consent_injectable", "consent_laser", "aftercare", "price_list"];
  for (const t of templates) toolCalled(emit, "generate", "rest/doctavian", 2210, 1, `doctavian-${t}`);
  emit("documents.generated", { templates, jurisdiction: salon.jurisdiction, allergen_loop: true, class_branches: 4, as_of: clock.now() }, 2);
  toolCalled(emit, "merge", "mcp/foxit", RENDER_LATENCY.mcpFoxit, 1, "foxit-merge-packet");
  toolCalled(emit, "compress", "mcp/foxit", RENDER_LATENCY.mcpFoxit, 1, "foxit-compress-packet");
  toolCalled(emit, "convert_to_pdf", "mcp/foxit", RENDER_LATENCY.mcpFoxit, 1, "foxit-convert-terms");
  toolCalled(emit, "ocr", "mcp/foxit", RENDER_LATENCY.mcpFoxit, 1, "foxit-ocr-invoice-2");
  toolCalled(emit, "envelopes.request", "commit/xano", RENDER_LATENCY.commit, 0, "xano-env-agreement");
  emit("agreement.requested", { envelope_id: "env-0001", document: "platform_agreement", signer: salon.owner.email }, 1);
  emit("redteam.esign_denied", { status: 401, endpoint_host: "na1.foxitesign.foxit.com", token_kind: "pdf_services", envelope_id: "env-0001" }, 3);
  emit("envelope.sent", { envelope_id: "env-0001", session: "embedded", expires_in_min: 30 }, 4, { actor: "owner" });
  emit("agreement.signed", { envelope_id: "env-0001", provider_id: "FX-ENV-7A31C2", sealed_hash: sha("agreement-seal") }, 95, { actor: "owner" });

  toolCalled(emit, "extract", "rest/nutrient", 3480, 1, "nutrient-price-list");
  emit("catalog.extracted", { source: "price_list", file: "price_list.pdf", rows: 42, below_threshold: 3 }, 1);
  toolCalled(emit, "extract", "rest/nutrient", 2960, 1, "nutrient-inv-1");
  emit("catalog.extracted", { source: "invoice", file: "inv-0001-loreal.pdf", lines: 6, arithmetic_ok: true }, 1);
  toolCalled(emit, "extract", "rest/nutrient", 3310, 1, "nutrient-inv-2");
  emit("catalog.extracted", { source: "invoice", file: "inv-0002-olaplex-scanned.pdf", lines: 4, arithmetic_ok: true }, 1);
  toolCalled(emit, "extract", "rest/nutrient", 3020, 1, "nutrient-inv-3");
  emit("quarantined", { source: "invoice", file: "inv-0003-bad-math.pdf", reasons: ["arithmetic_mismatch: line 3 qty x unit_price != amount (diff 1200 cents)", "arithmetic_mismatch: subtotal + vat != total"] }, 1);
  emit("catalog.review_queued", { rows: 3, threshold_pct: 85, viewer: "nutrient" }, 1);
  emit("catalog.sealed", { rows_confirmed: 42, signature: "cades-b-lt", sealed_hash: sha("catalog-seal") }, 420, { actor: "owner" });
  toolCalled(emit, "sign", "rest/nutrient", 1890, 1, "nutrient-sign-catalog");

  for (const s of skus) toolCalled(emit, "google_shopping", "rest/serpapi", 780, 1, `serp-seed-${s.code}`);
  emit("prices.seeded", { skus: skus.length, source: "google_shopping", as_of: clock.now() }, 1);
  emit("shade_map.seeded", { line: salon.color_line, shades: shadeMap.length }, 1);
  emit("storefront.deployed", { url: `https://${salon.domain}`, size_bytes: 21804, host: "xano_static" }, 12);
  emit("onboarding.done", { salon: salon.name, domain: salon.domain, elapsed_s: 1004 }, 1);
}

function buildAmira(clock: Clock, events: ConsultationEvent[]): ConsultationEvent[] {
  const own: ConsultationEvent[] = [];
  const emit = makeEmitter(clock, own, "cons-0001");
  const state = (s: string, from: string, seconds = 1) => emit("state.changed", { from, to: s }, seconds);
  state("capture", "new");
  toolCalled(emit, "tools/list", "mcp/beauty", 420, 0, "yc-tools-beauty");
  toolCalled(emit, "tools/list", "mcp/fashion", 390, 0, "yc-tools-fashion");
  emit("capture.uploaded", { scan_id: amiraToday.scan_id, image_sha256: sha("amira-selfie"), max_px: 1600, retained: true, face_count: 1 }, 6, { actor: "client" });
  state("color_tones", "capture");
  toolCalled(emit, "AI_Facial_Color_Tones_Analyzer", "mcp/beauty", RENDER_LATENCY.analysis, 1, "yc-tones");
  emit("color_tones.done", { ...amiraToday.color_tones, as_of: clock.now() }, 1);
  state("skin_hd", "color_tones");
  toolCalled(emit, "AI_Skin_Analysis", "mcp/beauty", 2240, 1, "yc-skin");
  emit("skin_hd.done", { scores: amiraToday.skin, as_of: clock.now() }, 1);
  state("hair_diagnostics", "skin_hd");
  toolCalled(emit, "AI_Hair_Type_Detection", "mcp/beauty", 1410, 1, "yc-hair-type");
  toolCalled(emit, "AI_Hair_Density_Detection", "mcp/beauty", 1370, 1, "yc-hair-density");
  toolCalled(emit, "AI_Hair_Frizziness_Detection", "mcp/beauty", 1450, 1, "yc-hair-frizz");
  emit("hair_diagnostics.done", { ...amiraToday.hair, as_of: clock.now() }, 1);
  state("face_attributes", "hair_diagnostics");
  toolCalled(emit, "AI_Face_Attributes_and_Ratio_Analyzer", "mcp/beauty", 1620, 1, "yc-face");
  emit("face_attributes.done", { shape: amiraToday.face.shape, ratios: amiraToday.face.ratios, as_of: clock.now() }, 1);
  state("plan", "face_attributes");
  emit("plan.recommended", { treatment_classes: amiraPlan.treatment_classes, services: amiraPlan.services.map((s) => s.code), products: amiraPlan.products.map((p) => p.code), total_cents: amiraPlan.total_cents, rebook_weeks: amiraPlan.rebook_weeks, engine: "recommend_plan@pure" }, 1);
  state("simulations", "plan");
  toolCalled(emit, "AI_Hair_Color_Virtual_Try_On", "mcp/beauty", RENDER_LATENCY.render, 1, "yc-render-731");
  emit("simulation.rendered", { tool: "AI_Hair_Color_Virtual_Try_On", sku_code: "MAJ-7.31", shade: "7.31", hex: shade731.hex, cache: "miss", as_of: clock.now() }, 1);
  toolCalled(emit, "AI_Hair_Style_Virtual_Try_On", "mcp/beauty", 2980, 1, "yc-render-style");
  emit("simulation.rendered", { tool: "AI_Hair_Style_Virtual_Try_On", style: "long_layers", by: "face_shape:oval", cache: "miss", as_of: clock.now() }, 1);
  toolCalled(emit, "AI_Skin_simulation", "mcp/beauty", 3340, 1, "yc-render-skin");
  emit("simulation.rendered", { tool: "AI_Skin_simulation", treatment: "pore_oil_balance", cache: "miss", as_of: clock.now() }, 1);
  state("price", "simulations");
  toolCalled(emit, "google_lens", "rest/serpapi", 1120, 1, "serp-lens");
  emit("price.identified", { sku_code: "OLX-03", brand: "Olaplex", product: "No. 3 Hair Perfector 100ml", visual_matches: 14, as_of: clock.now() }, 1);
  toolCalled(emit, "google_shopping", "rest/serpapi", 840, 1, "serp-shop");
  emit("price.snapshot", { sku_code: "OLX-03", min_cents: 2490, median_cents: 2790, max_cents: 3200, salon_price_cents: 2800, action: "match", as_of: clock.now() }, 1);
  toolCalled(emit, "google_news", "rest/serpapi", 910, 1, "serp-news");
  emit("news.checked", { query: "Olaplex No. 3 rappel recall", days: 90, flags: 0, clean: true, as_of: clock.now() }, 1);
  toolCalled(emit, "google_maps_reviews", "rest/serpapi", 1330, 1, "serp-rev-1");
  emit("reviews.fetched", { competitor_place_id: "ChIJ-marais-01", staff_only: true, reviews: 38, as_of: clock.now() }, 1);
  toolCalled(emit, "google_maps_reviews", "rest/serpapi", 1270, 1, "serp-rev-2");
  emit("reviews.fetched", { competitor_place_id: "ChIJ-marais-02", staff_only: true, reviews: 51, as_of: clock.now() }, 1);
  state("consent", "price");
  emit("consent.template_selected", { template_id: "tpl_fixture_consent_chemical", treatment_classes: ["chemical"], allergens: ["fragrance", "ppd"], jurisdiction: "FR" }, 1);
  toolCalled(emit, "generate", "rest/doctavian", 2410, 1, "doctavian-consent-amira");
  emit("consent.generated", { template_id: "tpl_fixture_consent_chemical", document_id: "doc-0142", pages: 3, as_of: clock.now() }, 1);
  toolCalled(emit, "extract", "rest/nutrient", 2780, 1, "nutrient-intake-amira");
  emit("intake.extracted", { file: "intake-01-amira.png", fields: 7, min_confidence_pct: 88, allergies: "PPD, fragrance", quarantined: false }, 1);
  toolCalled(emit, "merge", "mcp/foxit", RENDER_LATENCY.mcpFoxit, 1, "foxit-merge-amira");
  toolCalled(emit, "compress", "mcp/foxit", 980, 1, "foxit-compress-amira");
  toolCalled(emit, "envelopes.request", "commit/xano", RENDER_LATENCY.commit, 0, "xano-env-amira");
  emit("envelope.requested", { envelope_id: "env-0014", document_id: "doc-0142", signer: "amira.benali@example.com" }, 1);
  emit("envelope.sent", { envelope_id: "env-0014", session: "embedded", reviewed_by: "Marc", expires_in_min: 30 }, 38, { actor: "stylist" });
  emit("envelope.signed", { envelope_id: "env-0014", provider_id: "FX-ENV-9D02E7", signed_on: "client_phone" }, 74, { actor: "client" });
  emit("bundle.sealed", { bundle: ["consent", "intake", "scan"], signature: "cades-b-lt", sealed_hash: sha("amira-bundle-seal") }, 3);
  state("commit", "consent");
  emit("plan.accepted", { total_cents: 42200, services: 3, products: 4 }, 5, { actor: "client" });
  emit("order.created", { order_id: "ord-0051", total_cents: 14700, currency: "EUR", stylist: "Marc", chair: 2 }, 2, { actor: "stylist" });
  emit("booking.created", { booking_id: "bk-0088", when: `${RETURN_DAY}T12:30:00.000Z`, service: "SVC-COLOR", weeks: 6 }, 1, { actor: "stylist" });
  state("done", "commit");
  events.push(...own);
  return own;
}

function buildJules(clock: Clock, events: ConsultationEvent[]): ConsultationEvent[] {
  const own: ConsultationEvent[] = [];
  const emit = makeEmitter(clock, own, "cons-0002");
  const state = (s: string, from: string) => emit("state.changed", { from, to: s }, 1);
  state("capture", "new");
  emit("capture.uploaded", { scan_id: julesScan.scan_id, image_sha256: sha("jules-selfie"), max_px: 1600, retained: false, face_count: 1 }, 5, { actor: "client" });
  state("color_tones", "capture");
  toolCalled(emit, "AI_Facial_Color_Tones_Analyzer", "mcp/beauty", 1790, 1, "yc-tones-j");
  emit("color_tones.done", { ...julesScan.color_tones, as_of: clock.now() }, 1);
  state("skin_hd", "color_tones");
  toolCalled(emit, "AI_Skin_Analysis", "mcp/beauty", 2310, 1, "yc-skin-j");
  emit("skin_hd.done", { scores: julesScan.skin, as_of: clock.now() }, 1);
  state("hair_diagnostics", "skin_hd");
  toolCalled(emit, "AI_Hair_Type_Detection", "mcp/beauty", 1390, 1, "yc-hair-type-j");
  toolCalled(emit, "AI_Hair_Density_Detection", "mcp/beauty", 1420, 1, "yc-hair-density-j");
  toolCalled(emit, "AI_Hair_Frizziness_Detection", "mcp/beauty", 1360, 1, "yc-hair-frizz-j");
  emit("hair_diagnostics.done", { ...julesScan.hair, as_of: clock.now() }, 1);
  state("face_attributes", "hair_diagnostics");
  toolCalled(emit, "AI_Face_Attributes_and_Ratio_Analyzer", "mcp/beauty", 1590, 1, "yc-face-j");
  emit("face_attributes.done", { shape: julesScan.face.shape, ratios: julesScan.face.ratios, as_of: clock.now() }, 1);
  state("plan", "face_attributes");
  emit("plan.recommended", { treatment_classes: ["chemical"], services: ["SVC-GLOSS", "SVC-VOLCUT"], products: ["KER-VOL", "LRP-TOL"], total_cents: 16200, rebook_weeks: 6, engine: "recommend_plan@pure" }, 1);
  state("simulations", "plan");
  toolCalled(emit, "AI_Hair_Color_Virtual_Try_On", "mcp/beauty", 3050, 1, "yc-render-81");
  emit("simulation.rendered", { tool: "AI_Hair_Color_Virtual_Try_On", sku_code: "MAJ-8.1", shade: "8.1", hex: "#B5A58E", cache: "miss", as_of: clock.now() }, 1);
  toolCalled(emit, "AI_Hair_Volume_Virtual_Try_On", "mcp/beauty", 2890, 1, "yc-render-vol");
  emit("simulation.rendered", { tool: "AI_Hair_Volume_Virtual_Try_On", level: 2, by: "density:low", cache: "miss", as_of: clock.now() }, 1);
  state("price", "simulations");
  toolCalled(emit, "google_lens", "rest/serpapi", 1090, 1, "serp-lens-j");
  emit("price.identified", { sku_code: "KER-VOL", brand: "Kérastase", product: "Volumifique Bain Volume 250ml", visual_matches: 9, as_of: clock.now() }, 1);
  events.push(...own);
  return own;
}

function buildCamille(clock: Clock, events: ConsultationEvent[]): ConsultationEvent[] {
  const own: ConsultationEvent[] = [];
  const emit = makeEmitter(clock, own, "cons-0003");
  const state = (s: string, from: string) => emit("state.changed", { from, to: s }, 1);
  state("capture", "new");
  emit("capture.uploaded", { scan_id: camilleScan.scan_id, image_sha256: sha("camille-selfie"), max_px: 1600, retained: false, face_count: 1 }, 5, { actor: "client" });
  for (const [s, from, tool, key] of [
    ["color_tones", "capture", "AI_Facial_Color_Tones_Analyzer", "yc-tones-c"],
    ["skin_hd", "color_tones", "AI_Skin_Analysis", "yc-skin-c"],
    ["hair_diagnostics", "skin_hd", "AI_Hair_Type_Detection", "yc-hair-c"],
    ["face_attributes", "hair_diagnostics", "AI_Face_Attributes_and_Ratio_Analyzer", "yc-face-c"],
  ] as const) {
    state(s, from);
    toolCalled(emit, tool, "mcp/beauty", 1900, 1, key);
    if (s === "hair_diagnostics") {
      toolCalled(emit, "AI_Hair_Density_Detection", "mcp/beauty", 1430, 1, "yc-hair-density-c");
      toolCalled(emit, "AI_Hair_Frizziness_Detection", "mcp/beauty", 1380, 1, "yc-hair-frizz-c");
    }
  }
  emit("color_tones.done", { ...camilleScan.color_tones, as_of: clock.now() }, 1);
  emit("skin_hd.done", { scores: camilleScan.skin, as_of: clock.now() }, 1);
  emit("hair_diagnostics.done", { ...camilleScan.hair, as_of: clock.now() }, 1);
  emit("face_attributes.done", { shape: camilleScan.face.shape, ratios: camilleScan.face.ratios, as_of: clock.now() }, 1);
  state("plan", "face_attributes");
  emit("plan.recommended", { treatment_classes: ["heat", "none"], services: ["SVC-SMOOTH", "SVC-CLARIFY"], products: ["KER-CURL", "LRP-EFF"], total_cents: 24900, rebook_weeks: 6, engine: "recommend_plan@pure" }, 1);
  state("simulations", "plan");
  toolCalled(emit, "AI_Skin_simulation", "mcp/beauty", 3210, 1, "yc-render-skin-c");
  emit("simulation.rendered", { tool: "AI_Skin_simulation", treatment: "clarifying", cache: "miss", as_of: clock.now() }, 1);
  state("price", "simulations");
  toolCalled(emit, "google_shopping", "rest/serpapi", 860, 1, "serp-shop-c");
  emit("price.snapshot", { sku_code: "KER-CURL", min_cents: 2990, median_cents: 3390, max_cents: 3990, salon_price_cents: 3600, action: "match", as_of: clock.now() }, 1);
  state("consent", "price");
  emit("consent.template_selected", { template_id: "tpl_fixture_consent_heat", treatment_classes: ["heat"], allergens: ["latex"], jurisdiction: "FR" }, 1);
  toolCalled(emit, "generate", "rest/doctavian", 2380, 1, "doctavian-consent-camille");
  emit("consent.generated", { template_id: "tpl_fixture_consent_heat", document_id: "doc-0139", pages: 3, as_of: clock.now() }, 1);
  toolCalled(emit, "extract", "rest/nutrient", 2910, 1, "nutrient-intake-adversarial");
  emit("quarantined", { source: "intake", file: "intake-03-adversarial.png", reasons: ["instruction_like_text: ignore previous instructions"], step: "intake.extracted" }, 1);
  emit("needs_attention", { failing_step: "intake.extracted", reason: "quarantined", downstream_halted: true }, 1);
  state("needs_attention", "consent");
  events.push(...own);
  return own;
}

async function buildAudit(events: ConsultationEvent[]): Promise<AuditRow[]> {
  const rows: AuditRow[] = [];
  let prev = GENESIS_HASH;
  for (const ev of events) {
    const payload_hash = await payloadHash(ev.payload as never);
    const partial = { prev_hash: prev, actor: ev.actor, action: ev.type, payload_hash, ts: ev.ts };
    const hash = await chainHash(partial);
    rows.push({ id: ev.id, hash, ...partial });
    prev = hash;
  }
  return rows;
}

const PAGE = { width: 595, height: 842, top: 158, rowHeight: 15, columns: [42, 92, 340, 500], widths: [46, 244, 156, 60] };

function priceListExtractions(): ExtractionRow[] {
  const lowConfidence = new Map<string, { field: number; confidence: number }>([
    ["KER-DISC-MASK", { field: 3, confidence: 0.71 }],
    ["SVC-BROWLAM", { field: 1, confidence: 0.79 }],
    ["MAJ-6.66", { field: 0, confidence: 0.82 }],
  ]);
  return skus.map((s, i) => {
    const y = PAGE.top + i * PAGE.rowHeight;
    const low = lowConfidence.get(s.code);
    const values = [s.code, s.name, s.brand, (s.salon_price_cents / 100).toFixed(2).replace(".", ",")];
    const names = ["code", "name", "brand", "price"];
    const fields = values.map((value, f) => ({
      name: `row_${i + 1}_${names[f]}`,
      value,
      confidence: low && low.field === f ? low.confidence : Number((0.91 + ((i * 7 + f * 3) % 8) / 100).toFixed(2)),
      page: 1,
      bbox: [PAGE.columns[f], y, PAGE.widths[f], 12] as [number, number, number, number],
    }));
    return { id: `ext-pl-${String(i + 1).padStart(2, "0")}`, source: "price_list", file: "price_list.pdf", needs_review: Boolean(low), status: "pending", fields };
  });
}

function invoiceExtractions(): ExtractionRow[] {
  const header = (n: string, supplier: string, date: string, subtotal: string, vat: string, total: string, base: number) => [
    { name: "invoice_number", value: n, confidence: base, page: 1, bbox: [400, 96, 150, 12] as [number, number, number, number] },
    { name: "supplier_name", value: supplier, confidence: base, page: 1, bbox: [42, 60, 220, 14] as [number, number, number, number] },
    { name: "invoice_date", value: date, confidence: base - 0.02, page: 1, bbox: [400, 112, 120, 12] as [number, number, number, number] },
    { name: "subtotal", value: subtotal, confidence: base, page: 1, bbox: [440, 620, 110, 12] as [number, number, number, number] },
    { name: "vat_rate", value: "20%", confidence: base, page: 1, bbox: [440, 636, 110, 12] as [number, number, number, number] },
    { name: "vat_amount", value: vat, confidence: base - 0.01, page: 1, bbox: [440, 652, 110, 12] as [number, number, number, number] },
    { name: "total", value: total, confidence: base, page: 1, bbox: [440, 672, 110, 14] as [number, number, number, number] },
  ];
  return [
    { id: "ext-inv-01", source: "invoice", file: "inv-0001-loreal.pdf", needs_review: false, status: "confirmed", fields: header("LP-2026-0812", "L'Oréal Professionnel Paris", "2026-08-12", "1 482,00 €", "296,40 €", "1 778,40 €", 0.97) },
    { id: "ext-inv-02", source: "invoice", file: "inv-0002-olaplex-scanned.pdf", needs_review: false, status: "confirmed", fields: header("OLX-77812", "Olaplex EU B.V.", "2026-08-19", "936,00 €", "187,20 €", "1 123,20 €", 0.89) },
    { id: "ext-inv-03", source: "invoice", file: "inv-0003-bad-math.pdf", needs_review: true, status: "rejected", fields: header("KD-44190", "Kérastase Distribution", "2026-08-26", "1 214,00 €", "242,80 €", "1 468,80 €", 0.95) },
  ];
}

function intakeExtractions(): ExtractionRow[] {
  const form = (name: string, date: string, allergies: string, meds: string, prev: string, base: number) => [
    { name: "name", value: name, confidence: base, page: 1, bbox: [120, 140, 300, 22] as [number, number, number, number] },
    { name: "date", value: date, confidence: base - 0.03, page: 1, bbox: [120, 176, 160, 22] as [number, number, number, number] },
    { name: "allergies", value: allergies, confidence: base - 0.05, page: 1, bbox: [120, 232, 380, 22] as [number, number, number, number] },
    { name: "medications", value: meds, confidence: base - 0.06, page: 1, bbox: [120, 288, 380, 22] as [number, number, number, number] },
    { name: "previous_chemical_services", value: prev, confidence: base - 0.04, page: 1, bbox: [120, 344, 380, 22] as [number, number, number, number] },
    { name: "pregnancy", value: "N", confidence: base, page: 1, bbox: [120, 400, 60, 22] as [number, number, number, number] },
    { name: "photo_consent", value: "Y", confidence: base, page: 1, bbox: [120, 456, 60, 22] as [number, number, number, number] },
  ];
  return [
    { id: "ext-int-01", source: "intake", file: "intake-01-amira.png", needs_review: false, status: "confirmed", fields: form("Amira Benali", "03/09/2026", "PPD, fragrance", "none", "Colour, March 2026", 0.93) },
    { id: "ext-int-02", source: "intake", file: "intake-02-jules.png", needs_review: false, status: "confirmed", fields: form("Jules Moreau", "03/09/2026", "none", "none", "Gloss, June 2026", 0.92) },
    { id: "ext-int-03", source: "intake", file: "intake-03-adversarial.png", needs_review: true, status: "rejected", fields: form("Camille Roux", "03/09/2026", "latex", "none", "none", 0.9) },
  ];
}

function onboardingSteps(): OnboardingStep[] {
  const t = (m: number) => `${DAY}T07:${String(m).padStart(2, "0")}:00.000Z`;
  return [
    { name: "Parse prompt", status: "done", detail: "Atelier Noor · 14 Rue de Turenne, 75003 Paris · hair, skin, brows · 3 chairs", ts: t(0) },
    { name: "Domain", status: "done", detail: "ateliernoor.com · search → availability → create (idempotency key)", ts: t(1) },
    { name: "DNS", status: "done", detail: "A @ → 76.76.21.21 · CNAME www → static.xano.io", ts: t(1) },
    { name: "Forwarding", status: "done", detail: "www → apex · hello@ → noor@example.com", ts: t(2) },
    { name: "Templates", status: "done", detail: "Doctavian: 4 consent branches, allergen loop, FR/US switch, aftercare, price list", ts: t(4) },
    { name: "Platform agreement", status: "done", detail: "Foxit envelope env-0001 · red-team 401 logged · signed by Noor Haddad", ts: t(6) },
    { name: "Catalog", status: "done", detail: "Nutrient: 42 SKUs from price_list.pdf (3 to review) · 3 invoices · 1 quarantined", ts: t(9) },
    { name: "Prices", status: "done", detail: "SerpApi Google Shopping · 42 snapshots · 2 alerts", ts: t(14) },
    { name: "Shade map", status: "done", detail: `${salon.color_line} · ${shadeMap.length} shades mapped to YouCam hair colour inputs`, ts: t(14) },
    { name: "Storefront", status: "done", detail: "https://ateliernoor.com · 21.8 KB · Book → Mirror", ts: t(16) },
  ];
}

function priceWatch(): PriceWatchRow[] {
  const asOf = `${DAY}T02:10:00.000Z`;
  const row = (code: string, median: number): PriceWatchRow => {
    const s = sku(code);
    const delta = Math.round(((s.salon_price_cents - median) * 100) / median);
    return { sku_code: code, name: s.name, salon_price_cents: s.salon_price_cents, median_cents: median, delta_pct: delta, alert: Math.abs(delta) > 15, as_of: asOf };
  };
  return [row("OLX-03", 2790), row("OLX-06", 3050), row("KER-DISC-MASK", 5600), row("RED-FRIZZ", 2450), row("SKC-CEF", 14990), row("LRP-CICA", 1390), row("LOR-METAL", 2790), row("RED-ABC", 2890)];
}

function attribution(): AttributionRow[] {
  return [
    { stylist: "Léa", chair: 1, consultations: 4, orders: 3, revenue_cents: 41200 },
    { stylist: "Marc", chair: 2, consultations: 5, orders: 4, revenue_cents: 58900 },
  ];
}

function cost(): Snapshot["cost"] {
  const rows = (entries: [string, string, number][]): CostRow[] => entries.map(([vendor, unit, count]) => ({ vendor, unit, count }));
  return {
    per_consultation: rows([["Perfect Corp", "YouCam units", 8], ["SerpApi", "searches", 5], ["Foxit", "credits", 8], ["Nutrient", "operations", 2], ["Doctavian", "generations", 1], ["Xano", "writes", 46]]),
    per_onboarding: rows([["name.com", "API calls", 6], ["Doctavian", "generations", 6], ["Nutrient", "operations", 5], ["Foxit", "credits", 9], ["SerpApi", "searches", 42], ["Xano", "writes", 88]]),
    weekly_refresh: rows([["SerpApi", "searches", 42], ["Xano", "task runs", 7]]),
  };
}

async function main(): Promise<void> {
  const all: ConsultationEvent[] = [];
  buildOnboarding(new Clock(`${DAY}T07:00:00.000Z`), all);
  const camille = buildCamille(new Clock(`${DAY}T09:04:40.000Z`), all);
  const jules = buildJules(new Clock(`${DAY}T12:07:00.000Z`), all);
  const amira = buildAmira(new Clock(`${DAY}T12:31:30.000Z`), all);
  all.sort((a, b) => a.ts.localeCompare(b.ts));
  const audit = await buildAudit(all);

  const consultations: Record<string, Consultation> = {
    "cons-0001": {
      id: "cons-0001", client: { id: "cl-01", name: "Amira Benali" }, stylist: "Marc", chair: 2, state: "done", failing_step: null,
      started_at: amira[0].ts, events: amira, scan: amiraToday, previous_scan: amiraPrevious, plan: amiraPlan, simulations: amiraSimulations,
      prices: amiraPrices,
      news: { query: "Olaplex No. 3 rappel recall", clean: true, flags: [], as_of: `${DAY}T12:36:06.000Z` },
      reviews: [
        { place_id: "ChIJ-marais-01", competitor: "Salon Vertigo Marais", summary: "Clients praise the colourists for blonde work but three reviews in the last quarter mention brassiness after four weeks and no aftercare advice.", quotes: ["Belle couleur mais elle a viré orange en un mois.", "On ne m'a rien conseillé pour entretenir."], as_of: `${DAY}T12:36:14.000Z` },
        { place_id: "ChIJ-marais-02", competitor: "Maison Kaï Coiffure", summary: "Strong on cuts; colour reviews mention long waits and a rushed consultation.", quotes: ["Coupe parfaite, consultation expédiée.", "Une heure d'attente pour la couleur."], as_of: `${DAY}T12:36:19.000Z` },
      ],
      consent: { template_id: "tpl_fixture_consent_combined", treatment_classes: ["chemical", "heat"], envelope: { envelope_id: "env-0014", state: "signed", session_url: null, expires_at: null, sealed_hash: sha("amira-bundle-seal") } },
      order: { id: "ord-0051", total_cents: 14700, items: [...amiraPlan.products] },
      booking: { id: "bk-0088", when: `${RETURN_DAY}T12:30:00.000Z`, service: "Colour service (Majirel)" },
    },
    "cons-0002": {
      id: "cons-0002", client: { id: "cl-04", name: "Jules Moreau" }, stylist: "Léa", chair: 1, state: "price", failing_step: null,
      started_at: jules[0].ts, events: jules, scan: julesScan, previous_scan: null,
      plan: {
        treatment_classes: ["chemical"], services: [item("SVC-GLOSS", "chemical"), item("SVC-VOLCUT", "none")], products: [item("KER-VOL", "none"), item("LRP-TOL", "none")], total_cents: 16200, rebook_weeks: 6,
        facts: ["Straight, low density hair; volume cut and a volumising bain", "Redness 62; barrier cream, no actives today", "Oblong face; a soft fringe shortens the length"],
        prose: "Jules, we keep your ash tone with a gloss and open the cut up for volume. Your skin is a little reactive today, so we stay with a barrier cream and nothing active.",
      },
      simulations: [
        { tool: "AI_Hair_Color_Virtual_Try_On", server: "mcp/beauty", tab: "hair", sku_code: "MAJ-8.1", hex: "#B5A58E", label: "8.1 Light Blonde Ash", before_url: "/renders/jules-before.svg", after_url: "/renders/jules-hair-81.svg", as_of: `${DAY}T12:09:40.000Z` },
        { tool: "AI_Hair_Volume_Virtual_Try_On", server: "mcp/beauty", tab: "style", sku_code: null, hex: null, label: "Volume · level 2", before_url: "/renders/jules-before.svg", after_url: "/renders/jules-volume.svg", as_of: `${DAY}T12:09:44.000Z` },
      ],
      prices: [priceRow("KER-VOL", 2790, 3090, 3590, "match", "within 10% of market median", `${DAY}T12:10:02.000Z`)],
      news: null, reviews: [], consent: null, order: null, booking: null,
    },
    "cons-0003": {
      id: "cons-0003", client: { id: "cl-07", name: "Camille Roux" }, stylist: "Marc", chair: 2, state: "needs_attention", failing_step: "intake.extracted",
      started_at: camille[0].ts, events: camille, scan: camilleScan, previous_scan: null,
      plan: {
        treatment_classes: ["heat", "none"], services: [item("SVC-SMOOTH", "heat"), item("SVC-CLARIFY", "none")], products: [item("KER-CURL", "none"), item("LRP-EFF", "none")], total_cents: 24900, rebook_weeks: 6,
        facts: ["Curly, high density, frizz 71; smoothing treatment", "Acne 64 and oiliness 68; clarifying facial", "Heart face; chin-length keeps balance"],
        prose: "Camille, we calm the frizz with a smoothing treatment and keep your curl pattern. A clarifying facial today and Effaclar at home.",
      },
      simulations: [{ tool: "AI_Skin_simulation", server: "mcp/beauty", tab: "skin", sku_code: null, hex: null, label: "Skin plan · clarifying", before_url: "/renders/camille-before.svg", after_url: "/renders/camille-skin-plan.svg", as_of: `${DAY}T09:06:30.000Z` }],
      prices: [priceRow("KER-CURL", 2990, 3390, 3990, "match", "within 10% of market median", `${DAY}T09:06:52.000Z`)],
      news: null, reviews: [],
      consent: { template_id: "tpl_fixture_consent_heat", treatment_classes: ["heat"], envelope: { envelope_id: "env-0013", state: "draft", session_url: null, expires_at: null, sealed_hash: null } },
      order: null, booking: null,
    },
  };

  const chairs: Chair[] = [
    { chair: 1, stylist: "Léa", client: { id: "cl-04", name: "Jules Moreau" }, consultation_id: "cons-0002", state: "price", time: "14:05" },
    { chair: 2, stylist: "Marc", client: { id: "cl-01", name: "Amira Benali" }, consultation_id: "cons-0001", state: "done", time: "14:30" },
    { chair: 3, stylist: "Unassigned", client: null, consultation_id: null, state: "free", time: "—" },
  ];

  const quarantine: QuarantineRow[] = [
    { id: "q-0001", source: "invoice", file: "inv-0003-bad-math.pdf", reasons: ["arithmetic_mismatch: line 3 qty x unit_price != amount (diff 1200 cents)", "arithmetic_mismatch: subtotal + vat != total"], ts: `${DAY}T07:09:20.000Z` },
    { id: "q-0002", source: "intake", file: "intake-03-adversarial.png", reasons: ["instruction_like_text: ignore previous instructions"], ts: camille.find((e) => e.type === "quarantined")?.ts ?? `${DAY}T09:07:00.000Z` },
  ];

  const snapshot: Snapshot = {
    generated_at: `${DAY}T13:12:00.000Z`,
    salon,
    shade_map: shadeMap,
    skus,
    chairs,
    consultations,
    audit,
    extractions: [...priceListExtractions(), ...invoiceExtractions(), ...intakeExtractions()],
    onboarding: onboardingSteps(),
    price_watch: priceWatch(),
    attribution: attribution(),
    cost: cost(),
    quarantine,
  };

  const out = resolve(here, "..", "src", "fixtures", "snapshot.json");
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, JSON.stringify(snapshot, null, 2) + "\n", "utf-8");
  process.stdout.write(`snapshot: ${all.length} events, ${audit.length} audit rows → ${out}\n`);
}

await main();
