import { describe, expect, it } from "vitest";
import { priceBarTicks, verdictLabel } from "./priceBar";

describe("priceBarTicks", () => {
  it("places min at 0 and max at 100", () => {
    const ticks = priceBarTicks(2000, 2600, 3200, 2800);

    expect(ticks.min).toBe(0);
    expect(ticks.max).toBe(100);
  });

  it("places the median proportionally", () => {
    const ticks = priceBarTicks(2000, 2600, 3200, 2800);

    expect(ticks.median).toBe(50);
  });

  it("places the salon price proportionally and rounds to an integer", () => {
    const ticks = priceBarTicks(2000, 2600, 3200, 2800);

    expect(ticks.salon).toBe(67);
    expect(Number.isInteger(ticks.salon)).toBe(true);
  });

  it("clamps a salon price below the market minimum to 0", () => {
    const ticks = priceBarTicks(2000, 2600, 3200, 1500);

    expect(ticks.salon).toBe(0);
    expect(ticks.clamped).toBe("below");
  });

  it("clamps a salon price above the market maximum to 100", () => {
    const ticks = priceBarTicks(2000, 2600, 3200, 4000);

    expect(ticks.salon).toBe(100);
    expect(ticks.clamped).toBe("above");
  });

  it("reports no clamping inside the range", () => {
    const ticks = priceBarTicks(2000, 2600, 3200, 2600);

    expect(ticks.clamped).toBeNull();
  });

  it("centres everything when min equals max", () => {
    const ticks = priceBarTicks(2500, 2500, 2500, 2500);

    expect(ticks).toEqual({ min: 50, median: 50, max: 50, salon: 50, clamped: null });
  });
});

describe("verdictLabel", () => {
  it("maps every action to a label", () => {
    expect(verdictLabel("match")).toBe("Match");
    expect(verdictLabel("bundle")).toBe("Bundle");
    expect(verdictLabel("hold")).toBe("Hold");
  });
});
