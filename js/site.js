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
  window.__lbOpen = open;
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

/* „Iš ko pagaminta“: desktop'e medžiaga keičia plokštės nuotrauką, telefone atidaro projekto nuotraukas */
(function () {
  var root = document.querySelector('[data-mat]');
  var raw = document.getElementById('mat-data');
  if (!root || !raw) return;
  var data = JSON.parse(raw.textContent);
  var a = root.querySelector('[data-plate-a]'), b = root.querySelector('[data-plate-b]');
  var nameEl = root.querySelector('[data-plate-name]'), codeEl = root.querySelector('[data-plate-code]');
  var link = root.querySelector('[data-plate-link]'), projEl = root.querySelector('[data-plate-proj]');
  var btns = [].slice.call(root.querySelectorAll('[data-sw]'));
  var wide = matchMedia('(min-width: 1024px)');
  var fine = matchMedia('(hover: hover) and (pointer: fine)');
  var front = a, back = b, token = 0;
  var scrolledAt = 0;
  addEventListener('scroll', function () { scrolledAt = Date.now(); }, { passive: true });
  var cur = (btns.filter(function (x) { return x.getAttribute('aria-pressed') === 'true'; })[0] || btns[0]).getAttribute('data-sw');

  function select(id) {
    if (!data[id] || id === cur) return;
    cur = id;
    var d = data[id], t = ++token, img = back;
    btns.forEach(function (x) { x.setAttribute('aria-pressed', x.getAttribute('data-sw') === id ? 'true' : 'false'); });
    nameEl.textContent = d.name; codeEl.textContent = d.code;
    projEl.textContent = d.projTitle; link.setAttribute('data-lb', d.proj);
    img.style.objectPosition = d.pos; img.alt = d.alt; img.width = d.w; img.height = d.h;
    img.srcset = d.srcset; img.src = d.src;
    var swap = function () {
      if (t !== token) return;
      img.classList.add('is-front'); img.removeAttribute('aria-hidden');
      front.classList.remove('is-front'); front.setAttribute('aria-hidden', 'true');
      back = front; front = img;
    };
    if (img.decode) img.decode().then(swap, swap); else img.onload = swap;
  }

  btns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (wide.matches) select(btn.getAttribute('data-sw'));
      else if (window.__lbOpen) window.__lbOpen(btn.getAttribute('data-proj'), btn);
    });
    /* hover swaps only when the pointer moves onto a swatch, not when the page scrolls under a resting cursor */
    btn.addEventListener('mouseenter', function () { if (wide.matches && fine.matches && Date.now() - scrolledAt > 250) select(btn.getAttribute('data-sw')); });
  });
})();
