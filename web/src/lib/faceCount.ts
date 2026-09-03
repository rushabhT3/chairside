/** Uses the browser FaceDetector when present; otherwise a skin-tone blob heuristic that only distinguishes "one centered face" from "none" or "several" and is not a face detector. */

interface DetectedFace {
  boundingBox: DOMRectReadOnly;
}

interface FaceDetectorLike {
  detect(source: ImageBitmapSource): Promise<DetectedFace[]>;
}

declare global {
  interface Window {
    FaceDetector?: new (options?: { maxDetectedFaces?: number }) => FaceDetectorLike;
  }
}

const sampleSize = 64;
const minBlobArea = 40;
const maxFaces = 4;

function isSkin(r: number, g: number, b: number): boolean {
  const y = 0.299 * r + 0.587 * g + 0.114 * b;
  const cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b;
  const cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b;
  return y > 40 && cb >= 77 && cb <= 127 && cr >= 133 && cr <= 173;
}

function skinMask(source: CanvasImageSource): Uint8Array {
  const canvas = document.createElement("canvas");
  canvas.width = sampleSize;
  canvas.height = sampleSize;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return new Uint8Array(sampleSize * sampleSize);
  context.drawImage(source, 0, 0, sampleSize, sampleSize);
  const { data } = context.getImageData(0, 0, sampleSize, sampleSize);
  const mask = new Uint8Array(sampleSize * sampleSize);
  for (let i = 0; i < mask.length; i += 1) {
    mask[i] = isSkin(data[i * 4], data[i * 4 + 1], data[i * 4 + 2]) ? 1 : 0;
  }
  return mask;
}

function countBlobs(mask: Uint8Array): number {
  const seen = new Uint8Array(mask.length);
  let blobs = 0;
  for (let start = 0; start < mask.length; start += 1) {
    if (!mask[start] || seen[start]) continue;
    const stack = [start];
    let area = 0;
    seen[start] = 1;
    while (stack.length) {
      const index = stack.pop() as number;
      area += 1;
      const x = index % sampleSize;
      const y = (index - x) / sampleSize;
      const neighbours = [
        x > 0 ? index - 1 : -1,
        x < sampleSize - 1 ? index + 1 : -1,
        y > 0 ? index - sampleSize : -1,
        y < sampleSize - 1 ? index + sampleSize : -1,
      ];
      for (const n of neighbours) {
        if (n >= 0 && mask[n] && !seen[n]) {
          seen[n] = 1;
          stack.push(n);
        }
      }
    }
    if (area >= minBlobArea) blobs += 1;
  }
  return blobs;
}

export async function countFaces(source: HTMLVideoElement | ImageBitmap): Promise<number> {
  if (window.FaceDetector) {
    const detector = new window.FaceDetector({ maxDetectedFaces: maxFaces });
    const faces = await detector.detect(source);
    return faces.length;
  }
  return countBlobs(skinMask(source));
}
