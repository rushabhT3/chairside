import { WorkerEntrypoint } from "cloudflare:workers";
import type { AuthProps, Env } from "./types";

const SESSION_HEADER = "Mcp-Session-Id";
const PROTOCOL_HEADER = "Mcp-Protocol-Version";

function upstreamHeaders(request: Request, xanoToken: string): Headers {
  const headers = new Headers();
  for (const name of ["content-type", "accept", SESSION_HEADER, PROTOCOL_HEADER]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  headers.set("Authorization", `Bearer ${xanoToken}`);
  return headers;
}

function downstreamHeaders(upstream: Response): Headers {
  const headers = new Headers();
  for (const name of ["content-type", "cache-control", SESSION_HEADER, PROTOCOL_HEADER]) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  return headers;
}

export class McpProxy extends WorkerEntrypoint<Env, AuthProps> {
  async fetch(request: Request): Promise<Response> {
    const { xanoToken } = this.ctx.props;
    if (!xanoToken) return new Response("missing upstream identity", { status: 401 });

    const upstream = await fetch(this.env.XANO_MCP_STREAM_URL, {
      method: request.method,
      headers: upstreamHeaders(request, xanoToken),
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    });

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: downstreamHeaders(upstream),
    });
  }
}
