# -*- coding: utf-8 -*-
"""Strict check that a torrent / source name is the title that was asked for (Kodi-iOS).

Picking "Fall" (2022) listed torrents of "Fall" (2026): every source route now asks this module first.

  * Burst (script.elementum.burst, patched by scripts/build_customized_ipa.py BURST_PATCHES): every provider's results,
    before Elementum sees them, so Elementum's dialog, its auto-pick ("silent") plays and downloads are verified too.
  * The Deck's "Choose a version" page (deck_picker.py) for Elementum and Umbrella (umbrella_picker.py).

Rules (check()):
  * the parsed title must EQUAL one of the expected titles (title, original title, translations, TMDb alternative
    titles), after normalisation (accents, punctuation, "&"/"and", leading "The", roman numerals); a longer title
    ("Free Fall", "Fall Guy", "It Chapter Two") never matches a shorter one;
  * movies: the year in the name must be the release year; the year before/after only when the release itself
    spans a year boundary (Elementum's per-country years, TMDb premiere/theatrical dates). A name without a year
    passes only when no other film has the same title (TMDb search, cached); otherwise, or when that cannot be
    checked, it is hidden;
  * episodes: show title, then exact season and episode (season packs: the right season; S01-S05 ranges and
    complete series count); a year or country tag (Doctor Who 2005, The Office US) must be the show's when known;
  * an IMDb / TMDb id in a provider's result must be the title's.
Nothing here deletes silently: callers show "N hidden (wrong title/year)" and let it be revealed, and every check is
logged to kodi.log with counts and reasons.

Imported in three places: service.kodi.ios.bootstrap/resources/lib (Umbrella, Burst through sys.path) and
plugin.video.elementum/resources/site-packages/elementum (next to deck_picker.py). Plain Python, no Kodi imports at
module level.
"""
import json
import os
import re
import threading
import time
import unicodedata

VERSION = 1
PROPERTY = 'KodiIOS.SourceMatch'          # Home window: the identity Burst checked, for the version page
FRESH = 1800
CACHE_TTL = 7 * 86400
CACHE_PATH = 'special://profile/addon_data/service.kodi.ios.bootstrap/source_match_cache.json'
TMDB = 'https://api.themoviedb.org/3'
HELPER = 'plugin.video.themoviedb.helper'
YEAR_MIN = 1890
YEAR_MAX = time.gmtime().tm_year + 2

ROMAN = {'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10',
         'xi': '11', 'xii': '12', 'xiii': '13', 'xiv': '14', 'xv': '15', 'xvi': '16', 'xvii': '17', 'xviii': '18',
         'xix': '19', 'xx': '20'}
COUNTRY = {'us': 'US', 'usa': 'US', 'uk': 'GB', 'gb': 'GB', 'au': 'AU', 'nz': 'NZ', 'ca': 'CA', 'ie': 'IE'}
EDITION = set('extended unrated uncut remastered remaster restored directors director dc cut theatrical final special '
              'edition imax criterion collection anniversary version open matte ultimate redux despecialized '
              'colorized hybrid'.split())
TAGS = set(('2160p 1080p 1080i 720p 576p 540p 480p 360p 4k 8k uhd fhd qhd sd hdtv pdtv sdtv hdrip bdrip brrip dvdrip '
            'dvdscr dvd dvd5 dvd9 dvdr bluray blu bd bd25 bd50 bd66 bd100 bdmv remux bdremux web webdl webrip webrp '
            'webhd hdcam cam camrip ts hdts telesync tc telecine scr screener r5 x264 x265 h264 h265 hevc avc xvid '
            'divx av1 vp9 10bit 8bit 12bit hdr hdr10 hdr10plus dv dovi sdr aac aac2 ac3 eac3 dts dtshd dtsx ddp ddp5 '
            'dd5 dd2 atmos truehd flac mp3 opus lpcm proper repack rerip internal limited readnfo nfofix '
            'multi dual dubbed subbed subs hardsub amzn nf dsnp hmax atvp hulu pcok pmtp stan itunes mkv mp4 '
            'avi m2ts iso 3d hsbs hou sbs yify yts rarbg eztv ettv complete season seasons episode episodes '
            'english eng french truefrench vff vfq vf vostfr fr german ger deu ita italian spanish esp spa castellano '
            'latino russian rus ukr hindi tamil telugu korean kor japanese jap jpn chinese chs cht portuguese por '
            'nordic swedish swe danish norwegian finnish dutch polish turkish tur czech cze '
            'hungarian hun greek arabic hebrew thai vietnamese').split())
