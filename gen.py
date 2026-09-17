#!/usr/bin/env python3
"""Pikio baldai: static site generator (Python 3 stdlib only).

Reads assets/data/site.json, projects.json and media.json and writes every page,
sitemap.xml and robots.txt. Fails loudly if a media ref is missing from media.json.

Testing only: PIKIO_MEDIA=<media.json path>, PIKIO_OUT=<output dir>, PIKIO_MEDIA_ROOT=<dir the media paths resolve in>.
"""
import datetime
import hashlib
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'assets', 'data')
OUT = os.path.abspath(os.environ.get('PIKIO_OUT') or ROOT)
MEDIA_FILE = os.path.abspath(os.environ.get('PIKIO_MEDIA') or os.path.join(DATA, 'media.json'))
MEDIA_ROOT = os.path.abspath(os.environ.get('PIKIO_MEDIA_ROOT') or ROOT)
DOMAIN = 'https://pikiobaldai.lt'
TODAY = datetime.date.today().isoformat()
YEAR = datetime.date.today().year


def load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def fail(title, items):
    print('\nFAIL: ' + title, file=sys.stderr)
    for it in items:
        print('  - ' + str(it), file=sys.stderr)
    sys.exit(1)


SITE = load(os.path.join(DATA, 'site.json'))
PJ = load(os.path.join(DATA, 'projects.json'))
if not os.path.exists(MEDIA_FILE):
    fail('media.json not found', [MEDIA_FILE])
MEDIA = load(MEDIA_FILE)

B = SITE['brand']
IMG = MEDIA.get('images', {})
UI = MEDIA.get('ui', {})
SW = MEDIA.get('swatches', {})
VID = MEDIA.get('videos', {})
LOGO = MEDIA.get('logo', {})
ICONS = MEDIA.get('icons', {})
REJ = {r['ref']: r.get('reason', '') for r in MEDIA.get('rejected', [])}

PROJECTS = PJ['projects']
PROJ = {p['slug']: p for p in PROJECTS}
CATS = PJ['categories']
CAT = {c['slug']: c['name'] for c in CATS}
FLAG = next(p for p in PROJECTS if p.get('flagship'))
WARN = []


def E(s):
    # a space before % must never break a line ("100 %")
    return html.escape(str(s), quote=True).replace(' %', '\u00a0%')


# ---------------------------------------------------------------- media validation
def project_photos(p):
    out = list(p.get('photos', []))
    for st in p.get('stages', []):
        out += st.get('photos', [])
    return out


def collect_refs():
    imgs, vids = [], []
    for p in PROJECTS:
        if p.get('cover'):
            imgs.append((p['cover'], p['slug'] + ' cover'))
        for ph in project_photos(p):
            imgs.append((ph['src'], p['slug']))
        for key in ('before_after', 'viz_pair'):
            for v in (p.get(key) or {}).values():
                imgs.append((v, p['slug'] + ' ' + key))
        if p.get('video'):
            vids.append((p['video'], p['slug']))
        for st in p.get('stages', []):
            v = (st.get('media') or {}).get('video')
            if v:
                vids.append((v, p['slug'] + ' stage'))
    for g in SITE['materials']['groups']:
        for it in g['items']:
            imgs.append((it['plate'], 'materials plate ' + it['id']))
    for st in SITE['process']['steps']:
        viz = st.get('viz')
        if viz:
            imgs.append((viz['render'], 'process viz'))
            imgs.append((viz['real'], 'process viz'))
    imgs.append((SITE['reviews']['press']['image'], 'reviews press'))
    return imgs, vids


def validate():
    missing = []
    imgs, vids = collect_refs()
    for ref, where in imgs:
        if ref in REJ:
            continue
        m = IMG.get(ref)
        if not m:
            missing.append('image %s (%s)' % (ref, where))
            continue
        for k in ('w', 'h', 'widths', 'path'):
            if k not in m:
                missing.append('image %s lacks "%s"' % (ref, k))
    for name, where in vids:
        v = VID.get(name)
        if not v:
            missing.append('video %s (%s)' % (name, where))
            continue
        for k in ('mp4', 'webm', 'poster', 'w', 'h'):
            if not v.get(k):
                missing.append('video %s lacks "%s"' % (name, k))
    for key in ('hero-d', 'hero-m', 'break'):
        if key not in UI:
            missing.append('ui.' + key)
    if not UI.get('og'):
        missing.append('ui.og')
    for g in SITE['materials']['groups']:
        for it in g['items']:
            if it['id'] not in SW:
                missing.append('swatches.' + it['id'])
    for k in ('dark', 'light', 'widths', 'ar'):
        if k not in LOGO:
            missing.append('logo.' + k)
    for k in ('ico', '48', '96', '144', '180', '192', '512'):
        if k not in ICONS:
            missing.append('icons.' + k)
    # every referenced file must exist on disk
    for label, path in iter_media_files(imgs, vids):
        fp = os.path.join(MEDIA_ROOT, path.lstrip('/').split('?')[0])
        if not os.path.exists(fp):
            missing.append('file not on disk: %s (%s)' % (path, label))
    if missing:
        fail('%d media refs missing from %s' % (len(missing), MEDIA_FILE), missing)
    for ref, why in REJ.items():
        WARN.append('rejected media skipped: %s (%s)' % (ref, why))


def iter_media_files(imgs, vids):
    seen = set()

    def widths_paths(m):
        return [m['path'].replace('{w}', str(w)) for w in m.get('widths', [])]

    for ref, where in imgs:
        if ref in REJ or ref not in IMG or ref in seen:
            continue
        seen.add(ref)
        for p in widths_paths(IMG[ref]):
            yield ref, p
    for key in ('hero-d', 'hero-m', 'break'):
        if key in UI:
            for p in widths_paths(UI[key]):
                yield 'ui.' + key, p
    if UI.get('og'):
        yield 'ui.og', UI['og']
    for sid, s in SW.items():
        for p in widths_paths(s):
            yield 'swatch ' + sid, p
    for name, _ in vids:
        v = VID.get(name) or {}
        for k in ('mp4', 'webm', 'poster'):
            if v.get(k):
                yield 'video ' + name, v[k]
    for k in ('dark', 'light'):
        if LOGO.get(k):
            for w in LOGO.get('widths', []):
                yield 'logo ' + k, LOGO[k].replace('{w}', str(w))
    for k, v in ICONS.items():
        yield 'icon ' + k, v


def ok(ref):
    return bool(ref) and ref in IMG and ref not in REJ


# ---------------------------------------------------------------- helpers
ARROW = ('<svg class="arr" viewBox="0 0 22 12" width="22" height="12" aria-hidden="true" focusable="false">'
         '<path d="M0 6h20.4M15.2.9 20.4 6l-5.2 5.1" fill="none" stroke="currentColor" stroke-width="1.25"/></svg>')
ARROW_L = ('<svg class="arr arr--l" viewBox="0 0 22 12" width="22" height="12" aria-hidden="true" focusable="false">'
           '<path d="M22 6H1.6M6.8.9 1.6 6l5.2 5.1" fill="none" stroke="currentColor" stroke-width="1.25"/></svg>')
PLAY = ('<svg class="ico-play" viewBox="0 0 12 14" width="10" height="12" aria-hidden="true" focusable="false">'
        '<path d="M1.2 1.3v11.4L10.8 7z" fill="none" stroke="currentColor" stroke-width="1.25" stroke-linejoin="round"/></svg>')
PAUSE = ('<svg class="ico-pause" viewBox="0 0 12 14" width="10" height="12" aria-hidden="true" focusable="false">'
         '<path d="M3.2 1.5v11M8.8 1.5v11" fill="none" stroke="currentColor" stroke-width="1.25"/></svg>')


def fill(path, w):
    return path.replace('{w}', str(w))


def srcset(m):
    return ', '.join('%s %sw' % (fill(m['path'], w), w) for w in sorted(m['widths']))


def src_at(m, target):
    ws = sorted(m['widths'])
    w = next((x for x in ws if x >= target), ws[-1])
    return fill(m['path'], w)


def largest(m):
    return fill(m['path'], max(m['widths']))


def sizes(desk, tab='92vw', mob='92vw'):
    """desk = number of the 12 columns an element spans on desktop."""
    vw = round(desk / 12 * 92, 1)
    px = round(desk / 12 * 1250)
    return '(min-width: 1024px) min(%svw, %spx), (min-width: 768px) %s, %s' % (vw, px, tab, mob)


PHOTO_INFO = {}
for _p in PROJECTS:
    for _ph in project_photos(_p):
        PHOTO_INFO.setdefault(_ph['src'], _ph)


def info(ref):
    return PHOTO_INFO.get(ref, {})


def img(ref, sz, cls='', alt=None, eager=False, fx=None, fy=None, style='', attrs='', m=None):
    m = m or IMG[ref]
    inf = info(ref) if ref else {}
    fx = inf.get('fx', 50) if fx is None else fx
    fy = inf.get('fy', 50) if fy is None else fy
    if alt is None:
        alt = inf.get('alt', '')
    st = '--fx:%s%%;--fy:%s%%;background-color:%s' % (fx, fy, m.get('bg', '#E2DAD0'))
    if style:
        st += ';' + style
    return ('<img class="%s" src="%s" srcset="%s" sizes="%s" width="%s" height="%s" alt="%s" '
            'loading="%s" decoding="async" style="%s"%s>' % (
                cls, src_at(m, 1000), srcset(m), sz, m['w'], m['h'], E(alt),
                'eager' if eager else 'lazy', st, attrs))


