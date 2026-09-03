import { useMemo, useState } from "react";
import { ServerChip, StateChip } from "../components/Chips";
import { PageHeader } from "../components/PageHeader";
import { Empty, WithSnapshot } from "../components/States";
import { TraceTimeline } from "../components/TraceTimeline";
import { assetUrl } from "../../lib/assetUrl";
import { formatCents, formatClock, formatDate, shortHash } from "../format";
import type { SnapshotState } from "../useSnapshot";
import type { Consultation as ConsultationRecord, PlanItem, PriceRow, Scan } from "../../lib/snapshot";

const INVERTED = new Set(["firmness", "radiance", "moisture"]);
const CONCERN_ORDER = ["pore", "oiliness", "spot", "dark_circle", "texture", "redness", "eye_bag", "wrinkle", "acne", "droopy_upper_eyelid", "droopy_lower_eyelid", "moisture", "radiance", "firmness"];
const MAX_SCORE = 100;
const PERCENT = 100;

function labelOf(key: string): string {
  return key.replace(/_/g, " ");
}

function ClientCard({ c }: { c: ConsultationRecord }) {
  const scan = c.scan;
  return (
    <div className="pane">
      <h2 className="pane__title">{c.client.name}</h2>
      <dl className="kv">
        <dt>Consultation</dt>
        <dd className="mono">{c.id}</dd>
        <dt>Stylist</dt>
        <dd>
          {c.stylist} · Chair {c.chair}
        </dd>
        <dt>State</dt>
        <dd>
          <StateChip state={c.state} />
          {c.failing_step && <span className="muted"> at {c.failing_step}</span>}
        </dd>
        <dt>Started</dt>
        <dd>
          {formatDate(c.started_at)} · {formatClock(c.started_at)}
        </dd>
      </dl>
      {scan ? <ScanCard scan={scan} previous={c.previous_scan} /> : <Empty>No scan yet.</Empty>}
    </div>
  );
}

function ScanCard({ scan, previous }: { scan: Scan; previous: Scan | null }) {
  return (
    <>
      <dl className="kv">
        <dt>Undertone</dt>
        <dd>
          <span className="swatch" style={{ background: scan.color_tones.hair_color_hex }} aria-hidden="true" />{" "}
          {scan.color_tones.undertone} · {scan.color_tones.skin_tone}
        </dd>
        <dt>Eyes</dt>
        <dd>{scan.color_tones.eye_color}</dd>
        <dt>Hair</dt>
        <dd>
          {scan.hair.type} · frizz {scan.hair.frizz} · {scan.hair.density} density
        </dd>
        <dt>Face</dt>
        <dd>{scan.face.shape}</dd>
        <dt>Scanned</dt>
        <dd>
          {formatDate(scan.ts)} · {formatClock(scan.ts)}
          {previous && <span className="muted"> · vs {formatDate(previous.ts)}</span>}
        </dd>
      </dl>
      <ul className="concerns" aria-label="Skin readings">
        {CONCERN_ORDER.filter((k) => k in scan.skin).map((k) => {
          const value = scan.skin[k];
          const delta = previous ? value - previous.skin[k] : null;
          const better = delta === null ? null : INVERTED.has(k) ? delta > 0 : delta < 0;
          return (
            <li key={k} className="concern">
              <span className="concern__name">
                <span>{labelOf(k)}</span>
                <span className="bar" aria-hidden="true">
                  <span className={INVERTED.has(k) ? "bar__fill bar__fill--ok" : "bar__fill"} style={{ width: `${(value / MAX_SCORE) * PERCENT}%` }} />
                </span>
              </span>
              <span className="mono">{value}</span>
              <span className="concern__delta mono">
                {delta === null ? "" : delta === 0 ? "=" : `${delta > 0 ? "↑" : "↓"}${Math.abs(delta)}${better ? " ✓" : ""}`}
              </span>
            </li>
          );
        })}
      </ul>
    </>
  );
}

function PlanEditor({ c }: { c: ConsultationRecord }) {
  const [qty, setQty] = useState<Record<string, number>>({});
  const plan = c.plan;
  const priceFor = useMemo(() => new Map(c.prices.map((p) => [p.sku_code, p])), [c.prices]);
  if (!plan) return <Empty>No plan yet. It appears after face shape.</Empty>;
  const items: PlanItem[] = [...plan.services, ...plan.products];
  const total = items.reduce((sum, i) => sum + i.price_cents * (qty[i.code] ?? i.qty), 0);
  return (
    <div className="plan">
      {items.map((i) => (
        <PlanRow key={i.code} item={i} price={priceFor.get(i.code)} qty={qty[i.code] ?? i.qty} onQty={(n) => setQty({ ...qty, [i.code]: n })} />
      ))}
      <div className="plan__total">
        <span>Total</span>
        <span>{formatCents(total)}</span>
      </div>
      <p className="muted">
        Rebook in {plan.rebook_weeks} weeks · classes: {plan.treatment_classes.join(", ")}
      </p>
    </div>
  );
}

