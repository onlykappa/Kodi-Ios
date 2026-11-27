"""720pStream (listing and links) and its embedsports.me player (stream address), read by us.

Port of the JetExtractors P720Stream and Embedstream scrapers (MIT, (c) 2020 t4ils) with our own fetching; nothing here
imports The Loop or JetExtractors. The player handshake follows what embedsports.me serves today (SecKeyPlayerConfig,
and the older template page); the site can change it at any time, in which case resolve() raises and the source is
simply absent. A playlist is only reported after it answers with #EXTM3U."""
import base64
import html as htmllib
import json
import re
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

HOST = '720pstream.cx'
BASE = 'https://' + HOST
NAME = 'Independent720pStream'
EMBED_HOST = 'embedsports.me'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
CATEGORIES = {'nfl-online': 'NFL', 'nhl-online': 'NHL', 'nba-online': 'NBA', 'mlb-online': 'MLB', 'ncaaf-online': 'CFB',
              'ncaam-online': 'CBB', 'mma-online': 'MMA', 'boxing-online': 'BOXING', 'soccer-online': 'SOCCER'}
EMBED_HOSTS = (EMBED_HOST, 'sportsframe.me')   # the page's player moved from the first to the second in 2026-11; both use one player family
FRAME = re.compile(r'<iframe[^>]+src=["\'](https://(?:embedsports\.me|sportsframe\.me)/[^"\']+)["\']')


def make_get():
    """get(url, headers=None) -> (status, final address, text); one cookie jar per resolution."""
    from sports_independent import PublicRedirect, public_url
    opener = build_opener(PublicRedirect(), HTTPCookieProcessor(CookieJar()))

    def get(url, headers=None, timeout=8, data=None):
        if not public_url(url):
            raise ValueError('invalid source address')
        request = Request(url, data=data, headers=dict({'User-Agent': UA}, **(headers or {})))
        try:
            with opener.open(request, timeout=timeout) as response:
                return response.status, response.geturl(), response.read(1024 * 1024).decode('utf-8', 'replace')
        except Exception as error:
            status = getattr(error, 'code', None)
            if isinstance(status, int):
                return status, url, ''
            raise
    return get


def b64(value):
    return base64.b64decode(value + '=' * (-len(value) % 4)).decode()


class P720Stream:
    name = NAME

    def __init__(self, get=None, slugs=None):
        self.get, self.slugs = get, slugs or list(CATEGORIES)

    def get_items(self):
        from sports_independent import Link
        get = self.get or make_get()
        items, failures = [], 0
        for slug in self.slugs:
            try:
                status, _, page = get('%s/%s' % (BASE, slug), {'Referer': BASE + '/'})
            except Exception:
                failures += 1
                continue
            if status != 200:
                failures += 1
                continue
            league = CATEGORIES.get(slug, slug.upper())
            for href, inner in re.findall(r'<a class="match-card" href="([^"]+)">(.*?)</a>', page, re.S):
                if not href.startswith('/'):
                    continue
                shown = re.search(r'<div class="match-time">\s*<span>([^<]+)</span>', inner)
                when = ' '.join(shown.group(1).split()) if shown else ''
                teams = re.search(r'<div class="match-teams">(.*?)</div>', inner, re.S)
                title = ' '.join(htmllib.unescape(re.sub(r'<[^>]+>', ' ', teams.group(1))).split()) if teams else ''
                if not title or '24/7' in when:
                    continue
                start = None
                if re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC', when):
                    start = datetime.strptime(when, '%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                items.append(SimpleNamespace(title=title, links=[Link(BASE + href)], starttime=start,
                                             status='LIVE' if 'class="live-badge"' in inner else '', league=league))
        if not items and failures == len(self.slugs):
            raise RuntimeError('720pStream did not answer')
        return items


