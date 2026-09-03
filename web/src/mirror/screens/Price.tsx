import { useState } from "react";
import { formatCents, formatTime } from "../../lib/format";
import { verdictLabel } from "../../lib/priceBar";
import { Button } from "../components/Button";
import { Notice } from "../components/Notice";
import { RangeBar } from "../components/RangeBar";
import { Skeleton } from "../components/Skeleton";
import { navigate } from "../router";
import { useMirrorState } from "../store";

interface LensPayload {
  brand?: string;
  product?: string;
  as_of?: string;
  visual_matches?: { title: string; price_cents?: number; source?: string }[];
}

const matchesShown = 3;

export function Price() {
  const { status, consultation } = useMirrorState();
  const [lensOpen, setLensOpen] = useState(false);

  if (status !== "ready" || !consultation) return <Skeleton lines={6} label="Checking prices" />;

  const lensEvent = consultation.events.find((event) => event.type === "price.identified");
  const lens = (lensEvent?.payload ?? null) as LensPayload | null;
  const news = consultation.news;

  return (
    <section className="price">
      {consultation.prices.length === 0 ? (
        <Notice title="No prices yet." />
      ) : (
        <ul className="rows">
          {consultation.prices.map((row) => (
            <li key={row.sku_code} className="row">
              <div className="row-head">
                <span className="row-name">{row.name}</span>
                <span className={`badge badge-${row.action}`}>{verdictLabel(row.action)}</span>
              </div>
              <p className="row-price">
                <span className="row-salon">{formatCents(row.salon_price_cents)}</span>
                <span className="row-asof">as of {formatTime(row.as_of)}</span>
              </p>
              <RangeBar minCents={row.min_cents} medianCents={row.median_cents} maxCents={row.max_cents} salonCents={row.salon_price_cents} />
              <p className="row-reason">{row.reason}</p>
            </li>
          ))}
        </ul>
      )}

      <p className={`recall ${news && !news.clean ? "recall-flagged" : ""}`.trim()}>
        {news
          ? news.clean
            ? `No recalls or ingredient flags in the last 90 days · as of ${formatTime(news.as_of)}`
            : `${news.flags.length} flag${news.flags.length === 1 ? "" : "s"} in the last 90 days · as of ${formatTime(news.as_of)}`
          : "Recall check not run yet."}
      </p>
      {news && !news.clean && (
        <ul className="flags">
          {news.flags.map((flag) => (
            <li key={flag.link}>
              <a href={flag.link} target="_blank" rel="noreferrer">{flag.title}</a> · {flag.source}
            </li>
          ))}
        </ul>
      )}

      <Button variant="secondary" onClick={() => setLensOpen((open) => !open)} aria-expanded={lensOpen}>
        {lensOpen ? "Hide bottle check" : "Identify a bottle"}
      </Button>
      {lensOpen &&
        (lens ? (
          <section className="lens" aria-label="Bottle identified">
            <p className="lens-title">
              {[lens.brand, lens.product].filter(Boolean).join(" ")}
              {lens.as_of ? ` · as of ${formatTime(lens.as_of)}` : ""}
            </p>
            <ul className="lens-matches">
              {(lens.visual_matches ?? []).slice(0, matchesShown).map((match) => (
                <li key={match.title}>
                  {match.title}
                  {typeof match.price_cents === "number" ? ` · ${formatCents(match.price_cents)}` : ""}
                  {match.source ? ` · ${match.source}` : ""}
                </li>
              ))}
            </ul>
          </section>
        ) : (
          <Notice title="No bottle identified yet.">
            <p>Hold the bottle in frame and your stylist runs the check from the chair.</p>
          </Notice>
        ))}

      <Button onClick={() => navigate("consent")}>Continue to consent</Button>
    </section>
  );
}
