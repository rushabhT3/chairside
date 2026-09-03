export class RenderProxyError extends Error {}

export function renderProxyUrl(): string | null {
  const url = import.meta.env.VITE_RENDER_PROXY_URL as string | undefined;
  return url ? url.replace(/\/$/, "") : null;
}

export function isLiveRenderAvailable(): boolean {
  return renderProxyUrl() !== null;
}

/** Sends the client's own scan to the worker that holds the YouCam key, and returns the rendered image URL. */
export async function renderHairColour(image: Blob, hex: string): Promise<string> {
  const base = renderProxyUrl();
  if (!base) throw new RenderProxyError("no render proxy configured");
  const response = await fetch(`${base}/render?shade=${encodeURIComponent(hex)}`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream" },
    body: image,
  });
  const payload = (await response.json()) as { url?: string; error?: string };
  if (!response.ok || !payload.url) {
    throw new RenderProxyError(payload.error ?? `render proxy returned ${response.status}`);
  }
  return payload.url;
}
