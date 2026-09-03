import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { loadSnapshot } from "../lib/data";
import type { Consultation, ShadeEntry } from "../lib/snapshot";
import { ClientDataDeletedError, mirrorApi } from "../lib/xano";

export type MirrorStatus = "loading" | "ready" | "error" | "deleted";

export interface CapturedScan {
  image: Blob;
  sha256: string;
  width: number;
  height: number;
  scan_id: string;
}

export interface MirrorState {
  status: MirrorStatus;
  error: string | null;
  salonName: string;
  shadeMap: ShadeEntry[];
  consultation: Consultation | null;
  retained: boolean;
  captured: CapturedScan | null;
  signedAt: string | null;
  accepted: boolean;
  tombstoned: number;
}

export interface MirrorActions {
  reload(): void;
  setRetained(retained: boolean): Promise<void>;
  deleteEverything(): Promise<void>;
  acceptPlan(): Promise<void>;
  markSigned(signedAt: string): void;
  setCaptured(captured: CapturedScan): void;
}

const StateContext = createContext<MirrorState | null>(null);
const ActionsContext = createContext<MirrorActions | null>(null);

const initialState: MirrorState = {
  status: "loading",
  error: null,
  salonName: "",
  shadeMap: [],
  consultation: null,
  retained: false,
  captured: null,
  signedAt: null,
  accepted: false,
  tombstoned: 0,
};

function hasAcceptedEvent(consultation: Consultation): boolean {
  return consultation.events.some((event) => event.type === "plan.accepted");
}

export function MirrorProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<MirrorState>(initialState);
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, status: "loading", error: null }));
    Promise.all([loadSnapshot(), mirrorApi().demoConsultation()])
      .then(([snapshot, consultation]) => {
        if (cancelled) return;
        setState((s) => ({
          ...s,
          status: "ready",
          salonName: snapshot.salon.name,
          shadeMap: snapshot.shade_map,
          consultation,
          accepted: hasAcceptedEvent(consultation),
        }));
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const deleted = error instanceof ClientDataDeletedError;
        setState((s) => ({
          ...s,
          status: deleted ? "deleted" : "error",
          error: error instanceof Error ? error.message : String(error),
        }));
      });
    return () => {
      cancelled = true;
    };
  }, [generation]);

  const reload = useCallback(() => setGeneration((g) => g + 1), []);

  const setRetained = useCallback(async (retained: boolean) => {
    const clientId = state.consultation?.client.id;
    if (clientId) await mirrorApi().setRetention(clientId, retained);
    setState((s) => ({ ...s, retained }));
  }, [state.consultation]);

  const deleteEverything = useCallback(async () => {
    const clientId = state.consultation?.client.id;
    if (!clientId) return;
    const result = await mirrorApi().deleteClientData(clientId);
    setState((s) => ({ ...s, status: "deleted", consultation: null, tombstoned: result.tombstoned }));
  }, [state.consultation]);

  const acceptPlan = useCallback(async () => {
    const id = state.consultation?.id;
    if (!id) return;
    const consultation = await mirrorApi().acceptPlan(id);
    setState((s) => ({ ...s, consultation, accepted: true }));
  }, [state.consultation]);

  const markSigned = useCallback((signedAt: string) => {
    setState((s) => ({ ...s, signedAt }));
  }, []);

  const setCaptured = useCallback((captured: CapturedScan) => {
    setState((s) => ({ ...s, captured }));
  }, []);

  const actions = useMemo<MirrorActions>(
    () => ({ reload, setRetained, deleteEverything, acceptPlan, markSigned, setCaptured }),
    [reload, setRetained, deleteEverything, acceptPlan, markSigned, setCaptured],
  );

  return (
    <StateContext.Provider value={state}>
      <ActionsContext.Provider value={actions}>{children}</ActionsContext.Provider>
    </StateContext.Provider>
  );
}

export function useMirrorState(): MirrorState {
  const value = useContext(StateContext);
  if (!value) throw new Error("useMirrorState needs MirrorProvider");
  return value;
}

export function useMirrorActions(): MirrorActions {
  const value = useContext(ActionsContext);
  if (!value) throw new Error("useMirrorActions needs MirrorProvider");
  return value;
}
