/// <reference lib="webworker" />

export interface ResizeRequest {
  image: Blob;
  maxEdge: number;
}

export interface ResizeResponse {
  image: Blob;
  sha256: string;
  width: number;
  height: number;
}

const jpegQuality = 0.86;

async function sha256Hex(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await blob.arrayBuffer());
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

async function resize({ image, maxEdge }: ResizeRequest): Promise<ResizeResponse> {
  const bitmap = await createImageBitmap(image);
  const scale = Math.min(1, maxEdge / Math.max(bitmap.width, bitmap.height));
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);
  const canvas = new OffscreenCanvas(width, height);
  const context = canvas.getContext("2d");
  if (!context) throw new Error("OffscreenCanvas 2D context unavailable");
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();
  const resized = await canvas.convertToBlob({ type: "image/jpeg", quality: jpegQuality });
  return { image: resized, sha256: await sha256Hex(resized), width, height };
}

self.onmessage = async (event: MessageEvent<ResizeRequest>) => {
  try {
    self.postMessage(await resize(event.data));
  } catch (error) {
    self.postMessage({ error: error instanceof Error ? error.message : String(error) });
  }
};
