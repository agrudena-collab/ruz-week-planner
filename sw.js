const CACHE_NAME = "mezhdot25-2-v3";

const APP_FILES = [
  "./",
  "./index.html",
  "./schedule.json",
  "./changes.json",
  "./manifest.json"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_FILES))
  );

  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
  );

  self.clients.claim();
});

self.addEventListener("fetch", event => {
  const requestUrl = new URL(event.request.url);
  const isDataFile =
    requestUrl.pathname.endsWith("/schedule.json") ||
    requestUrl.pathname.endsWith("/changes.json");

  if (isDataFile) {
    const cacheKey = new Request(
      new URL(requestUrl.pathname, self.location.origin).href
    );

    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Never replace a good cached response with an HTTP error page.
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => cache.put(cacheKey, copy))
              .catch(() => {});
          }

          return response;
        })
        .catch(() => caches.match(cacheKey))
    );

    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(cached => cached || fetch(event.request))
  );
});

// Keep this branch synchronized so the PR workflow can install the UI.