def ratio(ref):
    m = IMG[ref]
    return m['w'] / float(m['h'])


def lb_item(ref, alt=None):
    m = IMG[ref]
    return {'src': largest(m), 'srcset': srcset(m), 'w': m['w'], 'h': m['h'],
            'alt': alt if alt is not None else info(ref).get('alt', ''), 'bg': m.get('bg', '#2A2622')}


def ld(obj):
    return ('<script type="application/ld+json">%s</script>'
            % json.dumps(obj, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))


def first_sentence(text):
    m = re.match(r'(.+?[.!?])(\s|$)', text)
    return m.group(1) if m else text


def cover_of(p):
    photos = [ph for ph in project_photos(p) if ok(ph['src'])]
    ref = p.get('cover')
    if not ok(ref):
        pick = next((ph for ph in photos if ph.get('role') not in ('before', 'render')), None)
        if pick is None:
            return None
        if ref:
            WARN.append('%s: cover %s rejected, using %s' % (p['slug'], ref, pick['src']))
        ref = pick['src']
    inf = next((ph for ph in project_photos(p) if ph['src'] == ref), {})
    return {'ref': ref, 'fx': inf.get('fx', 50), 'fy': inf.get('fy', 50), 'alt': inf.get('alt') or p['title']}


def line_title(text):
    words = str(text).split()
    if len(words) < 2:
        return '<span class="nw">%s</span>' % E(text)
    return '%s <span class="nw">%s</span>' % (E(' '.join(words[:-1])), E(words[-1]))


def phone_link(cls='handle-link'):
    return '<a class="%s tnum" href="%s">%s</a>' % (cls, B['phone_href'], E(B['phone']))


def cat_counts():
    return {c['slug']: sum(1 for p in PROJECTS if c['slug'] in p['cats']) for c in CATS}


def vfile_hash():
    h = hashlib.md5()
    for rel in ('css/site.css', 'js/site.js'):
        with open(os.path.join(ROOT, rel), 'rb') as fh:
            h.update(fh.read())
    return h.hexdigest()[:8]


VER = vfile_hash()


def logo_img(kind, cls):
    path = LOGO[kind]
    ws = sorted(LOGO['widths'])
    ar = float(LOGO['ar'])
    ss = ', '.join('%s %sw' % (fill(path, w), w) for w in ws)
    if kind == 'dark':
        sz = '(min-width: 1024px) %dpx, %dpx' % (round(58 * ar), round(44 * ar))
    else:
        sz = '%dpx' % round(52 * ar)
    return ('<img class="%s" src="%s" srcset="%s" sizes="%s" width="%d" height="%d" alt="Pikio baldai" decoding="async">'
            % (cls, fill(path, ws[0]), ss, sz, round(100 * ar), 100))


# ---------------------------------------------------------------- shared partials
INLINE_JS = ("(function(d,w){var e=d.documentElement;e.classList.add('js');"
             "if(/[?&]qa=1(&|$)/.test(location.search)){e.classList.add('qa');return}"
             "try{if(!w.matchMedia('(prefers-reduced-motion: reduce)').matches&&'IntersectionObserver' in w){"
             "e.classList.add('js-anim');w.setTimeout(function(){if(!w.__pikio)e.classList.remove('js-anim')},4000)}}catch(x){}"
             "})(document,window);")


def head(title, desc, path, noindex=False, preload='', jsonld=()):
    canon = DOMAIN + path
    og = DOMAIN + UI['og']
    icons = ICONS
    out = ['<!doctype html>', '<html lang="lt">', '<head>',
           '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
           '<title>%s</title>' % E(title),
           '<meta name="description" content="%s">' % E(desc)]
    if noindex:
        out.append('<meta name="robots" content="noindex">')
    else:
        out.append('<link rel="canonical" href="%s">' % E(canon))
    out += ['<meta name="theme-color" content="#F5F2ED">',
            '<meta property="og:type" content="website">',
            '<meta property="og:locale" content="lt_LT">',
            '<meta property="og:site_name" content="Pikio baldai">',
            '<meta property="og:title" content="%s">' % E(title),
            '<meta property="og:description" content="%s">' % E(desc),
            '<meta property="og:url" content="%s">' % E(canon),
            '<meta property="og:image" content="%s">' % E(og),
            '<meta name="twitter:card" content="summary_large_image">',
            '<link rel="icon" href="%s" sizes="any">' % icons['ico'],
            '<link rel="icon" type="image/png" sizes="48x48" href="%s">' % icons['48'],
            '<link rel="icon" type="image/png" sizes="96x96" href="%s">' % icons['96'],
            '<link rel="icon" type="image/png" sizes="192x192" href="%s">' % icons['192'],
            '<link rel="apple-touch-icon" sizes="180x180" href="%s">' % icons['180'],
            '<link rel="manifest" href="/site.webmanifest">',
            '<link rel="preload" href="/fonts/josefin-sans-latin.woff2" as="font" type="font/woff2" crossorigin>']
    if preload:
        out.append(preload)
    out += ['<link rel="stylesheet" href="/css/site.css?v=%s">' % VER,
            '<script>%s</script>' % INLINE_JS,
            '<script src="/js/site.js?v=%s" defer></script>' % VER]
    out += [ld(j) for j in jsonld]
    out += ['</head>']
    return '\n'.join(out)


def nav_href(href, page):
    if page == 'home' and href.startswith('/#'):
        return href[1:]
    return href


def current_attr(href, page):
    if page == 'projects' and href == '/projektai/':
        return ' aria-current="page"'
    if page == 'project' and href == '/projektai/':
        return ' aria-current="true"'
    if page == 'contacts' and href == '/kontaktai/':
        return ' aria-current="page"'
    return ''


def request_href(page):
    return '#uzklausa' if page in ('home', 'contacts') else '/kontaktai/'


def nav(page):
    links = ''.join('<li><a class="t-label nav__link" href="%s"%s>%s</a></li>'
                    % (nav_href(n['href'], page), current_attr(n['href'], page), E(n['label']))
                    for n in SITE['nav'])
    mlinks = ''.join('<li><a class="t-h3 menu__link" href="%s"%s>%s</a></li>'
                     % (nav_href(n['href'], page), current_attr(n['href'], page), E(n['label']))
                     for n in SITE['nav'])
    over = ' data-over' if page == 'home' else ''
    return '''<a class="skip" href="#main">Pereiti prie turinio</a>
<header class="nav" data-nav%(over)s>
  <div class="wrap nav__in">
    <a class="nav__logo" href="/" aria-label="Pikio baldai, pradžia">%(logo)s</a>
    <nav class="nav__links" aria-label="Pagrindinė navigacija"><ul role="list">%(links)s</ul></nav>
    <div class="nav__end">
      %(tel)s
      <a class="btn btn--line btn--sm nav__cta" href="%(req)s"><span class="btn__t">Užklausa</span></a>
      <button class="nav__menu t-label" type="button" aria-haspopup="dialog" aria-expanded="false" aria-controls="menu" data-menu-open>Meniu</button>
    </div>
  </div>
</header>
<dialog class="menu" id="menu" aria-label="Meniu" data-menu>
  <div class="menu__in">
    <div class="wrap menu__top">
      <a class="nav__logo" href="/" aria-label="Pikio baldai, pradžia" tabindex="-1">%(logo2)s</a>
      <button class="menu__close t-label" type="button" data-menu-close>Uždaryti</button>
    </div>
    <div class="wrap menu__body">
      <nav aria-label="Meniu nuorodos"><ul class="menu__list" role="list">%(mlinks)s</ul></nav>
      <div class="menu__actions">
        <a class="btn" href="%(tel_href)s"><span class="btn__t tnum">%(phone)s</span>%(arrow)s</a>
        <a class="btn btn--line" href="%(req)s"><span class="btn__t">Užklausa</span></a>
      </div>
      <p class="menu__social"><a class="handle-link" href="%(fb)s" target="_blank" rel="noopener">Facebook</a><a class="handle-link" href="%(ig)s" target="_blank" rel="noopener">Instagram</a></p>
    </div>
  </div>
</dialog>''' % {
        'over': over, 'logo': logo_img('dark', 'nav__img'), 'logo2': logo_img('dark', 'nav__img'),
        'links': links, 'mlinks': mlinks,
        'tel': '<a class="nav__tel tnum" href="%s">%s</a>' % (B['phone_href'], E(B['phone'])),
        'req': request_href(page), 'tel_href': B['phone_href'], 'phone': E(B['phone']), 'arrow': ARROW,
        'fb': B['facebook'], 'ig': B['instagram']}


def callbar(page):
    return ('<div class="callbar" data-callbar>'
            '<a class="callbar__a t-label" href="%s">Skambinti</a>'
            '<a class="callbar__a t-label" href="%s">Užklausa</a></div>' % (B['phone_href'], request_href(page)))


