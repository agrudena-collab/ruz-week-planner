const CACHE_NAME = "mezhdot25-2-v1";

const APP_FILES = [
  "./",
  "./index.html",
  "./schedule.json",
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
   schedule.json всегда пытаемся
   получить свежим из сети.
  */

  if(
    event.request.url.includes("schedule.json")
  ){

    event.respondWith(

      fetch(event.request)
        .then(response => {

          const copy =
            response.clone();

          caches.open(CACHE_NAME)
            .then(cache =>
              cache.put(
                event.request,
                copy
              )
            );

          return response;

        })

        .catch(() =>
          caches.match(event.request)
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
