import { useMemo, useState } from "react";
import { ConfidenceChip } from "../components/Chips";
import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Empty, WithSnapshot } from "../components/States";
import { formatCents } from "../format";
import { href, navigate } from "../router";
import type { SnapshotState } from "../useSnapshot";
import type { ExtractionRow, ShadeEntry, Sku } from "../../lib/snapshot";

const SKU_COLUMNS: Column<Sku>[] = [
  { key: "code", header: "Code", render: (s) => <span className="mono">{s.code}</span> },
  { key: "name", header: "Product / service", render: (s) => s.name },
  { key: "brand", header: "Brand", render: (s) => s.brand },
  { key: "kind", header: "Kind", render: (s) => s.kind },
  { key: "shade", header: "Shade", render: (s) => (s.shade_code ? <span className="mono">{s.shade_code}</span> : <span className="muted">—</span>) },
  { key: "price", header: "Salon price", numeric: true, render: (s) => formatCents(s.salon_price_cents) },
];

function lowestConfidence(row: ExtractionRow): number {
  return Math.min(...row.fields.map((f) => f.confidence));
}

function ShadeEditor({ initial }: { initial: ShadeEntry[] }) {
  const [shades, setShades] = useState(initial);
  const update = (code: string, patch: Partial<ShadeEntry>) => setShades((all) => all.map((s) => (s.code === code ? { ...s, ...patch } : s)));
  const columns: Column<ShadeEntry>[] = [
    { key: "code", header: "Code", render: (s) => <span className="mono">{s.code}</span> },
    { key: "name", header: "Name", render: (s) => s.name },
    {
      key: "hex",
      header: "Hex",
      render: (s) => (
        <label className="field">
          <span className="visually-hidden">Hex for {s.code}</span>
          <span>
            <span className="swatch" aria-hidden="true" style={{ background: s.hex }} />{" "}
            <input className="field__input field__input--hex" value={s.hex} onChange={(e) => update(s.code, { hex: e.target.value })} />
          </span>
        </label>
      ),
    },
    {
      key: "undertone",
      header: "Undertone",
      render: (s) => (
        <label className="field">
          <span className="visually-hidden">Undertone for {s.code}</span>
          <select className="field__input field__input--short" value={s.undertone} onChange={(e) => update(s.code, { undertone: e.target.value as ShadeEntry["undertone"] })}>
            <option value="warm">warm</option>
            <option value="cool">cool</option>
            <option value="neutral">neutral</option>
          </select>
        </label>
      ),
    },
    {
      key: "level",
      header: "Level",
      numeric: true,
      render: (s) => (
        <label className="field">
          <span className="visually-hidden">Level for {s.code}</span>
          <input className="field__input field__input--short" type="number" min={1} max={10} value={s.level} onChange={(e) => update(s.code, { level: Number(e.target.value) })} />
        </label>
      ),
    },
  ];
  return <DataTable caption="Shade map" columns={columns} rows={shades} rowKey={(s) => s.code} />;
}

export function Catalog({ snapshot }: { snapshot: SnapshotState }) {
  return (
    <WithSnapshot snapshot={snapshot} label="Loading catalog">
      {(data) => <CatalogBody skus={data.skus} shades={data.shade_map} extractions={data.extractions} />}
    </WithSnapshot>
  );
}

function CatalogBody({ skus, shades, extractions }: { skus: Sku[]; shades: ShadeEntry[]; extractions: ExtractionRow[] }) {
  const review = useMemo(() => extractions.filter((e) => e.needs_review && e.status === "pending"), [extractions]);
  const reviewColumns: Column<ExtractionRow>[] = [
    { key: "id", header: "Row", render: (r) => <span className="mono">{r.id}</span> },
    { key: "file", header: "Source", render: (r) => `${r.source} · ${r.file}` },
    { key: "value", header: "Extracted", render: (r) => r.fields.map((f) => f.value).join(" · ") },
    { key: "conf", header: "Lowest confidence", render: (r) => <ConfidenceChip confidence={lowestConfidence(r)} /> },
    {
      key: "link",
      header: "",
      render: (r) => (
        <a href={href({ page: "catalog-review", id: r.id })} className="button button--quiet">
          Review in Viewer
        </a>
      ),
    },
  ];
  return (
    <>
      <PageHeader
        kicker="Catalog"
        title={`${skus.length} SKUs`}
        lede="Extracted by Nutrient from the salon's price list and invoices. Rows under 85 % confidence wait for a person; the confirmed catalog is sealed."
      />
      <section className="section">
        <div className="section__head">
          <h2>To review</h2>
          <span className="section__meta">{review.length} rows under threshold</span>
        </div>
        {review.length === 0 ? (
          <Empty>Nothing to review. Every extracted row cleared the 85 % threshold or has been confirmed.</Empty>
        ) : (
          <DataTable caption="Extraction rows needing review" columns={reviewColumns} rows={review} rowKey={(r) => r.id} rowClass={() => "row--warn"} onSelect={(r) => navigate({ page: "catalog-review", id: r.id })} />
        )}
      </section>
      <section className="section">
        <div className="section__head">
          <h2>SKUs</h2>
          <span className="section__meta">EUR · sealed catalog</span>
        </div>
        <DataTable caption="Catalog SKUs" columns={SKU_COLUMNS} rows={skus} rowKey={(s) => s.code} />
      </section>
      <section className="section">
        <div className="section__head">
          <h2>Shade map</h2>
          <span className="section__meta">the salon's line, mapped to YouCam hair-colour inputs · edits are in memory</span>
        </div>
        <ShadeEditor initial={shades} />
      </section>
    </>
  );
}
