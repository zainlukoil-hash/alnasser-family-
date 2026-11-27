/* Al-Nasser family platform · the page's worker · build 238
   It does three small things: it makes the page installable as an app, it keeps one copy of the page for opening without the internet
   (the page opens from that copy at once; a new build is brought by the page's own update, with a progress bar), and it can tell the phone that a newer build is out. */
var B = 238, CACHE = 'nsr-page';
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil(self.clients.claim());
});
self.addEventListener('fetch', function (e) {
  var r = e.request;
  if (r.method !== 'GET' || r.mode !== 'navigate') return;
  /* build 209: the page is opened FROM THE PHONE whenever a copy is kept, at once, with no question asked of the network. Before, every opening asked the network first (a 15 MB page, on a weak
     connection a long black wait and a download of its own each time). A newer build is brought by the page's own update (it checks «latest.json», takes the new page through this worker with a
     progress bar, and restarts itself), so nothing is hidden by the kept copy.
     Only an explicit refresh («update now», address with ?b=) and the very first opening (nothing kept yet) go to the network, and wait for it as long as it takes. */
  var forced = /[?&]b=\d/.test(r.url);
  var fin, finished = new Promise(function (res) { fin = res; });
  e.waitUntil(finished);
  e.respondWith(
    caches.open(CACHE).then(function (c) { return c.match('./index.html'); }).catch(function () { return null; }).then(function (cached) {
      if (cached && !forced) { fin(); return cached; }
      return fetch(r).then(function (res) {
        if (res && res.ok && res.type === 'basic' && !res.redirected) {
          var cp = res.clone();
          caches.open(CACHE).then(function (c) { return c.put('./index.html', cp); }).catch(function () {}).then(function () { fin(); });
        } else fin();
        return res;
      }, function (err) { fin(); if (cached) return cached; throw err; });
    })
  );
});
/* build 204 · the page's own update talk (it was written long ago and never answered): «are you there?» → «yes»; «bring build N» → the new page is fetched here, in the background, with progress,
   and kept; the page then starts it by itself. While it comes, the page in use goes on working. */
self.addEventListener('message', function (e) {
  var d = e.data || {}, src = e.source;
  function say(m) { try { if (src) src.postMessage(m); } catch (x) {} }
  if (d.type === 'afia-ping') { say({ type: 'afia-pong', b: B }); return; }
  if (d.type === 'afia-refresh') e.waitUntil(pull(d, say));
});
function pull(d, say) {
  return fetch('./index.html', { cache: 'reload' }).then(function (res) {
    if (!res || !res.ok) throw 'http ' + (res && res.status);
    var rd = res.body && res.body.getReader ? res.body.getReader() : null, parts = [], got = 0, last = 0;
    if (!rd) return res.blob();
    return (function pump() {
      return rd.read().then(function (x) {
        if (x.done) return new Blob(parts, { type: 'text/html; charset=utf-8' });
        parts.push(x.value); got += x.value.length;
        var n = Date.now(); if (n - last > 200) { last = n; say({ type: 'afia-prog', got: got, tot: d.size || 0 }); }
        return pump();
      });
    })();
  }).then(function (blob) {
    if (!blob || blob.size < 1000000) throw 'short';
    return caches.open(CACHE).then(function (c) {
      return c.put('./index.html', new Response(blob, { headers: { 'content-type': 'text/html; charset=utf-8' } }));
    });
  }).then(function () { say({ type: 'afia-ready', b: d.build }); }, function (err) { say({ type: 'afia-fail', why: String((err && err.message) || err) }); });
}
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
