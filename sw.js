const CACHE_NAME = "mezhdot25-2-v7";

const APP_FILES = [
  "./",
  "./index.html",
  "./schedule.json",
  "./changes.json",
  "./groups.json",
  "./manifest.json"
];

function cacheKey(request) {
  const url = new URL(request.url);
  url.search = "";
  return new Request(url.href, {
    method: "GET",
    headers: request.headers,
    mode: request.mode,
    credentials: request.credentials,
    redirect: request.redirect
  });
}

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_FILES)));
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const requestUrl = new URL(event.request.url);
  const isDataFile =
    requestUrl.pathname.endsWith("/schedule.json") ||
    requestUrl.pathname.endsWith("/changes.json") ||
    requestUrl.pathname.endsWith("/groups.json") ||
    requestUrl.pathname.includes("/group_schedules/");
  const isAppShell = event.request.mode === "navigate" || requestUrl.pathname.endsWith("/index.html");

  if (isDataFile || isAppShell) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(cacheKey(event.request), copy)).catch(() => {});
          }
          return response;
        })
        .catch(() => caches.match(event.request).then(cached => cached || caches.match(cacheKey(event.request))))
    );
    return;
  }

  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
