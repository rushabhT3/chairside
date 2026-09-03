import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { contrastRatio, parseTokens } from "./contrast";

const tokens = parseTokens(readFileSync(resolve(__dirname, "../tokens.css"), "utf-8"));
const minimum = 7;

const pairs: [string, string][] = [
  ["ink", "paper"],
  ["ink", "bone"],
  ["paper", "accent"],
  ["paper", "ink"],
  ["ink-2", "paper"],
  ["ok", "paper"],
  ["warn", "paper"],
  ["err", "paper"],
  ["ink", "surface-raised"],
];

describe("tokens.css contrast", () => {
  it.each(pairs)("%s on %s is at least 7:1", (foreground, background) => {
    const ratio = contrastRatio(tokens[foreground], tokens[background]);

    expect(ratio).toBeGreaterThanOrEqual(minimum);
  });
});