SEASON_RANGE = [re.compile(r'(?<![a-z0-9])s(\d{1,2})\s*(?:-|to|thru)\s*s?(\d{1,2})(?![0-9]|\s*e\d)'),
                re.compile(r'(?<![a-z0-9])seasons?\s*(\d{1,2})\s*(?:-|to|thru|&|and)\s*(\d{1,2})(?!\d)')]
EPISODE = [re.compile(r'(?<![a-z0-9])s(\d{1,3})\s*e(\d{1,4})(?:-?e(\d{1,4})|\s*-\s*e?(\d{1,4})(?![0-9p]))?(?![0-9])'),
           re.compile(r'(?<![a-z0-9])(\d{1,2})x(\d{2,3})(?![0-9])'),
           re.compile(r'(?<![a-z0-9])season\s*(\d{1,2})\s*episode\s*(\d{1,4})(?!\d)')]
SEASON = [re.compile(r'(?<![a-z0-9])season\s*(\d{1,2})(?!\d)'), re.compile(r'(?<![a-z0-9])s(\d{1,2})(?![0-9])')]
ABSOLUTE = re.compile(r'(?:^|\s)(?:-\s)?(?:e|ep|episode\s?)?(\d{1,4})(?:v\d)?(?=\s|$)')
JUNK_HEAD = re.compile(r'^\s*(?:\[[^\]]*\]|\{[^}]*\}|【[^】]*】|www\.[^\s]+|[a-z0-9-]+\.(?:com|org|net|to|mx|se|io|cc|me|tv|info|lol)(?=[\s\]]))\s*[-:_.]*\s*', re.I)
TOKEN = re.compile(r'[^\W_]+', re.U)
EXT = re.compile(r'\.(?:mkv|mp4|avi|m4v|ts|mov|wmv|iso|m2ts)$', re.I)
IDKEYS = (('imdb', ('imdb', 'imdb_id', 'imdbid')), ('tmdb', ('tmdb', 'tmdb_id', 'tmdbid')))

_lock = threading.Lock()
_cache = {}
_cache_loaded = []


def _s(value):
    return u'' if value is None else (value if isinstance(value, type(u'')) else str(value))


def log(message):
    try:
        import xbmc
        xbmc.log('[Kodi-iOS source check] ' + message, xbmc.LOGINFO)
    except Exception:
        pass


# ---------------------------------------------------------------------------------------------------------------
# names
# ---------------------------------------------------------------------------------------------------------------
def _fold(text):
    text = unicodedata.normalize('NFKD', _s(text).replace(u'ß', u'ss'))
    text = u''.join(c for c in text if not unicodedata.combining(c)).lower()
    text = text.replace(u'&', u' and ')
    return re.sub(u"['’‘`´]", u'', text)


def normalize(text):
    """'The Lord of the Rings: The Two Towers' -> 'lord of the rings the two towers'; 'Rocky V' -> 'rocky 5'."""
    words = [ROMAN.get(w, w) for w in TOKEN.findall(_fold(text))]
    if len(words) > 1 and words[0] == 'the':
        words = words[1:]
    return u' '.join(words)


def title_keys(title):
    norm = normalize(title)
    if not norm:
        return set()
    out = {norm, norm.replace(u' ', u'')}
    out.add(u' '.join(w for w in norm.split() if w != 'and').replace(u' ', u''))
    return out


def _year(token):
    return int(token) if token.isdigit() and len(token) == 4 and YEAR_MIN <= int(token) <= YEAR_MAX else None


def _boundary(token, numbers=False):
    return ((numbers and token.isdigit() and len(token) <= 4) or _year(token) is not None or token in TAGS or token in EDITION or token in COUNTRY
            or re.match(r'^(?:s\d{1,3}(?:e\d{1,4})*|\d{1,2}x\d{2,3}|e\d{1,4}|\d{3,4}p|x26[45]|h26[45])$', token) is not None)


def _clean(name):
    name = _s(name).strip()
    name = EXT.sub(u'', name)
    for _ in range(4):
        new = JUNK_HEAD.sub(u'', name)
        if new == name:
            break
        name = new
    return name


def parse_name(name):
    """{'cuts': [(title_key_set, tail_start)], 'tokens': [...], 'text': folded name} for one release name."""
    text = _fold(_clean(name))
    tokens = [(m.group(0), m.start(), m.end()) for m in TOKEN.finditer(text)]
    return {'text': text, 'tokens': tokens}


