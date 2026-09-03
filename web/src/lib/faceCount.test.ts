import { describe, expect, it } from "vitest";
import { countFaceBlobs } from "./faceCount";

const size = 64;

function maskWith(rects: Array<[number, number, number, number]>): Uint8Array {
  const mask = new Uint8Array(size * size);
  for (const [x0, y0, w, h] of rects) {
    for (let y = y0; y < y0 + h; y += 1) {
      for (let x = x0; x < x0 + w; x += 1) mask[y * size + x] = 1;
    }
  }
  return mask;
}

describe("countFaceBlobs", () => {
  it("returns zero when nothing skin-toned is large enough", () => {
    expect(countFaceBlobs(maskWith([[10, 10, 3, 3]]))).toBe(0);
  });

  it("counts one face when a hand-sized blob sits beside it", () => {
    expect(countFaceBlobs(maskWith([[20, 10, 24, 30], [2, 40, 8, 8]]))).toBe(1);
  });

  it("counts two faces when two comparable blobs are present", () => {
    expect(countFaceBlobs(maskWith([[4, 10, 20, 26], [36, 12, 20, 24]]))).toBe(2);
  });
});
