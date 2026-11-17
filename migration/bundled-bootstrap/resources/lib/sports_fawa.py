"""Independent FawaNews listings, matched to live schedule data; no JetExtractors import."""
import re
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen
BASE = 'http://www.fawanews.sc/'
NAME = 'IndependentFawaNews'
HEADERS = {'User-Agent': 'Kodi-iOS-Sports/1.0', 'Referer': BASE}


def fetch(url):
    if urlsplit(url).hostname not in ('www.fawanews.sc', 'fawanews.sc'):
        raise ValueError('invalid FawaNews event')
    with urlopen(Request(url, headers=HEADERS), timeout=6) as response:
        return response.read(524288).decode('utf-8', 'replace')


class FawaNews:
    name = NAME

    def get_items(self):
        import sports_jet as sj
        sj.add_module_paths('script.module.beautifulsoup4', sj._folder)
        from bs4 import BeautifulSoup
        import sports_scores, sports_espn, sports_merge
        from sports_independent import Link
        soup = BeautifulSoup(fetch(BASE), 'html.parser')
        schedules = sports_scores.fetch_live([entry[0] for entry in sports_espn.LEAGUES])
        result = []
        for card in soup.find_all('div', class_='user-item'):
            name = card.find(class_='user-item__name'); anchor = card.find('a', href=True)
            if name is None or anchor is None:
                continue
            pair = sj.teams(name.get_text(' ', strip=True))
            raw = anchor['href'].split('?')[0].split('#')[0].strip()
            if not pair or not raw or raw.startswith(('http:', 'https:', '//')):
                continue
            matches = [g for g in schedules if sports_merge.same_team(pair[0], g['away']['name']) and sports_merge.same_team(pair[1], g['home']['name']) or sports_merge.same_team(pair[1], g['away']['name']) and sports_merge.same_team(pair[0], g['home']['name'])]
            if len(matches) != 1:
                continue
            game = matches[0]
            result.append(SimpleNamespace(title=game['away']['name']+' vs '+game['home']['name'], league=game['league_name'], status='LIVE', starttime=datetime.fromtimestamp(game['start']), links=[Link(urljoin(BASE, quote(raw)))]))
        return result


def resolve(address):
    page = fetch(address)
    values = dict(re.findall(r'var\s+d([123])\s*=\s*["\']([^"\']*)["\']', page))
    if set(values) != {'1', '2', '3'}:
        raise RuntimeError('FawaNews has no supported HLS source')
    url = urljoin(BASE, ''.join(values[key] for key in ('1', '2', '3')))
    from sports_independent import public_url
    if not public_url(url):
        raise ValueError('invalid media address')
    import sports_jet as sj
    sj.add_module_paths('script.module.requests', sj._folder)
    from fawa_proxy.util.stream_proxy import get_stream_proxy
    proxy = get_stream_proxy('fawa', HEADERS, options={'strip_png': False, 'prefetch_segments': True, 'upstream_keep_alive': True, 'keep_alive': False, 'proxy_absolute_urls': True})
    return proxy.get_proxy_url(url, HEADERS)
