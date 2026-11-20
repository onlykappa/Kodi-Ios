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

import subtitle_match

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


def _impaired(s):
    name = _words(s.get('name'))
    return bool(s.get('isimpaired') or 'sdh' in name or 'hearing' in name or ' cc' in ' ' + name or 'caption' in name)


def _forced(s):
    return bool(s.get('isforced') or 'forced' in _words(s.get('name')))


def pick(streams, video=None):
    """The subtitle streams worth showing: one per language, never a broken one (owner, 2026-11-20: "there should never be more than
    one English ... I just want the CC version of English", "stop having them show broken subtitles").

    - a stream whose language is unknown (UND) is dropped when any stream names its language;
    - a stream the matcher refused (empty, wrong timing, wrong episode) is dropped;
    - of the rest, each language keeps one: a subtitle the viewer downloaded or added first, then the closed-caption / SDH version, then a full track before a forced (foreign
      parts only) one, then the matcher's order (best first). A language with only a forced track keeps it.
    Each stream keeps its own Kodi index, so choosing a row still selects the right stream."""
    ranked = subtitle_match.rank(streams or [], video) if video is not None else [dict(s) for s in streams or []]
    # A track the matcher found broken goes; one that is merely another language stays (Spanish is Spanish).
    ranked = [s for s in ranked if not s.get('match_rejected') or s.get('match_reason') == 'Different language']
    def lang(s):   # the stream's language, or the one a file name carries ("Show.S01E05.en.srt"), else ''
        return subtitle_match.language(s.get('language')) or subtitle_match._file_language(s.get('filename') or s.get('name') or '') or ''
    known = [s for s in ranked if lang(s)]
    if known:
        ranked = known
    best = {}
    for n, s in enumerate(ranked):
        key = lang(s) or str(s.get('language') or '').lower()
        rank = (not (s.get('downloaded') or s.get('removable')), not _impaired(s), _forced(s), n)   # a subtitle the viewer added wins its language
        if key not in best or rank < best[key][0]:
            best[key] = (rank, s)
    keep = {id(entry[1]) for entry in best.values()}
    return [s for s in ranked if id(s) in keep]


def subtitle_rows(streams, current, enabled, video=None):
    """[{'label', 'tag', 'on', 'index'}]: Off first, then one row per language (pick). index None is Off. The closed-caption version
    of a language is tagged CC."""
    all_streams = list(streams or [])
    streams = pick(all_streams, video)
    # The stream Kodi has on may be one the menu hides (the plain English when CC is shown): its language's row is the one that is on.
    playing = next((s for s in all_streams if s.get('index') == current), None) if current is not None else None
    on_language = (subtitle_match.language(playing.get('language')) if playing else '') or None
    on_index = current if any(s.get('index') == current for s in streams) else next(
        (s.get('index') for s in streams if on_language and subtitle_match.language(s.get('language')) == on_language), None)
    out = [{'label': 'Off', 'tag': '', 'on': not enabled or not streams, 'index': None}]
    for s in streams:
        tag = 'FORCED' if _forced(s) else 'CC' if _impaired(s) else ''
        if not tag and s.get('downloaded'):
            tag = 'NEW'
        row = {'label': language_name(s.get('language'), s.get('name')), 'tag': tag,
               'on': bool(enabled and on_index is not None and s.get('index') == on_index), 'index': s.get('index'),
               'language': s.get('language') or '', 'removable': bool(s.get('removable'))}
        row.update({k: v for k, v in s.items() if k.startswith('match_')})
        row.setdefault('match_reason', 'Timing not checked')
        out.append(row)
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


RELEASE = re.compile(r'(?i)^(.+?)[ ._-]+s(\d{1,2})[ ._-]?e(\d{1,3})\b')


def from_release(text):
    """{'title', 'season', 'episode'} from a release or file name ('phony.s01e01.1080p…'), or None."""
    m = RELEASE.match(re.sub(r'\[[^\]]*\]', '', str(text or '')).strip())
    if not m:
        return None
    title = re.sub(r'[._]+', ' ', m.group(1)).strip(' -')
    return {'title': title, 'season': int(m.group(2)), 'episode': int(m.group(3))} if title else None


MOVIE_RELEASE = re.compile(r'(?i)^(.+)[ ._(\[-]+((?:19|20)\d{2})(?:[ ._)\]-]|$)')


def movie_from_release(text):
    """{'title', 'year'} from a movie file name ('Interstellar.2014.2160p.4K.BluRay…mp4' -> 'Interstellar', 2014), or
    None. Owner log 94605e4b (build 280): a copy played without details searched the whole file name with year 0."""
    name = re.sub(r'\[[^\]]*\]', '', str(text or '')).strip()
    name = re.sub(r'(?i)\.(mkv|mp4|m4v|avi|mov|ts|webm)$', '', name)
    m = MOVIE_RELEASE.match(name)
    if not m:
        return None
    title = re.sub(r'[._]+', ' ', m.group(1)).strip(' -(')
    return {'title': title, 'year': int(m.group(2))} if title else None


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
        out.append({'id': str(pid), 'releases': releases, 'language': lang,
                    'impaired': 'hearing_impaired' in (d.get('flags') or [])})
    return out


