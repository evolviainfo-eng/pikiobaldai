/* Pikio baldai: darbų galerijos peržiūra (native <dialog>, rodyklės, Esc, braukimas) */
(function () {
  var box = document.querySelector('[data-lbox]');
  var raw = document.getElementById('lb-data');
  if (!box || !raw || typeof box.showModal !== 'function') return;
  var data = JSON.parse(raw.textContent);
  var img = box.querySelector('[data-lb-img]');
  var title = box.querySelector('[data-lb-title]');
  var count = box.querySelector('[data-lb-count]');
  var root = document.documentElement;
  var cur = null, i = 0, opener = null;

  function lenis() { return window.__motion && window.__motion.lenis; }

  function show() {
    var p = cur.photos[i];
    img.removeAttribute('srcset');
    img.src = p.src;
    img.srcset = p.srcset;
    img.sizes = '100vw';
    img.width = p.w; img.height = p.h;
    img.alt = p.alt;
    count.textContent = (i + 1) + ' / ' + cur.photos.length;
    var next = cur.photos[(i + 1) % cur.photos.length];
    if (next) { var pre = new Image(); pre.sizes = '100vw'; pre.srcset = next.srcset; }
  }
  function step(d) { if (!cur) return; i = (i + d + cur.photos.length) % cur.photos.length; show(); }

  function open(slug, btn) {
    cur = data[slug]; if (!cur) return;
    opener = btn; i = 0;
    title.textContent = cur.title;
    show();
    box.showModal();
    root.classList.add('lb-open');
    if (lenis()) lenis().stop();
  }
  box.addEventListener('close', function () {
    root.classList.remove('lb-open');
    if (lenis()) lenis().start();
    if (opener) opener.focus();
  });

  document.addEventListener('click', function (ev) {
    var t = ev.target.closest('[data-lb]');
    if (t) { ev.preventDefault(); open(t.getAttribute('data-lb'), t); }
  });
  box.querySelector('[data-lb-close]').addEventListener('click', function () { box.close(); });
  box.querySelector('[data-lb-prev]').addEventListener('click', function () { step(-1); });
  box.querySelector('[data-lb-next]').addEventListener('click', function () { step(1); });
  box.addEventListener('keydown', function (ev) {
    if (ev.key === 'ArrowRight') { ev.preventDefault(); step(1); }
    if (ev.key === 'ArrowLeft') { ev.preventDefault(); step(-1); }
  });
  img.addEventListener('click', function () { step(1); });

  var x0 = null;
  box.addEventListener('pointerdown', function (ev) { if (ev.pointerType !== 'mouse') x0 = ev.clientX; });
  box.addEventListener('pointerup', function (ev) {
    if (x0 === null) return;
    var dx = ev.clientX - x0; x0 = null;
    if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1);
  });
})();
