/* Pikio baldai: site.js (loaded with defer) */
(function () {
  'use strict';

  var d = document;
  var de = d.documentElement;
  var w = window;
  w.__pikio = 1;

  var qa = de.classList.contains('qa') || /[?&]qa=1(&|$)/.test(location.search);
  if (qa) {
    de.classList.add('qa');
    de.classList.remove('js-anim');
    de.style.scrollBehavior = 'auto';
  }

  var mq = function (q) { return w.matchMedia ? w.matchMedia(q) : { matches: false, addEventListener: function () {} }; };
  var mqReduce = mq('(prefers-reduced-motion: reduce)');
  var mqCoarse = mq('(pointer: coarse)');
  var mqFine = mq('(hover: hover) and (pointer: fine)');
  var mqDesk = mq('(min-width: 1024px)');
  var hasIO = 'IntersectionObserver' in w;
  var $ = function (s, c) { return (c || d).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || d).querySelectorAll(s)); };
  var reduced = function () { return qa || mqReduce.matches; };
  var animOn = function () { return de.classList.contains('js-anim') && !reduced(); };
  var onChange = function (m, fn) {
    if (m.addEventListener) m.addEventListener('change', fn);
    else if (m.addListener) m.addListener(fn);
  };
  /* resolve once an image can be shown: decode a detached copy (in-DOM decode() waits for frames),
     never wait longer than the fallback */
  var whenReady = function (im, cb, limit) {
    var done = false;
    var fire = function () { if (!done) { done = true; cb(); } };
    var decoded = function () {
      if (im.decode) im.decode().then(fire, fire);
      else fire();
      w.setTimeout(fire, 250);
    };
    if (im.complete && im.naturalWidth) decoded();
    else {
      im.addEventListener('load', decoded, { once: true });
      im.addEventListener('error', fire, { once: true });
    }
    w.setTimeout(fire, limit || 2500);
  };
  var rafThrottle = function (fn) {
    var queued = false;
    return function () {
      if (queued) return;
      queued = true;
      w.requestAnimationFrame(function () { queued = false; fn(); });
    };
  };

  /* ---------------------------------------------------------------- reveal */
  function initReveal() {
    var els = $$('.rv, .rv-line').filter(function (el) { return !el.closest('[data-hero]'); });
    var show = function (el) { el.classList.add('is-in'); };
    if (!animOn() || !hasIO) {
      els.forEach(show);
      return;
    }
    /* a hairline at scaleX(0) has no area, so its row is observed instead */
    var targetOf = function (el) { return el.classList.contains('rv-line') && el.parentElement ? el.parentElement : el; };
    var byTarget = new Map();
    els.forEach(function (el) {
      var t = targetOf(el);
      if (!byTarget.has(t)) byTarget.set(t, []);
      byTarget.get(t).push(el);
    });
    var alive = false;
    var io = new IntersectionObserver(function (entries) {
      alive = true;
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        (byTarget.get(e.target) || []).forEach(show);
        io.unobserve(e.target);
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
    byTarget.forEach(function (list, t) { io.observe(t); });

    var sweep = function () {
      var vh = w.innerHeight || de.clientHeight;
      byTarget.forEach(function (list, t) {
        if (list.every(function (el) { return el.classList.contains('is-in'); })) return;
        var r = t.getBoundingClientRect();
        if (r.bottom > 0 && r.top < vh && (r.width || r.height)) {
          list.forEach(show);
          io.unobserve(t);
        }
      });
    };
    w.setTimeout(function () {
      if (!alive) els.forEach(show); /* observer never answered: fail to visible */
      else sweep();
    }, 2500);
    w.addEventListener('load', function () { w.setTimeout(sweep, 60); });
    d.addEventListener('visibilitychange', function () { if (!d.hidden) sweep(); });
    onChange(mqReduce, function () { if (mqReduce.matches) els.forEach(show); });
  }

  /* ---------------------------------------------------------------- hero */
  function initHero() {
    var hero = $('[data-hero]');
    if (!hero) return;
    var done = false;
    var go = function () {
      if (done) return;
      done = true;
      hero.classList.add('is-in');
    };
    if (!animOn()) { go(); return; }
    var img = $('.hero__img', hero);
    var start = function () {
      w.requestAnimationFrame(function () { w.requestAnimationFrame(go); });
    };
    if (img && !img.complete && img.decode) {
      img.decode().then(start, start);
    } else {
      start();
    }
    w.setTimeout(go, 700); /* rAF can be throttled; never leave the hero hidden */
  }

  /* ---------------------------------------------------------------- nav */
  function initNav() {
    var nav = $('[data-nav]');
    if (!nav) return;
    var last = null;
    var update = function () {
      var on = (w.scrollY || w.pageYOffset) > 40;
      if (on !== last) {
        nav.classList.toggle('is-scrolled', on);
        last = on;
      }
    };
    update();
    w.addEventListener('scroll', update, { passive: true });
    w.addEventListener('pageshow', update);
  }

  /* ---------------------------------------------------------------- menu */
  function initMenu() {
    var dlg = $('[data-menu]');
    var openBtn = $('[data-menu-open]');
    if (!dlg || !openBtn || typeof dlg.showModal !== 'function') return;
    var closeBtn = $('[data-menu-close]', dlg);
    var closing = null;

    var finish = function (refocus) {
      if (closing) { w.clearTimeout(closing); closing = null; }
      if (dlg.open) dlg.close();
      de.classList.remove('is-locked');
      openBtn.setAttribute('aria-expanded', 'false');
      if (refocus) openBtn.focus({ preventScroll: true });
    };
    var open = function () {
      if (closing) finish(false);
      dlg.showModal();
      de.classList.add('is-locked');
      openBtn.setAttribute('aria-expanded', 'true');
      void dlg.offsetWidth;
      dlg.classList.add('is-open');
      if (closeBtn) closeBtn.focus({ preventScroll: true });
    };
    var close = function (refocus) {
      if (!dlg.open) return;
      dlg.classList.remove('is-open');
      if (reduced()) { finish(refocus); return; }
      closing = w.setTimeout(function () { finish(refocus); }, 460);
    };
    openBtn.addEventListener('click', open);
    if (closeBtn) closeBtn.addEventListener('click', function () { close(true); });
    dlg.addEventListener('cancel', function (e) { e.preventDefault(); close(true); });
    dlg.addEventListener('click', function (e) {
      var a = e.target.closest('a');
      if (a) close(false);
    });
    onChange(mqDesk, function () { if (mqDesk.matches && dlg.open) finish(false); });
  }

  /* ---------------------------------------------------------------- call bar */
  function initCallbar() {
    var bar = $('[data-callbar]');
    if (!bar) return;
    var phone = mq('(max-width: 767.98px)');
    var top = $('[data-hero]') || $('.phead') || $('.proj__head') || $('.solo');
    var form = $('#uzklausa');
    var update = function () {
      if (!phone.matches) { bar.classList.remove('is-on'); return; }
      var vh = w.innerHeight || de.clientHeight;
      var topOut = top ? top.getBoundingClientRect().bottom <= 0 : true;
      var fr = form ? form.getBoundingClientRect() : null;
      var formIn = fr ? (fr.top < vh && fr.bottom > 0) : false;
      bar.classList.toggle('is-on', topOut && !formIn);
    };
    w.addEventListener('scroll', update, { passive: true });
    w.addEventListener('resize', update, { passive: true });
    w.addEventListener('pageshow', update);
    onChange(phone, update);
    update();
  }

  /* ---------------------------------------------------------------- parallax */
  function initParallax() {
    var items = $$('[data-parallax]');
    if (!items.length || qa) return;
    var enabled = false;
    var update = function () {
      if (!enabled) return;
      var vh = w.innerHeight || de.clientHeight;
      items.forEach(function (el) {
        var host = el.closest('.hero, .brk');
        if (!host) return;
        var r = host.getBoundingClientRect();
        if (r.bottom < -40 || r.top > vh + 40) return;
        var ty;
        if (el.getAttribute('data-parallax') === 'hero') {
          ty = Math.min(Math.max(-r.top, 0), r.height) * 0.08;
        } else {
          var p = (vh - r.top) / (vh + r.height);
          p = Math.min(Math.max(p, 0), 1);
          ty = (p - 0.5) * 2 * 0.06 * r.height;
        }
        el.style.transform = 'translate3d(0,' + ty.toFixed(1) + 'px,0)';
      });
    };
    var check = function () {
      enabled = !mqReduce.matches && !mqCoarse.matches;
      if (!enabled) items.forEach(function (el) { el.style.transform = ''; });
      else update();
    };
    var tick = rafThrottle(update);
    w.addEventListener('scroll', tick, { passive: true });
    w.addEventListener('resize', tick, { passive: true });
    onChange(mqReduce, check);
    onChange(mqCoarse, check);
    check();
  }

  /* ---------------------------------------------------------------- filters */
  function listPlan(n) { /* mirrors list_plan() in gen.py */
    var size = { A: 2, B: 2, C: 3 };
    var cycle = 'ABC';
    var rows = [];
    var left = n;
    var i = 0;
    while (left > 0) {
      var t = cycle[i % 3];
      if (left >= size[t]) {
        rows.push(t);
        left -= size[t];
        i++;
        continue;
      }
      if (t === 'C') {
        if (left === 2) rows.push('A');
        else rows[rows.length - 1] = 'C';
      } else if (!rows.length) {
        rows.push('S');
      } else if (rows[rows.length - 1] === 'C') {
        rows[rows.length - 1] = 'A';
        rows.push('B');
      } else {
        rows[rows.length - 1] = 'C';
      }
      left = 0;
    }
    var map = { A: ['c-a1', 'c-a2'], B: ['c-b1', 'c-b2'], C: ['c-c', 'c-c', 'c-c'], S: ['c-s'] };
    var out = [];
    rows.forEach(function (r) { out = out.concat(map[r]); });
    return out;
  }

  function initTabs(tabs, onSelect) {
    var row = $('.tabs__row', tabs);
    var ind = $('.tabs__ind', tabs);
    var btns = $$('.tab', tabs);
    var active = btns.filter(function (b) { return b.getAttribute('aria-pressed') === 'true'; })[0] || btns[0];

    var place = function (instant) {
      if (!active || !ind) return;
      if (instant) ind.style.transition = 'none';
      ind.style.setProperty('--x', active.offsetLeft + 'px');
      ind.style.setProperty('--w', String(active.offsetWidth));
      if (instant) {
        void ind.offsetWidth;
        ind.style.transition = '';
      }
    };
    var edges = function () {
      var over = row.scrollWidth > row.clientWidth + 1;
      row.classList.toggle('is-overflow', over);
      row.classList.toggle('is-end', !over || row.scrollLeft + row.clientWidth >= row.scrollWidth - 2);
    };
    var reveal = function (btn) {
      if (row.scrollWidth <= row.clientWidth + 1) return;
      var l = btn.offsetLeft;
      var r = l + btn.offsetWidth;
      var target = null;
      if (l < row.scrollLeft + 8) target = Math.max(0, l - 16);
      else if (r > row.scrollLeft + row.clientWidth - 48) target = r - row.clientWidth + 56;
      if (target !== null) {
        try { row.scrollTo({ left: target, behavior: reduced() ? 'auto' : 'smooth' }); } catch (e) { row.scrollLeft = target; }
      }
    };
    var select = function (btn, fromUser) {
      if (!btn) return;
      btns.forEach(function (b) { b.setAttribute('aria-pressed', b === btn ? 'true' : 'false'); });
      active = btn;
      place(!fromUser);
      reveal(btn);
      onSelect(btn.getAttribute('data-k') || '', !!fromUser);
    };
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        if (b === active) return;
        select(b, true);
      });
    });
    row.addEventListener('scroll', rafThrottle(edges), { passive: true });
    var refresh = function () { place(true); edges(); };
    if (w.ResizeObserver) new ResizeObserver(rafThrottle(refresh)).observe(row);
    else w.addEventListener('resize', rafThrottle(refresh));
    if (d.fonts && d.fonts.ready) d.fonts.ready.then(refresh);
    refresh();
    return {
      selectKey: function (k, fromUser) {
        var b = btns.filter(function (x) { return (x.getAttribute('data-k') || '') === k; })[0];
        if (b) select(b, fromUser);
        return !!b;
      }
    };
  }

  /* plain crossfade: cards arrive at opacity 0, then fade in together (CSS 400ms) */
  function animateIn(grid, nodes) {
    if (reduced()) return;
    nodes.forEach(function (c) { c.classList.add('is-pre'); });
    void grid.offsetWidth;
    nodes.forEach(function (c) { c.classList.remove('is-pre'); });
  }

  function initHomeFilter() {
    var tabs = $('[data-tabs="home"]');
    var grid = $('[data-grid="home"]');
    var tpl = $('#tpl-cards');
    if (!tabs || !grid || !tpl || !tpl.content) return;
    var featured = JSON.parse(grid.getAttribute('data-featured') || '[]');
    var sizes = JSON.parse(grid.getAttribute('data-sizes') || '[]');
    var source = {};
    var order = [];
    $$('.card', tpl.content).forEach(function (c) {
      var s = c.getAttribute('data-slug');
      source[s] = c;
      order.push(s);
    });
    var pick = function (k) {
      if (!k) return featured.filter(function (s) { return source[s]; });
      return order.filter(function (s) {
        return (' ' + source[s].getAttribute('data-cats') + ' ').indexOf(' ' + k + ' ') > -1;
      }).slice(0, 6);
    };
    var token = 0;
    var swap = function (k) {
      var my = ++token;
      var list = pick(k);
      var build = function () {
        if (my !== token) return;
        var frag = d.createDocumentFragment();
        var nodes = list.map(function (slug, i) {
          var c = source[slug].cloneNode(true);
          c.className = 'card slot slot-' + (i + 1);
          var im = $('img', c);
          if (im) {
            if (sizes[i]) im.setAttribute('sizes', sizes[i]);
            im.setAttribute('loading', 'eager');
          }
          frag.appendChild(c);
          return c;
        });
        while (grid.firstChild) grid.removeChild(grid.firstChild);
        grid.appendChild(frag);
        grid.classList.remove('is-leaving');
        animateIn(grid, nodes);
      };
      if (reduced()) { build(); return; }
      grid.classList.add('is-leaving');
      w.setTimeout(build, 200);
    };
    initTabs(tabs, function (k) { swap(k); });
  }

  function initListFilter() {
    var tabs = $('[data-tabs="list"]');
    var grid = $('[data-grid="list"]');
    if (!tabs || !grid) return;
    var sizes = JSON.parse(grid.getAttribute('data-sizes') || '{}');
    var cards = $$('.card', grid);
    var cls = ['c-a1', 'c-a2', 'c-b1', 'c-b2', 'c-c', 's-c', 'c-s', 'is-alt'];
    var apply = function (k) {
      var vis = cards.filter(function (c) {
        return !k || (' ' + c.getAttribute('data-cats') + ' ').indexOf(' ' + k + ' ') > -1;
      });
      var rest = vis.filter(function (c) { return !c.hasAttribute('data-feat'); });
      var plan = listPlan(rest.length);
      cards.forEach(function (c) { c.hidden = vis.indexOf(c) < 0; });
      rest.forEach(function (c, i) {
        cls.forEach(function (x) { c.classList.remove(x); });
        c.classList.add(plan[i]);
        var im = $('img', c);
        if (im && sizes[plan[i]]) im.setAttribute('sizes', sizes[plan[i]]);
      });
      vis.forEach(function (c, i) { c.classList.toggle('is-alt', i % 2 === 1); });
      return vis;
    };
    var token = 0;
    var sync = function (k) {
      try {
        var u = new URL(location.href);
        if (k) u.searchParams.set('k', k);
        else u.searchParams.delete('k');
        history.replaceState(history.state, '', u.pathname + u.search + u.hash);
      } catch (e) { /* URL API missing: state stays in memory */ }
    };
    var ctl = initTabs(tabs, function (k, fromUser) {
      if (!fromUser) { apply(k); return; }
      sync(k);
      var my = ++token;
      if (reduced()) { apply(k); return; }
      grid.classList.add('is-leaving');
      w.setTimeout(function () {
        if (my !== token) return;
        var vis = apply(k);
        grid.classList.remove('is-leaving');
        animateIn(grid, vis);
      }, 200);
    });
    var k0 = null;
    try { k0 = new URLSearchParams(location.search).get('k'); } catch (e) { k0 = null; }
    if (k0 && !ctl.selectKey(k0, false)) sync('');
  }

  /* ---------------------------------------------------------------- materials */
  function initMaterials() {
    var root = $('[data-mat]');
    var dataEl = $('#mat-data');
    if (!root || !dataEl) return;
    var data;
    try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
    var a = $('[data-plate-a]', root);
    var b = $('[data-plate-b]', root);
    var nameEl = $('[data-plate-name]', root);
    var codeEl = $('[data-plate-code]', root);
    var link = $('[data-plate-link]', root);
    var groups = $('.mat__groups', root);
    var btns = $$('.sw', root);
    if (!a || !b || !btns.length) return;
    var selected = (btns.filter(function (x) { return x.getAttribute('aria-pressed') === 'true'; })[0] || btns[0]).getAttribute('data-sw');
    var shown = selected;
    var front = a;
    var back = b;
    var token = 0;
    var sizes = a.getAttribute('sizes');
    b.setAttribute('aria-hidden', 'true');

    var preload = function (id) {
      var it = data[id];
      if (!it) return null;
      if (!it._pre) {
        var im = new Image();
        im.decoding = 'async';
        im.sizes = sizes;
        im.srcset = it.srcset;
        im.src = it.src;
        it._pre = im;
      }
      return it._pre;
    };
    var caption = function (it) {
      nameEl.textContent = it.name;
      codeEl.textContent = it.code;
      link.setAttribute('href', it.href);
      link.textContent = it.ptitle;
    };
    var show = function (id) {
      var it = data[id];
      if (!it || id === shown) return;
      shown = id;
      var my = ++token;
      var next = back;
      next.setAttribute('sizes', sizes);
      next.style.setProperty('--fx', it.fx + '%');
      next.style.setProperty('--fy', it.fy + '%');
      next.style.backgroundColor = it.bg;
      next.setAttribute('srcset', it.srcset);
      next.setAttribute('src', it.src);
      next.setAttribute('alt', it.alt);
      next.removeAttribute('loading');
      var swap = function () {
        if (my !== token) return;
        next.classList.add('is-on');
        next.removeAttribute('aria-hidden');
        front.classList.remove('is-on');
        front.setAttribute('aria-hidden', 'true');
        back = front;
        front = next;
        caption(it);
      };
      whenReady(preload(id), swap, 1200);
    };
    btns.forEach(function (btn) {
      var id = btn.getAttribute('data-sw');
      btn.addEventListener('click', function () {
        selected = id;
        btns.forEach(function (x) { x.setAttribute('aria-pressed', x === btn ? 'true' : 'false'); });
        show(id);
      });
      btn.addEventListener('pointerenter', function (e) {
        if (e.pointerType !== 'mouse' || !mqFine.matches) return;
        preload(id);
        show(id);
      });
      btn.addEventListener('focus', function () { preload(id); });
    });
    if (groups) {
      groups.addEventListener('pointerleave', function (e) {
        if (e.pointerType !== 'mouse') return;
        show(selected);
      });
    }
    /* warm the cache once the section is near */
    if (hasIO) {
      var io = new IntersectionObserver(function (es) {
        if (!es[es.length - 1].isIntersecting) return;
        io.disconnect();
        if (mqFine.matches) Object.keys(data).forEach(preload);
      }, { rootMargin: '300px 0px' });
      io.observe(root);
    }
  }

  /* ---------------------------------------------------------------- video */
  function initVideos() {
    var boxes = $$('[data-vid]');
    if (!boxes.length) return;
    var ua = navigator.userAgent || '';
    var apple = /iP(hone|ad|od)/.test(ua) ||
      (/Safari\//.test(ua) && !/Chrome|Chromium|CriOS|FxiOS|Edg|OPR|SamsungBrowser/.test(ua)) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    var guard = !!navigator.webdriver || w.self !== w.top || qa;
    var autoOk = function () { return !guard && !mqReduce.matches; };

    boxes.forEach(function (box) {
      var v = $('video', box);
      var btn = $('[data-vid-btn]', box);
      if (!v || !btn) return;
      v.muted = true;
      v.defaultMuted = true;
      v.playsInline = true;
      var loaded = false;
      var userPaused = false;
      var inView = false;

      var load = function () {
        if (loaded) return;
        loaded = true;
        var mp4 = box.getAttribute('data-mp4');
        var webm = box.getAttribute('data-webm');
        var order = apple ? [[mp4, 'video/mp4'], [webm, 'video/webm']] : [[webm, 'video/webm'], [mp4, 'video/mp4']];
        order.forEach(function (pair) {
          if (!pair[0]) return;
          var s = d.createElement('source');
          s.src = pair[0];
          s.type = pair[1];
          v.appendChild(s);
        });
        v.preload = 'auto';
        v.load();
      };
      var state = function (playing) {
        box.classList.toggle('is-playing', playing);
        btn.setAttribute('aria-pressed', playing ? 'true' : 'false');
        btn.setAttribute('aria-label', playing ? 'Sustabdyti vaizdo įrašą' : 'Paleisti vaizdo įrašą');
      };
      var play = function () {
        load();
        var p = v.play();
        if (p && p.catch) p.catch(function () { state(false); });
      };
      v.addEventListener('playing', function () { state(true); });
      v.addEventListener('pause', function () { state(false); });
      v.addEventListener('ended', function () { state(false); });
      btn.addEventListener('click', function () {
        if (v.paused) {
          userPaused = false;
          play();
        } else {
          userPaused = true;
          v.pause();
        }
      });
      box._sync = function () {
        if (inView && autoOk() && !userPaused && v.paused) play();
      };
      if (hasIO) {
        new IntersectionObserver(function (es) {
          var e = es[es.length - 1];
          inView = e.isIntersecting && e.intersectionRatio >= 0.4;
          if (inView) box._sync();
          else if (!v.paused) v.pause();
        }, { threshold: [0, 0.4, 0.6] }).observe(box);
      }
    });
  }

  /* ---------------------------------------------------------------- lightbox */
  function initLightbox() {
    var dlg = $('[data-lb-dialog]');
    var dataEl = $('#lb-data');
    if (!dlg || !dataEl || typeof dlg.showModal !== 'function') return;
    var groups;
    try { groups = JSON.parse(dataEl.textContent); } catch (e) { return; }
    var img = $('[data-lb-img]', dlg);
    var cap = $('[data-lb-cap]', dlg);
    var count = $('[data-lb-count]', dlg);
    var stage = $('[data-lb-stage]', dlg);
    var closeBtn = $('[data-lb-close]', dlg);
    var list = [];
    var idx = 0;
    var trigger = null;
    var token = 0;
    var closing = null;

    var setImg = function (it) {
      img.setAttribute('sizes', '100vw');
      img.setAttribute('srcset', it.srcset);
      img.setAttribute('src', it.src);
      img.setAttribute('width', it.w);
      img.setAttribute('height', it.h);
      img.setAttribute('alt', it.alt || '');
    };
    var meta = function () {
      var it = list[idx];
      cap.textContent = it.alt || '';
      count.textContent = (idx + 1) + ' / ' + list.length;
    };
    var warm = function (i) {
      var it = list[(i + list.length) % list.length];
      if (!it || it._pre) return;
      var im = new Image();
      im.decoding = 'async';
      im.sizes = '100vw';
      im.srcset = it.srcset;
      im.src = it.src;
      it._pre = im;
    };
    var go = function (i) {
      if (list.length < 2) return;
      idx = (i + list.length) % list.length;
      var it = list[idx];
      var my = ++token;
      meta();
      img.classList.add('is-swap');
      var pre = it._pre || new Image();
      if (!it._pre) {
        pre.decoding = 'async';
        pre.sizes = '100vw';
        pre.srcset = it.srcset;
        pre.src = it.src;
        it._pre = pre;
      }
      var started = Date.now();
      whenReady(pre, function () {
        if (my !== token) return;
        w.setTimeout(function () {
          if (my !== token) return;
          setImg(it);
          img.classList.remove('is-swap');
        }, reduced() ? 0 : Math.max(0, 140 - (Date.now() - started)));
      }, 1800);
      warm(idx + 1);
      warm(idx - 1);
    };
    var finish = function () {
      if (closing) { w.clearTimeout(closing); closing = null; }
      if (dlg.open) dlg.close();
      de.classList.remove('is-locked');
      if (trigger && trigger.focus) trigger.focus({ preventScroll: true });
    };
    var close = function () {
      if (!dlg.open) return;
      dlg.classList.remove('is-open');
      if (reduced()) { finish(); return; }
      closing = w.setTimeout(finish, 460);
    };
    var openAt = function (group, i, from) {
      if (closing) finish();
      list = group;
      idx = Math.min(Math.max(i, 0), list.length - 1);
      trigger = from;
      token++;
      img.classList.remove('is-swap');
      setImg(list[idx]);
      meta();
      dlg.classList.toggle('is-single', list.length < 2);
      $$('.lb__btn', dlg).forEach(function (bn) { bn.hidden = list.length < 2; });
      dlg.showModal();
      de.classList.add('is-locked');
      void dlg.offsetWidth;
      dlg.classList.add('is-open');
      if (closeBtn) closeBtn.focus({ preventScroll: true });
      warm(idx + 1);
      warm(idx - 1);
    };

    d.addEventListener('click', function (e) {
      var t = e.target.closest ? e.target.closest('.lb-trig') : null;
      if (!t) return;
      var g = groups[t.getAttribute('data-lb')];
      if (!g || !g.length) return;
      e.preventDefault();
      openAt(g, parseInt(t.getAttribute('data-i'), 10) || 0, t);
    });
    $('[data-lb-prev]', dlg).addEventListener('click', function () { go(idx - 1); });
    $('[data-lb-next]', dlg).addEventListener('click', function () { go(idx + 1); });
    if (closeBtn) closeBtn.addEventListener('click', close);
    dlg.addEventListener('cancel', function (e) { e.preventDefault(); close(); });
    dlg.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); go(idx + 1); }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); go(idx - 1); }
    });

    /* swipe / drag */
    var x0 = null;
    var y0 = 0;
    var t0 = 0;
    var dx = 0;
    var moved = false;
    var pid = null;
    stage.addEventListener('pointerdown', function (e) {
      if (e.pointerType === 'mouse' && e.button !== 0) return;
      x0 = e.clientX;
      y0 = e.clientY;
      t0 = w.performance ? performance.now() : Date.now();
      dx = 0;
      moved = false;
      pid = e.pointerId;
    });
    stage.addEventListener('pointermove', function (e) {
      if (x0 === null || e.pointerId !== pid) return;
      dx = e.clientX - x0;
      if (!moved && Math.abs(dx) > 6 && Math.abs(dx) > Math.abs(e.clientY - y0)) {
        moved = true;
        img.classList.add('is-drag');
        try { stage.setPointerCapture(pid); } catch (err) { /* ignore */ }
      }
      if (moved && list.length > 1) img.style.transform = 'translate3d(' + dx + 'px,0,0)';
    });
    var end = function (e) {
      if (x0 === null || (e && e.pointerId !== pid)) return;
      var dt = (w.performance ? performance.now() : Date.now()) - t0;
      var velocity = Math.abs(dx) / Math.max(dt, 1);
      img.classList.remove('is-drag');
      img.style.transform = '';
      if (moved && list.length > 1 && (Math.abs(dx) > 64 || (velocity > 0.45 && Math.abs(dx) > 18))) {
        go(idx + (dx < 0 ? 1 : -1));
      } else if (!moved && e && e.type === 'pointerup' && e.target === stage) {
        close(); /* tap on the dark area closes */
      }
      x0 = null;
      pid = null;
    };
    stage.addEventListener('pointerup', end);
    stage.addEventListener('pointercancel', end);
  }

  /* ---------------------------------------------------------------- accordion */
  function initAccordion() {
    $$('.acc__btn').forEach(function (btn) {
      var acc = btn.closest('.acc');
      btn.addEventListener('click', function () {
        var open = btn.getAttribute('aria-expanded') !== 'true';
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
        acc.classList.toggle('is-open', open);
      });
    });
  }

  /* ---------------------------------------------------------------- form */
  function initForms() {
    $$('[data-form]').forEach(function (form) {
      var next = $('[data-next]', form);
      if (next) next.value = location.origin + '/aciu/';
      var submit = $('[data-submit]', form);
      var label = $('[data-submit-label]', form);
      var labelText = label ? label.textContent : '';
      var fileInput = $('input[type="file"]', form);
      var fileField = $('[data-files-field]', form);
      var list = $('[data-files]', form);
      var drop = $('[data-drop]', form);
      var MAX_FILES = 6;
      var MAX_BYTES = 10 * 1024 * 1024;
      var canRebuild = typeof DataTransfer === 'function';
      var store = [];

      var setErr = function (field, msg, input) {
        if (!field) return;
        var p = $('.field__err', field);
        if (p) p.textContent = msg || '';
        field.classList.toggle('is-invalid', !!msg);
        if (input) {
          if (msg) input.setAttribute('aria-invalid', 'true');
          else input.removeAttribute('aria-invalid');
        }
      };
      var check = function (input) {
        var v = (input.value || '').trim();
        var msg = '';
        if (input.required && !v) {
          msg = input.getAttribute('data-msg') || 'Užpildykite šį lauką.';
        } else if (v && input.type === 'tel' && !/^\+?\d{8,12}$/.test(v.replace(/[\s()-]/g, ''))) {
          msg = input.getAttribute('data-msg-bad') || 'Patikrinkite numerį.';
        } else if (v && input.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) {
          msg = input.getAttribute('data-msg-bad') || 'Patikrinkite adresą.';
        }
        setErr(input.closest('[data-field]'), msg, input);
        return !msg;
      };
      var inputs = $$('input[required], input[type="email"], input[type="tel"]', form);
      inputs.forEach(function (inp) {
        inp.addEventListener('input', function () {
          inp.setAttribute('data-touched', '1');
          if (inp.closest('.is-invalid')) check(inp);
        });
        inp.addEventListener('blur', function () {
          if (inp.getAttribute('data-touched') || inp.value) check(inp);
        });
      });

      /* files */
      var total = function (arr) { return arr.reduce(function (s, f) { return s + f.size; }, 0); };
      var fmt = function (b) {
        if (b < 1024 * 1024) return Math.max(1, Math.round(b / 1024)) + ' KB';
        return (b / 1048576).toFixed(1).replace('.', ',') + ' MB';
      };
      var typeOk = function (f) {
        return /^image\//.test(f.type) || f.type === 'application/pdf' || /\.(pdf|jpe?g|png|heic|heif|webp)$/i.test(f.name);
      };
      var render = function () {
        if (!list) return;
        while (list.firstChild) list.removeChild(list.firstChild);
        store.forEach(function (f, i) {
          var li = d.createElement('li');
          li.className = 'file';
          var n = d.createElement('span');
          n.className = 'file__name';
          n.textContent = f.name;
          var s = d.createElement('span');
          s.className = 'file__size';
          s.textContent = fmt(f.size);
          li.appendChild(n);
          li.appendChild(s);
          if (canRebuild) {
            var rm = d.createElement('button');
            rm.type = 'button';
            rm.className = 'file__rm';
            rm.setAttribute('aria-label', 'Pašalinti failą ' + f.name);
            rm.addEventListener('click', function () {
              store.splice(i, 1);
              setErr(fileField, '');
              sync();
              if (fileInput) fileInput.focus();
            });
            li.appendChild(rm);
          }
          list.appendChild(li);
        });
      };
      var sync = function () {
        if (canRebuild && fileInput) {
          try {
            var dt = new DataTransfer();
            store.forEach(function (f) { dt.items.add(f); });
            fileInput.files = dt.files;
          } catch (e) { /* older engines keep the native list */ }
        }
        render();
      };
      var add = function (files) {
        var err = '';
        if (!canRebuild) store = [];
        files.forEach(function (f) {
          if (!typeOk(f)) { err = err || 'Tinka tik nuotraukos arba PDF failai.'; return; }
          var dup = store.some(function (x) { return x.name === f.name && x.size === f.size; });
          if (dup) return;
          if (store.length >= MAX_FILES) { err = err || 'Galima pridėti iki 6 failų.'; return; }
          if (total(store) + f.size > MAX_BYTES) { err = err || 'Visi failai kartu negali viršyti 10 MB.'; return; }
          store.push(f);
        });
        setErr(fileField, err, fileInput);
        sync();
      };
      if (fileInput) {
        fileInput.addEventListener('change', function () {
          add(Array.prototype.slice.call(fileInput.files || []));
        });
      }
      if (drop) {
        ['dragenter', 'dragover'].forEach(function (t) {
          drop.addEventListener(t, function (e) {
            e.preventDefault();
            drop.classList.add('is-over');
          });
        });
        ['dragleave', 'dragend'].forEach(function (t) {
          drop.addEventListener(t, function (e) {
            if (!e.relatedTarget || !drop.contains(e.relatedTarget)) drop.classList.remove('is-over');
          });
        });
        drop.addEventListener('drop', function (e) {
          e.preventDefault();
          drop.classList.remove('is-over');
          var fl = e.dataTransfer && e.dataTransfer.files;
          if (fl && fl.length) add(Array.prototype.slice.call(fl));
        });
      }

      var busy = function (on) {
        if (!submit) return;
        submit.disabled = on;
        if (on) submit.setAttribute('aria-busy', 'true');
        else submit.removeAttribute('aria-busy');
        if (label) label.textContent = on ? 'Siunčiama…' : labelText;
      };
      form.addEventListener('submit', function (e) {
        var bad = inputs.filter(function (inp) { return !check(inp); });
        if (store.length > MAX_FILES || total(store) > MAX_BYTES) {
          setErr(fileField, 'Sumažinkite failų kiekį arba dydį.', fileInput);
          bad.push(fileInput);
        }
        if (bad.length) {
          e.preventDefault();
          bad[0].focus();
          return;
        }
        if (qa || w.__pikioNoSubmit) {
          e.preventDefault();
          busy(true);
          if (w.console) console.info('[pikio] submit intercepted (test mode)');
          w.setTimeout(function () { busy(false); }, 1500);
          return;
        }
        busy(true);
      });
      w.addEventListener('pageshow', function () { busy(false); });
    });
  }

  /* ---------------------------------------------------------------- boot */
  var boot = function () {
    var steps = [initHero, initReveal, initNav, initMenu, initCallbar, initParallax, initHomeFilter,
      initListFilter, initMaterials, initVideos, initLightbox, initAccordion, initForms];
    steps.forEach(function (fn) {
      try { fn(); } catch (err) {
        if (w.console) console.error('[pikio] ' + (fn.name || 'init') + ' failed', err);
        if (fn === initReveal || fn === initHero) {
          $$('.rv, .rv-line, [data-hero]').forEach(function (el) { el.classList.add('is-in'); });
        }
      }
    });
  };
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
