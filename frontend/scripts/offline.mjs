import { readdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const assets = (await readdir('dist/assets')).map(name => `/assets/${name}`);
const version = createHash('sha256').update(await readFile('dist/index.html')).digest('hex').slice(0, 12);
await writeFile('dist/sw.js', `
const CACHE = 'fantasy-shell-${version}';
const ASSETS = ${JSON.stringify(['/', '/index.html', ...assets])};
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('fantasy-shell-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  if (event.request.mode === 'navigate' && ['/', '/index.html'].includes(url.pathname)) {
    event.respondWith(caches.open(CACHE).then(cache => cache.match('/index.html')).then(saved => saved || fetch(event.request)));
  } else if (ASSETS.includes(url.pathname)) {
    event.respondWith(caches.open(CACHE).then(cache => cache.match(url.pathname, { ignoreVary: true })).then(saved => saved || fetch(event.request)));
  }
});
`);