def _tail_info(text, tokens, i):
    """Year, country and episode numbering right after the title (tokens[i:])."""
    info = {'year': None, 'country': None, 'season': None, 'episodes': None, 'seasons': None, 'complete': False,
            'absolute': None}
    j = i
    while j < len(tokens):
        w = tokens[j][0]
        if w in COUNTRY and info['country'] is None and info['year'] is None:
            info['country'] = COUNTRY[w]
        elif w in EDITION or (w == 'the' and j + 1 < len(tokens) and tokens[j + 1][0] in EDITION):
            pass
        elif _year(w) is not None and info['year'] is None:
            info['year'] = _year(w)
        else:
            break
        j += 1
    tail = text[tokens[i][1]:] if i < len(tokens) else u''
    tail = u' '.join(re.sub(r'[\s._\[\]()]+', u' ', tail).split())
    for rx in SEASON_RANGE:
        m = rx.search(tail)
        if m and int(m.group(1)) <= int(m.group(2)):
            info['seasons'] = (int(m.group(1)), int(m.group(2)))
            break
    if info['seasons'] is None:
        for rx in EPISODE:
            m = rx.search(tail)
            if m:
                first = int(m.group(2))
                extra = [int(g) for g in m.groups()[2:] if g]
                last = extra[0] if extra and first <= extra[0] <= first + 50 else first
                rest = tail[m.end():]
                more = re.match(r'^(?:-?e\d{1,4})+', rest)          # S08E01E02E03
                if more:
                    last = max([last] + [int(n) for n in re.findall(r'\d+', more.group(0)) if int(n) <= first + 50])
                info['season'], info['episodes'] = int(m.group(1)), (first, last)
                break
    if info['seasons'] is None and info['season'] is None:
        for rx in SEASON:
            m = rx.search(tail)
            if m:
                info['season'] = int(m.group(1))
                break
    if re.search(r'(?<![a-z])(?:complete\s*(?:series|serie|collection|box\s*set)|all\s*seasons)', tail):
        info['complete'] = True
    if info['season'] is None and info['seasons'] is None:
        m = ABSOLUTE.search(tail[:24])
        if m and _year(m.group(1)) is None:
            info['absolute'] = int(m.group(1))
    return info, j


def interpretations(name, keys, numbers=False):
    """Every way the start of the name equals one of the expected title keys: [(tail_info, cut)]."""
    parsed = parse_name(name)
    text, tokens = parsed['text'], parsed['tokens']
    found = []
    for i in range(1, len(tokens) + 1):
        title = normalize(text[:tokens[i - 1][2]])
        if not title:
            continue
        if title in keys or title.replace(u' ', u'') in keys:
            edition = tokens[i][0] == 'the' and i + 1 < len(tokens) and tokens[i + 1][0] in EDITION if i < len(tokens) else False
            if i < len(tokens) and not edition and not _boundary(tokens[i][0], numbers):
                continue                              # the title goes on: "Fall Guy", "Free Fall", "It Chapter Two"
            info, _ = _tail_info(text, tokens, i)
            found.append(info)
    return found, parsed


# ---------------------------------------------------------------------------------------------------------------
# expected identity
# ---------------------------------------------------------------------------------------------------------------
def _int(value):
    try:
        value = int(_s(value).strip()[:4]) if value not in (None, '') else None
        return value if value else None
    except (TypeError, ValueError):
        return None


def expected(kind='movie', titles=(), year=None, years=(), imdb=None, tmdb=None, season=None, episode=None,
             absolute=None, show_year=None, countries=(), label=None):
    """The identity a source must match. kind: movie, episode, season or anime."""
    clean = []
    for t in titles:
        t = _s(t).strip()
        if t and t not in clean:
            clean.append(t)
    exp = {'v': VERSION, 'kind': kind, 'titles': clean, 'year': _int(year),
           'years': sorted(set(y for y in (_int(v) for v in years) if y)), 'imdb': _s(imdb).strip() or None,
           'tmdb': _s(tmdb).strip() or None, 'season': _int(season) if season not in (None, '') else None,
           'episode': _int(episode), 'absolute': _int(absolute), 'show_year': _int(show_year),
           'countries': sorted(set(_s(c).upper() for c in countries if c)), 'others': None, 'label': label or u''}
    if season in (0, '0'):
        exp['season'] = 0
    if not exp['label'] and clean:
        if kind == 'movie':
            exp['label'] = clean[0] + (u' (%d)' % exp['year'] if exp['year'] else u'')
        elif exp['season'] is not None and exp['episode']:
            exp['label'] = u'%s S%02dE%02d' % (clean[0], exp['season'], exp['episode'])
        elif exp['season'] is not None:
            exp['label'] = u'%s season %d' % (clean[0], exp['season'])
        else:
            exp['label'] = clean[0]
    return exp


