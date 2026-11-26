"""Independent site adapters and their merge (roadmap step 9). Plain Python, no Kodi imports.

Each adapter is one site family: `plan(request)` -> request URLs, `parse(text, request)` -> rows [{'name','torrent_hash','seeders','size'}].
search_all() asks every applicable adapter at once (bounded), verifies each row with provider_fallback.verified (the same strict identity
rules as every route), merges and de-duplicates by info hash, and reports one typed outcome per site. A failing site never blocks or
changes the others: adapters share no state and no host. The sites stay external dependencies; nothing here talks to a debrid service.

Fixtures in the tests are synthetic pages in each site's documented format, not live responses.
"""
import html
import json
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, wait

import independent_search
import provider_fallback
import source_contract

MAX_ROWS = 40
MAX_WORKERS = 4
HASH = re.compile(r'[0-9a-fA-F]{40}')


def _title(request):
    exp = provider_fallback.expected(request)
    return re.sub(r'[^A-Za-z0-9\s.-]+', '', (exp.get('titles') or [''])[0].replace('&', 'and')).strip(), exp


def _num(value, default=0.0):
    try:
        number = float(value)
        return number if number == number and number >= 0 else default
    except (TypeError, ValueError):
        return default


def _hash(value):
    value = str(value or '').strip().lower()
    return value if HASH.fullmatch(value) and set(value) != {'0'} else ''


# ---- apibay (The Pirate Bay's public JSON API): movies and episodes ----
class Apibay:
    name, host = 'apibay', 'https://apibay.org'

    def applies(self, request):
        return True

    def plan(self, request):
        title, exp = _title(request)
        tail = ('S%02dE%02d' % (int(exp['season']), int(exp['episode']))) if request.get('media_type') == 'episode' else str(exp.get('year') or '')
        return ['%s/q.php?q=%s&cat=0' % (self.host, urllib.parse.quote(('%s %s' % (title, tail)).strip()))]

    def parse(self, text, request):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError('layout changed')
        rows = []
        for item in data[:MAX_ROWS]:
            if not isinstance(item, dict) or 'name' not in item:
                raise ValueError('layout changed')
            found = _hash(item.get('info_hash'))
            if found:                       # the "No results returned" placeholder has an all-zero hash
                rows.append({'name': str(item['name']), 'torrent_hash': found, 'seeders': int(_num(item.get('seeders'))), 'size': _num(item.get('size'))})
        return rows


# ---- YTS public API: movies only ----
class Yts:
    name, host = 'yts', 'https://movies-api.accel.li'

    def applies(self, request):
        return request.get('media_type') == 'movie'

    def plan(self, request):
        title, exp = _title(request)
        term = request.get('imdb') or title
        return ['%s/api/v2/list_movies.json?query_term=%s&limit=20' % (self.host, urllib.parse.quote(str(term)))]

    def parse(self, text, request):
        data = json.loads(text)
        if not isinstance(data, dict) or data.get('status') != 'ok' or not isinstance(data.get('data'), dict):
            raise ValueError('layout changed')
        rows = []
        for movie in (data['data'].get('movies') or [])[:MAX_ROWS]:
            title = re.sub(r'[^A-Za-z0-9\s-]+', '', str(movie.get('title') or '')).strip().replace(' ', '.')
            for torrent in movie.get('torrents') or []:
                found = _hash(torrent.get('hash'))
                quality = str(torrent.get('quality') or '')
                if found and title and movie.get('year'):
                    kind = {'web': 'WEB', 'bluray': 'BluRay'}.get(str(torrent.get('type') or '').lower(), 'WEB')
                    rows.append({'name': '%s.%s.%s.%s.x264-YTS' % (title, movie['year'], quality, kind), 'torrent_hash': found,
                                 'seeders': int(_num(torrent.get('seeds'))), 'size': _num(torrent.get('size_bytes'))})
        return rows