TOKENS = re.compile(r'[a-z0-9]+')
QUALITY = ('2160p', '1080p', '720p', 'web', 'webrip', 'web-dl', 'bluray', 'remux', 'hdtv', 'amzn', 'nf', 'dsnp', 'hmax', 'atvp')


def rank(results, filename, dubbed=False):
    """Best match first: the most release-name words shared with the playing file (group and source count most),
    hearing-impaired versions after plain ones. ISSUE-339: for a dubbed video, captions made from the English audio
    (CC / SDH / dub, hearing impaired) come first, ahead of release words."""
    mine = set(TOKENS.findall(_words(filename)))
    group = TOKENS.findall(_words(re.sub(r'\.[a-z0-9]{2,4}$', '', str(filename or ''))))[-1:] if filename else []

    def score(r):
        best = 0
        for rel in r['releases'] or ['']:
            theirs = set(TOKENS.findall(_words(rel)))
            s = len(mine & theirs) + 3 * len(set(group) & theirs) + 2 * len(mine & theirs & set(QUALITY))
            best = max(best, s)
        if dubbed:
            marked = r['impaired'] or bool(subtitle_match.DUB_MARK.search(' '.join(r['releases'] or [])))
            return (1 if marked else 0, best)
        return (best, 0 if r['impaired'] else 1)
    return sorted(results, key=score, reverse=True)


def subtitle_from_zip(blob, season=None, episode=None):
    """The .srt (or .ass / .ssa / .sub / .vtt) inside a subtitle zip: (name, bytes) or None. A season pack's zip
    (SubDL) gives the file of this episode (S01E05, 1x05)."""
    try:
        z = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        return None
    names = [n for n in z.namelist() if n.lower().endswith(('.srt', '.ass', '.ssa', '.vtt', '.sub'))]
    if season is not None and episode:
        mark = re.compile(r'(?i)(?:s0*%d[ ._-]?e0*%d|\b0*%dx0*%d)(?!\d)' % (int(season), int(episode), int(season), int(episode)))
        matching = [n for n in names if mark.search(n.rsplit('/', 1)[-1])]
        # Even a zip with one file may be the wrong episode. An unnumbered single file remains a candidate.
        if len(names) == 1:
            names = matching or [n for n in names if not subtitle_match.episode_identity(n)]
        else:
            names = matching
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
       'done': 'Downloaded and on', 'none': 'Try again', 'error': 'Try again', 'nokey': 'Try again'}
NOTE = {'none': 'No %s subtitles found for this video.', 'error': 'The subtitle site did not answer. Check the Wi-Fi and try again.',
        # 2026-11-12: Podnapisi is gone; SubDL and OpenSubtitles need a free key (subtitle_sources).
        'nokey': 'Add a free subtitle key: More › Subtitle keys.'}


def cta(state, language):
    text = CTA.get(state, CTA['idle'])
    return text % language if '%s' in text else text


def note(state, language):
    text = NOTE.get(state, '')
    return text % language if '%s' in text else text


BOOST_STEP = 3    # dB per tap; Kodi's VolAmpUp/Down move 1 dB each
BOOST_TOP = 18    # Kodi allows 60 dB; past ~18 dB speech distorts on the phone speaker


def boost_change(current, up):
    """(new dB, Kodi actions to send) for one tap on Volume boost - or +. Kodi keeps the gain only inside the player
    and offers no way to read it, so the menu counts it per video (roadmap B.2)."""
    new = max(0, min(BOOST_TOP, int(current) + (BOOST_STEP if up else -BOOST_STEP)))
    n = abs(new - int(current))
    return new, ['VolAmpUp' if up else 'VolAmpDown'] * n


def boost_text(db):
    return 'Off' if not db else '+%d dB' % db


SPEEDS = (0.8, 0.9, 1.0, 1.1, 1.25, 1.5)


def speed_rows(current):
    """Playback speed rows (roadmap B.7: Kodi's select box replaced by the track menu); index is the tempo."""
    try:
        now = float(current or 1)
    except ValueError:
        now = 1.0
    if now <= 0:
        now = 1.0
    near = min(SPEEDS, key=lambda s: abs(s - now))
    return [{'label': 'Normal' if s == 1.0 else '%g×' % s, 'tag': '', 'on': s == near, 'index': s} for s in SPEEDS]   # board 02


