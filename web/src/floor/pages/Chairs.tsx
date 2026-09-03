import { StateChip } from "../components/Chips";
import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Empty, WithSnapshot } from "../components/States";
import { formatDate } from "../format";
import { navigate } from "../router";
import type { SnapshotState } from "../useSnapshot";
import type { Chair } from "../../lib/snapshot";

const COLUMNS: Column<Chair>[] = [
  { key: "chair", header: "Chair", render: (c) => `Chair ${c.chair}` },
  { key: "stylist", header: "Stylist", render: (c) => c.stylist },
  { key: "client", header: "Client", render: (c) => c.client?.name ?? <span className="muted">—</span> },
  { key: "state", header: "State", render: (c) => <StateChip state={c.state} /> },
  { key: "time", header: "Started", render: (c) => <span className="mono">{c.time}</span> },
  { key: "id", header: "Consultation", render: (c) => <span className="mono">{c.consultation_id ?? "—"}</span> },
];

export function Chairs({ snapshot }: { snapshot: SnapshotState }) {
  return (
    <>
      <PageHeader kicker="Today" title="Chairs" lede="Every chair, its stylist, and where the consultation stands. Enter opens the trace." />
      <WithSnapshot snapshot={snapshot} label="Loading chairs">
        {(data) =>
          data.chairs.length === 0 ? (
            <Empty>No chairs yet. Onboarding creates them from the salon prompt.</Empty>
          ) : (
            <section className="section">
              <div className="section__head">
                <h2>{formatDate(data.generated_at)}</h2>
                <span className="section__meta">
                  {data.chairs.filter((c) => c.consultation_id).length} of {data.chairs.length} chairs in consultation
                </span>
              </div>
              <DataTable
                caption="Chairs today"
                columns={COLUMNS}
                rows={data.chairs}
                rowKey={(c) => String(c.chair)}
                rowClass={(c) => (c.state === "needs_attention" ? "row--alert" : undefined)}
                onSelect={(c) => {
                  if (c.consultation_id) navigate({ page: "consultation", id: c.consultation_id });
                }}
              />
            </section>
          )
        }
      </WithSnapshot>
    </>
  );
}