def allowed_years(exp):
    out = set([exp['year']]) if exp.get('year') else set()
    if exp.get('year'):
        out.update(y for y in exp.get('years') or () if abs(y - exp['year']) == 1)   # release spans New Year
    return out


def all_keys(exp):
    keys = set()
    for t in exp.get('titles') or ():
        keys |= title_keys(t)
    return keys


def from_burst(payload, method):
    """Elementum's search payload (Burst search()) as an identity, or None for a free-text search."""
    if method not in ('movie', 'episode', 'season', 'anime') or not isinstance(payload, dict):
        return None
    titles = [payload.get('title')] + list((payload.get('titles') or {}).values())
    years = (payload.get('years') or {}).values() if isinstance(payload.get('years'), dict) else ()
    if method == 'movie':
        return expected('movie', titles, payload.get('year'), years, payload.get('imdb_id'), payload.get('tmdb_id'))
    return expected(method, titles, None, (), payload.get('imdb_id'), payload.get('show_tmdb_id') or payload.get('tmdb_id'),
                    payload.get('season'), payload.get('episode') if method != 'season' else None,
                    payload.get('absolute_number'))


def from_meta(meta):
    """Umbrella / TMDb Helper item meta as an identity, or None."""
    meta = meta or {}
    aliases = []
    for a in meta.get('aliases') or ():
        aliases.append(a.get('title') if isinstance(a, dict) else a)
    if meta.get('tvshowtitle'):
        titles = [meta.get('tvshowtitle'), meta.get('originaltvshowtitle')] + aliases
        if meta.get('episode') not in (None, ''):
            kind = 'episode'
        else:
            kind = 'season'
        return expected(kind, titles, None, (), meta.get('imdb'), meta.get('tmdb'), meta.get('season'),
                        meta.get('episode') if kind == 'episode' else None, show_year=meta.get('tvshowyear'))
    if not meta.get('title'):
        return None
    years = []
    for key in ('premiered', 'released'):
        if meta.get(key):
            years.append(_s(meta[key])[:4])
    return expected('movie', [meta.get('title'), meta.get('originaltitle')] + aliases, meta.get('year'), years,
                    meta.get('imdb'), meta.get('tmdb'))


# ---------------------------------------------------------------------------------------------------------------
# the check
# ---------------------------------------------------------------------------------------------------------------
def _id_check(exp, result):
    if not isinstance(result, dict):
        return None
    for kind, names in IDKEYS:
        want = exp.get(kind)
        for n in names:
            got = _s(result.get(n)).strip()
            if want and got and got not in ('0', 'None') and got.lower() != want.lower():
                return u'different %s id' % ('IMDb' if kind == 'imdb' else 'TMDb')
    return None


def _check_one(name, exp, keys):
    found, parsed = interpretations(name, keys, exp['kind'] == 'anime')
    if not found:
        return False, u'wrong title'
    kind = exp['kind']
    reasons = []
    for info in found:
        if kind == 'movie':
            if info['season'] is not None or info['seasons'] or (info['episodes']):
                reasons.append(u'an episode, not the film')
                continue
            years = allowed_years(exp)
            if info['year'] is not None:
                if not years or info['year'] in years:
                    return True, u''
                reasons.append(u'wrong year')
                continue
            if not years:
                return True, u''
            if exp.get('others') is False:
                return True, u''
            reasons.append(u'no year, another film has this title' if exp.get('others') else u'no year (cannot verify)')
            continue
        # shows
        if info['country'] and exp.get('countries') and info['country'] not in exp['countries']:
            reasons.append(u'another country\'s show')
            continue
        if info['year'] is not None and exp.get('show_year') and info['year'] != exp['show_year']:
            reasons.append(u'wrong show year')
            continue
        season, episode = exp.get('season'), exp.get('episode')
        if info['seasons']:
            ok = season is None or info['seasons'][0] <= season <= info['seasons'][1]
        elif info['season'] is not None:
            ok = season is None or info['season'] == season
            if ok and kind in ('episode', 'anime') and info['episodes'] and episode:
                ok = info['episodes'][0] <= episode <= info['episodes'][1]
                if not ok:
                    reasons.append(u'wrong episode')
                    continue
        elif info['complete']:
            ok = True
        elif kind == 'anime' and info['absolute'] is not None:
            # Season 2+ with its absolute number known: only that number (S2E13 is "045", never "013").
            ok = (info['absolute'] == exp['absolute'] if exp.get('absolute') and (season or 1) > 1
                  else info['absolute'] in (exp.get('absolute'), episode))
            if not ok:
                reasons.append(u'wrong episode')
                continue
        else:
            reasons.append(u'no season/episode in the name')
            continue
        if ok:
            return True, u''
        reasons.append(u'wrong season')
    return False, (reasons[0] if reasons else u'wrong title')


