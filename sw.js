const CACHE_NAME = "mezhdot25-2-v18";
const FETCH_TIMEOUT_MS = 4000;

const APP_SHELL = [
  "./",
  "./index.html",
  "./manifest.json",
  "./icon.png",
  "./schedule.json",
  "./archive.json",
  "./exams.json",
  "./changes.json",
  "./group-search.js",
  "./group_schedules/164606.json"
];

function cacheKey(request) {
  const url = new URL(request.url);
  url.search = "";
  return new Request(url.href, { method: "GET" });
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

async function warmShell() {
  const cache = await caches.open(CACHE_NAME);

  await Promise.allSettled(
    APP_SHELL.map(async file => {
      try {
        const response = await fetchWithTimeout(new Request(file, {
          cache: "reload",
          credentials: "same-origin"
        }));
        if (response.ok) {
          await cache.put(cacheKey(new Request(file)), response.clone());
        }
      } catch (_) {}
    })
  );

  const shell = await cache.match(cacheKey(new Request("./index.html")))
    || await cache.match(cacheKey(new Request("./")));
  if (!shell) throw new Error("offline app shell could not be cached");
}

self.addEventListener("install", event => {
  event.waitUntil(
    warmShell().then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys
          .filter(key => key.startsWith("mezhdot25-2-") && key !== CACHE_NAME)
          .map(key => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const key = cacheKey(request);
  const cached = await cache.match(key, { ignoreSearch: true });
  if (cached) return cached;

  try {
    const response = await fetchWithTimeout(request);
    if (response.ok) await cache.put(key, response.clone());
    return response;
  } catch (_) {
    return Response.error();
  }
}

async function injectGroupSearch(response) {
  if (!response || !response.ok) return response;
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("text/html")) return response;

  try {
    const html = await response.text();
    if (html.includes('src="./group-search.js"')) {
      return new Response(html, {
        status: response.status,
        statusText: response.statusText,
        headers: new Headers(response.headers)
      });
    }

    const injected = html.replace(
      /<\/body>/i,
      '<script src="./group-search.js"></script></body>'
    );

    const headers = new Headers(response.headers);
    headers.delete("content-length");
    headers.delete("content-encoding");
    headers.delete("etag");
    headers.delete("content-md5");
    return new Response(injected, {
      status: response.status,
      statusText: response.statusText,
      headers
    });
  } catch (_) {
    return response;
  }
}

async function networkFirstNavigation(request) {
  const cache = await caches.open(CACHE_NAME);
  const key = cacheKey(request);

  try {
    const response = await fetchWithTimeout(request, 2500);
    if (response.ok) await cache.put(key, response.clone());
    return injectGroupSearch(response);
  } catch (_) {
    const cached = await cache.match(key, { ignoreSearch: true });
    if (cached) return injectGroupSearch(cached);

    return new Response(
      "<!doctype html><meta charset=\"utf-8\"><title>Расписание</title><body style=\"font-family:-apple-system,sans-serif;padding:24px;background:#07090f;color:#fff\"><h1>Расписание</h1><p>Офлайн-версия ещё не сохранена на этом устройстве.</p></body>",
      { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
    );
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const key = cacheKey(request);
  const cached = await cache.match(key, { ignoreSearch: true });

  const refresh = fetchWithTimeout(request).then(async response => {
    if (response.ok) await cache.put(key, response.clone());
    return response;
  }).catch(() => null);

  if (cached) return cached;

  return (await refresh) || new Response(
    JSON.stringify({ error: "offline-or-timeout" }),
    { status: 504, headers: { "Content-Type": "application/json; charset=utf-8" } }
  );
}

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  const isData =
    url.pathname.endsWith("/schedule.json") ||
    url.pathname.endsWith("/changes.json") ||
    url.pathname.endsWith("/groups.json") ||
    url.pathname.endsWith("/group_schedules.json") ||
    url.pathname.includes("/group_schedules/") ||
    url.pathname.includes("/changes_by_group/");

  const isNavigation = request.mode === "navigate" || url.pathname.endsWith("/index.html");

  if (isNavigation) {
    event.respondWith(networkFirstNavigation(request));
    return;
  }

  if (isData) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  event.respondWith(cacheFirst(request));
});