function PlanRow({ item, price, qty, onQty }: { item: PlanItem; price: PriceRow | undefined; qty: number; onQty: (n: number) => void }) {
  return (
    <div className="plan__row">
      <div>
        <div>{item.name}</div>
        <span className="muted mono">
          {item.code}
          {item.treatment_class !== "none" && ` · ${item.treatment_class}`}
          {price && ` · market ${formatCents(price.min_cents)}–${formatCents(price.max_cents)} · ${price.action}`}
        </span>
      </div>
      <label className="visually-hidden" htmlFor={`qty-${item.code}`}>
        Quantity for {item.name}
      </label>
      <input id={`qty-${item.code}`} className="plan__qty" type="number" min={1} value={qty} onChange={(e) => onQty(Math.max(1, Number(e.target.value)))} />
      <span className="num mono">{formatCents(item.price_cents * qty)}</span>
    </div>
  );
}

function StaffNotes({ c }: { c: ConsultationRecord }) {
  if (c.reviews.length === 0) return null;
  return (
    <div className="note">
      <span className="note__label">
        <span className="dot dot--err" aria-hidden="true" />
        Staff only — never shown to the client
      </span>
      {c.reviews.map((r) => (
        <div key={r.place_id}>
          <strong>{r.competitor}</strong>
          <p className="muted">{r.summary}</p>
          {r.quotes.map((q) => (
            <blockquote key={q}>{q}</blockquote>
          ))}
          <span className="muted">as of {formatClock(r.as_of)}</span>
        </div>
      ))}
    </div>
  );
}

function Outcome({ c }: { c: ConsultationRecord }) {
  return (
    <dl className="kv">
      <dt>Consent</dt>
      <dd>
        {c.consent ? (
          <>
            {c.consent.envelope.state} · <span className="mono">{c.consent.template_id}</span>
            {c.consent.envelope.sealed_hash && (
              <>
                {" "}
                · sealed <span className="mono">{shortHash(c.consent.envelope.sealed_hash)}</span>
              </>
            )}
          </>
        ) : (
          <span className="muted">not yet</span>
        )}
      </dd>
      <dt>Order</dt>
      <dd>{c.order ? `${formatCents(c.order.total_cents)} · ${c.order.id}` : <span className="muted">not yet</span>}</dd>
      <dt>Rebook</dt>
      <dd>{c.booking ? `${formatDate(c.booking.when)} · ${c.booking.service}` : <span className="muted">not yet</span>}</dd>
      <dt>News</dt>
      <dd>{c.news ? (c.news.clean ? `No recalls or ingredient flags in the last 90 days · ${formatClock(c.news.as_of)}` : `${c.news.flags.length} flags`) : <span className="muted">not checked</span>}</dd>
    </dl>
  );
}

function Simulations({ c }: { c: ConsultationRecord }) {
  if (c.simulations.length === 0) return null;
  return (
    <div className="sim-grid">
      {c.simulations.map((s) => (
        <figure key={`${s.tool}-${s.label}`} className="sim">
          <div className="sim__pair">
            <img src={assetUrl(s.before_url)} alt={`Before · ${s.label}`} width={200} height={260} loading="lazy" />
            <img src={assetUrl(s.after_url)} alt={`After · ${s.label}`} width={200} height={260} loading="lazy" />
          </div>
          <figcaption>
            {s.label}
            <br />
            <ServerChip server={s.server} /> <span className="muted">{formatClock(s.as_of)}</span>
          </figcaption>
        </figure>
      ))}
    </div>
  );
}

export function Consultation({ id, snapshot }: { id: string; snapshot: SnapshotState }) {
  return (
    <WithSnapshot snapshot={snapshot} label="Loading consultation">
      {(data) => {
        const c = data.consultations[id];
        if (!c) {
          return (
            <>
              <PageHeader kicker="Consultation" title="Not found" />
              <Empty>{`No consultation ${id}. Pick a chair.`}</Empty>
            </>
          );
        }
        return (
          <>
            <PageHeader kicker="Consultation" title={c.client.name} lede={c.plan?.prose} />
            <div className="panes">
              <ClientCard c={c} />
              <div className="pane">
                <h2 className="pane__title">Trace</h2>
                <TraceTimeline events={c.events} />
              </div>
              <div className="pane">
                <h2 className="pane__title">Plan</h2>
                <PlanEditor c={c} />
                {c.plan && (
                  <ul className="facts">
                    {c.plan.facts.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                )}
                <Outcome c={c} />
                <StaffNotes c={c} />
              </div>
            </div>
            <section className="section">
              <div className="section__head">
                <h2>Simulations</h2>
                <span className="section__meta">rendered on the client's device · cached by shade</span>
              </div>
              <Simulations c={c} />
            </section>
          </>
        );
      }}
    </WithSnapshot>
  );
}
