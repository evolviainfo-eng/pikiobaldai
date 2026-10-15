#!/usr/bin/env python3
"""Pikio baldai, vieno puslapio svetainė.

  python3 build.py

Visas turinys yra šiame faile (sutrumpintas iš ankstesnės svetainės, nieko naujo).
Nuotraukos kopijuojamos iš ../pikiobaldai (ankstesnio projekto media rinkinio) į img/w/,
tada perrašomas index.html. Be priklausomybių, tik standartinė biblioteka.
"""
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / 'pikiobaldai'
WIDTHS = (480, 800, 1200, 1600)

BRAND = {
    'name': 'Pikio baldai',
    'legal': 'MB „Pikio baldai“',
    'code': '307094158',
    'phone': '+370 631 88918',
    'phone_href': 'tel:+37063188918',
    'email': 'pikiobaldai@gmail.com',
    'facebook': 'https://www.facebook.com/pikiobaldai/',
    'facebook_reviews': 'https://www.facebook.com/pikiobaldai/reviews',
    'instagram': 'https://www.instagram.com/pikiobaldai/',
    'site': 'https://pikiobaldai.vercel.app',
}

HERO = {
    'h1': 'Nestandartiniai korpusiniai baldai Kaune',
    'lead': 'Virtuves, spintas, prieškambario ir vonios baldus projektuojame, gaminame ir montuojame patys.',
    'cta': 'Susisiekti',
    'alt': 'Lentynos ir spintelės per visą sieną namų bibliotekoje',
}

SERVICES = {
    'lead': 'Atvykstame išmatuoti ir sumontuoti Kaune, Vilniuje, Alytuje ir Varėnoje.',
    'items': [
        ('Virtuvės', 'Virtuvės baldai pagal patalpos matmenis: spintelės, stalviršiai, salos ir furnitūra.'),
        ('Spintos ir drabužinės', 'Spintos iki lubų ir drabužinės, pritaikytos nišoms, kampams ir nuožulnioms luboms.'),
        ('Prieškambariai', 'Prieškambario spintos su minkštasuoliu ar paslėptomis durimis.'),
        ('Vonios', 'Vonios spintelės ir spintos iki lubų su lengvai prižiūrimais paviršiais.'),
        ('Svetainės ir kambariai', 'Lentynos per visą sieną, TV baldai, darbo vietos ir vaikų kambarių baldai.'),
        ('Verslui', 'Baldai paslaugų patalpoms: virtuvė, vonia ir priimamojo stalas.'),
    ],
}

# geriausios nuotraukos pirmos; trumpas pavadinimas iš ankstesnio projekto turinio
WORK = [
    ('akademijos-miestelis', 'Virtuvė Akademijos miestelyje'),
    ('spinteles-aukso-rankenelemis', 'Svetainės spintelės'),
    ('prieskambaris-su-minkstasuoliu', 'Prieškambario spintos'),
    ('drabuzine', 'Drabužinė'),
    ('svajoniu-virtuve', 'Šviesi virtuvė'),
    ('tamsi-virtuve', 'Tamsių tonų virtuvė'),
    ('kampine-spinta-su-komoda', 'Kampinė spinta su komoda'),
    ('namu-biblioteka', 'Namų biblioteka'),
    ('azuolo-vonios-spintele', 'Vonios spintelė'),
    ('virtuve-su-tamsia-sienele', 'Virtuvė su tamsia sienele'),
    ('paslaugu-butas-vilniuje', 'Paslaugų butas Vilniuje'),
    ('vonios-baldai-su-spinta', 'Vonios baldai'),
]

# atsiliepimai tokie, kokie buvo svetainėje (iš „Facebook“), be trumpinimo
REVIEWS = [
    ('Dovilė Š.', 'Esame patenkinti darbu ir norų išpildymu 100\u00a0%. Malonu bendradarbiauti, kai atsižvelgia į kiekvieną smulkmeną, pataria ir padeda rasti geriausią sprendimą klientui.'),
    ('Aistė Č.', 'Puikiai komunikuoja proceso metu, idėjas pagauna ir įgyvendina, jokių nesusipratimų nebuvo, dirba greitai ir labai švariai.'),
    ('Gintarė P.', 'Tik pačios geriausios rekomendacijos! Nereikia laukti kelių mėnesių savo užsakymo, dirba greitai ir kokybiškai. Atsakingi ir darbštūs vyrukai. Aš būtinai vėl kreipsiuosi.'),
]

