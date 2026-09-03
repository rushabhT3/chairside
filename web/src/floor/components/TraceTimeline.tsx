import type { ConsultationEvent, ToolCalledPayload } from "../../lib/events";
import { formatTime, shortHash } from "../format";
import { ServerChip } from "./Chips";

const MAX_FACT_CHARS = 140;

function factsOf(payload: Record<string, unknown>): string {
  const parts = Object.entries(payload)
    .filter(([k]) => k !== "as_of")
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : typeof v === "object" && v !== null ? "…" : String(v)}`);
  const line = parts.join(" · ");
  return line.length > MAX_FACT_CHARS ? `${line.slice(0, MAX_FACT_CHARS)}…` : line;
}

function itemClass(ev: ConsultationEvent): string {
  if (ev.type === "needs_attention" || ev.type === "quarantined" || ev.type === "redteam.esign_denied") {
    return "trace__item trace__item--attention";
  }
  if (ev.type === "state.changed") return "trace__item trace__item--state";
  if (ev.type === "tool.called") return "trace__item trace__item--tool";
  return "trace__item";
}

export function TraceTimeline({ events }: { events: ConsultationEvent[] }) {
  if (events.length === 0) return <p className="empty">No events yet. The first scan takes about 20 seconds.</p>;
  return (
    <ol className="trace" aria-label="Trace timeline">
      {events.map((ev) => (
        <li key={ev.id} className={itemClass(ev)}>
          <span className="trace__time">{formatTime(ev.ts)}</span>
          <div className="trace__body">
            {ev.type === "tool.called" ? (
              <ToolLine payload={ev.payload as unknown as ToolCalledPayload} />
            ) : (
              <>
                <div className="trace__line">
                  <span>{ev.type}</span>
                  {ev.actor !== "agent" && <span className="chip">{ev.actor}</span>}
                </div>
                <span className="trace__facts">{factsOf(ev.payload)}</span>
              </>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

function ToolLine({ payload }: { payload: ToolCalledPayload }) {
  return (
    <>
      <div className="trace__line">
        <span className="mono">{payload.tool}</span>
        <ServerChip server={payload.server} />
      </div>
      <span className="trace__facts">
        {payload.latency_ms} ms · {payload.units} {payload.units === 1 ? "unit" : "units"} ·{" "}
        <span className="mono">{shortHash(payload.result_sha256)}</span>
      </span>
    </>
  );
}
