import { PageHeader } from "../components/PageHeader";
import { Empty, WithSnapshot } from "../components/States";
import { formatClock } from "../format";
import type { SnapshotState } from "../useSnapshot";
import type { OnboardingStep } from "../../lib/snapshot";

const MARK: Record<OnboardingStep["status"], { glyph: string; className: string }> = {
  done: { glyph: "✓", className: "step__mark step__mark--done" },
  running: { glyph: "…", className: "step__mark" },
  pending: { glyph: "·", className: "step__mark" },
  failed: { glyph: "✕", className: "step__mark step__mark--failed" },
};

export function Onboarding({ snapshot }: { snapshot: SnapshotState }) {
  return (
    <>
      <PageHeader kicker="Act 1 · one prompt" title="Onboarding" lede="Open Chairside for Atelier Noor, 14 Rue de Turenne, 75003 Paris. Hair, skin, brows. Three chairs. Owner: Noor Haddad, noor@example.com." />
      <WithSnapshot snapshot={snapshot} label="Loading onboarding">
        {(data) =>
          data.onboarding.length === 0 ? (
            <Empty>No onboarding run yet. Type the prompt into the agent to begin.</Empty>
          ) : (
            <section className="section">
              <div className="section__head">
                <h2>{data.salon.name}</h2>
                <span className="section__meta">
                  {data.onboarding.filter((s) => s.status === "done").length} of {data.onboarding.length} steps · {data.salon.domain}
                </span>
              </div>
              <ol className="steps" aria-label="Onboarding steps">
                {data.onboarding.map((s) => (
                  <li key={s.name} className="step">
                    <span className={MARK[s.status].className} aria-label={s.status}>
                      {MARK[s.status].glyph}
                    </span>
                    <span>
                      {s.name}
                      <span className="step__detail">{s.detail}</span>
                    </span>
                    <span className="step__time">{s.ts ? formatClock(s.ts) : "—"}</span>
                  </li>
                ))}
              </ol>
            </section>
          )
        }
      </WithSnapshot>
    </>
  );
}
