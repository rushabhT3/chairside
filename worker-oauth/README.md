# worker-oauth — OAuth 2.1 in front of chairside-mcp

Claude Web and ChatGPT are OAuth-only MCP clients: no header field, and a token in the URL sends them to a consent page that cannot complete. This Cloudflare Worker (free plan) speaks OAuth 2.1 to the client, exchanges the sign-in for the user's own Xano JWT, and forwards every MCP request upstream with that JWT. Xano then authenticates and scopes per user through `$auth`, so a booking made from a chat client arrives on Floor with the user's identity.

```
client ──OAuth access token──▶ Worker ──Authorization: Bearer <user's Xano JWT>──▶ Xano chairside-mcp
```

Files:

| File | Role |
|---|---|
| `src/index.ts` | `OAuthProvider` with `/mcp` protected, `/authorize`, `/oauth/token`, `/oauth/register` |
| `src/authorize.ts` | HTTPS login form (POST only, CSRF cookie signed with `COOKIE_SECRET`), `POST {XANO_AUTH_BASE}/auth/login`, `completeAuthorization` with the JWT in `props` |
| `src/proxy.ts` | Drops the client's Authorization, injects the Xano JWT, streams `upstream.body` without buffering, preserves `Mcp-Session-Id` both ways |
| `wrangler.jsonc` | Worker config with the `OAUTH_KV` binding |

The password is forwarded to Xano and dropped. It is never logged and never stored; only the resulting JWT lives in the encrypted grant in KV.

## Deploy

```bash
cd worker-oauth
npm install
npx wrangler login
npx wrangler kv namespace create OAUTH_KV        # paste the id into wrangler.jsonc
npx wrangler deploy
npx wrangler secret put XANO_MCP_STREAM_URL      # the Streaming URL from Xano's Connect this backend → MCP Server URLs
npx wrangler secret put XANO_AUTH_BASE           # https://<instance>.xano.io/api:chairside-auth
npx wrangler secret put COOKIE_SECRET            # openssl rand -hex 32
npx wrangler deploy
```

Then in Claude Web / ChatGPT add a custom connector with the URL `https://chairside-mcp-oauth.<account>.workers.dev/mcp`. The client discovers the metadata, registers itself (RFC 7591), the user signs in with their Chairside email and password, and every tool call runs as that user.

## Xano side

`xano/workspace/ai/mcp_server/chairside_mcp.xs` lists every tool with `auth: "user"`, which is what makes the upstream JWT meaningful. Header-capable clients (Claude Code, Cursor) can skip this Worker and connect to the Xano MCP URL with a user JWT as the bearer token.

## Verify

```bash
npx tsc --noEmit                                 # passes
curl -i https://chairside-mcp-oauth.<account>.workers.dev/mcp        # 401 with OAuth metadata
curl -s https://chairside-mcp-oauth.<account>.workers.dev/.well-known/oauth-authorization-server | jq .
```
