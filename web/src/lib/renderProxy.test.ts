import { describe, expect, it } from "vitest";
import { renderQuery } from "./renderProxy";

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