# ---- EZTV JSON API: episodes, looked up by IMDb id ----
class Eztv:
    name, host = 'eztv', 'https://eztvx.to'

    def applies(self, request):
        return request.get('media_type') == 'episode' and bool(re.fullmatch(r'tt\d{5,9}', str(request.get('imdb') or '')))

    def plan(self, request):
        return ['%s/api/get-torrents?imdb_id=%s&limit=100' % (self.host, str(request['imdb'])[2:])]

    def parse(self, text, request):
        data = json.loads(text)
        if not isinstance(data, dict) or not isinstance(data.get('torrents', []), list):
            raise ValueError('layout changed')
        want = (str(request.get('season')), str(request.get('episode')))
        rows = []
        for item in data.get('torrents', [])[:MAX_ROWS * 5]:
            if (str(item.get('season')), str(item.get('episode'))) != want:
                continue                    # the site's own numbers must agree before the name is even looked at
            found = _hash(item.get('hash'))
            name = str(item.get('filename') or item.get('title') or '')
            if found and name:
                rows.append({'name': name, 'torrent_hash': found, 'seeders': int(_num(item.get('seeds'))), 'size': _num(item.get('size_bytes'))})
        return rows


# ---- Knaben public search API: an index over many trackers (an aggregator, not a single site) ----
class Knaben:
    name, host = 'knaben', 'https://api.knaben.org'

    def applies(self, request):
        return True

    def plan(self, request):
        title, exp = _title(request)
        episode = request.get('media_type') == 'episode'
        tail = ('S%02dE%02d' % (int(exp['season']), int(exp['episode']))) if episode else str(exp.get('year') or '')
        query = urllib.parse.quote_plus(('%s %s' % (title, tail)).strip())
        return ['%s/v2/search?dead&o=date&c=%s&q=%s' % (self.host, '2000000' if episode else '3000000', query)]

    def parse(self, text, request):
        data = json.loads(text)
        if not isinstance(data, dict) or not isinstance(data.get('hits'), list):
            raise ValueError('layout changed')
        rows = []
        for item in data['hits'][:MAX_ROWS]:
            if not isinstance(item, dict):
                raise ValueError('layout changed')
            found = _hash(item.get('hash'))
            if found and item.get('title'):
                rows.append({'name': str(item['title']), 'torrent_hash': found, 'seeders': int(_num(item.get('seeders'))), 'size': _num(item.get('bytes'))})
        return rows


UNITS = {'b': 1, 'kb': 1 << 10, 'kib': 1 << 10, 'mb': 1 << 20, 'mib': 1 << 20, 'gb': 1 << 30, 'gib': 1 << 30, 'tb': 1 << 40, 'tib': 1 << 40}


def _size(text):
    found = re.search(r'([\d.,]+)\s*([KMGT]?i?B)\b', str(text or ''), re.I)
    return float(found.group(1).replace(',', '')) * UNITS[found.group(2).lower()] if found else 0.0


def _text(fragment):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', fragment or ''))).strip()


def _words(request):
    """'Title S02E05' for an episode, 'Title 2024' for a film (the query words every HTML site gets)."""
    title, exp = _title(request)
    tail = ('S%02dE%02d' % (int(exp['season']), int(exp['episode']))) if request.get('media_type') == 'episode' else str(exp.get('year') or '')
    return ('%s %s' % (title, tail)).strip()


def _count(match):
    return int(match.group(1).replace(',', '')) if match else 0


class _Html:
    """Shared parts of the HTML list-page families: the page must contain the family's marker or it is `layout changed`."""
    marker = ''

    def applies(self, request):
        return True

    def check(self, text):
        if not isinstance(text, str) or self.marker not in text:
            raise ValueError('layout changed')

    def _rows(self, text, pattern, link_group_hash=1, link_group_name=2):
        rows = []
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.S):
            link = re.search(pattern, row, re.S)
            if not link:
                continue
            found = _hash(link.group(link_group_hash))
            if found:
                rows.append({'name': _text(link.group(link_group_name)), 'torrent_hash': found,
                             'seeders': _count(re.search(r'class="(?:tdseed|green center)">\s*([\d,]+)\s*<', row)),
                             'size': _size((re.search(r'class="(?:tdnormal|nobr center)">\s*([\d.,]+\s*[KMGT]B)', row) or [None, ''])[1])})
        return rows[:MAX_ROWS]


