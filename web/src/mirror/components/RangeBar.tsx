import type { CSSProperties } from "react";
import { formatCents } from "../../lib/format";
import { priceBarTicks } from "../../lib/priceBar";

export interface RangeBarProps {
  minCents: number;
  medianCents: number;
  maxCents: number;
  salonCents: number;
}

function at(position: number): CSSProperties {
  return { "--pos": `${position}%` } as CSSProperties;
}

export function RangeBar({ minCents, medianCents, maxCents, salonCents }: RangeBarProps) {
  const ticks = priceBarTicks(minCents, medianCents, maxCents, salonCents);
  const salonClass = `range-salon ${ticks.clamped ? `range-salon-${ticks.clamped}` : ""}`.trim();
  return (
    <div
      className="range"
      role="img"
      aria-label={`Market ${formatCents(minCents)} to ${formatCents(maxCents)}, median ${formatCents(medianCents)}, salon ${formatCents(salonCents)}`}
    >
      <span className="range-track" />
      <span className="range-tick" style={at(ticks.min)} />
      <span className="range-tick range-tick-median" style={at(ticks.median)} />
      <span className="range-tick" style={at(ticks.max)} />
      <span className={salonClass} style={at(ticks.salon)} />
      <span className="range-legend">
        <span>{formatCents(minCents)}</span>
        <span>{formatCents(medianCents)}</span>
        <span>{formatCents(maxCents)}</span>
      </span>
    </div>
  );
}
