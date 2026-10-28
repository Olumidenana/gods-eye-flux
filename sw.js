// Self-destroying service worker to ensure instant fresh live deployment
self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  // Always fetch fresh network
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
