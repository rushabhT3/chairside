/// <reference lib="webworker" />

const worker = self as unknown as ServiceWorkerGlobalScope;

const shellCache = "chairside-shell-v1";
const shell = ["./", "./mirror/", "./manifest.webmanifest", "./icon.svg"];

worker.addEventListener("install", (event: ExtendableEvent) => {
  event.waitUntil(
    caches
      .open(shellCache)
      .then((cache) => cache.addAll(shell))
      .then(() => worker.skipWaiting()),
  );
});

worker.addEventListener("activate", (event: ExtendableEvent) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== shellCache).map((k) => caches.delete(k))))
      .then(() => worker.clients.claim()),
  );
});

worker.addEventListener("fetch", (event: FetchEvent) => {
  if (event.request.method !== "GET" || event.request.mode !== "navigate") return;
  event.respondWith(
    fetch(event.request).catch(async () => {
      const cached = (await caches.match(event.request)) ?? (await caches.match("./mirror/"));
      return cached ?? Response.error();
    }),
  );
});