def footer(page):
    links = ''.join('<li><a class="t-label foot__link" href="%s">%s</a></li>'
                    % (nav_href(n['href'], page), E(n['label'])) for n in SITE['nav'])
    legal = ('© %d %s · Įmonės kodas %s · Registracijos adresas: Taikos g. 4, Stakliškių k., Prienų r. · '
             'Veiklos vieta: %s' % (YEAR, E(B['legal']), E(B['code']), E(B['base'])))
    return '''<footer class="foot">
  <div class="wrap">
    <div class="foot__top">
      <a class="foot__logo" href="/" aria-label="Pikio baldai, pradžia">%(logo)s</a>
      <nav class="foot__nav" aria-label="Poraštės navigacija"><ul role="list">%(links)s</ul></nav>
      <div class="foot__col">
        <a class="foot__a tnum" href="%(tel_href)s">%(phone)s</a>
        <a class="foot__a" href="mailto:%(email)s">%(email)s</a>
      </div>
      <div class="foot__col">
        <a class="foot__a" href="%(fb)s" target="_blank" rel="noopener">Facebook</a>
        <a class="foot__a" href="%(ig)s" target="_blank" rel="noopener">Instagram</a>
      </div>
    </div>
    <p class="foot__legal t-small">%(legal)s</p>
  </div>
</footer>''' % {'logo': logo_img('light', 'foot__img'), 'links': links, 'tel_href': B['phone_href'],
                'phone': E(B['phone']), 'email': E(B['email']), 'fb': B['facebook'], 'ig': B['instagram'],
                'legal': legal}


def lightbox():
    return '''<dialog class="lb" aria-label="Nuotraukų peržiūra" data-lb-dialog>
  <div class="lb__stage" data-lb-stage><img class="lb__img" alt="" decoding="async" data-lb-img></div>
  <div class="lb__bar">
    <p class="lb__cap t-small" data-lb-cap></p>
    <p class="lb__count t-label" aria-live="polite" data-lb-count></p>
  </div>
  <button class="lb__btn lb__btn--prev" type="button" aria-label="Ankstesnė nuotrauka" data-lb-prev>%s</button>
  <button class="lb__btn lb__btn--next" type="button" aria-label="Kita nuotrauka" data-lb-next>%s</button>
  <button class="lb__close t-label" type="button" data-lb-close>Uždaryti</button>
</dialog>''' % (ARROW_L, ARROW)


