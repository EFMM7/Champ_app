// Service worker minimal : met en cache la "coquille" de l'app (HTML, icônes,
// manifest) pour un chargement plus rapide et un affichage possible hors-ligne
// de l'interface — les DONNÉES (zones, champs) nécessitent toujours l'API et
// ne sont pas mises en cache ici, volontairement, pour ne jamais afficher de
// données satellite périmées sans que l'utilisateur le sache.
//
// Un service worker (même minimal) est nécessaire sur Android/Chrome pour que
// le navigateur propose "Installer l'application" — sur iOS/Safari, ce n'est
// pas requis pour "Sur l'écran d'accueil" mais ne gêne pas non plus.

const CACHE_NAME = 'champ-app-shell-v1';
const SHELL_FILES = [
  '/onboarding_mobile.html',
  '/apercu_champ_mobile.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // ne jamais mettre en cache les appels API (/auth, /fields, /crops) —
  // uniquement la coquille visuelle statique
  if (SHELL_FILES.includes(url.pathname)) {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
  }
});
