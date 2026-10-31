// Makes the dashboard installable as an app on phones and tablets. Nothing is cached: every request goes to the
// server as usual, so an update of the dashboard shows at once and private data never sits in a cache.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