# ---- Bitsearch (captured 2026-11-26): cards with the info hash in the torrent download link ----
class Bitsearch(_Html):
    name, host, marker = 'bitsearch', 'https://bitsearch.eu', 'torrent-result-card'

    def plan(self, request):
        return ['%s/search?limit=100&q=%s' % (self.host, urllib.parse.quote_plus(_words(request)))]

    def parse(self, text, request):
        self.check(text)
        rows = []
        for card in text.split('torrent-result-card')[1:MAX_ROWS + 1]:
            title = re.search(r'<h3[^>]*>.*?<a [^>]*>(.*?)</a>', card, re.S)
            link = re.search(r'/download/torrent/([0-9A-Fa-f]{40})', card) or re.search(r'btih(?:&#x3D;|=|:)([0-9A-Fa-f]{40})', card)
            seeds = re.search(r'<span class="font-medium">\s*([\d,]+)\s*</span>\s*<span>seeders', card)
            size = re.search(r'fa-download"></i>\s*<span>([^<]+)</span>', card)
            if title and link and _hash(link.group(1)):
                rows.append({'name': _text(title.group(1)), 'torrent_hash': _hash(link.group(1)), 'seeders': _count(seeds), 'size': _size(size.group(1)) if size else 0.0})
        return rows


# ---- TorrentDownload (captured 2026-11-26): rows whose link is /<40-hex hash>/<release-name> ----
class TorrentDownload(_Html):
    name, host, marker = 'torrentdownload', 'https://www.torrentdownload.info', 'tt-name'

    def plan(self, request):
        return ['%s/search?q=%s' % (self.host, urllib.parse.quote_plus(_words(request)))]

    def parse(self, text, request):
        self.check(text)
        return self._rows(text, r'<a href="/([0-9A-Fa-f]{40})/[^"]*">(.*?)</a>')


# ---- LimeTorrents (captured 2026-11-26; the .lol host redirects to another domain): hash in the itorrents link ----
class Lime(_Html):
    name, host, marker = 'limetorrents', 'https://www.limetorrents.lol', 'tt-name'

    def plan(self, request):
        return ['%s/search/all/%s/' % (self.host, urllib.parse.quote(re.sub(r'\s+', '-', _words(request))))]

    def parse(self, text, request):
        self.check(text)
        return self._rows(text, r'/torrent/([0-9A-Fa-f]{40})\.torrent[^>]*>\s*</a>\s*<a href="[^"]*">(.*?)</a>')


# ---- Kick4ss (captured 2026-11-26): the hash is inside the URL-encoded magnet of each row ----
class Kick(_Html):
    name, host, marker = 'kick4ss', 'https://kick4ss.com', 'cellMainLink'

    def plan(self, request):
        return ['%s/usearch/%s/' % (self.host, urllib.parse.quote(_words(request)))]

    def parse(self, text, request):
        self.check(text)
        return self._rows(text, r'btih(?:%3A|:)([0-9A-Fa-f]{40}).*?class="cellMainLink">(.*?)</a>')


# ---- Nyaa RSS (captured 2026-11-26): anime releases; the info hash is in the feed ----
class Nyaa:
    name, host = 'nyaa', 'https://nyaa.si'
    NS = '{https://nyaa.si/xmlns/nyaa}'

    def applies(self, request):
        return request.get('media_type') == 'episode'

    def plan(self, request):
        return ['%s/?page=rss&q=%s' % (self.host, urllib.parse.quote_plus(_words(request)))]

    def parse(self, text, request):
        if not isinstance(text, str) or '<rss' not in text[:500]:
            raise ValueError('layout changed')
        if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
            raise ValueError('layout changed')        # no entity tricks in a feed
        rows = []
        for item in ET.fromstring(text).iter('item'):
            found = _hash(item.findtext(self.NS + 'infoHash'))
            title = item.findtext('title')
            if found and title:
                rows.append({'name': _text(title), 'torrent_hash': found, 'seeders': int(_num(item.findtext(self.NS + 'seeders'))), 'size': _size(item.findtext(self.NS + 'size'))})
            if len(rows) >= MAX_ROWS:
                break
        return rows


class Leet:
    """The 1337x list/detail adapter from independent_search, as one more family (its pages are not JSON)."""
    name, host = '1337x', independent_search.DOMAINS[0]

    def applies(self, request):
        return True


