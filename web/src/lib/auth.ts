import { dataMode, xanoBaseUrl } from "./data";

export type Role = "owner" | "stylist" | "client";

export interface Session {
  token: string;
  role: Role;
  name: string;
  email: string;
  salon_id: string;
}

interface DemoAccount {
  email: string;
  role: Role;
  name: string;
}

const storageKey = "chairside.session";
const demoPassword = "chairside-demo";
const demoSalonId = "salon-atelier-noor";

export const DEMO_ACCOUNTS: readonly DemoAccount[] = [
  { email: "noor@example.com", role: "owner", name: "Noor Haddad" },
  { email: "lea@example.com", role: "stylist", name: "Léa" },
  { email: "amira@example.com", role: "client", name: "Amira Benali" },
];

function readStorage(): Session | null {
  try {
    const raw = sessionStorage.getItem(storageKey);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

function writeStorage(session: Session | null): void {
  try {
    if (session) sessionStorage.setItem(storageKey, JSON.stringify(session));
    else sessionStorage.removeItem(storageKey);
  } catch {
    return;
  }
}

export function currentSession(): Session | null {
  return readStorage();
}

export function hasRole(session: Session | null, ...roles: Role[]): boolean {
  return session !== null && roles.includes(session.role);
}

export function logout(): void {
  writeStorage(null);
}

function demoLogin(email: string, password: string): Session {
  const account = DEMO_ACCOUNTS.find((a) => a.email === email.trim().toLowerCase());
  if (!account || password !== demoPassword) throw new Error("Unknown demo login");
  return {
    token: `demo.${account.role}`,
    role: account.role,
    name: account.name,
    email: account.email,
    salon_id: demoSalonId,
  };
}

async function xanoJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${xanoBaseUrl()}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (!response.ok) throw new Error(`${path} failed with ${response.status}`);
  return response.json() as Promise<T>;
}

async function liveSession(token: string): Promise<Session> {
  const me = await xanoJson<{ name: string; email: string; role: Role; salon_id: string }>(
    "/auth/me",
    { method: "GET", headers: { Authorization: `Bearer ${token}` } },
  );
  return { token, role: me.role, name: me.name, email: me.email, salon_id: me.salon_id };
}

export async function login(email: string, password: string): Promise<Session> {
  const session =
    dataMode() === "fixtures"
      ? demoLogin(email, password)
      : await xanoJson<{ authToken: string }>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        }).then((r) => liveSession(r.authToken));
  writeStorage(session);
  return session;
}

export async function signup(input: {
  email: string;
  password: string;
  name: string;
  role: Role;
}): Promise<Session> {
  if (dataMode() === "fixtures") return login(input.email, input.password);
  const created = await xanoJson<{ authToken: string }>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(input),
  });
  const session = await liveSession(created.authToken);
  writeStorage(session);
  return session;
}
