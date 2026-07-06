const CACHE_NAME = 'upt-guardian-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/index.html',
  '/static/dashboard.html',
  '/static/style.css',
  '/static/dashboard.css',
  '/static/js/main.js',
  '/static/js/dashboard.js',
  '/static/js/visuals.js',
  '/static/icon-192.png',
  '/static/icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS_TO_CACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  // Try network first, then cache
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});

// Push Notification Event
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || '⚠️ CRITICAL ALERT';
  const options = {
    body: data.body || 'Disaster detected near your location.',
    icon: '/static/icon-192.png',
    badge: '/static/icon-192.png',
    vibrate: [500, 250, 500, 250, 500], // SOS vibration pattern
    requireInteraction: true,
    data: {
      url: data.url || '/'
    }
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Notification Click Event
self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url)
  );
});
