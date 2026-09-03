import type { OAuthHelpers } from "@cloudflare/workers-oauth-provider";

export interface Env {
  OAUTH_KV: KVNamespace;
  OAUTH_PROVIDER: OAuthHelpers;
  XANO_MCP_STREAM_URL: string;
  XANO_AUTH_BASE: string;
  COOKIE_SECRET: string;
}

export interface AuthProps extends Record<string, unknown> {
  xanoToken: string;
  email: string;
  role: string;
}