def lb_data(groups):
    return ('<script type="application/json" id="lb-data">%s</script>'
            % json.dumps(groups, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'))


def page(title, desc, path, page_id, body, noindex=False, preload='', jsonld=(), lb=None):
    parts = [head(title, desc, path, noindex=noindex, preload=preload, jsonld=jsonld),
             '<body class="pg-%s">' % page_id, nav(page_id),
             '<main id="main" tabindex="-1">', body, '</main>', footer(page_id), callbar(page_id)]
    if lb:
        parts += [lightbox(), lb_data(lb)]
    parts += ['</body>', '</html>', '']
    return '\n'.join(parts)


def video_block(name, label, cls='', vt=''):
    v = VID[name]
    style = ' style="%s"' % vt if vt else ''
    return ('<div class="vid %s" data-vid data-mp4="%s" data-webm="%s"%s>'
            '<video muted playsinline loop preload="none" poster="%s" width="%s" height="%s" aria-label="%s"></video>'
            '<button class="vid__btn" type="button" aria-label="Paleisti vaizdo įrašą" aria-pressed="false" data-vid-btn>%s%s</button>'
            '</div>' % (cls, v['mp4'], v['webm'], style, v['poster'], v['w'], v['h'], E(label), PLAY, PAUSE))


# ---------------------------------------------------------------- cards
def card(p, cls='', sz='', heading='h3', eager=False, extra_attrs=''):
    cv = cover_of(p)
    if not cv:
        WARN.append('%s: no usable photo, card skipped' % p['slug'])
        return ''
    cats = ' · '.join(CAT[c] for c in p['cats'])
    vid = ('<span class="card__vid t-label">%sVideo</span>' % PLAY) if p.get('video') else ''
    image = img(cv['ref'], sz or sizes(6), cls='card__img', alt=cv['alt'], eager=eager, fx=cv['fx'], fy=cv['fy'],
                style='view-transition-name:p-%s' % p['slug'])
    return ('<a class="card %s" href="/projektai/%s/" data-slug="%s" data-cats="%s"%s>'
            '<figure class="card__fig">%s</figure>'
            '<div class="card__cap"><div class="card__txt">'
            '<%s class="t-title card__title"><span class="card__line">%s</span></%s>'
            '<p class="t-small card__meta">%s</p><p class="card__cats">%s</p></div>%s</div></a>'
            % (cls, p['slug'], p['slug'], ' '.join(p['cats']), extra_attrs, image,
               heading, line_title(p['title']), heading, E(p['card_meta']), E(cats), vid))


def tabs(mode, total):
    counts = cat_counts()
    btns = ['<button class="tab t-label" type="button" aria-pressed="true" data-k=""><span class="tab__t">Visi</span><span class="tab__n">%d</span></button>' % total]
    for c in CATS:
        btns.append('<button class="tab t-label" type="button" aria-pressed="false" data-k="%s"><span class="tab__t">%s</span><span class="tab__n">%d</span></button>'
                    % (c['slug'], E(c['name']), counts[c['slug']]))
    return ('<div class="tabs" data-tabs="%s"><div class="tabs__row" role="group" aria-label="Rodyti projektus pagal erdvę">%s'
            '<span class="tabs__ind" aria-hidden="true"></span></div></div>' % (mode, ''.join(btns)))


HOME_SLOTS = [7, 4, 4, 6, 4, 6]
HOME_SIZES = [sizes(n, tab='46vw') for n in HOME_SLOTS]


# ---------------------------------------------------------------- home sections
def s_hero():
    h = SITE['hero']
    hd, hm = UI['hero-d'], UI['hero-m']
    alt = cover_of(PROJ['namu-biblioteka'])['alt'] if 'namu-biblioteka' in PROJ else h['caption']
    return '''<section class="hero" aria-labelledby="hero-title" data-hero>
  <div class="hero__media">
    <div class="hero__par" data-parallax="hero">
      <picture>
        <source media="(max-width: 767.98px)" srcset="%(ms)s" sizes="100vw" width="%(mw)s" height="%(mh)s">
        <img class="hero__img" src="%(dsrc)s" srcset="%(ds)s" sizes="100vw" width="%(dw)s" height="%(dh)s" alt="%(alt)s" fetchpriority="high" decoding="async" style="background-color:%(bg)s">
      </picture>
    </div>
    <a class="hero__cap handle-link handle-link--light" href="%(caph)s">%(cap)s</a>
  </div>
  <div class="hero__panel">
    <h1 id="hero-title" class="t-hero">%(h1)s</h1>
    <p class="t-lead hero__lead">%(lead)s</p>
    <div class="hero__actions">
      <a class="btn" href="#uzklausa"><span class="btn__t">%(cta)s</span>%(arrow)s</a>
      %(tel)s
    </div>
    <a class="hero__proof" href="#atsiliepimai"><span class="hero__fig tnum">%(fig)s</span><span class="t-small hero__ptxt">%(ptxt)s</span></a>
  </div>
</section>''' % {
        'ms': srcset(hm), 'mw': hm['w'], 'mh': hm['h'], 'dsrc': src_at(hd, 1600), 'ds': srcset(hd),
        'dw': hd['w'], 'dh': hd['h'], 'alt': E(alt), 'bg': hd.get('bg', '#E2DAD0'),
        'caph': h['caption_href'], 'cap': E(h['caption']), 'h1': E(h['h1']), 'lead': E(h['lead']),
        'cta': E(h['cta']), 'arrow': ARROW, 'tel': phone_link('handle-link hero__tel'),
        'fig': E(h['proof_figure']), 'ptxt': E(h['proof_text'])}


def hero_preload():
    hd, hm = UI['hero-d'], UI['hero-m']
    return ('<link rel="preload" as="image" imagesrcset="%s" imagesizes="100vw" media="(min-width: 768px)" fetchpriority="high">\n'
            '<link rel="preload" as="image" imagesrcset="%s" imagesizes="100vw" media="(max-width: 767.98px)" fetchpriority="high">'
            % (srcset(hd), srcset(hm)))


def s_work():
    w = SITE['work']
    feat = [PROJ[s] for s in PJ['home_featured'] if s in PROJ]
    cards = ''.join(card(p, cls='slot slot-%d' % (i + 1), sz=HOME_SIZES[i]) for i, p in enumerate(feat[:6]))
    tpl = ''.join(card(p, cls='slot', sz=HOME_SIZES[0]) for p in PROJECTS)
    return '''<section class="sec work" id="projektai" aria-labelledby="work-title">
  <div class="wrap">
    <div class="grid work__head">
      <h2 id="work-title" class="t-h2 work__h rv">%(h2)s</h2>
      <div class="work__aside rv" style="--rd:70ms">
        <p class="work__text">%(text)s</p>
        <a class="handle-link" href="/projektai/">%(all)s (%(n)d)</a>
      </div>
    </div>
    %(tabs)s
    <div class="work__grid" data-grid="home" data-featured='%(featured)s' data-sizes='%(sizes)s'>%(cards)s</div>
    <template id="tpl-cards">%(tpl)s</template>
  </div>
</section>''' % {
        'h2': E(w['h2']), 'text': E(w['text']), 'all': E(w['all_label']), 'n': len(PROJECTS),
        'tabs': tabs('home', len(PROJECTS)), 'cards': cards, 'tpl': tpl,
        'featured': E(json.dumps([p['slug'] for p in feat[:6]])), 'sizes': E(json.dumps(HOME_SIZES))}


def s_flag(lb):
    f = SITE['flagship']
    p = FLAG
    stages = p.get('stages', [])
    reel = p.get('video') if p.get('video') in VID else next(
        ((st.get('media') or {}).get('video') for st in stages if (st.get('media') or {}).get('video') in VID), None)
    frame = ('<div class="flag__frame">%s</div>' % video_block(reel, p['title'], cls='vid--fill')) if reel else ''
    rows = []
    for si, st in enumerate(stages):
        photos = [x for x in st.get('photos', []) if ok(x['src'])]
        thumbs = ''
        if photos:
            key = 'st%d' % si
            lb[key] = [lb_item(x['src'], x['alt']) for x in photos]
            thumbs = '<ul class="stage__thumbs rv" style="--rd:210ms" role="list">%s</ul>' % ''.join(
                '<li><button class="thumb lb-trig" type="button" data-lb="%s" data-i="%d" aria-label="Padidinti: %s">%s</button></li>'
                % (key, i, E(x['alt']), img(x['src'], '(min-width: 1024px) 150px, 30vw', cls='thumb__img', alt='',
                                           fx=x.get('fx'), fy=x.get('fy')))
                for i, x in enumerate(photos[:3]))
        rows.append('''<li class="stage">
          <p class="t-label stage__label rv">%s</p>
          <h3 class="t-h3 stage__title rv" style="--rd:70ms">%s</h3>
          <p class="stage__text rv" style="--rd:140ms">%s</p>
          %s
        </li>''' % (E(st['label']), E(st['title']), E(st['text']), thumbs))
    return '''<section class="sec flag" id="akademija" aria-labelledby="flag-title">
  <div class="wrap grid flag__grid">
    <div class="flag__media">%(frame)s</div>
    <div class="flag__body">
      <p class="t-small flag__meta rv">%(meta)s</p>
      <h2 id="flag-title" class="t-h2 flag__h rv" style="--rd:70ms">%(h2)s</h2>
      <p class="t-lead flag__lead rv" style="--rd:140ms">%(lead)s</p>
      <ol class="stages" role="list">%(rows)s</ol>
      <a class="handle-link handle-link--dark flag__link" href="/projektai/%(slug)s/">%(link)s</a>
    </div>
  </div>
</section>''' % {'frame': frame, 'meta': E(f['meta']), 'h2': E(f['h2']), 'lead': E(f['lead']),
                 'rows': ''.join(rows), 'slug': p['slug'], 'link': E(f['link'])}


def material_items():
    items = []
    for g in SITE['materials']['groups']:
        for it in g['items']:
            proj = PROJ.get(it['project'])
            ref = it['plate'] if ok(it['plate']) else None
            if not ref and ok(it.get('swatch')):
                ref = it['swatch']
            if not ref and proj:
                cv = cover_of(proj)
                ref = cv and cv['ref']
            if ref != it['plate']:
                WARN.append('materials %s: plate %s rejected, using %s' % (it['id'], it['plate'], ref))
            items.append((g, it, proj, ref))
    return items


def s_mat():
    m = SITE['materials']
    items = material_items()
    data = {}
    for g, it, proj, ref in items:
        im = IMG[ref]
        inf = info(ref)
        data[it['id']] = {'src': src_at(im, 1000), 'srcset': srcset(im), 'w': im['w'], 'h': im['h'],
                          'bg': im.get('bg', '#E2DAD0'), 'fx': inf.get('fx', 50), 'fy': inf.get('fy', 50),
                          'alt': inf.get('alt', it['name']), 'name': it['name'], 'code': it['code'],
                          'href': '/projektai/%s/' % it['project'], 'ptitle': proj['title'] if proj else ''}
    g0, it0, p0, ref0 = items[0]
    d0 = data[it0['id']]
    plate_sizes = '(min-width: 1024px) min(46vw, 640px), (min-width: 768px) 92vw, 1px'

    def sw_img(sid, sz):
        s = SW[sid]
        return ('<img class="sw__img" src="%s" srcset="%s" sizes="%s" width="%d" height="%d" alt="" loading="lazy" decoding="async"%s>'
                % (src_at(s, 240), srcset(s), sz, max(s['widths']), max(s['widths']),
                   (' style="background-color:%s"' % s['bg']) if s.get('bg') else ''))

    groups, cards = [], []
    for gi, g in enumerate(m['groups']):
        btns, mcards = [], []
        for (gg, it, proj, ref) in items:
            if gg is not g:
                continue
            first = it['id'] == it0['id']
            btns.append('<li><button class="sw" type="button" aria-pressed="%s" data-sw="%s">'
                        '<span class="sw__box">%s</span><span class="sw__name">%s</span><span class="sw__code">%s</span>'
                        '</button></li>' % ('true' if first else 'false', it['id'],
                                            sw_img(it['id'], '(min-width: 1024px) 120px, 72px'),
                                            E(it['name']), E(it['code'])))
            mcards.append('<li class="swc"><span class="sw__box">%s</span><span class="sw__name">%s</span>'
                          '<span class="sw__code">%s</span><a class="swc__link" href="/projektai/%s/">Projektas%s'
                          '<span class="sr-only">: %s</span></a></li>'
                          % (sw_img(it['id'], '44vw'), E(it['name']), E(it['code']), it['project'], ARROW,
                             E(proj['title'] if proj else '')))
        groups.append('<div class="mat__group" role="group" aria-labelledby="mg%d"><h3 class="t-label mat__gt" id="mg%d">%s</h3>'
                      '<ul class="sws" role="list">%s</ul></div>' % (gi, gi, E(g['title']), ''.join(btns)))
        cards.append('<div class="mat__mgroup"><h3 class="t-label mat__gt">%s</h3><ul class="swcs" role="list">%s</ul></div>'
                     % (E(g['title']), ''.join(mcards)))
    return '''<section class="sec mat" id="medziagos" aria-labelledby="mat-title">
  <div class="wrap">
    <div class="grid mat__head">
      <h2 id="mat-title" class="t-h2 mat__h rv">%(h2)s</h2>
      <p class="t-lead mat__text rv" style="--rd:70ms">%(text)s</p>
    </div>
    <div class="grid mat__body" data-mat>
      <figure class="mat__plate">
        <div class="mat__frame">
          <img class="mat__img is-on" src="%(src)s" srcset="%(srcset)s" sizes="%(psz)s" width="%(w)s" height="%(h)s" alt="%(alt)s" loading="lazy" decoding="async" style="--fx:%(fx)s%%;--fy:%(fy)s%%;background-color:%(bg)s" data-plate-a>
          <img class="mat__img" alt="" decoding="async" sizes="%(psz)s" data-plate-b>
        </div>
        <figcaption class="mat__cap">
          <span class="mat__name"><span data-plate-name>%(name)s</span> · <span class="mat__code" data-plate-code>%(code)s</span></span>
          <a class="handle-link" href="%(href)s" data-plate-link>%(ptitle)s</a>
        </figcaption>
      </figure>
      <div class="mat__groups">%(groups)s<p class="t-small mat__note">%(note)s</p></div>
      <div class="mat__cards">%(cards)s<p class="t-small mat__note">%(note)s</p></div>
    </div>
    <script type="application/json" id="mat-data">%(data)s</script>
  </div>
</section>''' % {'h2': E(m['h2']), 'text': E(m['text']), 'src': d0['src'], 'srcset': d0['srcset'],
                 'psz': plate_sizes, 'w': d0['w'], 'h': d0['h'], 'alt': E(d0['alt']), 'fx': d0['fx'], 'fy': d0['fy'],
                 'bg': d0['bg'], 'name': E(d0['name']), 'code': E(d0['code']), 'href': d0['href'],
                 'ptitle': E(d0['ptitle']), 'groups': ''.join(groups), 'cards': ''.join(cards), 'note': E(m['note']),
                 'data': json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')}


def diptych(left_ref, right_ref, left_label, right_label, sz, cls='', lb_key=None, lb_idx=None):
    def item(ref, label, i):
        pic = img(ref, sz, cls='dip__img')
        if lb_key is not None and lb_idx is not None and ref in lb_idx:
            pic = ('<button class="lb-trig dip__btn" type="button" data-lb="%s" data-i="%d" aria-label="Padidinti: %s">%s</button>'
                   % (lb_key, lb_idx[ref], E(info(ref).get('alt', label)), pic))
        return ('<figure class="dip__item"><div class="dip__fig">%s</div><figcaption class="t-label dip__label">%s</figcaption></figure>'
                % (pic, E(label)))
    return '<div class="dip %s">%s%s</div>' % (cls, item(left_ref, left_label, 0), item(right_ref, right_label, 1))


def s_proc():
    pr = SITE['process']
    steps = []
    for i, st in enumerate(pr['steps']):
        extra = ''
        viz = st.get('viz')
        if viz and ok(viz['render']) and ok(viz['real']):
            extra = ('<div class="step__viz">%s<a class="handle-link step__vizlink" href="%s">%s</a></div>'
                     % (diptych(viz['render'], viz['real'], 'Vizualizacija', 'Įgyvendinta',
                                '(min-width: 1024px) min(27vw, 360px), (min-width: 768px) 45vw, 44vw', cls='dip--sm'),
                        viz['href'], E(viz['caption'])))
        steps.append('<li class="step"><span class="rv-line"></span><h3 class="t-h3 step__title rv">%s</h3>'
                     '<p class="step__text rv" style="--rd:70ms">%s</p>%s</li>' % (E(st['title']), E(st['text']), extra))
    return '''<section class="sec proc" id="procesas" aria-labelledby="proc-title">
  <div class="wrap grid">
    <div class="proc__side">
      <div class="proc__sticky">
        <h2 id="proc-title" class="t-h2 rv">%(h2)s</h2>
        <p class="t-lead proc__lead rv" style="--rd:70ms">%(lead)s</p>
        <a class="btn btn--line rv" style="--rd:140ms" href="#uzklausa"><span class="btn__t">%(cta)s</span>%(arrow)s</a>
      </div>
    </div>
    <ol class="steps" role="list">%(steps)s</ol>
  </div>
</section>''' % {'h2': E(pr['h2']), 'lead': E(pr['lead']), 'cta': E(SITE['hero']['cta']), 'arrow': ARROW,
                 'steps': ''.join(steps)}


def s_break():
    b = SITE['break']
    m = UI['break']
    inf = info(b['src'])
    return '''<figure class="brk" aria-label="%(cap)s">
  <div class="brk__media">
    <div class="brk__par" data-parallax="brk">
      <img class="brk__img" src="%(src)s" srcset="%(ss)s" sizes="100vw" width="%(w)s" height="%(h)s" alt="%(alt)s" loading="lazy" decoding="async" style="--fx:%(fx)s%%;--fy:%(fy)s%%;background-color:%(bg)s">
    </div>
  </div>
  <figcaption class="wrap brk__cap"><a class="handle-link handle-link--light" href="%(href)s">%(cap)s</a></figcaption>
</figure>''' % {'src': src_at(m, 1600), 'ss': srcset(m), 'w': m['w'], 'h': m['h'], 'alt': E(b['alt']),
                'fx': inf.get('fx', 50), 'fy': inf.get('fy', 50), 'bg': m.get('bg', '#E2DAD0'),
                'href': b['href'], 'cap': E(b['caption'])}


def s_reviews():
    r = SITE['reviews']
    ret = r['returning']
    ret_slug = ret['href'].strip('/').split('/')[-1]
    ret_title = PROJ[ret_slug]['title'] if ret_slug in PROJ else ret['title']
    press = r['press']
    press_img = ''
    if ok(press['image']):
        press_img = '<div class="rev__pfig">%s</div>' % img(
            press['image'], '140px', cls='rev__pimg', alt='Žurnalas „Jumsinfo Statyba“')
    items = ''.join('<li class="rev__item rv" style="--rd:%dms"><blockquote class="rev__q"><p>%s</p></blockquote>'
                    '<p class="t-small rev__name">%s</p></li>' % ((i % 2) * 70, E(it['text']), E(it['name']))
                    for i, it in enumerate(r['items']))
    return '''<section class="sec rev" id="atsiliepimai" aria-labelledby="rev-title">
  <div class="wrap grid">
    <div class="rev__side">
      <h2 id="rev-title" class="sr-only">%(h2)s</h2>
      <p class="t-figure rev__fig tnum rv">%(fig)s</p>
      <p class="rev__flabel rv" style="--rd:70ms"><span class="rev__fl1">%(flabel)s</span><span class="t-small rev__fl2">%(count)s</span></p>
      <a class="handle-link rv" style="--rd:140ms" href="%(fbr)s" target="_blank" rel="noopener">%(all)s</a>
      <div class="rev__ret rv">
        <h3 class="rev__h3">%(rtitle)s</h3>
        <p class="t-small rev__rtext">%(rtext)s</p>
        <a class="handle-link" href="%(rhref)s">%(rlink)s</a>
      </div>
      <div class="rev__press rv">%(pimg)s<p class="t-small rev__ptext">%(ptext)s</p></div>
    </div>
    <div class="rev__main">
      <figure class="rev__feat rv">
        <blockquote class="t-h3 rev__fq"><p>„%(ftext)s“</p></blockquote>
        <figcaption class="t-small rev__name">%(fname)s</figcaption>
      </figure>
      <ul class="rev__list" role="list">%(items)s</ul>
    </div>
  </div>
</section>''' % {'h2': E(r['h2']), 'fig': E(r['figure']), 'flabel': E(r['figure_label']), 'count': E(r['count_label']),
                 'fbr': B['facebook_reviews'], 'all': E(r['all_label']), 'rtitle': E(ret['title']),
                 'rtext': E(ret['text']), 'rhref': ret['href'], 'rlink': E(ret_title), 'pimg': press_img,
                 'ptext': E(press['text']), 'ftext': E(r['featured']['text']), 'fname': E(r['featured']['name']),
                 'items': items}


def s_cities():
    c = SITE['cities']
    lis = ''.join('<li class="cities__city">%s</li>' % E(x) for x in B['cities'])
    return '''<section class="cities" aria-labelledby="cities-title">
  <div class="wrap">
    <div class="cities__row">
      <h2 id="cities-title" class="t-label cities__label">%s</h2>
      <ul class="cities__list" role="list">%s</ul>
    </div>
    <p class="t-small cities__note">%s</p>
  </div>
</section>''' % (E(c['label']), lis, E(c['note']))


def s_faq():
    f = SITE['faq']
    items = []
    for i, it in enumerate(f['items']):
        items.append('''<div class="acc">
          <h3 class="acc__h"><button class="acc__btn" type="button" id="faq-b%(i)d" aria-expanded="false" aria-controls="faq-p%(i)d"><span class="acc__q">%(q)s</span><span class="acc__icon" aria-hidden="true"></span></button></h3>
          <div class="acc__panel" id="faq-p%(i)d" role="region" aria-labelledby="faq-b%(i)d"><div class="acc__inner"><p>%(a)s</p></div></div>
        </div>''' % {'i': i, 'q': E(it['q']), 'a': E(it['a'])})
    return '''<section class="sec faq" id="duk" aria-labelledby="faq-title">
  <div class="wrap grid">
    <div class="faq__side">
      <h2 id="faq-title" class="t-h2 rv">%(h2)s</h2>
      <p class="faq__aside rv" style="--rd:70ms">%(aside)s</p>
      <p class="rv" style="--rd:140ms">%(tel)s</p>
    </div>
    <div class="faq__list" data-acc>%(items)s</div>
  </div>
</section>''' % {'h2': E(f['h2']), 'aside': E(f['aside']), 'tel': phone_link(), 'items': ''.join(items)}


def faq_ld():
    return {'@context': 'https://schema.org', '@type': 'FAQPage',
            'mainEntity': [{'@type': 'Question', 'name': it['q'],
                            'acceptedAnswer': {'@type': 'Answer', 'text': it['a']}} for it in SITE['faq']['items']]}


def business_ld():
    return {'@context': 'https://schema.org', '@type': 'LocalBusiness', '@id': DOMAIN + '/#business',
            'name': B['name'], 'telephone': B['phone'], 'email': B['email'], 'url': DOMAIN + '/',
            'image': DOMAIN + UI['og'],
            'address': {'@type': 'PostalAddress', 'addressLocality': B['base'], 'addressCountry': 'LT'},
            'areaServed': [{'@type': 'City', 'name': c} for c in B['cities']],
            'sameAs': [B['facebook'], B['instagram']]}


def form():
    c = SITE['contact']
    chips = ''.join('<label class="chip"><input class="chip__in" type="checkbox" name="Baldai[]" value="%s">'
                    '<span class="chip__box" aria-hidden="true"></span><span class="chip__txt">%s</span></label>'
                    % (E(t), E(t)) for t in c['types'])
    opts = ''.join('<option>%s</option>' % E(x) for x in B['cities']) + '<option>Kita vietovė</option>'
    return '''<form class="form" action="%(action)s" method="POST" enctype="multipart/form-data" novalidate data-form>
  <input type="hidden" name="_subject" value="Nauja užklausa iš svetainės">
  <input type="hidden" name="_template" value="table">
  <input type="hidden" name="_captcha" value="false">
  <input type="hidden" name="_next" value="%(next)s" data-next>
  <div class="hp" aria-hidden="true"><label>Nepildykite šio lauko<input type="text" name="_honey" tabindex="-1" autocomplete="off"></label></div>
  <div class="form__row">
    <div class="field" data-field>
      <label class="t-label field__label" for="f-name">Vardas <span class="f-req" aria-hidden="true">*</span></label>
      <input class="input" id="f-name" name="Vardas" type="text" autocomplete="name" required aria-describedby="f-name-err" data-msg="Įrašykite vardą.">
      <p class="field__err" id="f-name-err" role="alert"></p>
    </div>
    <div class="field" data-field>
      <label class="t-label field__label" for="f-tel">Telefonas <span class="f-req" aria-hidden="true">*</span></label>
      <input class="input tnum" id="f-tel" name="Telefonas" type="tel" inputmode="tel" autocomplete="tel" required pattern="[+]?[0-9 ]{8,17}" aria-describedby="f-tel-err" data-msg="Įrašykite telefono numerį." data-msg-bad="Patikrinkite telefono numerį.">
      <p class="field__err" id="f-tel-err" role="alert"></p>
    </div>
  </div>
  <div class="field" data-field>
    <label class="t-label field__label" for="f-email">El. paštas</label>
    <input class="input" id="f-email" name="email" type="email" autocomplete="email" aria-describedby="f-email-err" data-msg-bad="Patikrinkite el. pašto adresą.">
    <p class="field__err" id="f-email-err" role="alert"></p>
  </div>
  <fieldset class="field chips">
    <legend class="t-label field__label">Kokių baldų reikia?</legend>
    <div class="chips__row">%(chips)s</div>
  </fieldset>
  <div class="field" data-field>
    <label class="t-label field__label" for="f-city">Miestas</label>
    <div class="select"><select class="input" id="f-city" name="Miestas" autocomplete="address-level2"><option value="">Pasirinkite</option>%(opts)s</select></div>
  </div>
  <div class="field" data-field>
    <label class="t-label field__label" for="f-msg">Trumpai apie projektą</label>
    <textarea class="input" id="f-msg" name="Apie projektą" rows="5" placeholder="Patalpa, apytiksliai matmenys, pageidavimai"></textarea>
  </div>
  <div class="field" data-field data-files-field>
    <label class="t-label field__label" for="f-file">Patalpos nuotraukos ar planas</label>
    <div class="drop" data-drop>
      <input class="drop__in" id="f-file" name="attachment" type="file" multiple accept="image/*,.pdf" aria-describedby="f-file-hint f-file-err">
      <span class="drop__txt" aria-hidden="true"><span class="drop__main">Pasirinkite failus</span><span class="drop__or"> arba nutempkite juos čia</span></span>
      <span class="drop__hint t-small" id="f-file-hint">Nuotraukos arba PDF, iki 6 failų, iš viso iki 10 MB.</span>
    </div>
    <ul class="files" role="list" data-files></ul>
    <p class="field__err" id="f-file-err" role="alert"></p>
  </div>
  <div class="form__end">
    <button class="btn form__submit" type="submit" data-submit><span class="btn__t" data-submit-label>%(submit)s</span>%(arrow)s</button>
    <div class="form__notes">
      <p class="t-small">%(after)s</p>
      <p class="t-small">%(privacy)s</p>
    </div>
  </div>
</form>''' % {'action': B['form_endpoint'], 'next': DOMAIN + '/aciu/', 'chips': chips, 'opts': opts,
              'submit': E(c['submit']), 'arrow': ARROW, 'after': E(c['after']), 'privacy': E(c['privacy'])}


def s_request(page_id):
    c = SITE['contact']
    loc = B['cities_loc']
    cities_line = '%s %s ir %s.' % (SITE['cities']['label'], ', '.join(loc[:-1]), loc[-1])
    rows = [
        ('Telefonas', phone_link('req__a')),
        ('El. paštas', '<a class="req__a" href="mailto:%s">%s</a>' % (B['email'], E(B['email']))),
        ('Messenger', '<a class="req__a" href="%s" target="_blank" rel="noopener">%s</a>'
         % (B['messenger'], E(B['messenger'].split('//', 1)[-1]))),
        ('Instagram', '<a class="req__a" href="%s" target="_blank" rel="noopener">%s</a>'
         % (B['instagram_dm'], E(B['instagram_handle']))),
        ('Darbo laikas', E(B['hours'])),
    ]
    dl = ''.join('<div class="req__row"><dt class="t-label">%s</dt><dd>%s</dd></div>' % (k, v) for k, v in rows)
    return '''<section class="sec req" id="uzklausa" aria-labelledby="req-title">
  <div class="wrap grid">
    <div class="req__info">
      <h2 id="req-title" class="t-h2 rv">%(h2)s</h2>
      <p class="t-lead req__text rv" style="--rd:70ms">%(text)s</p>
      <dl class="req__dl rv" style="--rd:140ms">%(dl)s</dl>
      <p class="t-small req__cities">%(cities)s</p>
    </div>
    <div class="req__form">%(form)s</div>
  </div>
</section>''' % {'h2': E(c['h2']), 'text': E(c['text']), 'dl': dl, 'cities': E(cities_line), 'form': form()}


def cta_band():
    c = SITE['cta_band']
    return '''<section class="cta" aria-labelledby="cta-title">
  <div class="wrap cta__in">
    <h2 id="cta-title" class="t-h2 cta__h rv">%(h2)s</h2>
    <p class="t-lead cta__text rv" style="--rd:70ms">%(text)s</p>
    <div class="cta__actions rv" style="--rd:140ms">
      <a class="btn btn--light" href="/kontaktai/"><span class="btn__t">%(btn)s</span>%(arrow)s</a>
      %(tel)s
    </div>
  </div>
</section>''' % {'h2': E(c['h2']), 'text': E(c['text']), 'btn': E(c['btn']), 'arrow': ARROW,
                 'tel': phone_link('handle-link handle-link--dark')}


# ---------------------------------------------------------------- layout allocators
def list_plan(n):
    """Row plan for the /projektai/ grid (non-feature cards). Mirrors listPlan() in site.js."""
    size = {'A': 2, 'B': 2, 'C': 3}
    cycle = 'ABC'
    rows, left, i = [], n, 0
    while left > 0:
        t = cycle[i % 3]
        if left >= size[t]:
            rows.append(t)
            left -= size[t]
            i += 1
            continue
        if t == 'C':  # 1 or 2 left, previous row is B
            if left == 2:
                rows.append('A')
            else:
                rows[-1] = 'C'
        elif not rows:
            rows.append('S')
        elif rows[-1] == 'C':  # 1 left after a C row: C+1 -> A,B
            rows[-1] = 'A'
            rows.append('B')
        else:  # 1 left after an A row: A+1 -> C
            rows[-1] = 'C'
        left = 0
    classes = []
    for r in rows:
        classes += {'A': ['c-a1', 'c-a2'], 'B': ['c-b1', 'c-b2'], 'C': ['c-c', 'c-c', 'c-c'], 'S': ['c-s']}[r]
    return classes


LIST_SIZES = {
    'c-feat': '(min-width: 1024px) min(92vw, 1250px), 92vw',
    'c-a1': sizes(7, tab='46vw'), 'c-a2': sizes(5, tab='46vw'), 'c-b1': sizes(4, tab='46vw'),
    'c-b2': sizes(8, tab='46vw'), 'c-c': sizes(4, tab='46vw'), 'c-s': sizes(7, tab='46vw'),
}

GAL_SPANS = {'75': [7, 5], '57': [5, 7], '12': [12], '6c': [6], '444': [4, 4, 4], 'S': [12], 'Sp': [7], '66': [6, 6]}


def gal_plan(items):
    """items: list of dicts with 'landscape' and 'big' flags. Returns list of (rowtype, [items])."""
    cycle = ['75', '57', '12', '444']
    need = {'75': 2, '57': 2, '12': 1, '444': 3}
    rows, rest, i = [], list(items), 0
    while rest:
        t = cycle[i % 4]
        n = need[t]
        if t == '12':
            pick = next((k for k, it in enumerate(rest) if it['landscape'] and it['big']), None)
            if pick is None:
                rows.append(['6c', [rest.pop(0)]])
            else:
                rows.append(['12', [rest.pop(pick)]])
            i += 1
            continue
        if len(rest) >= n:
            rows.append([t, rest[:n]])
            rest = rest[n:]
            i += 1
            continue
        # remainder
        if t == '444':
            if len(rest) == 2:
                rows.append(['75', rest[:2]])
            else:  # 1 left, previous row is a single (12/6c): pair them
                prev = rows.pop()
                rows.append(['75', prev[1] + rest[:1]])
        elif not rows:
            rows.append(['S' if rest[0]['landscape'] else 'Sp', rest[:1]])
        elif len(rows[-1][1]) == 3:  # 1 left after a 444 row
            prev = rows.pop()
            both = prev[1] + rest[:1]
            rows.append(['75', both[:2]])
            rows.append(['57', both[2:]])
        else:  # 1 left after a two-up row: make it three
            prev = rows.pop()
            rows.append(['444', prev[1] + rest[:1]])
        rest = []
    return rows


def gal_html(entries, lb_key, lb_index, sizes_for=None):
    """entries: list of dicts {kind:'img'|'video', ref/name, alt, fx, fy}."""
    items = []
    for e in entries:
        if e['kind'] == 'video':
            v = VID[e['name']]
            e['landscape'] = v['w'] > v['h']
            e['big'] = False
        else:
            m = IMG[e['ref']]
            e['landscape'] = m['w'] >= m['h'] * 1.05
            e['big'] = max(m['widths']) >= 1600 and m['w'] >= 1600
        items.append(e)
    if items and items[0]['kind'] == 'video':
        # the video always takes the 5-column cell of a 5/7 row, next to the first photo
        photos = items[1:]
        if photos:
            rows = [['57', [items[0], photos[0]]]] + (gal_plan(photos[1:]) if len(photos) > 1 else [])
        else:
            rows = [['Sp', [items[0]]]]
    else:
        rows = gal_plan(items)
    out = []
    for t, row in rows:
        spans = GAL_SPANS[t]
        cells = []
        for k, e in enumerate(row):
            span = spans[k] if k < len(spans) else spans[-1]
            if e['kind'] == 'video':
                v = VID[e['name']]
                ar = '%s / %s' % (v['w'], v['h'])
                inner = video_block(e['name'], e['alt'], cls='vid--fill')
            else:
                if t in ('12', 'S'):
                    ar = '3 / 2'
                else:
                    ar = '3 / 2' if e['landscape'] else '4 / 5'
                sz = sizes(span, tab='%dvw' % round(span / 12 * 92), mob='92vw')
                pic = img(e['ref'], sz, cls='gal__img', alt=e['alt'], fx=e.get('fx'), fy=e.get('fy'))
                if lb_key and e['ref'] in lb_index:
                    pic = ('<button class="lb-trig gal__btn" type="button" data-lb="%s" data-i="%d" aria-label="Padidinti: %s">%s</button>'
                           % (lb_key, lb_index[e['ref']], E(e['alt']), pic))
                inner = pic
            cells.append('<figure class="gal__item gal__item--%s" style="--ar:%s">%s</figure>' % (span, ar, inner))
        if t == '444':
            # uniform row: all three share the ratio of the majority
            land = sum(1 for e in row if e.get('landscape'))
            ar = '3 / 2' if land >= 2 else '4 / 5'
            cells = [re.sub(r'--ar:[^"]+"', '--ar:%s"' % ar, c, count=1) for c in cells]
        out.append('<div class="gal__row gal__row--%s">%s</div>' % (t, ''.join(cells)))
    return '<div class="gal">%s</div>' % ''.join(out)


# ---------------------------------------------------------------- pages
def build_home():
    lb = {}
    body = '\n'.join([s_hero(), s_work(), s_flag(lb), s_mat(), s_proc(), s_break(), s_reviews(),
                      s_cities(), s_faq(), s_request('home')])
    return page(SITE['seo']['home_title'], SITE['seo']['home_description'], '/', 'home', body,
                preload=hero_preload(), jsonld=(business_ld(), faq_ld()), lb=lb)


def build_projects():
    flag = [p for p in PROJECTS if p.get('flagship')]
    rest = [p for p in PROJECTS if not p.get('flagship')]
    plan = list_plan(len(rest))
    cards = []
    for p in flag:
        cv = cover_of(p)
        if not cv:
            continue
        cats = ' · '.join(CAT[c] for c in p['cats'])
        cards.append('''<a class="card card--feat c-feat" href="/projektai/%(slug)s/" data-slug="%(slug)s" data-cats="%(cats_raw)s" data-feat>
      <figure class="card__fig">%(img)s</figure>
      <div class="card__cap card__cap--feat">
        <div class="card__txt">
          <h2 class="t-h3 card__title"><span class="card__line">%(title)s</span></h2>
          <p class="t-small card__meta">%(meta)s</p>
          <p class="card__cats">%(cats)s</p>
        </div>
        <p class="card__lead">%(lead)s</p>
        %(vid)s
      </div>
    </a>''' % {'slug': p['slug'], 'cats_raw': ' '.join(p['cats']),
               'img': img(cv['ref'], LIST_SIZES['c-feat'], cls='card__img', alt=cv['alt'], fx=cv['fx'], fy=cv['fy'],
                          eager=True, style='view-transition-name:p-%s' % p['slug']),
               'title': line_title(p['title']), 'meta': E(p.get('place') or p['card_meta']), 'cats': E(cats),
               'lead': E(first_sentence(p['lead'])),
               'vid': ('<span class="card__vid t-label">%sVideo</span>' % PLAY) if p.get('video') else ''})
    for i, p in enumerate(rest):
        cls = plan[i]
        cards.append(card(p, cls=cls, sz=LIST_SIZES[cls], heading='h2', eager=i < 2))
    body = '''<section class="phead" aria-labelledby="page-title">
  <div class="wrap">
    <h1 id="page-title" class="t-hero t-hero--page rv">Projektai</h1>
    <p class="t-lead phead__lead rv" style="--rd:70ms">Virtuvės, spintos, prieškambariai, vonios ir baldai verslui. Visi suprojektuoti ir pagaminti pagal konkrečią erdvę.</p>
    %(tabs)s
  </div>
</section>
<section class="plist" aria-label="Projektų sąrašas">
  <div class="wrap">
    <div class="plist__grid" data-grid="list" data-sizes='%(sizes)s'>%(cards)s</div>
  </div>
</section>
%(cta)s''' % {'tabs': tabs('list', len(PROJECTS)), 'cards': '\n'.join(cards), 'cta': cta_band(),
              'sizes': E(json.dumps(LIST_SIZES))}
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Pradžia', 'item': DOMAIN + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Projektai', 'item': DOMAIN + '/projektai/'}]}
    return page(SITE['seo']['projects_title'], SITE['seo']['projects_description'], '/projektai/', 'projects', body,
                jsonld=(crumbs,))