CONTACT = {
    'text': 'Paskambinkite arba atsiųskite patalpos nuotrauką ir apytikslius matmenis.',
    'hours': 'Skambinkite bet kuriuo metu',
    'cities': 'Kaunas, Vilnius, Alytus, Varėna',
}

ARROW = '<svg class="arr" viewBox="0 0 22 12" width="22" height="12" aria-hidden="true" focusable="false"><path d="M0 6h20.4M15.2.9 20.4 6l-5.2 5.1" fill="none" stroke="currentColor" stroke-width="1.25"/></svg>'

e = lambda s: html.escape(s, quote=True)


def load(name):
    return json.loads((SRC / 'assets/data' / name).read_text())


MEDIA = load('media.json')['images']
PROJECTS = {p['slug']: p for p in load('projects.json')['projects']}


def photo(key):
    """Kopijuoja vieno kadro WebP variantus ir grąžina src/srcset/matmenis."""
    m = MEDIA[key]
    out = []
    for w in m['widths']:
        if w not in WIDTHS:
            continue
        src = SRC / m['path'].replace('{w}', str(w)).lstrip('/')
        dst = ROOT / 'img/w' / f"{m['key']}-{w}.webp"
        if not dst.exists():
            shutil.copyfile(src, dst)
        out.append((w, f"/img/w/{m['key']}-{w}.webp"))
    big = out[-1][0]
    h = round(m['h'] * big / m['w'])
    return {
        'src': out[min(2, len(out) - 1)][1],
        'srcset': ', '.join(f'{u} {w}w' for w, u in out),
        'w': big, 'h': h, 'bg': m.get('bg', '#a09487'),
    }


def project_photos(p):
    seen, items = set(), []
    pool = list(p.get('photos', []))
    for st in p.get('stages', []):
        pool += st.get('photos', [])
    cover = p['cover']
    pool.sort(key=lambda q: q['src'] != cover)
    if not any(q['src'] == cover for q in pool):
        pool.insert(0, {'src': cover, 'alt': p['title']})
    for q in pool:
        if q['src'] in seen:
            continue
        seen.add(q['src'])
        items.append({**photo(q['src']), 'alt': q.get('alt') or p['title'],
                      'pos': f"{q.get('fx', 50)}% {q.get('fy', 50)}%"})
    return items


def work_html():
    tiles, data = [], {}
    for i, (slug, title) in enumerate(WORK):
        ph = project_photos(PROJECTS[slug])
        data[slug] = {'title': title, 'photos': [{k: v for k, v in q.items() if k != 'pos'} for q in ph]}
        c = ph[0]
        tiles.append(
            f'<li class="tile">'
            f'<button class="tile__btn" type="button" data-lb="{slug}" aria-label="{e(title)}, peržiūrėti {len(ph)} nuotr.">'
            f'<span class="tile__img" style="background:{c["bg"]}"><span class="tile__zoom">'
            f'<img src="{c["src"]}" srcset="{c["srcset"]}" sizes="(min-width: 1024px) 30vw, (min-width: 768px) 45vw, 46vw" '
            f'width="{c["w"]}" height="{c["h"]}" alt="{e(c["alt"])}" style="object-position:{c["pos"]}" data-par="5" '
            f'loading="{"eager" if i < 3 else "lazy"}" decoding="async"></span></span>'
            f'<span class="tile__t">{e(title)}</span></button></li>')
    return '\n        '.join(tiles), data


def lb_entry(slug):
    titles = dict(WORK)
    ph = project_photos(PROJECTS[slug])
    return {'title': titles.get(slug, PROJECTS[slug]['title']),
            'photos': [{k: v for k, v in q.items() if k != 'pos'} for q in ph]}


