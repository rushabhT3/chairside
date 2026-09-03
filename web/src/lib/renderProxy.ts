export class RenderProxyError extends Error {}

export type RenderKind = "hair" | "skin" | "style";

export interface RenderRequest {
  kind: RenderKind;
  shade?: string;
  template?: string;
}

export function renderProxyUrl(): string | null {
  const url = import.meta.env.VITE_RENDER_PROXY_URL as string | undefined;
  return url ? url.replace(/\/$/, "") : null;
}

export function isLiveRenderAvailable(): boolean {
  return renderProxyUrl() !== null;
}

export function renderQuery({ kind, shade, template }: RenderRequest): string {
  const params = new URLSearchParams({ kind });
  if (shade) params.set("shade", shade);
  if (template) params.set("template", template);
  return params.toString();
}

/** Sends the client's own scan to the worker that holds the YouCam key, and returns the rendered image URL. */
export async function renderScan(image: Blob, request: RenderRequest): Promise<string> {
  const base = renderProxyUrl();
  if (!base) throw new RenderProxyError("no render proxy configured");
  const response = await fetch(`${base}/render?${renderQuery(request)}`, {
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
