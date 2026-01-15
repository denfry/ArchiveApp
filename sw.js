// Service Worker для PWA Архив документов
const CACHE_NAME = 'archive-v1.0.0';
const STATIC_CACHE = 'archive-static-v1.0.0';

// Ресурсы для кеширования
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/scanner',
    '/icon-72.png',
    '/icon-96.png',
    '/icon-128.png',
    '/icon-144.png',
    '/icon-192.png',
    '/icon-512.png'
];

// Установка Service Worker
self.addEventListener('install', (event) => {
    console.log('Service Worker installing.');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then((cache) => {
                console.log('Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .catch((error) => {
                console.error('Failed to cache static assets:', error);
            })
    );
    // Принудительная активация нового SW
    self.skipWaiting();
});

// Активация Service Worker
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating.');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== STATIC_CACHE && cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    // Захват контроля над клиентами
    self.clients.claim();
});

// Обработка запросов
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Пропускаем запросы к API и динамическим данным
    if (url.pathname.startsWith('/api/') ||
        url.pathname.includes('archive.db') ||
        event.request.method !== 'GET') {
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    return cachedResponse;
                }

                return fetch(event.request)
                    .then((response) => {
                        // Кешируем только успешные GET запросы
                        if (response.status === 200 &&
                            event.request.method === 'GET' &&
                            !url.pathname.startsWith('/api/')) {
                            const responseClone = response.clone();
                            caches.open(CACHE_NAME)
                                .then((cache) => {
                                    cache.put(event.request, responseClone);
                                });
                        }
                        return response;
                    })
                    .catch((error) => {
                        console.error('Fetch failed:', error);
                        // Возвращаем страницу оффлайн, если доступна
                        if (event.request.mode === 'navigate') {
                            return caches.match('/');
                        }
                        return new Response('', { status: 503, statusText: 'Service Unavailable' });
                    });
            })
    );
});

// Обработка сообщений от основного потока
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});