def materials_html(lb):
    """„Iš ko pagaminta“: tikri plokščių, stalviršių ir furnitūros pavadinimai iš kliento įrašų.
    Desktop'e plokštės nuotrauka keičiasi pagal pasirinktą medžiagą ir visada telpa į ekraną;
    telefone medžiagos kortelėmis, paspaudus atsidaro to projekto nuotraukos."""
    mat = load('site.json')['materials']
    (ROOT / 'img/m').mkdir(exist_ok=True)
    data, groups, first = {}, [], None
    for gi, g in enumerate(mat['groups']):
        items = []
        for it in g['items']:
            sid, slug = it['id'], it['project']
            if slug not in lb:
                lb[slug] = lb_entry(slug)
            sw = []
            for w in (240, 480):
                src = SRC / 'img/m' / f'{sid}-{w}.webp'
                if src.exists():
                    shutil.copyfile(src, ROOT / 'img/m' / src.name)
                    sw.append((w, f'/img/m/{src.name}'))
            pl = photo(it['plate'])
            alt, pos = PROJECTS[slug]['title'], '50% 50%'
            for q in project_photos(PROJECTS[slug]):
                if q['srcset'] == pl['srcset']:
                    alt, pos = q['alt'], q['pos']
            data[sid] = {**pl, 'alt': alt, 'pos': pos, 'name': it['name'], 'code': it['code'],
                         'proj': slug, 'projTitle': lb[slug]['title']}
            first = first or sid
            pressed = 'true' if sid == first else 'false'
            items.append(
                f'<li><button class="sw" type="button" aria-pressed="{pressed}" data-sw="{sid}" data-proj="{slug}">'
                f'<span class="sw__box"><img src="{sw[0][1]}" srcset="{", ".join(f"{u} {w}w" for w, u in sw)}" '
                f'sizes="(min-width: 1024px) 112px, 64px" width="{sw[-1][0]}" height="{sw[-1][0]}" alt="{e(it["name"])}, paviršiaus pavyzdys" loading="lazy" decoding="async"></span>'
                f'<span class="sw__name">{e(it["name"])}</span><span class="sw__code">{e(it["code"])}</span></button></li>')
        groups.append(
            f'<div class="mat__group" role="group" aria-labelledby="mg{gi}"><h3 class="mat__gt" id="mg{gi}">{e(g["title"])}</h3>'
            f'<ul class="sws" role="list">{"".join(items)}</ul></div>')
    d = data[first]
    sizes = '(min-width: 1024px) 52vw, 1px'
    plate = (
        f'<figure class="mat__plate">'
        f'<div class="mat__frame">'
        f'<img class="mat__img is-front" src="{d["src"]}" srcset="{d["srcset"]}" sizes="{sizes}" width="{d["w"]}" height="{d["h"]}" '
        f'alt="{e(d["alt"])}" style="object-position:{d["pos"]}" loading="lazy" decoding="async" data-plate-a>'
        f'<img class="mat__img" src="data:," sizes="{sizes}" width="{d["w"]}" height="{d["h"]}" alt="{e(d["alt"])}" aria-hidden="true" decoding="async" data-plate-b>'
        f'</div>'
        f'<figcaption class="mat__cap"><span class="mat__name"><span data-plate-name>{e(d["name"])}</span> · '
        f'<span class="mat__code" data-plate-code>{e(d["code"])}</span></span>'
        f'<button class="link" type="button" data-lb="{d["proj"]}" data-plate-link><span data-plate-proj>{e(d["projTitle"])}</span>{ARROW}</button>'
        f'</figcaption></figure>')
    html_ = (
        f'<div class="mat" data-mat>\n        {plate}\n        <div class="mat__side">'
        f'<h2 class="h2 rv" id="mat-t">{e(mat["h2"])}</h2>'
        f'<p class="lead rv" style="--d:120ms">{e(mat["text"])}</p>'
        f'<div class="mat__groups">{"".join(groups)}'
        f'<p class="mat__note">{e(mat["note"])}</p></div></div>\n      </div>')
    return mat, html_, data


