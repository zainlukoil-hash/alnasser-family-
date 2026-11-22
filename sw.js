/* Al-Nasser family platform · the page's worker · build 195
   It does three small things: it makes the page installable as an app, it keeps one copy of the page for opening without the internet
   (the page is always asked from the network first, so a new build is never hidden by an old copy), and it can tell the phone that a newer build is out. */
var B = 195, CACHE = 'nsr-page';
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', function (e) {
  var r = e.request;
  if (r.method !== 'GET' || r.mode !== 'navigate') return;
  e.respondWith(
    fetch(r).then(function (res) {
      if (res && res.ok && res.type === 'basic' && !res.redirected) {
        var cp = res.clone();
        caches.open(CACHE).then(function (c) { return c.put('./index.html', cp); }).catch(function () {});
      }
      return res;
    }).catch(function () {
      return caches.open(CACHE).then(function (c) { return c.match('./index.html'); }).then(function (m) { return m || Response.error(); });
    })
  );
});
function check() {
  return fetch('latest.json?_=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (j) {
    if (j && j.b > B) return self.registration.showNotification('منصة عائلة الناصر', { body: 'نزل إصدار أحدث. افتح المنصة ليتحدّث تلقائياً.', tag: 'nsr-upd', icon: 'icon-192.png' });
  }).catch(function () {});
}
self.addEventListener('periodicsync', function (e) { if (e.tag === 'afia-upd') e.waitUntil(check()); });
self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (l) {
    for (var i = 0; i < l.length; i++) if ('focus' in l[i]) return l[i].focus();
    return self.clients.openWindow('./?src=app');
  }));
});
