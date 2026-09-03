import type { ConsultationState } from "../../lib/events";
import { formatConfidence } from "../format";

const CONFIDENCE_THRESHOLD = 0.85;

export function ServerChip({ server }: { server: string }) {
  const kind = server.startsWith("mcp/beauty")
    ? "chip chip--server-beauty"
    : server.startsWith("mcp/fashion")
      ? "chip chip--server-fashion"
      : server.startsWith("commit/")
        ? "chip chip--server-commit"
        : "chip";
  return <span className={kind}>{server}</span>;
}

const STATE_DOT: Record<ConsultationState | "free", string> = {
  capture: "dot dot--live",
  color_tones: "dot dot--live",
  skin_hd: "dot dot--live",
  hair_diagnostics: "dot dot--live",
  face_attributes: "dot dot--live",
  plan: "dot dot--live",
  simulations: "dot dot--live",
  price: "dot dot--live",
  consent: "dot dot--live",
  commit: "dot dot--live",
  done: "dot dot--ok",
  needs_attention: "dot dot--err",
  free: "dot dot--free",
};

const STATE_LABEL: Record<ConsultationState | "free", string> = {
  capture: "Capturing",
  color_tones: "Colour tones",
  skin_hd: "Skin",
  hair_diagnostics: "Hair",
  face_attributes: "Face shape",
  plan: "Planning",
  simulations: "Simulating",
  price: "Pricing",
  consent: "Consent",
  commit: "Committing",
  done: "Done",
  needs_attention: "Needs attention",
  free: "Free",
};

export function StateChip({ state }: { state: ConsultationState | "free" }) {
  return (
    <span className="chip">
      <span className={STATE_DOT[state]} aria-hidden="true" />
      {STATE_LABEL[state]}
    </span>
  );
}

export function ConfidenceChip({ confidence }: { confidence: number }) {
  const low = confidence < CONFIDENCE_THRESHOLD;
  return (
    <span className="chip" aria-label={`confidence ${formatConfidence(confidence)}${low ? ", needs review" : ""}`}>
      <span className={low ? "dot dot--err" : "dot dot--ok"} aria-hidden="true" />
      {formatConfidence(confidence)}
    </span>
  );
}
