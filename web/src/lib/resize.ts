import type { ResizeRequest, ResizeResponse } from "./resize.worker";

export const maxUploadEdge = 1600;

export function resizeForUpload(image: Blob): Promise<ResizeResponse> {
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL("./resize.worker.ts", import.meta.url), { type: "module" });
    worker.onmessage = (event: MessageEvent<ResizeResponse | { error: string }>) => {
      worker.terminate();
      if ("error" in event.data) reject(new Error(event.data.error));
      else resolve(event.data);
    };
    worker.onerror = (event) => {
      worker.terminate();
      reject(new Error(event.message));
    };
    const request: ResizeRequest = { image, maxEdge: maxUploadEdge };
    worker.postMessage(request);
  });
}
