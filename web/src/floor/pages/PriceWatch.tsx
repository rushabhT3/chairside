import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Empty, WithSnapshot } from "../components/States";
import { formatCents, formatClock, formatDate, formatPercent } from "../format";
import type { SnapshotState } from "../useSnapshot";
import type { PriceWatchRow } from "../../lib/snapshot";

const ALERT_THRESHOLD_PCT = 15;

const COLUMNS: Column<PriceWatchRow>[] = [
  { key: "code", header: "SKU", render: (r) => <span className="mono">{r.sku_code}</span> },
  { key: "name", header: "Product", render: (r) => r.name },
  { key: "salon", header: "Salon", numeric: true, render: (r) => formatCents(r.salon_price_cents) },
  { key: "median", header: "Market median", numeric: true, render: (r) => formatCents(r.median_cents) },
  { key: "delta", header: "Delta", numeric: true, render: (r) => <span className="mono">{formatPercent(r.delta_pct)}</span> },
  { key: "alert", header: "Alert", render: (r) => (r.alert ? <span className="chip"><span className="dot dot--err" aria-hidden="true" />over {ALERT_THRESHOLD_PCT} %</span> : <span className="muted">—</span>) },
  { key: "asof", header: "As of", render: (r) => <span className="mono">{formatDate(r.as_of)} {formatClock(r.as_of)}</span> },
];

export function PriceWatch({ snapshot }: { snapshot: SnapshotState }) {
  return (
    <>
      <PageHeader kicker="Nightly · SerpApi Google Shopping" title="Price watch" lede="A Xano task refreshes any snapshot older than seven days and raises an alert when the salon price drifts more than fifteen percent from the market median." />
      <WithSnapshot snapshot={snapshot} label="Loading price watch">
        {(data) =>
          data.price_watch.length === 0 ? (
            <Empty>No snapshots yet. The first refresh runs the night after onboarding.</Empty>
          ) : (
            <section className="section">
              <div className="section__head">
                <h2>{data.price_watch.filter((r) => r.alert).length} alerts</h2>
                <span className="section__meta">{data.price_watch.length} SKUs watched</span>
              </div>
              <DataTable caption="Price watch" columns={COLUMNS} rows={data.price_watch} rowKey={(r) => r.sku_code} rowClass={(r) => (r.alert ? "row--alert" : undefined)} />
            </section>
          )
        }
      </WithSnapshot>
    </>
  );
}
