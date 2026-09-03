import { describe, expect, it } from "vitest";
import { assetUrl, siteRelativeHref } from "./assetUrl";

describe("assetUrl", () => {
  it("resolves a root-relative asset against the site root under a subpath deploy", () => {
    const href = assetUrl("/renders/amira-before.svg", "https://example.github.io/chairside/mirror/");
    expect(href).toBe("https://example.github.io/chairside/renders/amira-before.svg");
  });

  it("resolves against the origin when the site is served from the root", () => {
    const href = assetUrl("/renders/amira-before.svg", "https://ateliernoor.com/floor/index.html");
    expect(href).toBe("https://ateliernoor.com/renders/amira-before.svg");
  });

  it("passes absolute vendor URLs through untouched", () => {
    const vendor = "https://cdn.youcam.example/render/731.png";
    expect(assetUrl(vendor, "https://example.github.io/chairside/mirror/")).toBe(vendor);
  });
});

describe("siteRelativeHref", () => {
  it("rewrites a root-relative path for a page one level below the site root", () => {
    expect(siteRelativeHref("/renders/amira-hair-731.svg")).toBe("../renders/amira-hair-731.svg");
  });

  it("passes absolute URLs through untouched", () => {
    expect(siteRelativeHref("https://cdn.example/x.png")).toBe("https://cdn.example/x.png");
  });
});