def more_rows(found, always, keys_tag='', current='', removable=False):
    """Subtitles › More as rows (roadmap B.6): Find another, Add from a file, Remove (only for a subtitle that was
    downloaded or added from a file), Use for all videos, Subtitle keys. The way back is the header's blue link (board 02).
    `current` is the language shown now ('English'), so the first row reads "Find another English"."""
    rows = [{'label': ('Find another %s' % current) if current else 'Choose another', 'tag': ('%d FOUND' % found) if found else '', 'on': False, 'index': 'choose'},
            {'label': 'Add from a file', 'tag': '', 'on': False, 'index': 'file'}]
    if removable and current:
        rows.append({'label': 'Remove %s from this video' % current, 'tag': '', 'on': False, 'index': 'remove', 'danger': True})
    return rows + [{'label': 'Use for all videos', 'tag': 'ON' if always else 'OFF', 'on': bool(always), 'index': 'always'},
                   {'label': 'Subtitle keys', 'tag': keys_tag, 'on': False, 'index': 'keys'}]


def hold_options(row):
    """What holding a subtitle row offers: ('Find another English', 'Remove from this video' or ''). Off has no menu (None).
    A track that is part of the video file cannot be removed, so it only offers Find another."""
    if row.get('index') is None:
        return None
    return ('Find another %s' % row['label'], 'Remove from this video' if row.get('removable') else '')


def sure_text(row):
    """The question that comes before a removal: (title, text)."""
    return ('Remove this subtitle?', '%s will be removed from this video. You can download it again any time.' % row['label'])


KEY_ROWS = (('subdl', 'SubDL key'), ('opensubtitles', 'OpenSubtitles key'), ('opensubtitles_user', 'OpenSubtitles username'),
            ('opensubtitles_password', 'OpenSubtitles password'))


def keys_rows(keys):
    """Subtitles › More › Subtitle keys as rows of the menu (owner, 2026-11-12: Kodi's select box looked wrong):
    each key, SET or ADD; tapping one opens the keyboard."""
    return [{'label': label, 'tag': 'SET' if keys.get(k) else 'ADD', 'on': False, 'index': 'key:' + k} for k, label in KEY_ROWS]


SUB_EXT = ('.srt', '.ass', '.ssa', '.vtt', '.sub')


def subtitle_files(roots, limit=40, depth=3, walk=None, mtime=None):
    """Subtitle files on the phone (Documents, Inbox, Kodi Downloads...), newest first, at most `limit`."""
    import os
    walk = walk or os.walk
    mtime = mtime or os.path.getmtime
    found = {}
    for root in roots:
        if not root:
            continue
        base = root.rstrip(os.sep).count(os.sep)
        for folder, dirs, files in walk(root):
            if folder.count(os.sep) - base >= depth:
                dirs[:] = []
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('Kodi', 'userdata', 'addons')]
            for f in files:
                if f.lower().endswith(SUB_EXT):
                    path = os.path.join(folder, f)
                    try:
                        found[path] = mtime(path)
                    except OSError:
                        continue
    return sorted(found, key=lambda p: -found[p])[:limit]


def file_rows(paths):
    """Subtitles › More › Add from a file as rows (owner, 2026-11-12: Kodi's file browser looked wrong): the file
    and the folder it is in; one plain row when there are none."""
    import os
    if not paths:
        return [{'label': 'No subtitle files on this iPhone', 'tag': '', 'on': False, 'index': 'nofiles'}]
    return [{'label': os.path.basename(p), 'tag': os.path.basename(os.path.dirname(p)).upper()[:18], 'on': False, 'index': 'sub:%d' % n}
            for n, p in enumerate(paths)]


_CODEC = ('x264', 'x265', 'h264', 'h265', 'hevc', 'avc', 'xvid', 'aac', 'ac3', 'dts', 'ddp5', 'dd5', 'mkv', 'mp4', 'srt')


def release_label(name, limit=34):
    """A release name as words that fit two lines of the row (DEC-050: no text is cut off): dots and underscores become spaces,
    the codec and release-group tail is dropped, then whole words from the end until it is at most `limit` letters."""
    text = str(name or '').strip()
    if ' ' not in text:
        text = text.replace('.', ' ').replace('_', ' ')
    words = []
    for word in text.split():
        if word.lower().strip('-') in _CODEC or '-' in word.strip('-') and word.lower().split('-')[0] in _CODEC:
            break
        words.append(word)
    while len(' '.join(words)) > limit and len(words) > 1:
        words.pop()
    return ' '.join(words) or text[:limit]


def result_rows(results):
    """Found subtitles as rows (the way back is the header's link); index is the result's position."""
    rows = []
    for n, r in enumerate(results):
        row = {'label': release_label(r['releases'][0]) if r['releases'] else 'Subtitle %s' % r['id'],
               'tag': 'SDH' if r['impaired'] else '', 'on': False, 'index': n}
        row.update({k: v for k, v in r.items() if k.startswith('match_')})
        row.setdefault('match_reason', 'Timing not checked')
        rows.append(row)
    return rows

