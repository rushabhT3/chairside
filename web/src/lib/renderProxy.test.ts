import { describe, expect, it } from "vitest";
import { renderCacheKey, renderQuery } from "./renderProxy";

describe("renderQuery", () => {
  it("carries the shade for a hair render", () => {
    expect(renderQuery({ kind: "hair", shade: "#A8804F" })).toBe("kind=hair&shade=%23A8804F");
  });

  it("sends only the kind when a skin plan needs no options", () => {
    expect(renderQuery({ kind: "skin" })).toBe("kind=skin");
  });

  it("carries the template for a style render", () => {
    expect(renderQuery({ kind: "style", template: "female_s_wave_brunette" })).toBe(
      "kind=style&template=female_s_wave_brunette",
    );
  });
});

describe("renderCacheKey", () => {
  it("separates two shades of the same scan", () => {
    const a = renderCacheKey("scan-1", { kind: "hair", shade: "#A8804F" });
    const b = renderCacheKey("scan-1", { kind: "hair", shade: "#B5A58E" });
    expect(a).not.toBe(b);
  });

  it("separates the same render across two scans", () => {
    expect(renderCacheKey("scan-1", { kind: "skin" })).not.toBe(renderCacheKey("scan-2", { kind: "skin" }));
  });
});