def spec_block(p, cls=''):
    if not p.get('spec'):
        return ''
    rows = ''.join('<div class="spec__row"><dt class="t-label">%s</dt><dd>%s</dd></div>' % (E(k), E(v))
                   for k, v in p['spec'])
    return ('<div class="spec %s"><h2 class="t-label spec__h">Iš ko pagaminta</h2><dl class="spec__dl">%s</dl></div>'
            % (cls, rows))


def build_project(p, idx):
    slug = p['slug']
    cats = [CAT[c] for c in p['cats']]
    first_cat = p['cats'][0]
    photos = [ph for ph in project_photos(p) if ok(ph['src'])]
    lb_list = [lb_item(ph['src'], ph['alt']) for ph in photos]
    lb_index = {}
    for i, ph in enumerate(photos):
        lb_index.setdefault(ph['src'], i)
    lb = {'all': lb_list} if lb_list else {}
    cv = cover_of(p)
    is_flag = bool(p.get('flagship'))
    has_split = bool(p.get('video')) and not is_flag and p['video'] in VID

    meta = '<div class="pmeta__row"><dt class="t-label">Erdvė</dt><dd>%s</dd></div>' % E(', '.join(cats))
    if p.get('place'):
        meta += '<div class="pmeta__row"><dt class="t-label">Vieta</dt><dd>%s</dd></div>' % E(p['place'])

    parts = ['''<article class="proj">
  <header class="wrap proj__head">
    <nav class="crumbs t-small" aria-label="Naršymo kelias"><a href="/projektai/">Projektai</a><span aria-hidden="true">/</span><a href="/projektai/?k=%s">%s</a></nav>
    <h1 class="t-h2 proj__title">%s</h1>
    <dl class="pmeta">%s</dl>
  </header>''' % (first_cat, E(CAT[first_cat]), E(p['title']), meta)]

    shown = set()
    body_html = ''.join('<p>%s</p>' % E(b) for b in p.get('body', []))
    prose = ('<div class="prose">%s</div>' % body_html) if body_html else ''
    ratio_cv = (IMG[cv['ref']]['w'] / float(IMG[cv['ref']]['h'])) if cv else 1.0
    if has_split:
        mode = 'video'
    elif cv and ratio_cv < 0.95:
        mode = 'portrait'
    else:
        mode = 'plate'

    def cover_pic(sz):
        pic = img(cv['ref'], sz, cls='pplate__img', alt=cv['alt'], eager=True, fx=cv['fx'], fy=cv['fy'],
                  style='view-transition-name:p-%s' % slug)
        if cv['ref'] in lb_index:
            pic = ('<button class="lb-trig pplate__btn" type="button" data-lb="all" data-i="%d" aria-label="Padidinti: %s">%s</button>'
                   % (lb_index[cv['ref']], E(cv['alt']), pic))
        return pic

    if mode in ('video', 'portrait'):
        if mode == 'video':
            media = ('<div class="psplit__media psplit__media--vid">%s</div>'
                     % video_block(p['video'], p['title'], cls='vid--fill',
                                   vt='view-transition-name:p-%s' % slug))
        else:
            shown.add(cv['ref'])
            media = ('<figure class="psplit__media" style="--ar:%.4f">%s</figure>'
                     % (max(ratio_cv, 0.8), cover_pic('(min-width: 1024px) min(46vw, 640px), 92vw')))
        short = not prose and not p.get('spec')
        parts.append('''  <section class="wrap grid psplit psplit--%s%s" aria-label="Apie projektą">
    %s
    <div class="psplit__text">
      <p class="t-lead">%s</p>
      %s
      %s
    </div>
  </section>''' % (mode, ' psplit--short' if short else '', media, E(p['lead']), prose, spec_block(p, 'spec--split')))
    else:
        if cv:
            shown.add(cv['ref'])
            parts.append('  <figure class="wrap pplate" style="--r:%.4f">%s</figure>'
                         % (min(ratio_cv, 1.6), cover_pic('(min-width: 1440px) 1250px, 92vw')))
        parts.append('''  <section class="wrap grid pintro" aria-label="Apie projektą">
    <div class="pintro__text"><p class="t-lead">%s</p>%s</div>
    %s
  </section>''' % (E(p['lead']), prose, spec_block(p, 'pintro__spec')))

    if is_flag:
        st_html = []
        for si, st in enumerate(p.get('stages', [])):
            entries = []
            v = (st.get('media') or {}).get('video')
            if v and v in VID:
                entries.append({'kind': 'video', 'name': v, 'alt': '%s: %s' % (p['title'], st['title'])})
            for ph in st.get('photos', []):
                if ok(ph['src']):
                    entries.append({'kind': 'img', 'ref': ph['src'], 'alt': ph['alt'], 'fx': ph.get('fx'), 'fy': ph.get('fy')})
            gal = gal_html(entries, 'all', lb_index) if entries else ''
            st_html.append('''<div class="pstage">
      <div class="grid pstage__head">
        <div class="pstage__meta"><p class="t-label stage__label">%s</p><h2 class="t-h3 pstage__title">%s</h2></div>
        <p class="pstage__text">%s</p>
      </div>
      %s
    </div>''' % (E(st['label']), E(st['title']), E(st['text']), gal))
        parts.append('  <section class="pstages" aria-label="Projekto etapai"><div class="wrap">%s</div></section>' % ''.join(st_html))

    ba = p.get('before_after')
    if ba and ok(ba.get('before')) and ok(ba.get('after')):
        parts.append('  <section class="wrap pdip" aria-label="Prieš ir po">%s</section>'
                     % diptych(ba['before'], ba['after'], 'Prieš', 'Po', '(min-width: 768px) 46vw, 92vw',
                               cls='dip--wide', lb_key='all', lb_idx=lb_index))
    vz = p.get('viz_pair')
    if vz and ok(vz.get('render')) and ok(vz.get('real')):
        parts.append('  <section class="wrap pdip" aria-label="Vizualizacija ir rezultatas">%s</section>'
                     % diptych(vz['render'], vz['real'], 'Vizualizacija', 'Įgyvendinta', '(min-width: 768px) 46vw, 92vw',
                               cls='dip--wide', lb_key='all', lb_idx=lb_index))

    if not is_flag:
        skip_roles = set()
        if ba and ok(ba.get('before')):
            skip_roles.add('before')
        if vz and ok(vz.get('render')):
            skip_roles.add('render')
        entries = [{'kind': 'img', 'ref': ph['src'], 'alt': ph['alt'], 'fx': ph.get('fx'), 'fy': ph.get('fy')}
                   for ph in photos if ph.get('role') not in skip_roles and ph['src'] not in shown]
        if entries:
            parts.append('  <section class="wrap pgal" aria-label="Nuotraukos">%s</section>' % gal_html(entries, 'all', lb_index))

    prev_p = PROJECTS[idx - 1]
    next_p = PROJECTS[(idx + 1) % len(PROJECTS)]

    def pn(q, label, cls):
        c = cover_of(q)
        pic = img(c['ref'], '(min-width: 768px) 240px, 40vw', cls='pn__img', alt='', fx=c['fx'], fy=c['fy'],
                  style='view-transition-name:p-%s' % q['slug']) if c else ''
        return ('<a class="pn__a %s" href="/projektai/%s/"><span class="pn__fig">%s</span>'
                '<span class="pn__txt"><span class="t-label pn__label">%s</span>'
                '<span class="t-title pn__title"><span class="card__line">%s</span></span></span></a>'
                % (cls, q['slug'], pic, label, line_title(q['title'])))

    parts.append('  <nav class="wrap pn" aria-label="Kiti projektai">%s%s</nav>'
                 % (pn(prev_p, 'Ankstesnis projektas', 'pn__a--prev'), pn(next_p, 'Kitas projektas', 'pn__a--next')))
    parts.append('</article>')
    parts.append(cta_band())
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Projektai', 'item': DOMAIN + '/projektai/'},
        {'@type': 'ListItem', 'position': 2, 'name': CAT[first_cat], 'item': DOMAIN + '/projektai/?k=' + first_cat},
        {'@type': 'ListItem', 'position': 3, 'name': p['title'], 'item': DOMAIN + '/projektai/%s/' % slug}]}
    return page('%s | Pikio baldai' % p['title'], p['lead'], '/projektai/%s/' % slug, 'project',
                '\n'.join(parts), jsonld=(crumbs,), lb=lb)


