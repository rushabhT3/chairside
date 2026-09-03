import { render as youcamRender, YouCamError, type RenderKind } from "./youcam";

export interface Env {
  PERFECTCORP_API_KEY: string;
  ALLOWED_ORIGINS?: string;
}

const DEFAULT_ORIGINS = "https://rushabht3.github.io,http://localhost:5173,http://localhost:4179";
const MAX_IMAGE_BYTES = 6 * 1024 * 1024;
const HEX = /^#[0-9a-f]{6}$/i;
const TEMPLATE = /^[a-z0-9_]{1,64}$/i;
const KINDS: RenderKind[] = ["hair", "skin", "style"];

function allowedOrigin(request: Request, env: Env): string | null {
  const origin = request.headers.get("Origin");
  if (!origin) return null;
  const allowed = (env.ALLOWED_ORIGINS ?? DEFAULT_ORIGINS).split(",").map((o) => o.trim());
  return allowed.includes(origin) ? origin : null;
}

function corsHeaders(origin: string | null): Record<string, string> {
  if (!origin) return {};
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(body: unknown, status: number, origin: string | null): Response {
  return Response.json(body, { status, headers: corsHeaders(origin) });
}

async function render(request: Request, env: Env, origin: string | null): Promise<Response> {
  if (!env.PERFECTCORP_API_KEY) return json({ error: "worker has no YouCam key" }, 500, origin);
  const params = new URL(request.url).searchParams;
  const kind = (params.get("kind") ?? "hair") as RenderKind;
  if (!KINDS.includes(kind)) return json({ error: `kind must be one of ${KINDS.join(", ")}` }, 400, origin);
  const shade = params.get("shade") ?? "#A8804F";
  if (!HEX.test(shade)) return json({ error: "shade must be a #rrggbb hex colour" }, 400, origin);
  const template = params.get("template") ?? "";
  if (template && !TEMPLATE.test(template)) return json({ error: "template id is not valid" }, 400, origin);
  const image = await request.arrayBuffer();
  if (image.byteLength === 0) return json({ error: "empty image" }, 400, origin);
  if (image.byteLength > MAX_IMAGE_BYTES) return json({ error: "image over 6 MB" }, 413, origin);
  try {
    const url = await youcamRender(env.PERFECTCORP_API_KEY, image, kind, shade, template);
    return json({ url }, 200, origin);
  } catch (error) {
    if (error instanceof YouCamError) return json({ error: error.message }, 502, origin);
    const detail = error instanceof Error ? error.message : String(error);
    return json({ error: `render failed: ${detail}` }, 502, origin);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const origin = allowedOrigin(request, env);
    const path = new URL(request.url).pathname;
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(origin) });
    if (path === "/health") return json({ service: "chairside-render", ready: Boolean(env.PERFECTCORP_API_KEY) }, 200, origin);
    if (path === "/render" && request.method === "POST") {
      if (!origin) return json({ error: "origin not allowed" }, 403, null);
      return render(request, env, origin);
    }
    return json({ error: "not found" }, 404, origin);
  },
};
