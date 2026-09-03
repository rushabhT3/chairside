import type { Snapshot } from "./snapshot";

export type DataMode = "fixtures" | "live";

export function dataMode(): DataMode {
  return import.meta.env.VITE_DATA_MODE === "live" ? "live" : "fixtures";
}

export function xanoBaseUrl(): string {
  const url = import.meta.env.VITE_XANO_BASE_URL as string | undefined;
  if (!url) throw new Error("VITE_XANO_BASE_URL is required in live mode");
  return url.replace(/\/$/, "");
}

let cached: Promise<Snapshot> | null = null;

export function loadSnapshot(): Promise<Snapshot> {
  if (!cached) {
    cached =
      dataMode() === "fixtures"
        ? import("../fixtures/snapshot.json").then((m) => m.default as unknown as Snapshot)
        : fetch(`${xanoBaseUrl()}/floor/snapshot`).then((r) => {
            if (!r.ok) throw new Error(`snapshot ${r.status}`);
            return r.json() as Promise<Snapshot>;
          });
  }
  return cached;
}
