"""Subtitles and Audio menus over the video (owner-approved mockup docs/design/player-subtitles-audio-mockups.html,
round 2: "MONEYYYY code it"). Pure logic, tested without Kodi; tracks.py drives the window (1080i/IOSTrackMenu.xml).

- rows(): Kodi's subtitle or audio streams (Player.GetProperties) as one-line rows: name, a small tag (SDH, FORCED,
  ATMOS, 5.1, COMMENTARY) and the check on the one in use. Subtitles start with "Off".
- Download and apply: no subtitle add-on is installed on the phone (build 223 log), so the app asks Podnapisi
  (podnapisi.net, free, no account) itself: search() by title, year and episode in the owner's subtitle language,
  rank() the results against the playing file's name, download() the best one (a zip with an .srt) and tracks.py
  turns it on with xbmc.Player().setSubtitles(). The API shape (data[].id, releases, custom_releases, movie, flags;
  /subtitles/<id>/download) is the one subliminal's provider uses; this sandbox cannot reach the site, so it is
  checked on the phone.
"""
import io
import json
import re
import urllib.parse
import zipfile

SEARCH = 'https://www.podnapisi.net/subtitles/search/advanced'
DOWNLOAD = 'https://www.podnapisi.net/subtitles/%s/download'
LANGUAGES = {'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'it': 'Italian', 'pt': 'Portuguese',
             'nl': 'Dutch', 'sv': 'Swedish', 'da': 'Danish', 'no': 'Norwegian', 'fi': 'Finnish', 'pl': 'Polish',
             'ru': 'Russian', 'ja': 'Japanese', 'ko': 'Korean', 'zh': 'Chinese', 'ar': 'Arabic', 'tr': 'Turkish',
             'el': 'Greek', 'he': 'Hebrew', 'hi': 'Hindi', 'cs': 'Czech', 'hu': 'Hungarian', 'ro': 'Romanian'}
THREE = {'eng': 'en', 'spa': 'es', 'fre': 'fr', 'fra': 'fr', 'ger': 'de', 'deu': 'de', 'ita': 'it', 'por': 'pt',
         'dut': 'nl', 'nld': 'nl', 'swe': 'sv', 'dan': 'da', 'nor': 'no', 'fin': 'fi', 'pol': 'pl', 'rus': 'ru',
         'jpn': 'ja', 'kor': 'ko', 'chi': 'zh', 'zho': 'zh', 'ara': 'ar', 'tur': 'tr', 'gre': 'el', 'ell': 'el',
         'heb': 'he', 'hin': 'hi', 'cze': 'cs', 'ces': 'cs', 'hun': 'hu', 'rum': 'ro', 'ron': 'ro'}


def language_name(code, name=''):
    """'English' from 'eng' / 'en' (or the stream's own name when it has one)."""
    code = str(code or '').lower().split('-')[0]
    two = THREE.get(code, code if len(code) == 2 else '')
    base = LANGUAGES.get(two) or (str(name).strip() or (code.upper() if code else 'Unknown'))
    return base


def _words(text):
    return str(text or '').lower()


def subtitle_rows(streams, current, enabled):
    """[{'label', 'tag', 'on', 'index'}]: Off first, then each subtitle stream. index None is Off."""
    out = [{'label': 'Off', 'tag': '', 'on': not enabled or not streams, 'index': None}]
    for s in streams or []:
        name = _words(s.get('name'))
        tag = 'FORCED' if s.get('isforced') or 'forced' in name else \
              'SDH' if s.get('isimpaired') or 'sdh' in name or 'hearing' in name or ' cc' in ' ' + name else ''
        if not tag and s.get('downloaded'):
            tag = 'NEW'
        out.append({'label': language_name(s.get('language'), s.get('name')), 'tag': tag,
                    'on': bool(enabled and current is not None and s.get('index') == current), 'index': s.get('index')})
    return out


def channels_tag(s):
    name = _words(s.get('name'))
    if 'commentary' in name:
        return 'COMMENTARY'
    if 'atmos' in name:
        return 'ATMOS'
    ch = int(s.get('channels') or 0)
    return {8: '7.1', 6: '5.1', 2: 'STEREO', 1: 'MONO'}.get(ch, '')


def audio_rows(streams, current):
    return [{'label': language_name(s.get('language'), s.get('name')), 'tag': channels_tag(s),
             'on': s.get('index') == current, 'index': s.get('index')} for s in streams or []]


