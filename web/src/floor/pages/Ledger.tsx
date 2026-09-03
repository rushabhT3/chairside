import { useState } from "react";
import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Empty, WithSnapshot } from "../components/States";
import { formatTime, shortHash } from "../format";
import { verifyChain, type AuditRow, type VerifyResult } from "../../lib/hashchain";
import type { SnapshotState } from "../useSnapshot";
import type { QuarantineRow } from "../../lib/snapshot";

type Verification = { status: "idle" } | { status: "running" } | { status: "done"; result: VerifyResult };

function rowClass(row: AuditRow): string | undefined {
  if (row.action === "redteam.esign_denied") return "row--alert";
  if (row.action === "quarantined" || row.action === "needs_attention") return "row--warn";
  if (row.action === "envelope.signed" || row.action === "agreement.signed" || row.action === "catalog.sealed" || row.action === "bundle.sealed") return "row--ok";
  return undefined;
}

function columns(quarantine: QuarantineRow[]): Column<AuditRow>[] {
  const reasonFor = (row: AuditRow) => quarantine.find((q) => q.ts === row.ts)?.reasons.join("; ");
  return [
    { key: "ts", header: "Time", render: (r) => <span className="mono">{formatTime(r.ts)}</span> },
    { key: "actor", header: "Actor", render: (r) => r.actor },
    {
      key: "action",
      header: "Action",
      render: (r) => (
        <>
          {r.action}
          {r.action === "redteam.esign_denied" && <span className="muted"> · agent process presented a PDF Services token to eSign · 401</span>}
          {r.action === "quarantined" && reasonFor(r) && <span className="muted"> · {reasonFor(r)}</span>}
        </>
      ),
    },
    { key: "payload", header: "Payload hash", render: (r) => <span className="mono">{shortHash(r.payload_hash)}</span> },
    { key: "prev", header: "Prev", render: (r) => <span className="mono">{shortHash(r.prev_hash)}</span> },
    { key: "hash", header: "Hash", render: (r) => <span className="mono">{shortHash(r.hash)}</span> },
  ];
}

export function Ledger({ snapshot }: { snapshot: SnapshotState }) {
  const [verification, setVerification] = useState<Verification>({ status: "idle" });
  const verify = (rows: AuditRow[]) => {
    setVerification({ status: "running" });
    verifyChain(rows).then((result) => setVerification({ status: "done", result }));
  };
  return (
    <>
      <PageHeader
        kicker="Audit chain · SHA-256 over canonical JSON"
        title="Ledger"
        lede="Every event appends an audit row whose hash covers the previous row. Verify recomputes the whole chain in this browser; nothing is trusted from the server."
        actions={
          snapshot.status === "ready" && (
            <button type="button" className="button button--primary" onClick={() => verify(snapshot.data.audit)} disabled={verification.status === "running"}>
              {verification.status === "running" ? "Verifying…" : "Verify chain"}
            </button>
          )
        }
      />
      <WithSnapshot snapshot={snapshot} label="Loading ledger">
        {(data) =>
          data.audit.length === 0 ? (
            <Empty>The ledger is empty. The first event is written when onboarding starts.</Empty>
          ) : (
            <section className="section">
              {verification.status === "done" && (
                <p className={verification.result.ok ? "status status--ok" : "status status--err"} role="status">
                  <span className={verification.result.ok ? "dot dot--ok" : "dot dot--err"} aria-hidden="true" />
                  {verification.result.ok ? `Chain verified · ${verification.result.checked} rows` : `Chain broken at row ${verification.result.firstBadIndex} · ${verification.result.reasons.join("; ")}`}
                </p>
              )}
              <div className="section__head">
                <h2>{data.audit.length} rows</h2>
                <span className="section__meta">genesis → {shortHash(data.audit[data.audit.length - 1].hash)}</span>
              </div>
              <DataTable caption="Audit events" columns={columns(data.quarantine)} rows={data.audit} rowKey={(r) => r.id} rowClass={rowClass} />
            </section>
          )
        }
      </WithSnapshot>
    </>
  );
}
