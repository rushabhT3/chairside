import type { AuditRow } from "./hashchain";
import type { ConsultationEvent, ConsultationState } from "./events";

export type Undertone = "warm" | "cool" | "neutral";
export type TreatmentClass = "chemical" | "heat" | "injectable" | "laser" | "none";

export interface Salon {
  id: string;
  name: string;
  address: string;
  city: string;
  postcode: string;
  country: string;
  jurisdiction: "FR" | "US";
  domain: string;
  owner: { name: string; email: string };
  stylists: { name: string; email: string }[];
  chairs: number;
  color_line: string;
}

export interface ShadeEntry {
  line: string;
  code: string;
  name: string;
  hex: string;
  undertone: Undertone;
  level: number;
}

export interface Sku {
  code: string;
  name: string;
  brand: string;
  salon_price_cents: number;
  shade_code: string | null;
  kind: "retail" | "backbar" | "service";
}

export interface ColorTones {
  skin_tone: string;
  undertone: Undertone;
  eye_color: string;
  hair_color_hex: string;
}

export interface Scan {
  scan_id: string;
  ts: string;
  color_tones: ColorTones;
  skin: Record<string, number>;
  hair: { type: string; frizz: number; density: string };
  face: { shape: string; ratios: Record<string, number> };
}

export interface PlanItem {
  code: string;
  name: string;
  price_cents: number;
  qty: number;
  treatment_class: TreatmentClass;
}

export interface Plan {
  treatment_classes: TreatmentClass[];
  services: PlanItem[];
  products: PlanItem[];
  total_cents: number;
  rebook_weeks: number;
  facts: string[];
  prose: string;
}

export interface Simulation {
  tool: string;
  server: string;
  tab: "hair" | "skin" | "style";
  sku_code: string | null;
  hex: string | null;
  label: string;
  before_url: string;
  after_url: string;
  as_of: string;
}

export interface PriceRow {
  sku_code: string;
  name: string;
  salon_price_cents: number;
  min_cents: number;
  median_cents: number;
  max_cents: number;
  as_of: string;
  action: "match" | "bundle" | "hold";
  reason: string;
}

export interface NewsCheck {
  query: string;
  clean: boolean;
  flags: { title: string; source: string; date: string; link: string }[];
  as_of: string;
}

export interface ReviewNote {
  place_id: string;
  competitor: string;
  summary: string;
  quotes: string[];
  as_of: string;
}

export interface Envelope {
  envelope_id: string;
  state: "draft" | "human_reviewed" | "sent" | "signed" | "expired";
  session_url: string | null;
  expires_at: string | null;
  sealed_hash: string | null;
}

export interface Consultation {
  id: string;
  client: { id: string; name: string };
  stylist: string;
  chair: number;
  state: ConsultationState;
  failing_step: string | null;
  started_at: string;
  events: ConsultationEvent[];
  scan: Scan | null;
  previous_scan: Scan | null;
  plan: Plan | null;
  simulations: Simulation[];
  prices: PriceRow[];
  news: NewsCheck | null;
  reviews: ReviewNote[];
  consent: { template_id: string; treatment_classes: TreatmentClass[]; envelope: Envelope } | null;
  order: { id: string; total_cents: number; items: PlanItem[] } | null;
  booking: { id: string; when: string; service: string } | null;
}

export interface Chair {
  chair: number;
  stylist: string;
  client: { id: string; name: string } | null;
  consultation_id: string | null;
  state: ConsultationState | "free";
  time: string;
}

export interface ExtractionField {
  name: string;
  value: string;
  confidence: number;
  page: number;
  bbox: [number, number, number, number];
}

export interface ExtractionRow {
  id: string;
  source: "price_list" | "invoice" | "intake";
  file: string;
  needs_review: boolean;
  status: "pending" | "confirmed" | "rejected";
  fields: ExtractionField[];
}

export interface OnboardingStep {
  name: string;
  status: "done" | "running" | "pending" | "failed";
  detail: string;
  ts: string | null;
}

export interface PriceWatchRow {
  sku_code: string;
  name: string;
  salon_price_cents: number;
  median_cents: number;
  delta_pct: number;
  alert: boolean;
  as_of: string;
}

export interface AttributionRow {
  stylist: string;
  chair: number;
  consultations: number;
  orders: number;
  revenue_cents: number;
}

export interface CostRow {
  vendor: string;
  unit: string;
  count: number;
}

export interface QuarantineRow {
  id: string;
  source: string;
  file: string;
  reasons: string[];
  ts: string;
}

export interface Snapshot {
  generated_at: string;
  salon: Salon;
  shade_map: ShadeEntry[];
  skus: Sku[];
  chairs: Chair[];
  consultations: Record<string, Consultation>;
  audit: AuditRow[];
  extractions: ExtractionRow[];
  onboarding: OnboardingStep[];
  price_watch: PriceWatchRow[];
  attribution: AttributionRow[];
  cost: { per_consultation: CostRow[]; per_onboarding: CostRow[]; weekly_refresh: CostRow[] };
  quarantine: QuarantineRow[];
}