SIMPLE = (Apibay(), Yts(), Eztv(), Knaben(), Bitsearch(), TorrentDownload(), Lime(), Kick(), Nyaa())
SITES = tuple(a.name for a in SIMPLE) + (Leet.name,)
# family -> (media, transport, needs, notes): the coverage matrix kept in docs/SOURCE-COVERAGE.md
COVERAGE = {
    'apibay': ('movie+episode', 'public JSON API', 'none', 'remote index'),
    'yts': ('movie', 'public JSON API', 'none', 'remote index'),
    'eztv': ('episode (IMDb id)', 'public JSON API', 'none', 'remote index'),
    'knaben': ('movie+episode', 'public JSON API', 'none', 'aggregator over many trackers'),
    'bitsearch': ('movie+episode', 'HTML list page', 'none', 'remote index'),
    'torrentdownload': ('movie+episode', 'HTML list page', 'none', 'remote index'),
    'limetorrents': ('movie+episode', 'HTML list page (host redirects)', 'none', 'remote index'),
    'kick4ss': ('movie+episode', 'HTML list page', 'none', 'remote index'),
    'nyaa': ('episode (anime)', 'RSS feed', 'none', 'remote index'),
    '1337x': ('movie+episode', 'HTML list + detail pages', 'none', 'remote index; Cloudflare on mirrors'),
}


def _one(adapter, request, fetch, deadline, clock):
    """Rows for one adapter, or raises. Each adapter makes its own requests and nothing else."""
    rows = []
    for url in adapter.plan(request)[:2]:
        text = fetch(url, max(.5, min(independent_search.FETCH_SECONDS, deadline - clock())))
        rows.extend(adapter.parse(text, request))
    return rows


def search_all(request, fetch=independent_search.default_fetch, cancel=None, timeout=independent_search.TOTAL_SECONDS,
               clock=time.monotonic, disabled=()):
    """-> (outcome, candidates, {site: outcome}). `disabled` skips a site entirely (used by tests and a future setting)."""
    if not provider_fallback.eligible(request):
        return source_contract.UNSUPPORTED, [], {}
    deadline = clock() + max(0, float(timeout))
    adapters = [a for a in SIMPLE if a.name not in disabled and a.applies(request)]
    report, found = {}, []
    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    try:
        jobs = {pool.submit(_one, a, request, fetch, deadline, clock): a for a in adapters}
        if '1337x' not in disabled:
            jobs[pool.submit(lambda: independent_search.search(request, fetch=fetch, cancel=cancel, timeout=max(.5, deadline - clock())))] = Leet()
        done, pending = wait(jobs, timeout=max(0, deadline - clock()))
        for job in pending:
            job.cancel()
            report[jobs[job].name] = source_contract.TIMEOUT
        for job in done:
            adapter = jobs[job]
            try:
                result = job.result()
            except Exception as error:
                report[adapter.name] = source_contract.classify(error)
                continue
            if adapter.name == '1337x':
                outcome, items = result
                report[adapter.name] = outcome
                found.extend(items)
                continue
            kept = provider_fallback.verified(result, request, independent_search.PROVIDER)     # seeders must be > 0: the hash is the handle
            report[adapter.name] = source_contract.OK if kept else source_contract.EMPTY
            for item in kept:
                item['magnet'] = 'magnet:?xt=urn:btih:' + item['torrent_hash']
                item['site'] = adapter.name
                found.append(source_contract.stamp(item))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    if cancel and cancel():
        return source_contract.CANCELED, [], report
    best = {}
    for item in found:
        key = str(item.get('torrent_hash') or '').lower()
        if key not in best or (item.get('seeders') or 0) > (best[key].get('seeders') or 0):
            best[key] = item
    merged = sorted(best.values(), key=lambda i: -(i.get('seeders') or 0))
    if merged:
        return source_contract.OK, merged, report
    outcomes = set(report.values())
    if source_contract.EMPTY in outcomes or not outcomes:
        return source_contract.EMPTY, [], report
    for kind in (source_contract.ACCOUNT_REQUIRED, source_contract.REFUSED, source_contract.UNSUPPORTED, source_contract.EXPIRED,
                 source_contract.TIMEOUT, source_contract.OFFLINE):      # the most actionable failure wins, deterministically
        if kind in outcomes:
            return kind, [], report
    return source_contract.OFFLINE, [], report
