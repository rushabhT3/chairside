// Keep in sync with agent/chairside_agent/events.py (docs/contracts.md section 2).

export const EVENT_TYPES = [
  "capture.uploaded",
  "color_tones.done",
  "skin_hd.done",
  "hair_diagnostics.done",
  "face_attributes.done",
  "plan.recommended",
  "simulation.rendered",
  "price.identified",
  "price.snapshot",
  "news.checked",
  "reviews.fetched",
  "consent.template_selected",
  "consent.generated",
  "intake.extracted",
  "envelope.requested",
  "envelope.sent",
  "envelope.signed",
  "bundle.sealed",
  "plan.accepted",
  "order.created",
  "booking.created",
  "state.changed",
  "needs_attention",
  "quarantined",
  "redteam.esign_denied",
  "data.tombstoned",
  "tool.called",
  "onboarding.parsed",
  "domain.searched",
  "domain.available",
  "domain.created",
  "dns.created",
  "forwarding.created",
  "documents.generated",
  "agreement.requested",
  "agreement.signed",
  "catalog.extracted",
  "catalog.review_queued",
  "catalog.sealed",
  "prices.seeded",
  "shade_map.seeded",
  "storefront.deployed",
  "onboarding.done",
] as const;

export type EventType = (typeof EVENT_TYPES)[number];
export type Actor = "agent" | "owner" | "stylist" | "client" | "system";

export type ToolServer =
  | "mcp/beauty"
  | "mcp/fashion"
  | "mcp/foxit"
  | "rest/serpapi"
  | "rest/namecom"
  | "rest/doctavian"
  | "rest/nutrient"
  | "rest/xano"
  | "commit/xano";

export interface ToolCalledPayload {
  tool: string;
  server: ToolServer;
  latency_ms: number;
  units: number;
  result_sha256: string;
  as_of: string;
}

export interface ConsultationEvent<P = Record<string, unknown>> {
  id: string;
  consultation_id: string | null;
  salon_id: string;
  type: EventType;
  payload: P;
  ts: string;
  actor: Actor;
}

export const CONSULTATION_STATES = [
  "capture",
  "color_tones",
  "skin_hd",
  "hair_diagnostics",
  "face_attributes",
  "plan",
  "simulations",
  "price",
  "consent",
  "commit",
  "done",
  "needs_attention",
] as const;

export type ConsultationState = (typeof CONSULTATION_STATES)[number];
