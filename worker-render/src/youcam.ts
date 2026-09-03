const API_BASE = "https://yce-api-01.makeupar.com/s2s";
// A Worker gets 50 subrequests, and three go on the upload and the task, so poll slower rather than more.
const POLL_INTERVAL_MS = 4000;
const POLL_ATTEMPTS = 42;

export class YouCamError extends Error {}

/** YouCam reports frame problems as codes; the client shows these strings to whoever is at the mirror. */
const FRAME_ADVICE: Record<string, string> = {
  error_src_face_too_small: "Come closer so your face fills the frame, then scan again.",
  error_src_face_out_of_bound: "Move back a little so your whole face is inside the frame.",
  error_face_angle_invalid: "Face the camera straight on, chin level, then scan again.",
  error_no_shoulder: "Step back so your shoulders are in the frame, then scan again.",
  error_hair_too_short: "This style needs longer hair to work from.",
  error_large_face_angle: "Face the camera straight on, then scan again.",
};

function advise(code: string, fallback: string): string {
  return FRAME_ADVICE[code] ?? fallback ?? code;
}

export type RenderKind = "hair" | "skin" | "style";

interface UploadTicket {
  fileId: string;
  method: string;
  url: string;
  headers: Record<string, string>;
}

interface TaskSpec {
  version: string;
  feature: string;
  body: Record<string, unknown>;
}

/** The salon's clarifying plan, the same weights the agent's deterministic table uses. */
const SKIN_TREATMENT = { radiance: 1.0, spots: 0.8 };
const DEFAULT_STYLE_TEMPLATE = "female_s_wave_brunette";

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

async function pollTask(spec: TaskSpec, apiKey: string, taskId: string): Promise<any> {
  for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
    const response = await fetch(`${API_BASE}/${spec.version}/task/${spec.feature}/${taskId}`, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });
    const payload = await response.json<any>();
    const data = payload?.data;
    if (data?.task_status === "error") {
      throw new YouCamError(advise(data.error ?? "", data.error_message ?? "The scan could not be read."));
    }
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

export function taskSpec(kind: RenderKind, fileId: string, shade: string, template: string): TaskSpec {
  if (kind === "hair") {
    return {
      version: "v2.0",
      feature: "hair-color",
      body: {
        src_file_id: fileId,
        pattern: { name: "full" },
        palettes: [{ color: shade.toUpperCase(), color_intensity: 100, shine_intensity: 100 }],
      },
    };
  }
  if (kind === "skin") {
    return { version: "v2.0", feature: "skin-simulation", body: { src_file_id: fileId, ...SKIN_TREATMENT } };
  }
  return {
    version: "v2.1",
    feature: "hair-transfer",
    body: { src_file_id: fileId, template_id: template || DEFAULT_STYLE_TEMPLATE },
  };
}

/** Uploads one scan and runs the requested render on it, returning the signed image URL. */
export async function render(
  apiKey: string,
  image: ArrayBuffer,
  kind: RenderKind,
  shade: string,
  template: string,
): Promise<string> {
  const ticket = await requestUploadTicket(apiKey, image.byteLength);
  await putBytes(ticket, image);
  const spec = taskSpec(kind, ticket.fileId, shade, template);
  const created = await postJson(`/${spec.version}/task/${spec.feature}`, apiKey, spec.body);
  const taskId = created?.data?.task_id;
  if (!taskId) throw new YouCamError("YouCam returned no task id");
  return firstUrl(await pollTask(spec, apiKey, taskId));
}
