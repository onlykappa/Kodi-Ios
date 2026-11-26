"""First-party torrent-site search that needs no add-on (roadmap step 5). Plain Python, no Kodi imports.

One adapter for one site layout (the 1337x list/detail pages that CocoScrapers' 1337x.py also reads, written here from the
page structure, not copied). It only finds torrents: debrid or Elementum still turn a hash into playback, and the site
itself stays an external dependency (a domain or layout change makes it return `unsupported`/`offline`, never a wrong match).

search(request, fetch=...) -> (outcome, candidates). `fetch(url, timeout)` returns page text and raises on failure; tests pass
fixtures, the default uses urllib. Concurrency, time and result counts are bounded; identity is checked by
provider_fallback.verified (the same strict source_match rules as every other route); outcomes are source_contract's.
"""
import html
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, wait

import provider_fallback
import source_contract

PROVIDER = 'local'
DOMAINS = ('https://1337x.to',)
MAX_WORKERS = 3
MAX_DETAIL = 8            # detail pages (one per magnet) per search
MAX_PAGE_BYTES = 1 << 20
FETCH_SECONDS = 7
TOTAL_SECONDS = 20
MIN_SEEDERS = 1
SEARCH = {'movie': '/sort-category-search/%s/Movies/size/desc/1/', 'episode': '/sort-category-search/%s/TV/size/desc/1/'}
ROW = re.compile(r'<tr\b[^>]*>(.*?)</tr>', re.S | re.I)
CELL = re.compile(r'<td\b([^>]*)>(.*?)</td>', re.S | re.I)
LINK = re.compile(r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S | re.I)
MAGNET = re.compile(r'href\s*=\s*["\'](magnet:\?[^"\']+)["\']', re.I)
HASH = re.compile(r'urn:btih:([0-9a-fA-F]{40}|[A-Za-z2-7]{32})', re.I)
SIZE = re.compile(r'([\d.,]+)\s*(KB|MB|GB|TB)', re.I)
UNITS = {'kb': 1 << 10, 'mb': 1 << 20, 'gb': 1 << 30, 'tb': 1 << 40}


def _text(fragment):
    return html.unescape(re.sub(r'<[^>]+>', '', fragment)).strip()


def query(request):
    """Search words: the title, then SxxEyy for an episode or the year for a film."""
    exp = provider_fallback.expected(request)
    title = (exp.get('titles') or [''])[0]
    title = re.sub(r'[^A-Za-z0-9\s.-]+', '', title.replace('&', 'and')).strip()
    if request.get('media_type') == 'episode':
        return '%s S%02dE%02d' % (title, int(exp['season']), int(exp['episode']))
    return '%s %s' % (title, exp.get('year') or '')


def parse_list(page, base):
    """Rows of a results page -> [{'name','detail','seeders','size'}]. A page with no results table raises ValueError
    ('layout changed') so an empty result and a broken parser are never confused."""
    if not isinstance(page, str) or '<tbody' not in page.lower():
        raise ValueError('no results table')
    items = []
    for row in ROW.findall(page.split('<tbody', 1)[1]):
        cells = CELL.findall(row)
        if len(cells) < 5:
            continue
        links = LINK.findall(cells[0][1])
        names = [(h, t) for h, t in links if '/torrent/' in h]
        if not names:
            continue
        href, label = names[0]
        name = _text(label)
        if not name or '__cf_email__' in label:
            continue
        try:
            seeders = int(_text(cells[1][1]).replace(',', ''))
        except ValueError:
            seeders = 0
        match = SIZE.search(_text(cells[4][1]))
        size = float(match.group(1).replace(',', '')) * UNITS[match.group(2).lower()] if match else 0
        detail = urllib.parse.urljoin(base, href)
        if urllib.parse.urlsplit(detail).netloc != urllib.parse.urlsplit(base).netloc:
            continue                      # a result may never send us to another host
        items.append({'name': name, 'detail': detail, 'seeders': seeders, 'size': size})
    return items


def parse_detail(page):
    """Magnet link and info hash from a detail page, or None."""
    found = MAGNET.search(page or '')
    if not found:
        return None
    magnet = html.unescape(found.group(1))
    digest = HASH.search(magnet)
    if not digest:
        return None
    return {'torrent_hash': digest.group(1).lower() if len(digest.group(1)) == 40 else digest.group(1), 'magnet': magnet.split('&tr=')[0]}


def default_fetch(url, timeout):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(MAX_PAGE_BYTES).decode('utf-8', 'replace')


def search(request, fetch=default_fetch, cancel=None, timeout=TOTAL_SECONDS, clock=time.monotonic, domains=DOMAINS):
    """Returns (outcome, candidates). Candidates are normalized and identity-verified; magnets stay in-memory only."""
    if not provider_fallback.eligible(request):
        return source_contract.UNSUPPORTED, []
    deadline = clock() + max(0, float(timeout))
    last = source_contract.OFFLINE
    for base in domains:
        try:
            if cancel and cancel():
                raise provider_fallback.Canceled('canceled')
            path = SEARCH[request['media_type']] % urllib.parse.quote(query(request))
            left = max(.5, min(FETCH_SECONDS, deadline - clock()))
            rows = parse_list(fetch(base + path, left), base)
        except Exception as error:
            last = source_contract.classify(error)
            if last == source_contract.CANCELED:
                return last, []
            continue
        rows = [r for r in rows if r['seeders'] >= MIN_SEEDERS]
        # Cheap identity check on the name first, so detail pages are only fetched for plausible rows.
        plausible = provider_fallback.verified([{'name': r['name'], 'url': 'https://x.invalid/', 'size': r['size'], 'seeders': r['seeders']} for r in rows], request, PROVIDER)
        names = {c['name'] for c in plausible}
        rows = [r for r in rows if r['name'] in names]
        rows.sort(key=lambda r: -r['seeders'])
        rows = rows[:MAX_DETAIL]
        if not rows:
            return source_contract.EMPTY, []
        found = []
        pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        try:
            jobs = {pool.submit(fetch, r['detail'], max(.5, min(FETCH_SECONDS, deadline - clock()))): r for r in rows}
            done, pending = wait(jobs, timeout=max(0, deadline - clock()))
            for job in pending:
                job.cancel()
            for job in done:
                row = jobs[job]
                try:
                    detail = parse_detail(job.result())
                except Exception:
                    continue
                if detail:
                    found.append(dict(row, **detail, resolver=None))
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        if cancel and cancel():
            return source_contract.CANCELED, []
        candidates = provider_fallback.verified([{'name': r['name'], 'torrent_hash': r['torrent_hash'], 'magnet': r['magnet'], 'size': r['size'], 'seeders': r['seeders']} for r in found], request, PROVIDER)
        if candidates:
            return source_contract.OK, [source_contract.stamp(c) for c in candidates]
        return (source_contract.TIMEOUT if pending else source_contract.EMPTY), []
    return last, []
