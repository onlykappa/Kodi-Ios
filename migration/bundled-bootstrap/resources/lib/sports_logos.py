"""League logos for the Sports pages (owner: "I want the real logos, not just letters").

Never committed (check_project rejects images; APPLE-UI-POLICY section 5.4: artwork comes from providers at runtime). The
phone fetches each league's logo from ESPN's public image host the first time a page shows it and keeps it in
addon_data/.../sports-logos/. A league without a logo (boxing has none) gets '' and the page draws a neutral ring on the
same light tile, never letters. Pure apart from the network fetch, which tests replace.
"""
import os
import re
import urllib.request

TEAMLOGOS = 'https://a.espncdn.com/i/teamlogos/leagues/500/%s.png'
SOCCER = 'https://a.espncdn.com/i/leaguelogos/soccer/500/%s.png'
# code -> logo address, checked against ESPN's host on 2026-11-19 (every league sports_espn.LEAGUES lists, plus UFC, F1, PGA, LPGA, WWE)
URLS = {
    'NFL': TEAMLOGOS % 'nfl', 'NBA': TEAMLOGOS % 'nba', 'WNBA': TEAMLOGOS % 'wnba', 'MLB': TEAMLOGOS % 'mlb',
    'NHL': TEAMLOGOS % 'nhl', 'MLS': TEAMLOGOS % 'mls', 'LPGA': TEAMLOGOS % 'lpga', 'UFC': TEAMLOGOS % 'ufc',
    'F1': TEAMLOGOS % 'f1', 'WWE': TEAMLOGOS % 'wwe', 'PGA': TEAMLOGOS % 'pgatour',
    'NCAAF': 'https://a.espncdn.com/redesign/assets/img/icons/NCAASports_Football.png',
    'NCAAB': 'https://a.espncdn.com/redesign/assets/img/icons/NCAASports_MensBasketball.png',
    'EPL': SOCCER % '23', 'LIGA': SOCCER % '15', 'UCL': SOCCER % '2', 'BUN': SOCCER % '10', 'SERA': SOCCER % '12', 'LIG1': SOCCER % '9',
}
MAX_BYTES = 400 * 1024
SAFE = re.compile(r'^[A-Za-z0-9_-]{1,12}$')


def folder(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', 'sports-logos')


def url_for(code):
    return URLS.get(str(code).upper(), '')


def cached(profile, code):
    """The saved file for a league, or ''."""
    if not SAFE.match(str(code)):
        return ''
    target = os.path.join(folder(profile), str(code).upper() + '.png')
    return target if os.path.isfile(target) and os.path.getsize(target) > 100 else ''


def download(url, timeout=8):
    request = urllib.request.Request(url, headers={'User-Agent': 'Kodi/21 (iOS)'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(MAX_BYTES + 1)


def fetch(profile, code, get=download):
    """The league's logo file (downloaded once), or '' when there is none or it cannot be fetched now."""
    if not os.path.isabs(str(profile)):   # an untranslated 'special://…' path (tests, a missing Kodi): never write beside the code
        return ''
    have = cached(profile, code)
    if have:
        return have
    url = url_for(code)
    if not url or not SAFE.match(str(code)):
        return ''
    try:
        data = get(url)
    except Exception:
        return ''
    if not data or len(data) > MAX_BYTES or not data.startswith(b'\x89PNG'):
        return ''
    target = os.path.join(folder(profile), str(code).upper() + '.png')
    os.makedirs(folder(profile), exist_ok=True)
    tmp = target + '.tmp'
    with open(tmp, 'wb') as handle:
        handle.write(data)
    os.replace(tmp, target)
    return target


def paths(profile, codes, get=download):
    """{code: file or ''} for several leagues."""
    return {c: fetch(profile, c, get) for c in codes}


# --- team crests (the game page's hero and the standings): the same rule as the league logos, one file per address -----------------
CREST_HOST = 'https://a.espncdn.com/'


def crest_file(profile, url):
    """Where a team crest from `url` is kept."""
    import hashlib
    return os.path.join(folder(profile), 'crests', hashlib.sha1(str(url).encode()).hexdigest()[:20] + '.png')


def crest(profile, url, get=download):
    """The crest's file (downloaded once), or '' for no address, a host other than ESPN's image host, or a failed download."""
    url = str(url or '')
    if not os.path.isabs(str(profile)) or not url.startswith(CREST_HOST):
        return ''
    target = crest_file(profile, url)
    if os.path.isfile(target) and os.path.getsize(target) > 100:
        return target
    try:
        data = get(url)
    except Exception:
        return ''
    if not data or len(data) > MAX_BYTES or not data.startswith(b'\x89PNG'):
        return ''
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tmp = target + '.tmp'
    with open(tmp, 'wb') as handle:
        handle.write(data)
    os.replace(tmp, target)
    return target


def crests(profile, urls, get=download):
    """{url: file} for the crests that could be had (several at once, so a table does not wait on them one by one)."""
    from concurrent.futures import ThreadPoolExecutor
    urls = [u for u in dict.fromkeys(urls) if u]
    if not urls:
        return {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        found = list(pool.map(lambda u: crest(profile, u, get), urls))
    return {u: f for u, f in zip(urls, found) if f}