def seconds_text(value, unit='s'):
    """Kodi's 'Player.SubtitleDelay' / 'AudioDelay' label ('-0.300 s') as '−0.3 s' / '0 ms'."""
    m = re.search(r'-?\d+(?:\.\d+)?', str(value or ''))
    v = float(m.group(0)) if m else 0.0
    if unit == 'ms':
        ms = int(round(v * 1000))
        return '0 ms' if ms == 0 else ('%+d ms' % ms).replace('-', '−')
    return '0.0 s' if abs(v) < 0.05 else ('%+.1f s' % v).replace('-', '−')


def search_url(lang, title, year=None, season=None, episode=None):
    q = {'keywords': title, 'language': lang}
    if season and episode:
        q.update(seasons=int(season), episodes=int(episode), movie_type='tv-series')
    else:
        q['movie_type'] = 'movie'
        if year:
            q['year'] = int(year)
    return SEARCH + '?' + urllib.parse.urlencode(q)


def parse(body, lang):
    """Podnapisi's JSON answer as [{'id', 'releases', 'impaired'}] in the asked language."""
    try:
        data = json.loads(body if isinstance(body, str) else body.decode('utf-8', 'replace'))
    except ValueError:
        return []
    out, seen = [], set()
    for d in (data or {}).get('data') or []:
        pid = d.get('id')
        if not pid or pid in seen:
            continue
        if d.get('language') and str(d['language']).split('-')[0] != lang:
            continue
        seen.add(pid)
        releases = [str(r) for r in (d.get('releases') or []) + (d.get('custom_releases') or []) if r]
        out.append({'id': str(pid), 'releases': releases, 'impaired': 'hearing_impaired' in (d.get('flags') or [])})
    return out


TOKENS = re.compile(r'[a-z0-9]+')
QUALITY = ('2160p', '1080p', '720p', 'web', 'webrip', 'web-dl', 'bluray', 'remux', 'hdtv', 'amzn', 'nf', 'dsnp', 'hmax', 'atvp')


def rank(results, filename):
    """Best match first: the most release-name words shared with the playing file (group and source count most),
    hearing-impaired versions after plain ones."""
    mine = set(TOKENS.findall(_words(filename)))
    group = TOKENS.findall(_words(re.sub(r'\.[a-z0-9]{2,4}$', '', str(filename or ''))))[-1:] if filename else []

    def score(r):
        best = 0
        for rel in r['releases'] or ['']:
            theirs = set(TOKENS.findall(_words(rel)))
            s = len(mine & theirs) + 3 * len(set(group) & theirs) + 2 * len(mine & theirs & set(QUALITY))
            best = max(best, s)
        return (best, 0 if r['impaired'] else 1)
    return sorted(results, key=score, reverse=True)


def subtitle_from_zip(blob):
    """The .srt (or .ass / .ssa / .sub / .vtt) inside Podnapisi's zip: (name, bytes) or None."""
    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        return None
    names = [n for n in z.namelist() if n.lower().endswith(('.srt', '.ass', '.ssa', '.vtt', '.sub'))]
    names.sort(key=lambda n: (not n.lower().endswith('.srt'), len(n)))
    return (names[0].rsplit('/', 1)[-1], z.read(names[0])) if names else None


def find(get, lang, title, year=None, season=None, episode=None, filename=''):
    """Search, then ranked results ([] when nothing). get(url) -> bytes; raises on network trouble."""
    results = parse(get(search_url(lang, title, year, season, episode)), lang)
    if not results and year and not (season and episode):
        results = parse(get(search_url(lang, title, None, season, episode)), lang)
    return rank(results, filename)


def fetch(get, result):
    """(file name, bytes) of one result, or None."""
    return subtitle_from_zip(get(DOWNLOAD % urllib.parse.quote(result['id'])))


CTA = {'idle': 'Download and apply', 'search': 'Searching for %s…', 'download': 'Downloading…',
       'done': 'Downloaded and on', 'none': 'Try again', 'error': 'Try again'}
NOTE = {'none': 'No %s subtitles found for this video.', 'error': 'The subtitle site did not answer. Check the Wi-Fi and try again.'}


def cta(state, language):
    text = CTA.get(state, CTA['idle'])
    return text % language if '%s' in text else text


def note(state, language):
    text = NOTE.get(state, '')
    return text % language if '%s' in text else text
