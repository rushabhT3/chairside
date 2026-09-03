import { formatDate } from "../../lib/format";
import { Button } from "../components/Button";
import { Notice } from "../components/Notice";
import { Skeleton } from "../components/Skeleton";
import { navigate } from "../router";
import { useMirrorState } from "../store";

const invertedReadings = new Set(["firmness", "radiance", "moisture"]);

function labelFor(key: string): string {
  return key.replace(/_/g, " ");
}

function direction(key: string, delta: number): "better" | "worse" | "same" {
  if (delta === 0) return "same";
  const improved = invertedReadings.has(key) ? delta > 0 : delta < 0;
  return improved ? "better" : "worse";
}

const arrows = { better: "↓", worse: "↑", same: "→" } as const;

export function Return() {
  const { status, consultation } = useMirrorState();
  if (status !== "ready" || !consultation) return <Skeleton lines={8} label="Comparing scans" />;

  const { scan, previous_scan: previous, plan } = consultation;
  if (!scan || !previous) {
    return (
      <Notice title="No earlier scan to compare." action={{ label: "Back to welcome", onClick: () => navigate("welcome") }}>
        <p>Come back in six weeks and Mirror shows what changed.</p>
      </Notice>
    );
  }

  const rows = Object.keys(scan.skin).map((key) => {
    const delta = scan.skin[key] - (previous.skin[key] ?? scan.skin[key]);
    return { key, delta, dir: direction(key, delta), today: scan.skin[key], before: previous.skin[key] };
  });

  return (
    <section className="return">
      <p className="ticket-kicker">
        {formatDate(previous.ts)} → {formatDate(scan.ts)}
      </p>
      <h1 className="consent-title">What changed</h1>
      <ul className="deltas">
        {rows.map((row) => (
          <li key={row.key} className="delta" data-dir={row.dir}>
            <span className="delta-label">{labelFor(row.key)}</span>
            <span className="delta-values">
              {row.before} → {row.today}
            </span>
            <span className="delta-arrow" aria-label={row.dir}>
              {invertedReadings.has(row.key) ? (row.dir === "better" ? "↑" : row.dir === "worse" ? "↓" : "→") : arrows[row.dir]}
              {row.delta !== 0 ? ` ${Math.abs(row.delta)}` : ""}
            </span>
          </li>
        ))}
      </ul>
      {plan && (
        <section className="plan-group" aria-label="What changed in your plan">
          <h2 className="ticket-heading">What changed in your plan</h2>
          <ul className="facts-list">
            {plan.facts.map((fact) => (
              <li key={fact}>{fact}</li>
            ))}
          </ul>
        </section>
      )}
      <Button variant="secondary" onClick={() => navigate("welcome")}>
        Done
      </Button>
    </section>
  );
}