def build_contacts():
    rek = [('Pavadinimas', E(B['legal'])), ('Įmonės kodas', E(B['code'])),
           ('Registracijos adresas', E(B['reg_address'])), ('Veiklos vieta', E(B['base'])),
           ('Vadovas', E(B['manager'])), ('Aptarnaujame', E(', '.join(B['cities'])))]
    dl = ''.join('<div class="rek__row"><dt class="t-label">%s</dt><dd>%s</dd></div>' % (k, v) for k, v in rek)
    body = '''<section class="phead phead--tight" aria-labelledby="page-title">
  <div class="wrap"><h1 id="page-title" class="t-hero t-hero--page rv">Kontaktai</h1></div>
</section>
%s
<section class="sec rek" aria-labelledby="rek-title">
  <div class="wrap grid">
    <h2 id="rek-title" class="t-h3 rek__h rv">Rekvizitai</h2>
    <dl class="rek__dl rv" style="--rd:70ms">%s</dl>
  </div>
</section>''' % (s_request('contacts'), dl)
    return page(SITE['seo']['contacts_title'], SITE['seo']['contacts_description'], '/kontaktai/', 'contacts', body,
                jsonld=(business_ld(),))


def build_thanks():
    c = SITE['contact']
    text = E(c['thanks_text']).replace(E(B['phone']), '<a class="inline-link tnum" href="%s">%s</a>' % (B['phone_href'], E(B['phone'])))
    body = '''<section class="solo" aria-labelledby="page-title">
  <div class="wrap">
    <h1 id="page-title" class="t-hero t-hero--page rv">%s</h1>
    <p class="t-lead solo__text rv" style="--rd:70ms">%s</p>
    <div class="solo__actions rv" style="--rd:140ms">
      <a class="btn" href="/projektai/"><span class="btn__t">%s</span>%s</a>
      <a class="btn btn--line" href="/"><span class="btn__t">Pradžia</span></a>
    </div>
  </div>
</section>''' % (E(c['thanks_h1']), text, E(SITE['work']['all_label']), ARROW)
    return page('%s | Pikio baldai' % c['thanks_h1'], c['thanks_text'], '/aciu/', 'thanks', body, noindex=True)