WHOLE_SERIES = re.compile(r'(?i)complete[ ._-]*series|collection[ ._-]*of[ ._-]*\d{3}|'
                          r'[(\[ ._-]0*1[ ._]*-[ ._]*\d{3}[)\] ._-]|\ball[ ._-]*\d{3}[ ._-]*episodes')


def coverage(name, exp):
    """For a season download (a show, a season, no episode): u'' for a release that holds the season (a pack, a range
    of seasons, a complete series) and u'Episode 3 only' / u'Episodes 1-4 only' for one that holds a few episodes.
    Owner (build 205): "i pressed full season" and got Lanterns S01E01 alone: a season search lists single episodes
    too, and nothing said so. None when this is not a season download or the name says nothing."""
    exp = exp or {}
    if exp.get('kind') == 'movie' or exp.get('episode') or exp.get('season') is None:
        return None
    # Owner (build 252, ISSUE-169): a season search listed files from "Naruto Shippuden (001-500) [Complete Series +
    # Movies]" and "(Collection of 500)" packs as if they were season packs. A whole-series pack is marked, ranked
    # after real season packs and never chosen automatically for a season.
    if WHOLE_SERIES.search(_s(name)):
        return u'Whole series'
    found, _ = interpretations(name, all_keys(exp), exp.get('kind') == 'anime')
    for info in found:
        if info['seasons'] or info['complete'] or (info['season'] is not None and not info['episodes']):
            return u''
        if info['episodes']:
            a, b = info['episodes']
            return u'Episode %d only' % a if a == b else u'Episodes %d-%d only' % (a, b)
    return None


def check(name, exp, result=None):
    """(True, '') when the release name is the expected title, else (False, reason)."""
    if not exp or not exp.get('titles'):
        return True, u''
    bad_id = _id_check(exp, result)
    if bad_id:
        return False, bad_id
    keys = exp.get('_keys') or all_keys(exp)
    ok, reason = _check_one(name, exp, keys)
    if not ok:
        # A release name followed by the file in it ("Pack Name/Show.S01E01.mkv"): the file name may verify it.
        parts = [p for p in re.split(r'[/\\]', _s(name)) if p.strip()]
        if len(parts) > 1:
            ok2, _ = _check_one(parts[-1], exp, keys)
            if ok2:
                return True, u''
        # Owner log fffb3cd8 (build 329): "[uP] Naruto Shippuden - Vol.01 (BDRip …) [uP] Naruto Shippuden - 005 (…).mkv"
        # (the pack's name and its file joined by a space) was hidden as "wrong title", so episode 5 fell back to a 4 GB
        # upscaled copy. A file name that starts again with a [group] tag is checked from there.
        text = _s(parts[-1] if parts else name)
        for at in [m.start() for m in re.finditer(r'\[', text) if m.start() > 0][::-1]:
            ok2, _ = _check_one(text[at:], exp, keys)
            if ok2:
                return True, u''
    return ok, reason


def split(items, exp, name=lambda it: it.get('name'), result=None):
    """(kept, hidden) where hidden is [(item, reason)]; the order is kept."""
    kept, hidden = [], []
    if not exp:
        return list(items), hidden
    exp = dict(exp, _keys=all_keys(exp))
    for it in items:
        try:
            ok, reason = check(name(it), exp, result(it) if result else (it if isinstance(it, dict) else None))
        except Exception as e:                      # a name this cannot read is not a verified one
            ok, reason = False, u'unreadable name (%s)' % e
        if ok:
            kept.append(it)
        else:
            hidden.append((it, reason))
    return kept, hidden


