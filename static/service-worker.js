// ─── SpendWise Service Worker ─────────────────────────────
const CACHE_NAME = 'spendwise-v1.2';
const STATIC_ASSETS = [
  '/',
  '/dashboard',
  '/transactions-page',
  '/settings',
  '/static/css/main.css',
  '/static/js/utils.js',
  '/static/js/dashboard.js',
  '/static/js/transactions.js',
  '/static/js/settings.js',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  'https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js',
];

const API_CACHE_NAME = 'spendwise-api-v1';
const API_CACHEABLE = ['/dashboard/data', '/transactions', '/categories'];

// ─── Install ──────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return Promise.allSettled(
        STATIC_ASSETS.map(url => cache.add(url).catch(() => {}))
      );
    }).then(() => self.skipWaiting())
  );
});

// ─── Activate ─────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME && name !== API_CACHE_NAME)
          .map(name => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

// ─── Fetch Strategy ───────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET and cross-origin (except fonts/cdn)
  if (event.request.method !== 'GET') return;
  if (url.origin !== self.location.origin &&
      !url.hostname.includes('fonts.') &&
      !url.hostname.includes('jsdelivr.')) return;

  // API routes: network-first, fallback to cache
  const isAPI = API_CACHEABLE.some(path => url.pathname.startsWith(path));
  if (isAPI) {
    event.respondWith(networkFirstStrategy(event.request));
    return;
  }

  // Static assets: cache-first
  event.respondWith(cacheFirstStrategy(event.request));
});

async function cacheFirstStrategy(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('<h2>You are offline</h2>', {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}

async function networkFirstStrategy(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(API_CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(
      JSON.stringify({ error: 'You are offline', offline: true }),
      { headers: { 'Content-Type': 'application/json' } }
    );
  }
}

// ─── Push Notifications ───────────────────────────────────
self.addEventListener('push', (event) => {
  let data = { title: 'SpendWise 💰', body: "Have you recorded today's expenses?" };
  if (event.data) {
    try { data = { ...data, ...event.data.json() }; } catch {}
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/static/icons/icon-192.png',
      badge: '/static/icons/icon-192.png',
      vibrate: [200, 100, 200],
      tag: 'daily-reminder',
      renotify: true,
      actions: [
        { action: 'open', title: '➕ Add Expense' },
        { action: 'dismiss', title: 'Dismiss' },
      ],
      data: { url: '/transactions-page' }
    })
  );
});

// ─── Notification Click ───────────────────────────────────
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.action === 'dismiss' ? null
    : (event.notification.data?.url || '/dashboard');

  if (!targetUrl) return;

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      return clients.openWindow(targetUrl);
    })
  );
});

// ─── Daily Reminder Scheduler ─────────────────────────────
// Triggered by the app via postMessage
self.addEventListener('message', (event) => {
  if (event.data?.type === 'SCHEDULE_REMINDER') {
    scheduleNextReminder();
  }
});

function scheduleNextReminder() {
  const now = new Date();
  const target = new Date();
  target.setHours(20, 0, 0, 0); // 8 PM
  if (target <= now) target.setDate(target.getDate() + 1);

  const delay = target.getTime() - now.getTime();

  setTimeout(() => {
    self.registration.showNotification('SpendWise 💰', {
      body: "Have you recorded today's expenses?",
      icon: '/static/icons/icon-192.png',
      badge: '/static/icons/icon-192.png',
      tag: 'daily-reminder',
      renotify: true,
      actions: [
        { action: 'open', title: '➕ Add Expense' },
        { action: 'dismiss', title: 'Later' },
      ],
      data: { url: '/transactions-page' }
    });
    // Reschedule for next day
    scheduleNextReminder();
  }, delay);
}

// ─── Background Sync (for offline transaction queue) ──────
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-transactions') {
    event.waitUntil(syncOfflineTransactions());
  }
});

async function syncOfflineTransactions() {
  // Placeholder for offline queue sync
  // In production: read from IndexedDB and POST to server
  console.log('[SW] Background sync triggered');
}
