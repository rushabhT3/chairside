import { useMemo } from "react";
import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Empty, WithSnapshot } from "../components/States";
import { formatCents } from "../format";
import type { SnapshotState } from "../useSnapshot";
import type { AttributionRow } from "../../lib/snapshot";

type Role = "owner" | "stylist";

function demoRole(): { role: Role; stylist: string | null } {
  const params = new URLSearchParams(window.location.search);
  const role = params.get("role") === "stylist" ? "stylist" : "owner";
  return { role, stylist: params.get("stylist") };
}

const COLUMNS: Column<AttributionRow>[] = [
  { key: "stylist", header: "Stylist", render: (r) => r.stylist },
  { key: "chair", header: "Chair", render: (r) => `Chair ${r.chair}` },
  { key: "consultations", header: "Consultations", numeric: true, render: (r) => r.consultations },
  { key: "orders", header: "Orders", numeric: true, render: (r) => r.orders },
  { key: "revenue", header: "Revenue", numeric: true, render: (r) => formatCents(r.revenue_cents) },
];

export function Attribution({ snapshot }: { snapshot: SnapshotState }) {
  const scope = useMemo(demoRole, []);
  return (
    <>
      <PageHeader
        kicker={scope.role === "owner" ? "Owner view · every chair" : "Stylist view · own chair only"}
        title="Attribution"
        lede="Every order is attributed to the stylist and chair that closed it. Owners see the salon; stylists see themselves. Scope comes from the JWT role in live mode."
      />
      <WithSnapshot snapshot={snapshot} label="Loading attribution">
        {(data) => {
          const rows = scope.role === "owner" ? data.attribution : data.attribution.filter((r) => r.stylist === (scope.stylist ?? data.salon.stylists[0]?.name));
          if (rows.length === 0) return <Empty>No orders attributed yet.</Empty>;
          const revenue = rows.reduce((sum, r) => sum + r.revenue_cents, 0);
          return (
            <section className="section">
              <div className="stats">
                <div className="stat">
                  <span className="stat__value">{formatCents(revenue)}</span>
                  <span className="stat__label">revenue in scope</span>
                </div>
                <div className="stat">
                  <span className="stat__value">{rows.reduce((s, r) => s + r.orders, 0)}</span>
                  <span className="stat__label">orders</span>
                </div>
                <div className="stat">
                  <span className="stat__value">{rows.reduce((s, r) => s + r.consultations, 0)}</span>
                  <span className="stat__label">consultations</span>
                </div>
              </div>
              <DataTable caption="Attribution by stylist and chair" columns={COLUMNS} rows={rows} rowKey={(r) => `${r.stylist}-${r.chair}`} />
            </section>
          );
        }}
      </WithSnapshot>
    </>
  );
}