def reasons_text(hidden):
    counts = {}
    for _, reason in hidden:
        counts[reason] = counts.get(reason, 0) + 1
    return u', '.join(u'%s %d' % (r, n) for r, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def report(where, exp, kept, hidden, name=lambda it: it.get('name')):
    msg = u'%s: %s: kept %d, hidden %d' % (where, (exp or {}).get('label') or u'?', len(kept), len(hidden))
    if hidden:
        msg += u' (%s)' % reasons_text(hidden)
        for it, reason in hidden[:15]:
            try:
                msg += u'\n  hidden [%s] %s' % (reason, name(it))
            except Exception:
                pass
    log(msg)
    return msg


# ---------------------------------------------------------------------------------------------------------------
# TMDb (TMDb Helper's key, as drivelibrary.tmdb_key reads it), cached
# ---------------------------------------------------------------------------------------------------------------
def _translate(path):
    try:
        import xbmcvfs
        return xbmcvfs.translatePath(path)
    except Exception:
        return ''


def tmdb_key(paths=None):
    for helper in paths or (_translate('special://home/addons/' + HELPER), _translate('special://xbmc/addons/' + HELPER)):
        try:
            with open(os.path.join(helper, 'resources', 'tmdbhelper', 'lib', 'api', 'api_keys', 'tmdb.py'), encoding='utf-8') as f:
                found = re.search(r"API_KEY\s*=\s*['\"]([0-9a-f]{20,})['\"]", f.read())
            if found:
                return found.group(1)
        except (OSError, TypeError):
            continue
    return ''


def _http(url, timeout=4):
    try:
        from urllib.request import urlopen
    except ImportError:                             # pragma: no cover (Python 2)
        from urllib2 import urlopen
    resp = urlopen(url, timeout=timeout)
    try:
        return resp.read().decode('utf-8')
    finally:
        resp.close()


def _cache_file():
    return _translate(CACHE_PATH)


def _load_cache():
    if _cache_loaded:
        return
    _cache_loaded.append(1)
    path = _cache_file()
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        now = time.time()
        _cache.update((k, v) for k, v in data.items() if now - v.get('t', 0) < CACHE_TTL)
    except Exception:
        pass


def _save_cache():
    path = _cache_file()
    if not path:
        return
    try:
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        with open(path + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(_cache, f)
        os.replace(path + '.tmp', path)
    except Exception:
        pass


def tmdb_get(path, query, key, get=None):
    """TMDb JSON for /path?query (cached a week, without the key), or None when TMDb cannot be reached."""
    try:
        from urllib.parse import urlencode
    except ImportError:                             # pragma: no cover
        from urllib import urlencode
    slot = path + '?' + urlencode(sorted(query.items()))
    with _lock:
        _load_cache()
        if slot in _cache:
            return _cache[slot]['d']
    if not key:
        return None
    try:
        data = json.loads((get or _http)(TMDB + path + '?' + urlencode(sorted(dict(query, api_key=key).items()))))
    except Exception as e:
        log(u'TMDb %s failed: %s' % (path, e))
        return None
    with _lock:
        _cache[slot] = {'t': time.time(), 'd': data}
        _save_cache()
    return data


def _theatrical_years(details):
    years = set()
    for country in ((details.get('release_dates') or {}).get('results') or ()):
        for r in country.get('release_dates') or ():
            if r.get('type') in (1, 2, 3) and _int(r.get('release_date')):
                years.add(_int(r.get('release_date')))
    return years


def enrich(exp, key=None, get=None):
    """Add TMDb's titles (all languages), release years, country and the "another film has this title" answer.
    Never fails: what cannot be fetched is left as it was."""
    if not exp or exp.get('enriched'):
        return exp
    exp = dict(exp)
    key = tmdb_key() if key is None else key
    try:
        if exp['kind'] == 'movie':
            _enrich_movie(exp, key, get)
        else:
            _enrich_show(exp, key, get)
    except Exception as e:
        log(u'TMDb details for %s failed: %s' % (exp.get('label'), e))
    exp['enriched'] = True
    return exp


def _add_titles(exp, titles):
    for t in titles:
        t = _s(t).strip()
        if t and t not in exp['titles']:
            exp['titles'].append(t)


def _enrich_movie(exp, key, get):
    tmdb = exp.get('tmdb')
    primary = exp['titles'][0] if exp['titles'] else u''
    if not tmdb and exp.get('imdb'):
        found = tmdb_get('/find/' + exp['imdb'], {'external_source': 'imdb_id'}, key, get) or {}
        hits = found.get('movie_results') or []
        tmdb = _s(hits[0].get('id')) if hits else None
    if not tmdb and primary:
        query = {'query': primary}
        if exp.get('year'):
            query['year'] = exp['year']
        hits = (tmdb_get('/search/movie', query, key, get) or {}).get('results') or []
        want = title_keys(primary)
        for h in hits:
            if (title_keys(h.get('title')) | title_keys(h.get('original_title'))) & want and \
                    (not exp.get('year') or _int(h.get('release_date')) == exp['year']):
                tmdb = _s(h.get('id'))
                break
    details = tmdb_get('/movie/%s' % tmdb, {'append_to_response': 'alternative_titles,release_dates,translations'}, key, get) if tmdb else None
    if details:
        exp['tmdb'] = _s(details.get('id') or tmdb)
        exp['imdb'] = exp.get('imdb') or details.get('imdb_id') or None
        _add_titles(exp, [details.get('title'), details.get('original_title')])
        _add_titles(exp, [a.get('title') for a in ((details.get('alternative_titles') or {}).get('titles') or ())])
        _add_titles(exp, [(t.get('data') or {}).get('title') for t in ((details.get('translations') or {}).get('translations') or ())])
        if not exp.get('year'):
            exp['year'] = _int(details.get('release_date'))
        exp['years'] = sorted(set(exp.get('years') or ()) | _theatrical_years(details))
    # Is there another film with this exact title? (decides about names without a year)
    if primary:
        hits = tmdb_get('/search/movie', {'query': primary}, key, get)
        if hits is not None:
            want = set()
            for t in [primary] + ([details.get('title'), details.get('original_title')] if details else []):
                want |= title_keys(t)
            others = [h for h in hits.get('results') or ()
                      if (title_keys(h.get('title')) | title_keys(h.get('original_title'))) & want
                      and _s(h.get('id')) != _s(exp.get('tmdb'))
                      and (exp.get('tmdb') or _int(h.get('release_date')) != exp.get('year'))]
            exp['others'] = bool(others)


def _enrich_show(exp, key, get):
    tmdb = exp.get('tmdb')
    if not tmdb and exp.get('imdb'):
        found = tmdb_get('/find/' + exp['imdb'], {'external_source': 'imdb_id'}, key, get) or {}
        hits = found.get('tv_results') or []
        tmdb = _s(hits[0].get('id')) if hits else None
    if not tmdb:
        return
    details = tmdb_get('/tv/%s' % tmdb, {'append_to_response': 'alternative_titles,translations'}, key, get)
    if not details:
        return
    exp['tmdb'] = _s(details.get('id') or tmdb)
    _add_titles(exp, [details.get('name'), details.get('original_name')])
    _add_titles(exp, [a.get('title') for a in ((details.get('alternative_titles') or {}).get('results') or ())])
    _add_titles(exp, [(t.get('data') or {}).get('name') for t in ((details.get('translations') or {}).get('translations') or ())])
    exp['show_year'] = exp.get('show_year') or _int(details.get('first_air_date'))
    # Absolute-numbered anime packs: season N episode E is absolute (episodes of seasons 1..N-1) + E.
    if exp.get('absolute') is None and exp.get('season') and exp.get('episode') and int(exp['season']) > 1:
        counts = {int(x.get('season_number') or 0): int(x.get('episode_count') or 0) for x in details.get('seasons') or ()}
        before = [counts.get(n) for n in range(1, int(exp['season']))]
        if before and all(before):
            exp['absolute'] = sum(before) + int(exp['episode'])
    if not exp.get('countries'):
        exp['countries'] = sorted(set(_s(c).upper() for c in details.get('origin_country') or ()))


# ---------------------------------------------------------------------------------------------------------------
# hand-over between Burst and the version page (Home window property, both run inside Kodi)
# ---------------------------------------------------------------------------------------------------------------
RECENT = PROPERTY + '.Recent'   # the last few identities: Build Season searches three episodes at once
RECENT_KEEP = 8


def publish(exp, hidden=0, revealed=False, window=None, now=None):
    try:
        if window is None:
            import xbmcgui
            window = xbmcgui.Window(10000)
        clean = dict((k, v) for k, v in exp.items() if not k.startswith('_'))
        entry = {'exp': clean, 'time': now or time.time(), 'hidden': hidden, 'revealed': bool(revealed)}
        window.setProperty(PROPERTY, json.dumps(entry))
        # Owner log 77b35834 (build 300): with three episode searches at once the single property held whichever
        # finished last, so episode 1's version page checked its links against episode 3 (ISSUE-178). Each search's
        # identity is kept here too, and published() takes the one for the page's own episode.
        try:
            recent = json.loads(window.getProperty(RECENT) or '[]')
        except ValueError:
            recent = []
        key = lambda e: (e['exp'].get('season'), e['exp'].get('episode'), tuple(e['exp'].get('titles') or ()))
        recent = [e for e in recent if isinstance(e, dict) and e.get('exp') and key(e) != key(entry)][-(RECENT_KEEP - 1):]
        window.setProperty(RECENT, json.dumps(recent + [entry]))
    except Exception:
        pass


def published(dialog_title, window=None, now=None):
    """The identity Burst checked last, when it is recent and its title is in the dialog's title, else None."""
    try:
        if window is None:
            import xbmcgui
            window = xbmcgui.Window(10000)
        now = now or time.time()
        try:
            entries = json.loads(window.getProperty(RECENT) or '[]')
        except ValueError:
            entries = []
        entries = [e for e in entries if isinstance(e, dict) and e.get('exp')]
        latest = json.loads(window.getProperty(PROPERTY) or '{}')
        if latest.get('exp'):
            entries.append(latest)
        heading = u' %s ' % normalize(dialog_title)
        page = page_episode(dialog_title)
        for data in sorted(entries, key=lambda e: -float(e.get('time', 0))):
            if now - float(data.get('time', 0)) > FRESH:
                continue
            exp = data['exp']
            if not any(u' %s ' % normalize(t) in heading for t in exp.get('titles') or () if normalize(t)):
                continue
            # A page for S01E01 never takes S01E03's identity (ISSUE-178).
            if page and exp.get('episode') is not None and (int(exp['episode']) != page[1] or
                                                            (exp.get('season') is not None and int(exp['season']) != page[0])):
                continue
            exp['revealed'] = bool(data.get('revealed'))
            return exp
        # Owner log 8bb997da (build 309): episodes 8 and 9 finished their Burst searches in the same millisecond, both
        # rewrote the shared list and episode 9's entry was lost, so its version page had no identity and the picker
        # asked the owner. The show is the same for every episode: a page naming its episode takes a recent identity
        # of the same show and swaps in the page's season and episode.
        if page:
            for data in sorted(entries, key=lambda e: -float(e.get('time', 0))):
                exp = dict(data['exp'])
                if now - float(data.get('time', 0)) > FRESH or exp.get('episode') is None:
                    continue
                if not any(u' %s ' % normalize(t) in heading for t in exp.get('titles') or () if normalize(t)):
                    continue
                exp.update(season=page[0], episode=page[1], revealed=False, borrowed=True)
                for k in ('label', 'episode_title', 'aired'):
                    exp.pop(k, None)
                return exp
        return None
    except Exception:
        return None


def page_episode(dialog_title):
    """(season, episode) named in a version page's title ("ナルト 疾風伝 S01E05"), else None."""
    found = re.search(r'\bS(\d{1,3})E(\d{1,4})\b', _s(dialog_title), re.I)
    return (int(found.group(1)), int(found.group(2))) if found else None


LABEL_EP = re.compile(r'^(.*?)[\s.:-]*\bS(\d{1,3})E(\d{1,4})\b', re.I)
LABEL_YEAR = re.compile(r'^(.*?)\s*\((\d{4})\)\s*$')


def from_details(dialog_title, window=None, now=None):
    """What the watch menu left for the version page (Deck.Picker.Title/Meta), when it is recent and in the title."""
    try:
        if window is None:
            import xbmcgui
            window = xbmcgui.Window(10000)
        title = _s(window.getProperty('Deck.Picker.Title')).strip()
        stamp = float(window.getProperty('Deck.Picker.Time') or 0)
        if not title or not 0 <= (now or time.time()) - stamp < FRESH:
            return None
        if u' %s ' % normalize(title) not in u' %s ' % normalize(dialog_title):
            return None
        meta = _s(window.getProperty('Deck.Picker.Meta'))
        ep = re.search(r'S(\d{1,3})E(\d{1,4})', meta)
        year = re.search(r'(?<!\d)(\d{4})(?!\d)', meta)
        if ep:
            page = page_episode(dialog_title)
            if page and page != (int(ep.group(1)), int(ep.group(2))):
                return None                                  # left for another episode (ISSUE-178)
            return expected('episode', [title], None, (), season=int(ep.group(1)), episode=int(ep.group(2)))
        return expected('movie', [title], int(year.group(1)) if year else None)
    except Exception:
        return None