def player_stream(page_address, get, note=lambda message: None, referer=BASE + '/'):
    """(playlist address, headers) from an embedsports.me or sportsframe.me page address."""
    status, _, text = get(page_address, {'Referer': referer, 'Origin': BASE})
    if status != 200:
        raise RuntimeError('embed page answered %s' % status)
    site = re.search(r'siteConfig\s*=\s*(\{.*?\});', text, re.S)
    loader = re.search(r'<script[^>]+embed\w*\.min\.js[^>]*>', text)
    if not site or not loader:
        raise RuntimeError('embed page has no player configuration')
    config = json.loads(site.group(1))
    attrs = dict(re.findall(r'(data-[a-z]+)="([^"]+)"', loader.group(0)))
    host, category = attrs.get('data-pldm'), attrs.get('data-gc', 'sports')
    if not host or not attrs.get('data-pid') or not attrs.get('data-play'):
        raise RuntimeError('embed page has no player attributes')
    fields = {'pid': attrs['data-pid'], 'vimg': attrs['data-play'], 'player': attrs.get('data-player', 'jw'), 'csrf': config['csrf'],
              'csrf_ip': config['csrf_ip'], 'expires': config['sec_expires'], 'sec_hash': config['sec_hash']}
    origin = 'https://' + host
    embed_origin = 'https://' + urlsplit(page_address).hostname
    if re.search(r'embedv\d+\.min\.js', loader.group(0)):
        # Player loader v4 (2026-11): the page posts the settings as a base64 JSON form field to /vimpl/<category>.
        player = '%s/vimpl/%s' % (origin, category)
        payload = base64.b64encode(json.dumps(fields, separators=(',', ':')).encode()).decode()
        status, _, ptext = get(player, {'Referer': page_address, 'Origin': embed_origin, 'Content-Type': 'application/x-www-form-urlencoded'},
                               data=urlencode({'payload': payload}).encode())
    else:
        fields['v'] = fields.pop('vimg')
        player = 'https://%s/sd0embed/%s?%s' % (host, category, urlencode(fields))
        status, _, ptext = get(player, {'Referer': page_address, 'Origin': embed_origin})
    if status != 200:
        raise RuntimeError('player page answered %s' % status)
    if 'SecKeyPlayerConfig' not in ptext:
        raise RuntimeError('player page is not the supported kind')
    found = re.search(r'window\.SecKeyPlayerConfig\["[^"]+"\]\s*=\s*(\{.*?\})\s*;', ptext, re.S)
    if not found:
        raise RuntimeError('player configuration missing')
    cfg = json.loads(found.group(1))
    source, token, token_url = cfg.get('urlSource'), cfg.get('csrf_token'), cfg.get('secTokenUrl')
    if not source or not token or not token_url:
        raise RuntimeError('player configuration incomplete')
    auth = b64(token_url).rstrip('/') + '/?' + urlencode({'scode': cfg.get('sCode', ''), 'stream': cfg.get('strUnqId', ''), 'expires': cfg.get('expireTs', ''),
                                                          'u_id': cfg.get('device_id', ''), 'session_id': cfg.get('session_id', ''), 'host_id': cfg.get('edgeHostId', '')})
    status, _, body = get(auth, {'Accept': 'application/json', 'X-CSRF-Auth': b64(token), 'Origin': origin, 'Referer': player})
    if status != 200:
        raise RuntimeError('player authorisation answered %s' % status)
    try:
        device = json.loads(body).get('device_id') or cfg.get('device_id')
    except ValueError:
        raise RuntimeError('player authorisation was not JSON')
    if not device:
        raise RuntimeError('player authorisation gave no device')
    parts = urlsplit(source.replace('\\/', '/'))
    values = dict(parse_qsl(parts.query))
    values['u_id'] = device
    playlist = urlunsplit(parts._replace(query=urlencode(values)))
    headers = {'Referer': player, 'Origin': origin, 'User-Agent': UA}
    status, _, manifest = get(playlist, headers)
    if status != 200 or not manifest.lstrip().startswith('#EXTM3U'):
        raise RuntimeError('playlist answered %s' % status)
    note('720pstream: verified HLS playlist')
    return playlist, headers


def resolve(address, note=lambda message: None, get=None):
    get = get or make_get()
    parts = urlsplit(address)
    if parts.scheme != 'https' or parts.hostname not in (HOST, 'www.' + HOST):
        raise ValueError('invalid game address')
    status, _, page = get(address, {'Referer': BASE + '/'})
    frames = []
    for frame in FRAME.findall(page if status == 200 else ''):
        if frame not in frames:
            frames.append(frame)
    note('720pstream: %d embed pages' % len(frames))
    for frame in frames[:4]:
        try:
            return player_stream(frame, get, note, address)
        except Exception as error:
            note('720pstream: embed failed (%s)' % error)
    raise RuntimeError('no verified HLS stream available')
