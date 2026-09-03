import type { CSSProperties } from "react";
import { formatTime } from "../../lib/format";
import { Button } from "../components/Button";
import { ConcernBar } from "../components/ConcernBar";
import { Notice } from "../components/Notice";
import { Skeleton } from "../components/Skeleton";
import { navigate } from "../router";
import { useMirrorState } from "../store";

const invertedReadings = new Set(["firmness", "radiance", "moisture"]);

const concernLabels: Record<string, string> = {
  wrinkle: "Fine lines",
  spot: "Spots",
  pore: "Pores",
  texture: "Texture",
  acne: "Blemishes",
  redness: "Redness",
  oiliness: "Oiliness",
  dark_circle: "Dark circles",
  eye_bag: "Eye bags",
  droopy_upper_eyelid: "Upper eyelid",
  droopy_lower_eyelid: "Lower eyelid",
  firmness: "Firmness",
  radiance: "Radiance",
  moisture: "Moisture",
};

function labelFor(key: string): string {
  return concernLabels[key] ?? key.replace(/_/g, " ");
}

export function Card() {
  const { status, consultation } = useMirrorState();
  if (status !== "ready" || !consultation) return <Skeleton lines={8} label="Reading your card" />;

  const scan = consultation.scan;
  if (!scan) {
    return (
      <Notice title="No scans yet — the first one takes about 20 seconds." action={{ label: "Scan now", onClick: () => navigate("capture") }} />
    );
  }

  const concerns = Object.entries(scan.skin)
    .filter(([key]) => !invertedReadings.has(key))
    .sort((a, b) => b[1] - a[1]);
  const readings = Object.entries(scan.skin).filter(([key]) => invertedReadings.has(key));
  const swatch = { "--swatch": scan.color_tones.hair_color_hex } as CSSProperties;

  return (
    <article className="ticket">
      <header className="ticket-header">
        <p className="ticket-kicker">Your readings · {formatTime(scan.ts)}</p>
        <h1 className="ticket-title">{consultation.client.name}</h1>
      </header>

      <section className="ticket-section" aria-labelledby="tones">
        <h2 id="tones" className="ticket-heading">Tones</h2>
        <div className="tone">
          <span className="tone-swatch" style={swatch} aria-hidden="true" />
          <dl className="tone-list">
            <dt>Undertone</dt>
            <dd>{scan.color_tones.undertone}</dd>
            <dt>Skin</dt>
            <dd>{scan.color_tones.skin_tone}</dd>
            <dt>Eyes</dt>
            <dd>{scan.color_tones.eye_color}</dd>
            <dt>Hair</dt>
            <dd className="mono">{scan.color_tones.hair_color_hex}</dd>
          </dl>
        </div>
      </section>

      <section className="ticket-section" aria-labelledby="concerns">
        <h2 id="concerns" className="ticket-heading">Concerns, ranked</h2>
        {concerns.map(([key, score]) => (
          <ConcernBar key={key} label={labelFor(key)} score={score} />
        ))}
      </section>

      <section className="ticket-section" aria-labelledby="readings">
        <h2 id="readings" className="ticket-heading">Readings, higher is better</h2>
        {readings.map(([key, score]) => (
          <ConcernBar key={key} label={labelFor(key)} score={score} inverted />
        ))}
      </section>

      <section className="ticket-section" aria-labelledby="hair">
        <h2 id="hair" className="ticket-heading">Hair and face</h2>
        <dl className="facts">
          <dt>Hair type</dt>
          <dd>{scan.hair.type}</dd>
          <dt>Frizz</dt>
          <dd>{scan.hair.frizz}</dd>
          <dt>Density</dt>
          <dd>{scan.hair.density}</dd>
          <dt>Face shape</dt>
          <dd>{scan.face.shape}</dd>
        </dl>
      </section>

      {consultation.plan && (
        <section className="ticket-section" aria-labelledby="voice">
          <h2 id="voice" className="ticket-heading">From {consultation.stylist}</h2>
          <p className="ticket-prose">{consultation.plan.prose}</p>
        </section>
      )}

      <Button onClick={() => navigate("simulate")}>See it on you</Button>
    </article>
  );
}
