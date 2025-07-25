/**
 * Car Auction Analyzer - Service Worker
 * 
 * This service worker provides:
 * - Offline capability through strategic caching
 * - Background sync for photo uploads when offline
 * - Push notification support for analysis results
 */

// Cache names with versioning for proper cache management
const CACHE_VERSION = 'v1';
const STATIC_CACHE = `car-auction-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `car-auction-dynamic-${CACHE_VERSION}`;
const IMAGE_CACHE = `car-auction-images-${CACHE_VERSION}`;
const API_CACHE = `car-auction-api-${CACHE_VERSION}`;

// Assets to precache for offline functionality
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icons/icon-72x72.png',
  '/icons/icon-96x96.png',
  '/icons/icon-128x128.png',
  '/icons/icon-144x144.png',
  '/icons/icon-152x152.png',
  '/icons/icon-192x192.png',
  '/icons/icon-384x384.png',
  '/icons/icon-512x512.png',
  '/icons/apple-icon-152.png',
  '/icons/apple-icon-167.png',
  '/icons/apple-icon-180.png'
];

// Install event - precache static assets
self.addEventListener('install', event => {
  console.log('[Service Worker] Installing...');
  
  // Skip waiting to ensure the new service worker activates immediately
  self.skipWaiting();
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('[Service Worker] Precaching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch(error => {
        console.error('[Service Worker] Precaching failed:', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating...');
  
  // Claim clients to ensure control over all pages immediately
  self.clients.claim();
  
  event.waitUntil(
    caches.keys()
      .then(keyList => {
        return Promise.all(keyList.map(key => {
          // If the cache name doesn't match our current version, delete it
          if (
            key !== STATIC_CACHE && 
            key !== DYNAMIC_CACHE && 
            key !== IMAGE_CACHE && 
            key !== API_CACHE
          ) {
            console.log('[Service Worker] Removing old cache:', key);
            return caches.delete(key);
          }
        }));
      })
  );
  
  return self.clients.claim();
});

// Helper function to determine if a request is for an image
function isImageRequest(request) {
  return request.destination === 'image' || 
         request.url.match(/\.(jpg|jpeg|png|gif|svg|webp)$/i);
}

// Helper function to determine if a request is for an API endpoint
function isApiRequest(request) {
  return request.url.includes('/api/') || 
         request.url.includes('/analyze') ||
         request.url.includes('/vehicle');
}

// Fetch event - handle different caching strategies based on request type
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  
  // Don't cache POST requests or requests to other domains
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }
  
  let fetchPromise;
  
  // Strategy 1: Cache-first for static assets
  if (STATIC_ASSETS.includes(url.pathname) || url.pathname.startsWith('/icons/')) {
    fetchPromise = caches.match(request)
      .then(response => {
        if (response) {
          return response;
        }
        
        // If not in cache, fetch from network and cache
        return fetch(request)
          .then(networkResponse => {
            if (networkResponse && networkResponse.status === 200) {
              const clonedResponse = networkResponse.clone();
              caches.open(STATIC_CACHE)
                .then(cache => cache.put(request, clonedResponse));
            }
            return networkResponse;
          });
      });
  }
  // Strategy 2: Cache-first with network update for images
  else if (isImageRequest(request)) {
    fetchPromise = caches.match(request)
      .then(response => {
        // Return cached image immediately, but update cache in background
        const fetchPromise = fetch(request)
          .then(networkResponse => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(IMAGE_CACHE)
                .then(cache => cache.put(request, networkResponse.clone()));
            }
            return networkResponse;
          })
          .catch(error => {
            console.log('[Service Worker] Image fetch failed:', error);
          });
        
        return response || fetchPromise;
      });
  }
  // Strategy 3: Network-first with cache fallback for API requests
  else if (isApiRequest(request)) {
    fetchPromise = fetch(request)
      .then(networkResponse => {
        if (networkResponse && networkResponse.status === 200) {
          const clonedResponse = networkResponse.clone();
          caches.open(API_CACHE)
            .then(cache => cache.put(request, clonedResponse));
        }
        return networkResponse;
      })
      .catch(error => {
        console.log('[Service Worker] API fetch failed, falling back to cache:', error);
        return caches.match(request);
      });
  }
  // Strategy 4: Stale-while-revalidate for everything else
  else {
    fetchPromise = caches.match(request)
      .then(response => {
        // Return cached response immediately (if available)
        const fetchPromise = fetch(request)
          .then(networkResponse => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(DYNAMIC_CACHE)
                .then(cache => cache.put(request, networkResponse.clone()));
            }
            return networkResponse;
          })
          .catch(error => {
            console.log('[Service Worker] Fetch failed:', error);
          });
        
        return response || fetchPromise;
      });
  }
  
  event.respondWith(fetchPromise);
});

// Background sync for photo uploads
self.addEventListener('sync', event => {
  console.log('[Service Worker] Background Sync Event:', event.tag);
  
  if (event.tag === 'sync-photos') {
    event.waitUntil(
      // Get all pending uploads from IndexedDB
      self.indexedDB.open('car-auction-db', 1)
        .then(db => {
          const tx = db.transaction('pending-uploads', 'readonly');
          const store = tx.objectStore('pending-uploads');
          return store.getAll();
        })
        .then(pendingUploads => {
          const uploadPromises = pendingUploads.map(upload => {
            // Attempt to upload each pending photo
            return fetch('/api/analyze', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify(upload)
            })
            .then(response => {
              if (response.ok) {
                // If successful, remove from pending uploads
                const tx = db.transaction('pending-uploads', 'readwrite');
                const store = tx.objectStore('pending-uploads');
                return store.delete(upload.id);
              }
            });
          });
          
          return Promise.all(uploadPromises);
        })
        .catch(error => {
          console.error('[Service Worker] Sync failed:', error);
        })
    );
  }
});

// Push notification support
self.addEventListener('push', event => {
  console.log('[Service Worker] Push received:', event);
  
  let notificationData = {};
  
  if (event.data) {
    try {
      notificationData = event.data.json();
    } catch (e) {
      notificationData = {
        title: 'Car Auction Analyzer',
        body: event.data.text(),
        icon: '/icons/icon-192x192.png'
      };
    }
  } else {
    notificationData = {
      title: 'Car Auction Analyzer',
      body: 'New update available',
      icon: '/icons/icon-192x192.png'
    };
  }
  
  const options = {
    body: notificationData.body || 'Analysis complete!',
    icon: notificationData.icon || '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      url: notificationData.url || '/'
    },
    actions: [
      {
        action: 'view',
        title: 'View Results',
        icon: '/icons/view-icon.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/icons/close-icon.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(notificationData.title, options)
  );
});

// Handle notification click
self.addEventListener('notificationclick', event => {
  console.log('[Service Worker] Notification click:', event);
  
  event.notification.close();
  
  if (event.action === 'view') {
    const urlToOpen = event.notification.data && event.notification.data.url ? 
      event.notification.data.url : '/';
      
    event.waitUntil(
      clients.matchAll({ type: 'window' })
        .then(windowClients => {
          // Check if there is already a window/tab open with the target URL
          for (let client of windowClients) {
            if (client.url === urlToOpen && 'focus' in client) {
              return client.focus();
            }
          }
          // If no window/tab is open, open one
          if (clients.openWindow) {
            return clients.openWindow(urlToOpen);
          }
        })
    );
  }
});

// Periodic background sync (if supported by browser)
self.addEventListener('periodicsync', event => {
  if (event.tag === 'update-market-prices') {
    event.waitUntil(
      fetch('/api/market-prices')
        .then(response => response.json())
        .then(data => {
          // Store updated market prices in IndexedDB for offline use
          const dbPromise = self.indexedDB.open('car-auction-db', 1);
          dbPromise.then(db => {
            const tx = db.transaction('market-prices', 'readwrite');
            const store = tx.objectStore('market-prices');
            store.put(data);
            return tx.complete;
          });
          
          // Notify user if there are significant price changes
          if (data.significantChanges) {
            return self.registration.showNotification('Market Price Update', {
              body: 'Vehicle market prices have been updated',
              icon: '/icons/icon-192x192.png'
            });
          }
        })
        .catch(error => {
          console.error('[Service Worker] Periodic sync failed:', error);
        })
    );
  }
});

// Helper function for the app to check if it's online
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'CHECK_ONLINE_STATUS') {
    const isOnline = self.navigator.onLine;
    
    // Respond to the client
    event.ports[0].postMessage({
      type: 'ONLINE_STATUS_RESULT',
      online: isOnline
    });
  }
});

console.log('[Service Worker] Loaded successfully');