def page():
    tiles, lb = work_html()
    mat, mat_html, mat_data = materials_html(lb)
    svc = '\n        '.join(
        f'<li class="svc"><h3 class="svc__t">{e(t)}</h3><p class="svc__p">{e(p)}</p></li>' for t, p in SERVICES['items'])
    rev = '\n        '.join(
        f'<li class="rev"><blockquote class="rev__q"><p>{e(q)}</p></blockquote><p class="rev__n">{e(n)}</p></li>'
        for n, q in REVIEWS)
    b = BRAND
    logo = ('<img class="hd__logo" src="/img/logo/pikio-baldai-dark-240.png" srcset="/img/logo/pikio-baldai-dark-240.png 240w, '
            '/img/logo/pikio-baldai-dark-480.png 480w" sizes="(min-width: 1024px) 104px, 82px" width="205" height="100" alt="Pikio baldai">')
    desc = 'Nestandartiniai korpusiniai baldai Kaune: virtuvės, spintos, prieškambariai, vonios ir baldai verslui. Projektuojame, gaminame ir montuojame patys.'
    ld = {
        '@context': 'https://schema.org', '@type': 'FurnitureStore', 'name': b['name'], 'legalName': b['legal'],
        'telephone': b['phone'].replace(' ', ''), 'email': b['email'], 'url': b['site'] + '/',
        'image': b['site'] + '/img/og.jpg', 'areaServed': ['Kaunas', 'Vilnius', 'Alytus', 'Varėna'],
        'sameAs': [b['facebook'], b['instagram']],
    }
    return f'''<!doctype html>
<html lang="lt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Pikio baldai | Nestandartiniai korpusiniai baldai Kaune</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#F5F2ED">
<link rel="canonical" href="{b['site']}/">
<meta property="og:type" content="website">
<meta property="og:locale" content="lt_LT">
<meta property="og:title" content="Pikio baldai | Nestandartiniai korpusiniai baldai Kaune">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{b['site']}/">
<meta property="og:image" content="{b['site']}/img/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon.png">
<link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preload" href="/fonts/josefin-sans-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/josefin-sans-latin-ext.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" as="image" href="/img/ui/hero-d-1920.webp" imagesrcset="/img/ui/hero-d-1280.webp 1280w, /img/ui/hero-d-1920.webp 1920w, /img/ui/hero-d-2560.webp 2560w" imagesizes="100vw" media="(min-width: 768px)">
<link rel="preload" as="image" href="/img/ui/hero-m-1200.webp" imagesrcset="/img/ui/hero-m-800.webp 800w, /img/ui/hero-m-1200.webp 1200w, /img/ui/hero-m-1600.webp 1600w" imagesizes="175vw" media="(max-width: 767px)">
<link rel="stylesheet" href="/css/site.css">
<script>document.documentElement.classList.add('js')</script>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<a class="skip" href="#turinys">Pereiti prie turinio</a>
<header class="hd" data-nav>
  <div class="wrap hd__in">
    <a class="hd__home" href="#top" aria-label="Pikio baldai, į puslapio pradžią">{logo}</a>
    <nav class="hd__nav" aria-label="Puslapio skyriai">
      <a href="#paslaugos">Paslaugos</a><a href="#darbai">Darbai</a><a href="#medziagos">Medžiagos</a><a href="#atsiliepimai">Atsiliepimai</a><a href="#kontaktai">Kontaktai</a>
    </nav>
    <a class="hd__tel" href="{b['phone_href']}"><span class="hd__tel-n">{b['phone']}</span><span class="hd__tel-s">Skambinti</span></a>
  </div>
</header>

<main id="turinys">
  <section class="hero" id="top" aria-labelledby="hero-t" data-hero>
    <picture>
      <source media="(min-width: 768px)" srcset="/img/ui/hero-d-1280.webp 1280w, /img/ui/hero-d-1920.webp 1920w, /img/ui/hero-d-2560.webp 2560w" sizes="100vw" width="2560" height="1600">
      <img class="hero__img" src="/img/ui/hero-m-1200.webp" srcset="/img/ui/hero-m-800.webp 800w, /img/ui/hero-m-1200.webp 1200w, /img/ui/hero-m-1600.webp 1600w" sizes="175vw" width="1600" height="2000" alt="{e(HERO['alt'])}" fetchpriority="high" decoding="async">
    </picture>
    <div class="wrap hero__in">
      <h1 class="hero__h rv" id="hero-t" style="--d:0ms">{e(HERO['h1'])}</h1>
      <p class="hero__p rv" style="--d:140ms">{e(HERO['lead'])}</p>
      <p class="rv" style="--d:280ms"><a class="btn" href="#kontaktai"><span>{e(HERO['cta'])}</span>{ARROW}</a></p>
    </div>
  </section>

  <section class="sec" id="paslaugos" aria-labelledby="svc-t">
    <div class="wrap">
      <div class="top">
        <h2 class="h2 rv" id="svc-t">Paslaugos</h2>
        <p class="lead rv" style="--d:120ms">{e(SERVICES['lead'])}</p>
      </div>
      <ul class="cols svc__list" role="list" data-stagger="70">
        {svc}
      </ul>
    </div>
  </section>

  <section class="sec sec--work" id="darbai" aria-labelledby="work-t">
    <div class="wrap">
      <h2 class="h2 rv" id="work-t">Atlikti darbai</h2>
      <ul class="grid" role="list">
        {tiles}
      </ul>
    </div>
  </section>

  <section class="sec sec--mat" id="medziagos" aria-labelledby="mat-t">
    <div class="wrap">
      {mat_html}
    </div>
  </section>

  <section class="sec" id="atsiliepimai" aria-labelledby="rev-t">
    <div class="wrap">
      <div class="top">
        <h2 class="h2 rv" id="rev-t">Atsiliepimai</h2>
        <p class="top__link rv" style="--d:120ms"><a class="link" href="{b['facebook_reviews']}" target="_blank" rel="noopener">Visi atsiliepimai „Facebook“{ARROW}</a></p>
      </div>
      <ul class="cols rev__list" role="list" data-stagger="90">
        {rev}
      </ul>
    </div>
  </section>

  <section class="sec sec--ct" id="kontaktai" aria-labelledby="ct-t">
    <div class="wrap split">
      <div class="split__head">
        <h2 class="h2 rv" id="ct-t">Kontaktai</h2>
        <p class="lead rv" style="--d:120ms">{e(CONTACT['text'])}</p>
      </div>
      <div class="ct rv" style="--d:200ms">
        <p class="ct__tel"><a href="{b['phone_href']}">{b['phone']}</a></p>
        <p class="ct__note">{e(CONTACT['hours'])}</p>
        <p class="ct__mail"><a href="mailto:{b['email']}">{b['email']}</a></p>
        <dl class="ct__dl">
          <div><dt>Socialiniai tinklai</dt><dd><a class="link" href="{b['facebook']}" target="_blank" rel="noopener">Facebook</a> <a class="link" href="{b['instagram']}" target="_blank" rel="noopener">Instagram</a></dd></div>
          <div><dt>Dirbame</dt><dd>{e(CONTACT['cities'])}</dd></div>
        </dl>
      </div>
    </div>
  </section>
</main>

<footer class="ft">
  <div class="wrap ft__in">
    <p>© 2026 {e(b['legal'])} · Įmonės kodas {b['code']}</p>
  </div>
</footer>

<dialog class="lb" aria-label="Nuotraukos" data-lbox>
  <div class="lb__bar">
    <p class="lb__t"><span data-lb-title></span> <span class="lb__c" data-lb-count></span></p>
    <button class="lb__x" type="button" data-lb-close>Uždaryti</button>
  </div>
  <figure class="lb__fig"><img data-lb-img src="data:," width="1200" height="1500" alt="" decoding="async"></figure>
  <div class="lb__nav">
    <button class="lb__b lb__b--prev" type="button" data-lb-prev aria-label="Ankstesnė nuotrauka">{ARROW}</button>
    <button class="lb__b" type="button" data-lb-next aria-label="Kita nuotrauka">{ARROW}</button>
  </div>
</dialog>
<script type="application/json" id="lb-data">{json.dumps(lb, ensure_ascii=False)}</script>
<script type="application/json" id="mat-data">{json.dumps(mat_data, ensure_ascii=False)}</script>
<script src="/js/lenis.min.js" defer></script>
<script src="/js/motion.js" defer></script>
<script src="/js/site.js" defer></script>
</body>
</html>
'''


if __name__ == '__main__':
    (ROOT / 'index.html').write_text(page())
    (ROOT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{BRAND["site"]}/</loc></url>\n</urlset>\n')
    (ROOT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {BRAND["site"]}/sitemap.xml\n')
    print('index.html', len((ROOT / 'index.html').read_text()), 'B;', len(list((ROOT / 'img/w').glob('*.webp'))), 'webp')