def build_404():
    body = '''<section class="solo" aria-labelledby="page-title">
  <div class="wrap">
    <h1 id="page-title" class="t-hero t-hero--page">Puslapis nerastas</h1>
    <div class="solo__actions">
      <a class="btn" href="/"><span class="btn__t">Pradžia</span>%s</a>
      <a class="btn btn--line" href="/projektai/"><span class="btn__t">%s</span></a>
    </div>
  </div>
</section>''' % (ARROW, E(SITE['work']['all_label']))
    return page('Puslapis nerastas | Pikio baldai', SITE['seo']['home_description'], '/404.html', '404', body, noindex=True)


def build_manifest():
    return json.dumps({'name': 'Pikio baldai', 'short_name': 'Pikio baldai', 'lang': 'lt', 'start_url': '/',
                       'display': 'browser', 'background_color': '#F5F2ED', 'theme_color': '#F5F2ED',
                       'icons': [{'src': ICONS['192'], 'sizes': '192x192', 'type': 'image/png'},
                                 {'src': ICONS['512'], 'sizes': '512x512', 'type': 'image/png'}]},
                      ensure_ascii=False, indent=1) + '\n'


# ---------------------------------------------------------------- write
def write(rel, text):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)
    return rel


def main():
    validate()
    written = []
    written.append(write('index.html', build_home()))
    written.append(write('projektai/index.html', build_projects()))
    for i, p in enumerate(PROJECTS):
        written.append(write('projektai/%s/index.html' % p['slug'], build_project(p, i)))
    written.append(write('kontaktai/index.html', build_contacts()))
    written.append(write('aciu/index.html', build_thanks()))
    written.append(write('404.html', build_404()))
    written.append(write('site.webmanifest', build_manifest()))
    urls = ['/', '/projektai/'] + ['/projektai/%s/' % p['slug'] for p in PROJECTS] + ['/kontaktai/']
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append('  <url><loc>%s%s</loc><lastmod>%s</lastmod></url>' % (DOMAIN, u, TODAY))
    sm.append('</urlset>')
    written.append(write('sitemap.xml', '\n'.join(sm) + '\n'))
    written.append(write('robots.txt', 'User-agent: *\nAllow: /\nDisallow: /assets/\n\nSitemap: %s/sitemap.xml\n' % DOMAIN))

    # hard rules on the output
    bad = []
    for rel in written:
        with open(os.path.join(OUT, rel), encoding='utf-8') as fh:
            txt = fh.read()
        if '\u2014' in txt:
            bad.append('%s contains an em-dash' % rel)
        if re.search(r'\s–\s', txt):
            bad.append('%s uses an en-dash as punctuation' % rel)
        if rel.endswith('.html'):
            if len(re.findall(r'<h1[\s>]', txt)) != 1:
                bad.append('%s must have exactly one h1' % rel)
            live = re.sub(r'<template[\s\S]*?</template>', '', txt)
            names = re.findall(r'view-transition-name:\s*([\w-]+)', live)
            dup = sorted({n for n in names if names.count(n) > 1})
            if dup:
                bad.append('%s duplicate view-transition-name: %s' % (rel, ', '.join(dup)))
    if bad:
        fail('output checks', bad)
    print('wrote %d files to %s (css/js v=%s)' % (len(written), OUT, VER))
    pages = [w for w in written if w.endswith('.html')]
    print('pages: %d' % len(pages))
    if WARN:
        print('\nwarnings:')
        for w in WARN:
            print('  - ' + w)


if __name__ == '__main__':
    main()
