export type PriceAction = "match" | "bundle" | "hold";

export interface PriceBarTicks {
  min: number;
  median: number;
  max: number;
  salon: number;
  clamped: "below" | "above" | null;
}

function position(value: number, min: number, span: number): number {
  if (span === 0) return 50;
  const raw = Math.round(((value - min) / span) * 100);
  return Math.min(100, Math.max(0, raw));
}

export function priceBarTicks(
  minCents: number,
  medianCents: number,
  maxCents: number,
  salonCents: number,
): PriceBarTicks {
  const span = maxCents - minCents;
  const clamped = salonCents < minCents ? "below" : salonCents > maxCents ? "above" : null;
  return {
    min: position(minCents, minCents, span),
    median: position(medianCents, minCents, span),
    max: position(maxCents, minCents, span),
    salon: position(salonCents, minCents, span),
    clamped,
  };
}

export function verdictLabel(action: PriceAction): string {
  switch (action) {
    case "match":
      return "Match";
    case "bundle":
      return "Bundle";
    case "hold":
      return "Hold";
  }
}
