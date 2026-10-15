/* Cardiff Plumbing motion (2026-10-12). Calm, robust, never strands content.
   - Lenis smooth wheel, lerp 0.11 (the dearto recipe), anchors with duration 1.15; off under reduced motion.
   - Hero: the photograph is visible at once and settles 1.08 -> 1; the text arrives as blocks, 140 ms apart.
   - Reveals: .rv blocks and [data-stagger] children fade up once. Three independent triggers
     (IntersectionObserver, scroll/resize, a 200 ms interval) mark in only what is on screen,
     so nothing is left hidden after fast scrolls, anchor jumps or in automation.
   - [data-par] photographs drift a few percent inside their frame on desktop.
   - The header steps away while reading down and returns on the way up. */
(function () {
  var root = document.documentElement;
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
  var nav = document.querySelector('[data-nav]');
  var hero = document.querySelector('[data-hero]');
  var navH = function () { return nav && getComputedStyle(nav).position === 'fixed' ? nav.offsetHeight : 0; };

  /* smooth scroll */
  var lenis = null;
  if (!reduce && fine && window.Lenis) {
    lenis = new Lenis({ smoothWheel: true, smoothTouch: false, lerp: 0.11 });
    (function raf(t) { lenis.raf(t); requestAnimationFrame(raf); })(0);
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href^="#"]'); if (!a) return;
    var id = a.getAttribute('href'); if (id.length < 2) return;
    var t = document.querySelector(id); if (!t) return;
    e.preventDefault();
    var off = t === hero ? 0 : -navH();
    if (lenis) lenis.scrollTo(t, { offset: off, duration: 1.15 });
    else window.scrollTo({ top: t.getBoundingClientRect().top + scrollY + off, behavior: reduce ? 'auto' : 'smooth' });
  });

  /* stagger indices for list children */
  [].forEach.call(document.querySelectorAll('[data-stagger]'), function (g) {
    var step = +(g.getAttribute('data-stagger') || 80);
    [].forEach.call(g.children, function (c, i) { c.style.setProperty('--i', i); c.style.setProperty('--step', step + 'ms'); });
  });

  var heroEls = hero ? [].slice.call(hero.querySelectorAll('.rv, [data-stagger]')) : [];
  var pending = [].slice.call(document.querySelectorAll('.rv, [data-stagger]')).filter(function (el) { return heroEls.indexOf(el) < 0; });
  var markIn = function (el) { el.classList.add('in'); };

  if (reduce) {
    root.classList.add('is-ready');
    heroEls.concat(pending).forEach(markIn);
    pending = [];
  } else {
    /* hero entrance after the display face is ready (never waits more than 700 ms) */
    var go = function () {
      if (root.classList.contains('is-ready')) return;
      root.classList.add('is-ready');
      requestAnimationFrame(function () { heroEls.forEach(markIn); });
    };
    var fonts = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    Promise.race([fonts, new Promise(function (r) { setTimeout(r, 700); })]).then(go);
    setTimeout(go, 1200);

    /* reveal everything that is on screen or already passed; nothing below the fold.
       Pikio: a block counts as on screen once it is 40 px in (a tall block peeking at the bottom of an iPhone was left hidden at 0.9h) */
    var tick = function () {
      if (!pending.length) return stop();
      var h = innerHeight;
      pending = pending.filter(function (el) {
        var r = el.getBoundingClientRect();
        if (r.top < h - 40 || r.bottom < 0) { markIn(el); return false; }
        return true;
      });
      if (!pending.length) stop();
    };
    var queued = false;
    var onScroll = function () { if (!queued) { queued = true; requestAnimationFrame(function () { queued = false; tick(); }); } };
    var io = 'IntersectionObserver' in window ? new IntersectionObserver(function () { tick(); }, { rootMargin: '0px 0px -40px 0px', threshold: [0, 0.15] }) : null;
    if (io) pending.forEach(function (el) { io.observe(el); });
    addEventListener('scroll', onScroll, { passive: true });
    addEventListener('resize', onScroll);
    if (lenis) lenis.on('scroll', onScroll);
    var iv = setInterval(tick, 200);
    var stop = function () { clearInterval(iv); removeEventListener('scroll', onScroll); removeEventListener('resize', onScroll); if (io) io.disconnect(); };
    addEventListener('beforeprint', function () { pending.forEach(markIn); pending = []; });
    setTimeout(tick, 60);
  }

  /* parallax inside photo frames: desktop, fine pointer, motion allowed */
  var pars = [].slice.call(document.querySelectorAll('[data-par]'));
  if (!reduce && fine && innerWidth >= 1024 && pars.length) {
    root.classList.add('has-par');
    var par = function () {
      var vh = innerHeight;
      pars.forEach(function (el) {
        var box = el.parentElement.getBoundingClientRect();
        if (box.bottom < -100 || box.top > vh + 100) return;
        var p = ((box.top + box.height / 2) - vh / 2) / (vh / 2 + box.height / 2);
        el.style.setProperty('--py', (-p * (+(el.getAttribute('data-par') || 5))).toFixed(3) + '%');
      });
    };
    par();
    addEventListener('scroll', par, { passive: true });
    if (lenis) lenis.on('scroll', par);
  }

  /* header: hairline once scrolled, steps away reading down past the hero, back on the way up */
  if (nav) {
    var lastY = scrollY;
    var onNav = function (y) {
      y = typeof y === 'number' ? y : scrollY;
      nav.classList.toggle('is-scrolled', y > 40);
      var dy = y - lastY; lastY = y;
      if (reduce) return;
      if (y > innerHeight * 0.9 && dy > 4) nav.classList.add('is-away');
      else if (dy < -4 || y < innerHeight * 0.5) nav.classList.remove('is-away');
    };
    addEventListener('scroll', function () { onNav(); }, { passive: true });
    nav.addEventListener('focusin', function () { nav.classList.remove('is-away'); });
    onNav();
  }

  window.__motion = { lenis: lenis };
})();
