import { useEffect, useState } from "react";
import { loadSnapshot } from "../lib/data";
import type { Snapshot } from "../lib/snapshot";

export type SnapshotState =
  | { status: "loading" }
  | { status: "ready"; data: Snapshot }
  | { status: "error"; message: string };

export function useSnapshot(): SnapshotState {
  const [state, setState] = useState<SnapshotState>({ status: "loading" });
  useEffect(() => {
    let cancelled = false;
    loadSnapshot()
      .then((data) => {
        if (!cancelled) setState({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({ status: "error", message: error instanceof Error ? error.message : String(error) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return state;
}
