import { AuthorizationError, type AuthRequest } from "@cloudflare/workers-oauth-provider";
import type { AuthProps, Env } from "./types";

const CSRF_COOKIE = "chairside_csrf";
const CSRF_TTL_SECONDS = 600;

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function hmacHex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return Array.from(new Uint8Array(signature), (b) => b.toString(16).padStart(2, "0")).join("");
}

async function issueCsrf(secret: string): Promise<{ nonce: string; cookie: string }> {
  const nonce = crypto.randomUUID();
  const expires = Math.floor(Date.now() / 1000) + CSRF_TTL_SECONDS;
  const mac = await hmacHex(secret, `${nonce}.${expires}`);
  const value = `${nonce}.${expires}.${mac}`;
  return {
    nonce,
    cookie: `${CSRF_COOKIE}=${value}; Path=/authorize; Max-Age=${CSRF_TTL_SECONDS}; HttpOnly; Secure; SameSite=Lax`,
  };
}

async function verifyCsrf(secret: string, cookieHeader: string | null, nonce: string): Promise<boolean> {
  if (!cookieHeader || !nonce) return false;
  const raw = cookieHeader
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${CSRF_COOKIE}=`));
  if (!raw) return false;
  const [cookieNonce, expires, mac] = raw.slice(CSRF_COOKIE.length + 1).split(".");
  if (cookieNonce !== nonce) return false;
  if (Number(expires) < Math.floor(Date.now() / 1000)) return false;
  return (await hmacHex(secret, `${cookieNonce}.${expires}`)) === mac;
}

function loginPage(clientName: string, nonce: string, error: string | null): string {
  const notice = error ? `<p class="error" role="alert">${escapeHtml(error)}</p>` : "";
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in to Chairside</title>
<style>
  :root{--paper:#F5F1EA;--ink:#161412;--ink-2:#4A443E;--rule:#D8CFC2;--accent:#5A1F1F;--err:#B3261E}
  body{margin:0;background:var(--paper);color:var(--ink);font:17.5px/1.45 Georgia,serif}
  main{max-width:420px;margin:64px auto;padding:0 24px}
  h1{font-size:27px;line-height:1.05;margin:0 0 8px}
  p{margin:0 0 24px;color:var(--ink-2)}
  label{display:block;font-size:14px;margin:16px 0 4px}
  input{width:100%;box-sizing:border-box;padding:12px;font:inherit;border:1px solid var(--rule);border-radius:4px;background:#fff;color:var(--ink)}
  input:focus{outline:2px solid var(--accent);outline-offset:2px}
  button{margin-top:24px;width:100%;min-height:44px;font:inherit;background:var(--accent);color:var(--paper);border:0;border-radius:4px;cursor:pointer}
  .error{color:var(--err)}
</style>
</head>
<body>
<main>
  <h1>Sign in to Chairside</h1>
  <p>${escapeHtml(clientName)} is asking to book and read on your behalf.</p>
  ${notice}
  <form method="post" autocomplete="on">
    <input type="hidden" name="csrf" value="${escapeHtml(nonce)}">
    <label for="email">Email</label>
    <input id="email" name="email" type="email" required autocomplete="username">
    <label for="password">Password</label>
    <input id="password" name="password" type="password" required autocomplete="current-password">
    <button type="submit">Continue</button>
  </form>
</main>
</body>
</html>`;
}

function redirectWithError(error: AuthorizationError): Response {
  if (!error.redirectUri) return new Response(error.description, { status: 400 });
  const redirect = new URL(error.redirectUri);
  redirect.searchParams.set("error", error.code);
  redirect.searchParams.set("error_description", error.description);
  if (error.state) redirect.searchParams.set("state", error.state);
  return Response.redirect(redirect.toString(), 302);
}

async function parseOrRedirect(
  request: Request,
  env: Env,
): Promise<{ oauth: AuthRequest } | { response: Response }> {
  try {
    return { oauth: await env.OAUTH_PROVIDER.parseAuthRequest(request) };
  } catch (error) {
    if (!(error instanceof AuthorizationError)) throw error;
    return { response: redirectWithError(error) };
  }
}

async function clientName(env: Env, clientId: string): Promise<string> {
  const client = await env.OAUTH_PROVIDER.lookupClient(clientId);
  return client?.clientName ?? clientId;
}

interface XanoLogin {
  authToken: string;
}

interface XanoMe {
  email: string;
  role: string;
}

async function exchangeCredentials(env: Env, email: string, password: string): Promise<AuthProps | null> {
  const login = await fetch(`${env.XANO_AUTH_BASE}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!login.ok) return null;
  const { authToken } = (await login.json()) as XanoLogin;
  if (!authToken) return null;

  const me = await fetch(`${env.XANO_AUTH_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${authToken}` },
  });
  if (!me.ok) return null;
  const profile = (await me.json()) as XanoMe;
  return { xanoToken: authToken, email: profile.email, role: profile.role };
}

export async function handleAuthorizeGet(request: Request, env: Env): Promise<Response> {
  const parsed = await parseOrRedirect(request, env);
  if ("response" in parsed) return parsed.response;
  const { nonce, cookie } = await issueCsrf(env.COOKIE_SECRET);
  const name = await clientName(env, parsed.oauth.clientId);
  return new Response(loginPage(name, nonce, null), {
    status: 200,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "set-cookie": cookie,
      "cache-control": "no-store",
      "referrer-policy": "no-referrer",
    },
  });
}

export async function handleAuthorizePost(request: Request, env: Env): Promise<Response> {
  const parsed = await parseOrRedirect(request, env);
  if ("response" in parsed) return parsed.response;

  const form = await request.formData();
  const nonce = String(form.get("csrf") ?? "");
  const email = String(form.get("email") ?? "").trim().toLowerCase();
  const password = String(form.get("password") ?? "");

  const name = await clientName(env, parsed.oauth.clientId);
  const reissue = await issueCsrf(env.COOKIE_SECRET);
  const failed = (message: string) =>
    new Response(loginPage(name, reissue.nonce, message), {
      status: 401,
      headers: {
        "content-type": "text/html; charset=utf-8",
        "set-cookie": reissue.cookie,
        "cache-control": "no-store",
      },
    });

  if (!(await verifyCsrf(env.COOKIE_SECRET, request.headers.get("cookie"), nonce))) {
    return failed("Your sign-in page expired. Try again.");
  }
  if (!email || !password) return failed("Email and password are required.");

  const props = await exchangeCredentials(env, email, password);
  if (!props) return failed("Email or password did not match.");

  const { redirectTo } = await env.OAUTH_PROVIDER.completeAuthorization({
    request: parsed.oauth,
    userId: email,
    metadata: { clientName: name, role: props.role },
    scope: parsed.oauth.scope,
    props,
  });
  return Response.redirect(redirectTo, 302);
}
