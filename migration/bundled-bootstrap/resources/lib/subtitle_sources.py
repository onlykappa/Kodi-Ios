"""Subtitles for every movie and episode (owner, 2026-11-12: "Ensure we have a system for all shows and movies").

Podnapisi (the only source until build 280) stopped resolving: owner log 94605e4b asked Cloudflare (1.1.1.1, 1.0.0.1)
and Google (8.8.8.8) over HTTPS for www.podnapisi.net, IPv4 and IPv6, and none had an address. The reliable services
today need a free key, so the app asks, in order:

- SubDL (subdl.com; free key: 2,000 searches and 50 downloads a day): GET https://api.subdl.com/api/v1/subtitles with
  api_key, film_name or tmdb_id, type movie|tv, season_number/episode_number, year, languages (EN, ES...); the answer
  has subtitles[] {release_name, name, lang, url, season, episode, hi}; the file is the zip at https://dl.subdl.com<url>.
- OpenSubtitles (opensubtitles.com; free API key, 5 downloads a day, 20 with a free account): GET
  https://api.opensubtitles.com/api/v1/subtitles (Api-Key and User-Agent headers; query parameters in alphabetical
  order, lower case, or the API redirects) with query or tmdb_id/parent_tmdb_id, season_number, episode_number, year,
  languages; data[].attributes {release, language, hearing_impaired, files[{file_id, file_name}]}; POST /download
  {file_id} answers {link, remaining}; the link is the subtitle file itself.
- Podnapisi is no longer asked (it does not resolve; each search waited 32 s for it, owner log 20b1ca76).

Keys live only on the phone (profile/addon_data/service.kodi.ios.bootstrap/subtitle-keys.json), never in Git. A
search runs every source that has a key, ranks all results together against the playing file (track_menu.rank) and
the best one is downloaded; when it fails, the next one is tried. These API shapes come from the services' public
documentation; this sandbox cannot reach either site, so the phone's log ('Kodi iOS subtitles' lines) is the check.
"""
import json
import os
import urllib.parse

import track_menu as tm

SUBDL = 'https://api.subdl.com/api/v1/subtitles'
SUBDL_FILES = 'https://dl.subdl.com'
OPENSUBS = 'https://api.opensubtitles.com/api/v1'
UA = 'KodiIOS v1.0'
KEYS_FILE = 'subtitle-keys.json'
KEY_NAMES = ('subdl', 'opensubtitles', 'opensubtitles_user', 'opensubtitles_password')


def load_keys(folder):
    try:
        with open(os.path.join(folder, KEYS_FILE), encoding='utf-8') as f:
            data = json.load(f)
        return {k: str(data.get(k) or '').strip() for k in KEY_NAMES}
    except (OSError, ValueError, AttributeError):
        return {k: '' for k in KEY_NAMES}


def save_keys(folder, keys):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, KEYS_FILE)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump({k: str(keys.get(k) or '').strip() for k in KEY_NAMES}, f)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def sources(keys):
    """The sources a search uses, best first."""
    out = []
    if keys.get('subdl'):
        out.append('subdl')
    if keys.get('opensubtitles'):
        out.append('opensubtitles')
    # Podnapisi is no longer asked: its name does not resolve anywhere, and each search waited 32 s for it to fail
    # (owner log 20b1ca76).
    return out


# --- SubDL -----------------------------------------------------------------------------------------------------------
def subdl_url(key, lang, title, year=None, season=None, episode=None, tmdb_id=None):
    q = {'api_key': key, 'languages': lang.upper(), 'subs_per_page': 30}
    if tmdb_id:
        q['tmdb_id'] = tmdb_id
    else:
        q['film_name'] = title
    if season and episode:
        q.update(type='tv', season_number=int(season), episode_number=int(episode))
    else:
        q['type'] = 'movie'
        if year:
            q['year'] = int(year)
    return SUBDL + '?' + urllib.parse.urlencode(q)


def subdl_parse(body, lang, season=None, episode=None):
    try:
        data = json.loads(body if isinstance(body, str) else body.decode('utf-8', 'replace'))
    except ValueError:
        return []
    if not isinstance(data, dict) or data.get('status') is False:
        return []
    out = []
    for s in data.get('subtitles') or []:
        url = s.get('url')
        if not url:
            continue
        if s.get('lang') and str(s['lang']).lower()[:2] != lang:
            continue
        # A season pack's zip has every episode; only take one that is this episode (or a whole-season pack).
        if season and episode and s.get('episode') not in (None, '', 0, '0') and str(s.get('episode')) != str(int(episode)):
            continue
        releases = [str(r) for r in ([s.get('release_name')] + list(s.get('releases') or []) + [s.get('name')]) if r]
        out.append({'source': 'subdl', 'id': url, 'releases': releases, 'impaired': bool(s.get('hi'))})
    return out


def subdl_fetch(get, result, season=None, episode=None):
    return tm.subtitle_from_zip(get(SUBDL_FILES + result['id']), season, episode)


