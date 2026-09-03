import { currentSession } from "./auth";
import { dataMode, loadSnapshot, xanoBaseUrl } from "./data";
import type { ConsultationEvent } from "./events";
import type { Consultation, Snapshot } from "./snapshot";

export interface ScanTicket {
  scan_id: string;
  upload_url: string;
}

export interface MirrorApi {
  demoConsultation(): Promise<Consultation>;
  getConsultation(id: string): Promise<Consultation>;
  createScan(consultationId: string): Promise<ScanTicket>;
  uploadImage(uploadUrl: string, image: Blob): Promise<void>;
  completeScan(scanId: string, imageSha256: string, retained: boolean): Promise<void>;
  acceptPlan(consultationId: string): Promise<Consultation>;
  setRetention(clientId: string, retained: boolean): Promise<{ retained: boolean }>;
  deleteClientData(clientId: string): Promise<{ tombstoned: number }>;
}

export class ClientDataDeletedError extends Error {
  constructor() {
    super("This client's data has been deleted.");
  }
}

const demoClientId = "cl-01";

function findDemo(snapshot: Snapshot): Consultation {
  const done = Object.values(snapshot.consultations).filter(
    (c) => c.client.id === demoClientId && c.state === "done",
  );
  const match = done[0] ?? Object.values(snapshot.consultations)[0];
  if (!match) throw new Error("The snapshot holds no consultations.");
  return match;
}

function nowIso(): string {
  return new Date().toISOString();
}

class FixtureMirrorApi implements MirrorApi {
  private readonly overlay = new Map<string, Consultation>();
  private readonly retention = new Map<string, boolean>();
  private readonly tombstoned = new Set<string>();
  private scanCounter = 0;

  private async resolve(id: string): Promise<Consultation> {
    const overlaid = this.overlay.get(id);
    if (overlaid) return overlaid;
    const snapshot = await loadSnapshot();
    const found = snapshot.consultations[id];
    if (!found) throw new Error(`No consultation ${id}`);
    return found;
  }

  private guard(consultation: Consultation): Consultation {
    if (this.tombstoned.has(consultation.client.id)) throw new ClientDataDeletedError();
    return consultation;
  }

  async demoConsultation(): Promise<Consultation> {
    const snapshot = await loadSnapshot();
    const base = findDemo(snapshot);
    return this.guard(await this.resolve(base.id));
  }

  async getConsultation(id: string): Promise<Consultation> {
    return this.guard(await this.resolve(id));
  }

  async createScan(consultationId: string): Promise<ScanTicket> {
    this.scanCounter += 1;
    return {
      scan_id: `scan-local-${this.scanCounter}`,
      upload_url: `fixture://uploads/${consultationId}/${this.scanCounter}`,
    };
  }

  async uploadImage(): Promise<void> {
    return;
  }

  async completeScan(): Promise<void> {
    return;
  }

  async acceptPlan(consultationId: string): Promise<Consultation> {
    const current = this.guard(await this.resolve(consultationId));
    const accepted: ConsultationEvent = {
      id: `evt-local-${current.events.length + 1}`,
      consultation_id: current.id,
      salon_id: current.events[0]?.salon_id ?? "salon-atelier-noor",
      type: "plan.accepted",
      payload: { total_cents: current.plan?.total_cents ?? 0, as_of: nowIso() },
      ts: nowIso(),
      actor: "client",
    };
    const next = { ...current, events: [...current.events, accepted] };
    this.overlay.set(consultationId, next);
    return next;
  }

  async setRetention(clientId: string, retained: boolean): Promise<{ retained: boolean }> {
    this.retention.set(clientId, retained);
    return { retained };
  }

  async deleteClientData(clientId: string): Promise<{ tombstoned: number }> {
    const snapshot = await loadSnapshot();
    const count = Object.values(snapshot.consultations).filter(
      (c) => c.client.id === clientId,
    ).length;
    this.tombstoned.add(clientId);
    return { tombstoned: count };
  }
}

class LiveMirrorApi implements MirrorApi {
  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const token = currentSession()?.token;
    const response = await fetch(`${xanoBaseUrl()}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init.headers ?? {}),
      },
    });
    if (response.status === 410) throw new ClientDataDeletedError();
    if (!response.ok) throw new Error(`${path} failed with ${response.status}`);
    return response.json() as Promise<T>;
  }

  async demoConsultation(): Promise<Consultation> {
    const snapshot = await loadSnapshot();
    return findDemo(snapshot);
  }

  getConsultation(id: string): Promise<Consultation> {
    return this.request(`/mirror/consultations/${id}`);
  }

  createScan(consultationId: string): Promise<ScanTicket> {
    return this.request("/mirror/scans", {
      method: "POST",
      body: JSON.stringify({ consultation_id: consultationId }),
    });
  }

  async uploadImage(uploadUrl: string, image: Blob): Promise<void> {
    const response = await fetch(uploadUrl, {
      method: "PUT",
      body: image,
      headers: { "Content-Type": image.type },
    });
    if (!response.ok) throw new Error(`upload failed with ${response.status}`);
  }

  async completeScan(scanId: string, imageSha256: string, retained: boolean): Promise<void> {
    await this.request(`/mirror/scans/${scanId}/complete`, {
      method: "POST",
      body: JSON.stringify({ image_sha256: imageSha256, retained }),
    });
  }

  acceptPlan(consultationId: string): Promise<Consultation> {
    return this.request(`/mirror/consultations/${consultationId}/accept-plan`, {
      method: "POST",
    });
  }

  setRetention(clientId: string, retained: boolean): Promise<{ retained: boolean }> {
    return this.request(`/mirror/clients/${clientId}/retention`, {
      method: "POST",
      body: JSON.stringify({ retained }),
    });
  }

  deleteClientData(clientId: string): Promise<{ tombstoned: number }> {
    return this.request(`/mirror/clients/${clientId}/data`, { method: "DELETE" });
  }
}

let instance: MirrorApi | null = null;

export function mirrorApi(): MirrorApi {
  if (!instance) instance = dataMode() === "fixtures" ? new FixtureMirrorApi() : new LiveMirrorApi();
  return instance;
}
