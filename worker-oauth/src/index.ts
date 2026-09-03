import OAuthProvider from "@cloudflare/workers-oauth-provider";
import { handleAuthorizeGet, handleAuthorizePost } from "./authorize";
import { McpProxy } from "./proxy";
import type { Env } from "./types";

const defaultHandler = {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/authorize" && request.method === "GET") return handleAuthorizeGet(request, env);
    if (url.pathname === "/authorize" && request.method === "POST") return handleAuthorizePost(request, env);
    if (url.pathname === "/" || url.pathname === "/health") {
      return Response.json({ service: "chairside-mcp-oauth", mcp: "/mcp", authorize: "/authorize" });
    }
    return new Response("not found", { status: 404 });
  },
};

export default new OAuthProvider({
  apiRoute: "/mcp",
  apiHandler: McpProxy,
  defaultHandler,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/oauth/token",
  clientRegistrationEndpoint: "/oauth/register",
  scopesSupported: ["mcp"],
  clientIdMetadataDocumentEnabled: true,
});
