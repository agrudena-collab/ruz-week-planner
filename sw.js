const CACHE_NAME = "mezhdot25-2-v11";

const APP_FILES = [
  "./",
  "./index.html",
  "./schedule.json",
  "./changes.json",
  "./groups.json",
  "./manifest.json",
  "./group_schedules/164606.json"
];

const FETCH_TIMEOUT_MS = 10000;

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

async function fetchWithTimeout(request, timeout = FETCH_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    return await fetch(request, { signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function cacheOne(cache, file) {
  try {
    const response = await fetchWithTimeout(new Request(file, {
      cache: "no-store",
      credentials: "same-origin"
    }));
    if (response.ok) {
      await cache.put(file, response.clone());
      return true;
    }
  } catch (_) {}
  return false;
}

async function installAssets() {
  const cache = await caches.open(CACHE_NAME);
  await Promise.allSettled(APP_FILES.map(file => cacheOne(cache, file)));

  // Do not activate a new worker unless the minimum offline shell is present.
  // If these critical assets cannot be cached, the previous worker remains active.
  const shell = await cache.match("./index.html") || await cache.match("./");
  const defaultGroup = await cache.match("./group_schedules/164606.json");
  if (!shell || !defaultGroup) {
    throw new Error("critical offline assets are missing");
  }
}

self.addEventListener("install", event => {
  event.waitUntil(
    installAssets().then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys
        .filter(key => key !== CACHE_NAME && key.startsWith("mezhdot25-2-"))
        .map(key => caches.delete(key))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;

  const requestUrl = new URL(request.url);
  const isSameOrigin = requestUrl.origin === self.location.origin;
  if (!isSameOrigin) return;

  const isDataFile =
    requestUrl.pathname.endsWith("/schedule.json") ||
    requestUrl.pathname.endsWith("/changes.json") ||
    requestUrl.pathname.endsWith("/groups.json") ||
    requestUrl.pathname.endsWith("/group_schedules.json") ||
    requestUrl.pathname.includes("/group_schedules/");

  const isAppShell =
    request.mode === "navigate" ||
    requestUrl.pathname.endsWith("/index.html");

  if (isDataFile || isAppShell) {
    event.respondWith((async () => {
      try {
        const response = await fetchWithTimeout(request);
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME)
            .then(cache => cache.put(cacheKey(request), copy))
            .catch(() => {});
        }
        return response;
      } catch (_) {
        const cache = await caches.open(CACHE_NAME);
        const cached = await cache.match(request, { ignoreSearch: true })
          || await cache.match(cacheKey(request));
        if (cached) return cached;

        if (isAppShell) {
          return new Response(
            "<!doctype html><meta charset=\"utf-8\"><title>Расписание</title><body style=\"font-family:-apple-system,sans-serif;padding:24px;background:#07090f;color:#fff\"><h1>Расписание</h1><p>Офлайн-версия ещё не была сохранена на этом устройстве.</p></body>",
            { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
          );
        }

        return new Response(
          JSON.stringify({ error: "offline-or-timeout" }),
          { status: 504, headers: { "Content-Type": "application/json; charset=utf-8" } }
        );
      }
    })());
    return;
  }

  event.respondWith(
    caches.open(CACHE_NAME).then(cache =>
      cache.match(request, { ignoreSearch: true }).then(cached =>
        cached || fetch(request)
      )
    )
  );
});
