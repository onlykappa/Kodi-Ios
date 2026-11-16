"""Independent StreamsCenter listings and conservative HLS resolution.

Does not import JetExtractors or alter its access checks. An embed is never
reported as playable unless its returned content is an HLS playlist.
"""
import html
import ipaddress
import json
import re
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

BASE = 'https://streamcenter.st'
NAME = 'IndependentStreamsCenter'
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile Safari/604.1'


def public_url(url):
    try:
        parts = urlsplit(url)
        host = (parts.hostname or '').lower()
        if parts.scheme not in ('https', 'http') or not host or host == 'localhost' or host.endswith('.local') or parts.username or parts.password:
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return True
    except ValueError:
        return False


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not public_url(newurl):
            raise ValueError("invalid redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, referer=BASE + '/', timeout=6):
    if not public_url(url):
        raise ValueError('invalid source address')
    request = Request(url, headers={'User-Agent': UA, 'Referer': referer})
    with build_opener(PublicRedirect()).open(request, timeout=timeout) as response:
        final = response.geturl()
        if not public_url(final):
            raise ValueError('invalid redirect')
        data = response.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ValueError('source response too large')
        return final, data.decode('utf-8', 'replace')


class Link:
    def __init__(self, address):
        self.address, self.name, self.links = address, '', False

    def to_dict(self):
        return {'address': self.address}


class StreamsCenter:
    name = NAME

    def __init__(self, get=fetch):
        self.get = get

    def get_items(self):
        _, page = self.get(BASE + '/game-cards/embed')
        items = []
        for block in re.findall(r'<article\b[^>]*class=["\'][^"\']*game-card-row[^"\']*["\'][^>]*>.*?</article>', page, re.I | re.S):
            title = re.search(r'<h3\b[^>]*aria-label=["\']([^"\']+)', block, re.I)
            path = re.search(r'href=["\'](/watch/[^"\']+)', block, re.I)
            if not title or not path:
                continue
            league = re.search(r'<p\b[^>]*class=["\'][^"\']*game-card-league[^"\']*["\'][^>]*>([^<]*)', block, re.I)
            timestamp = re.search(r'<time\b[^>]*datetime=["\']([^"\']+)', block, re.I)
            try:
                start = datetime.fromisoformat(timestamp.group(1).replace('Z', '+00:00')).astimezone().replace(tzinfo=None) if timestamp else None
            except ValueError:
                start = None
            items.append(SimpleNamespace(title=html.unescape(title.group(1)), links=[Link(urljoin(BASE, html.unescape(path.group(1))))],
                         starttime=start, status='LIVE' if 'game-card-status-live' in block else '',
                         league=html.unescape(league.group(1)) if league else ''))
        return items


def source_entries(page):
    # Next.js pages can encode JSON twice inside a flight response.
    page = page.replace('\\"', '"')
    return re.findall(r'\{\s*"id"\s*:\s*"([0-9a-fA-F-]{36})"\s*,\s*"provider"\s*:\s*"([a-zA-Z0-9_-]+)"', page)


def resolve(address, get=fetch):
    parts = urlsplit(address)
    match = re.fullmatch(r'/watch/([A-Za-z0-9_-]+)', parts.path)
    if parts.scheme != 'https' or parts.hostname != 'streamcenter.st' or not match:
        raise ValueError('invalid game address')
    _, page = get(address)
    entries = source_entries(page)
    for source_id, provider in entries[:8]:
        url = BASE + '/api/stream-link/' + quote(provider, safe='') + '/' + quote(match.group(1), safe='') + '/' + quote(source_id, safe='')
        referer = address
        try:
            for _ in range(6):
                final, body = get(url, referer)
                if body.lstrip().startswith('#EXTM3U'):
                    return final, {'User-Agent': UA, 'Referer': referer}
                iframe = re.search(r'<iframe\b[^>]*\bsrc\s*=\s*["\']([^"\']+)', body, re.I)
                candidates = re.findall(r'https?://[^\s"\'<>\\]+\.m3u8(?:\?[^\s"\'<>\\]*)?', body, re.I)
                if iframe:
                    referer, url = final, urljoin(final, html.unescape(iframe.group(1)))
                elif candidates:
                    referer, url = final, html.unescape(candidates[0])
                else:
                    break
        except Exception:
            continue
    raise RuntimeError('no verified HLS stream available')
