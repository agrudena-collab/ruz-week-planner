const CACHE_NAME = "mezhdot25-2-v2";

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

  /*
   schedule.json и changes.json всегда
   пытаемся получить свежими из сети.
   Для changes.json URL может содержать ?t=Date.now(),
   поэтому кэшируем и читаем данные по URL без query-параметров.
  */

  const requestUrl = new URL(event.request.url);
  const isDataFile =
    requestUrl.pathname.endsWith("/schedule.json") ||
    requestUrl.pathname.endsWith("/changes.json");

  if(isDataFile){

    const cacheKey = new Request(
      new URL(
        requestUrl.pathname,
        self.location.origin
      ).href
    );

    event.respondWith(
      fetch(event.request)
        .then(response => {

          const copy = response.clone();

          caches.open(CACHE_NAME)
            .then(cache =>
              cache.put(cacheKey, copy)
            );

          return response;

        })
        .catch(() =>
          caches.match(cacheKey)
        )
    );

    return;

  }


  /*
   Для остальных файлов:
   сначала кэш, затем сеть.
  */

  event.respondWith(

    caches.match(event.request)
      .then(cached =>

        cached ||
        fetch(event.request)

      )

  );

});
