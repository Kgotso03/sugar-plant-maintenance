/**
 * Sugar Plant Predictive Maintenance Service Worker
 * Caches only safe static assets and application shell.
 * Never caches dynamic or authenticated operational telemetry to prevent data leakage.
 */

const CACHE_NAME = "sugarmaint-v1.0";
const STATIC_ASSETS = [
  "/static/css/style.css",
  "/static/js/main.js",
  "/static/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  // Only intercept GET requests for static assets
  if (event.request.method === "GET" && event.request.url.includes("/static/")) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        return cached || fetch(event.request);
      })
    );
  }
});
