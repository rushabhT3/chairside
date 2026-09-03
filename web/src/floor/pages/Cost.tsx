import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { WithSnapshot } from "../components/States";
import type { SnapshotState } from "../useSnapshot";
import type { CostRow } from "../../lib/snapshot";

const COLUMNS: Column<CostRow>[] = [
  { key: "vendor", header: "Vendor", render: (r) => r.vendor },
  { key: "unit", header: "Unit", render: (r) => r.unit },
  { key: "count", header: "Count", numeric: true, render: (r) => r.count },
];

function Block({ title, meta, rows }: { title: string; meta: string; rows: CostRow[] }) {
  return (
    <section className="section">
      <div className="section__head">
        <h2>{title}</h2>
        <span className="section__meta">{meta}</span>
      </div>
      <DataTable caption={title} columns={COLUMNS} rows={rows} rowKey={(r) => `${r.vendor}-${r.unit}`} />
    </section>
  );
}

export function Cost({ snapshot }: { snapshot: SnapshotState }) {
  return (
    <>
      <PageHeader kicker="Metered units · from scripts/cost_report.py" title="Cost" lede="What one consultation, one onboarding, and one weekly refresh consume from each sponsor's meter. Fixtures mode consumes nothing." />
      <WithSnapshot snapshot={snapshot} label="Loading cost report">
        {(data) => (
          <>
            <Block title="Per consultation" meta="Act 2 · scan to rebook" rows={data.cost.per_consultation} />
            <Block title="Per onboarding" meta="Act 1 · prompt to storefront" rows={data.cost.per_onboarding} />
            <Block title="Weekly refresh" meta="Xano price_refresh task · snapshots older than 7 days" rows={data.cost.weekly_refresh} />
          </>
        )}
      </WithSnapshot>
    </>
  );
}
