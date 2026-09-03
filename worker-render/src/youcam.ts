const API_BASE = "https://yce-api-01.makeupar.com/s2s";
const POLL_INTERVAL_MS = 2000;
const POLL_ATTEMPTS = 30;

export class YouCamError extends Error {}

interface UploadTicket {
  fileId: string;
  method: string;
  url: string;
  headers: Record<string, string>;
}

async function postJson(path: string, apiKey: string, body: unknown): Promise<any> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json<any>();
  if (!response.ok) throw new YouCamError(payload?.error ?? `YouCam ${path} returned ${response.status}`);
  return payload;
}

async function requestUploadTicket(apiKey: string, size: number): Promise<UploadTicket> {
  const payload = await postJson("/v2.0/file", apiKey, {
    files: [{ content_type: "image/jpeg", file_name: "scan.jpg", file_size: size }],
  });
  const file = payload?.data?.files?.[0];
  const request = file?.requests?.[0];
  if (!file?.file_id || !request?.url) throw new YouCamError("YouCam returned no upload ticket");
  return { fileId: file.file_id, method: request.method ?? "PUT", url: request.url, headers: request.headers ?? {} };
}

async function putBytes(ticket: UploadTicket, image: ArrayBuffer): Promise<void> {
  const response = await fetch(ticket.url, { method: ticket.method, headers: ticket.headers, body: image });
  if (!response.ok) throw new YouCamError(`upload to storage returned ${response.status}`);
}

async function pollTask(feature: string, version: string, apiKey: string, taskId: string): Promise<any> {
  for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    const response = await fetch(`${API_BASE}/${version}/task/${feature}/${taskId}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    const payload = await response.json<any>();
    const data = payload?.data;
    if (data?.task_status === "error") throw new YouCamError(data.error_message ?? data.error ?? "task failed");
    if (data?.task_status && data.task_status !== "running") return data;
  }
  throw new YouCamError(`task ${taskId} still running after ${POLL_ATTEMPTS} polls`);
}

function firstUrl(data: any): string {
  const results = data?.results;
  const url = results?.url ?? results?.output?.[0]?.url;
  if (!url) throw new YouCamError("YouCam returned no render URL");
  return url;
}

/** Renders one hair colour on an uploaded scan and returns the signed image URL. */
export async function hairColour(apiKey: string, image: ArrayBuffer, hex: string): Promise<string> {
  const ticket = await requestUploadTicket(apiKey, image.byteLength);
  await putBytes(ticket, image);
  const created = await postJson("/v2.0/task/hair-color", apiKey, {
    src_file_id: ticket.fileId,
    pattern: { name: "full" },
    palettes: [{ color: hex.toUpperCase(), color_intensity: 100, shine_intensity: 100 }],
  });
  const taskId = created?.data?.task_id;
  if (!taskId) throw new YouCamError("YouCam returned no task id");
  return firstUrl(await pollTask("hair-color", "v2.0", apiKey, taskId));
}
