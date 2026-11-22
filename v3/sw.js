// v3 now lives at the site root. This worker removes itself and its caches so /v3/ falls through to the redirect.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.map(k => caches.delete(k)))).then(() => self.registration.unregister())));