# --- OpenSubtitles ---------------------------------------------------------------------------------------------------
def os_headers(keys, token=''):
    h = {'Api-Key': keys['opensubtitles'], 'User-Agent': UA, 'Accept': 'application/json'}
    if token:
        h['Authorization'] = 'Bearer ' + token
    return h


def os_url(lang, title, year=None, season=None, episode=None, tmdb_id=None):
    q = {'languages': lang}
    if season and episode:
        q.update(season_number=int(season), episode_number=int(episode))
        if tmdb_id:
            q['parent_tmdb_id'] = tmdb_id
        else:
            q['query'] = title.lower()
        q['type'] = 'episode'
    else:
        if tmdb_id:
            q['tmdb_id'] = tmdb_id
        else:
            q['query'] = title.lower()
        q['type'] = 'movie'
        if year:
            q['year'] = int(year)
    # The API redirects unless the parameters are sorted and lower case.
    return OPENSUBS + '/subtitles?' + urllib.parse.urlencode(sorted(q.items()))


def os_parse(body, lang):
    try:
        data = json.loads(body if isinstance(body, str) else body.decode('utf-8', 'replace'))
    except ValueError:
        return []
    out = []
    for d in (data or {}).get('data') or []:
        a = d.get('attributes') or {}
        if a.get('language') and str(a['language']).lower()[:2] != lang:
            continue
        files = a.get('files') or []
        if not files or not files[0].get('file_id'):
            continue
        releases = [str(r) for r in (a.get('release'), files[0].get('file_name')) if r]
        out.append({'source': 'opensubtitles', 'id': str(files[0]['file_id']), 'releases': releases,
                    'impaired': bool(a.get('hearing_impaired'))})
    return out


def os_token(post, keys):
    """A user token when the owner saved an OpenSubtitles account (20 downloads a day instead of 5), else ''."""
    if not (keys.get('opensubtitles_user') and keys.get('opensubtitles_password')):
        return ''
    try:
        answer = json.loads(post(OPENSUBS + '/login', json.dumps({'username': keys['opensubtitles_user'],
                                                                   'password': keys['opensubtitles_password']}).encode(),
                                 dict(os_headers(keys), **{'Content-Type': 'application/json'})).decode('utf-8', 'replace'))
        return answer.get('token') or ''
    except Exception:
        return ''


def os_fetch(get, post, keys, result):
    token = os_token(post, keys)
    answer = json.loads(post(OPENSUBS + '/download', json.dumps({'file_id': int(result['id'])}).encode(),
                             dict(os_headers(keys, token), **{'Content-Type': 'application/json'})).decode('utf-8', 'replace'))
    link = answer.get('link')
    if not link:
        raise ValueError('OpenSubtitles gave no download link (%s left today)' % answer.get('remaining', '?'))
    data = get(link)
    name = urllib.parse.urlsplit(link).path.rsplit('/', 1)[-1] or 'subtitle.srt'
    if not name.lower().endswith(('.srt', '.ass', '.ssa', '.vtt', '.sub')):
        name += '.srt'
    return name, data


# --- all together ----------------------------------------------------------------------------------------------------
def find(get, keys, lang, title, year=None, season=None, episode=None, filename='', tmdb_id=None, log=lambda m: None):
    """Ranked results from every source with a key. get(url, headers) -> bytes. A source that fails is logged and
    skipped; raises only when every source failed (so the menu can say the sites did not answer)."""
    results, errors = [], []
    for source in sources(keys):
        try:
            if source == 'subdl':
                found = subdl_parse(get(subdl_url(keys['subdl'], lang, title, year, season, episode, tmdb_id), None), lang, season, episode)
                if not found and tmdb_id:
                    found = subdl_parse(get(subdl_url(keys['subdl'], lang, title, year, season, episode), None), lang, season, episode)
            elif source == 'opensubtitles':
                found = os_parse(get(os_url(lang, title, year, season, episode, tmdb_id), os_headers(keys)), lang)
                if not found and tmdb_id:
                    found = os_parse(get(os_url(lang, title, year, season, episode), os_headers(keys)), lang)
            else:
                found = [dict(r, source='podnapisi') for r in tm.find(lambda url: get(url, None), lang, title, year, season, episode, filename)]
            log('%s: %d found' % (source, len(found)))
            results += found
        except Exception as error:
            log('%s: %s' % (source, type(error).__name__))
            errors.append(error)
    if not results and errors and len(errors) == len(sources(keys)):
        raise errors[0]
    return tm.rank(results, filename)


def fetch(get, post, keys, result, season=None, episode=None):
    """(file name, bytes) of one result, or None."""
    if result.get('source') == 'subdl':
        return subdl_fetch(lambda url: get(url, None), result, season, episode)
    if result.get('source') == 'opensubtitles':
        return os_fetch(lambda url: get(url, None), post, keys, result)
    return tm.fetch(lambda url: get(url, None), result)
