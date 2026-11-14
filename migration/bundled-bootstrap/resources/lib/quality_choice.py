"""DEC-049 (owner-approved docs/design/quality-choice-mockups.html, boards A-D): when the quality the owner chose does not
exist for a season, the app asks once for that season instead of downloading a lower version, or looping on a version
whose name claims the quality (ISSUE-264).

State (addon_data/service.kodi.ios.bootstrap/quality-choices.json, on the phone, never in Git):
  {'seasons': {'<tmdb>:<season>': {'state': 'asking' | 'best' | 'chosen' | 'looking', 'quality': '1080p', 'title': show,
                                   'best': {'name', 'quality'}, 'versions': [...], 'found': {pack folder: 'WxH'},
                                   'episodes': [held episode numbers], 'chosen': name, 'until': time, 'at': time}},
   'shows': {'<tmdb>': 'always'}}

- A fallback pick (deck_picker: nothing really the chosen quality) for a season with no answer is not queued: the season
  is 'asking', its episode is held, and one notice is posted (board A).
- The answer (board B) is kept: 'best' and 'chosen' let fallbacks through (and the copy is not refused, ISSUE-258);
  'looking' holds them for a day, then the next fallback asks again; 'always' answers every season of the show.
"""
import json
import os
import time

FILE = 'quality-choices.json'
LOOK_AGAIN = 24 * 3600


def path(profile):
    return os.path.join(str(profile), 'addon_data', 'service.kodi.ios.bootstrap', FILE)


def load(profile):
    try:
        with open(path(profile), encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    data.setdefault('seasons', {})
    data.setdefault('shows', {})
    return data


def save(profile, data):
    target = path(profile)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temp = target + '.tmp'
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    os.replace(temp, target)


def key(tmdb, season):
    return '%s:%s' % (tmdb, int(season or 0))


def state(profile, tmdb, season, now=None):
    """'best' (always for the show, or answered), 'chosen', 'asking', 'looking' (until it ends), or '' (never asked)."""
    if not tmdb:
        return ''
    data = load(profile)
    if data['shows'].get(str(tmdb)) == 'always':
        return 'best'
    record = data['seasons'].get(key(tmdb, season)) or {}
    value = record.get('state', '')
    if value == 'looking' and (time.time() if now is None else now) >= float(record.get('until') or 0):
        return ''
    return value


def lets_fallback(value):
    return value in ('best', 'chosen')


def hold(profile, tmdb, season, episode, quality, title, best=None, versions=None, now=None, keep=False):
    """A fallback for a season without an answer: hold the episode. True when the season was not asking before (post the
    notice once)."""
    now = time.time() if now is None else now
    data = load(profile)
    k = key(tmdb, season)
    record = data['seasons'].get(k) or {}
    fresh = record.get('state') != 'asking' and not keep   # keep: 'looking' holds the episode without asking again
    if fresh:
        record = {'state': 'asking', 'found': record.get('found') or {}, 'episodes': record.get('episodes') or [], 'at': now}
    record.update(quality=quality, title=title or record.get('title') or '')
    if best:
        record['best'] = {'name': str(best.get('name') or ''), 'quality': str(best.get('quality') or '')}
    if versions:
        record['versions'] = list(versions)[:8]
    try:
        n = int(episode)
        if n not in record['episodes']:
            record['episodes'] = sorted(record['episodes'] + [n])
    except (TypeError, ValueError):
        pass
    data['seasons'][k] = record
    save(profile, data)
    return fresh


def add_episode(profile, tmdb, season, episode):
    """An episode of a season that waits for the owner (Repair skipped it): looked up with the others after the answer."""
    data = load(profile)
    record = data['seasons'].get(key(tmdb, season))
    if not record:
        return
    n = int(episode)
    if n not in record.setdefault('episodes', []):
        record['episodes'] = sorted(record['episodes'] + [n])
        save(profile, data)


def note_found(profile, tmdb, season, folder, size):
    """A copy found a version lower than its name (ISSUE-264): kept for board C ("Says 1080p · a copy found 640x480")."""
    if not (tmdb and folder and size):
        return
    data = load(profile)
    record = data['seasons'].setdefault(key(tmdb, season), {'state': '', 'episodes': [], 'found': {}})
    record.setdefault('found', {})[folder] = size
    save(profile, data)


def answer(profile, tmdb, season, what, name='', now=None):
    """Board B's answer: 'best', 'chosen' (with the version's name), 'looking' or 'always'. Returns the held episodes,
    which are then looked up again (unless 'looking')."""
    now = time.time() if now is None else now
    data = load(profile)
    k = key(tmdb, season)
    record = data['seasons'].setdefault(k, {'episodes': [], 'found': {}})
    if what == 'always':
        data['shows'][str(tmdb)] = 'always'
        what = 'best'
    record['state'] = what
    record['answered'] = now
    if what == 'chosen':
        record['chosen'] = name
    if what == 'looking':
        record['until'] = now + LOOK_AGAIN
    held = list(record.get('episodes') or [])
    if what != 'looking':
        record['episodes'] = []
    save(profile, data)
    return held


def preferred(profile, tmdb, season):
    """The version the owner chose on board C for this season ('' when none): the automatic pick takes its pack first."""
    record = load(profile)['seasons'].get(key(tmdb, season)) or {}
    return record.get('chosen', '') if record.get('state') == 'chosen' else ''


def waiting(profile, tmdb):
    """Board D: {season: record} of this show's seasons that wait for the owner."""
    out = {}
    for k, record in load(profile)['seasons'].items():
        show, _, season = k.partition(':')
        if show == str(tmdb) and record.get('state') == 'asking' and season.isdigit():
            out[int(season)] = record
    return out


QUALITY_WORDS = {'4k': '4K', '1440p': '1440p', '1080p': '1080p', '720p': '720p', '480p': '480p', 'sd': 'SD'}


def word(quality):
    return QUALITY_WORDS.get(str(quality or '').lower(), str(quality or '') or 'a lower quality')


def short(name, show=''):
    """A version's name as people read it, never cut with "…" (owner, 2026-11-14): a pack's folder (not one episode's file),
    no extension, dots and underscores as spaces (but "AAC2.0", "H.264" kept), without the show's own name and the
    episode number the sheet already says. Long names wrap in the choice sheet."""
    import re
    text = str(name or '').strip().rstrip('/')
    parts = [x for x in text.split('/') if x.strip()]
    base = parts[0] if len(parts) > 1 else (parts[-1] if parts else '')
    base = re.sub(r'(?i)\.(mkv|mp4|avi|m4v|ts|webm)$', '', base)
    base = base.replace('.', ' ').replace('_', ' ')
    for w in [w for w in re.split(r'\W+', show or '') if w]:
        base = re.sub(r'(?i)\b%s\b' % re.escape(w), ' ', base, count=1)
    base = re.sub(r'(?i)\bS\d{1,2}E\d{1,3}\b', ' ', base)
    # The dots that belong in the words: AAC2.0, DDP5.1, H.264, 5.1.
    base = re.sub(r'(?i)\b(AAC|DDP?|AC3|EAC3|DTS|FLAC|OPUS)(\d) (\d)\b', r'\1\2.\3', base)
    base = re.sub(r'(?i)\b([HX]) (26[45])\b', r'\1.\2', base)
    base = re.sub(r'\b([257]) ([01])\b', r'\1.\2', base)
    base = re.sub(r'\s+', ' ', base).strip(' -·:')
    if len(base) > 64:   # three lines at most: tags with no numbers ("(Dual Audio)", "[Multi-Sub]") go first
        base = re.sub(r'\s+', ' ', re.sub(r'\[[^\]\d]*\]|\([^)\d]*\)', ' ', base)).strip(' -·:')
    return base or text.rsplit('/', 1)[-1]


def notice(record, season):
    """Board A: (title, text) of the one notice for the season."""
    best = record.get('best') or {}
    title = 'No real %s for season %s' % (word(record.get('quality')), season)
    found = next(iter((record.get('found') or {}).values()), '')
    if not best.get('quality') and found:   # from a refused copy (ISSUE-267): the best is not known yet
        return title, '%s \u00b7 the version named %s is really %s. Tap to choose.' % (
            record.get('title') or 'This show', word(record.get('quality')), found.replace('x', '\u00d7'))
    text = '%s · the best is %s%s. Tap to choose.' % (
        record.get('title') or 'This show', word(best.get('quality')),
        (' (%s)' % short(best.get('name'), record.get('title'))) if best.get('name') else '')
    return title, text


def _lower_than_named(record, name):
    folder = str(name or '').rsplit('/', 1)[0].strip().casefold() if '/' in str(name or '') else str(name or '').strip().casefold()
    return (record.get('found') or {}).get(folder, '')


def sheet(record, season):
    """Board B: (choice_sheet spec, actions)."""
    asked = word(record.get('quality'))
    best = record.get('best') or {}
    found = next(iter((record.get('found') or {}).values()), '')
    why = 'You chose %s.' % asked
    if found:
        why += ' A version named %s turned out to be %s.' % (asked, found.replace('x', '×'))
    why += ' The best real version is %s.' % word(best.get('quality')) if best.get('quality') else ' No real %s version exists.' % asked
    n = len(record.get('episodes') or [])
    rows = [{'label': 'Use the Best · %s' % word(best.get('quality')) if best.get('quality') else 'Use the Best Available',
             'detail': ' · '.join(x for x in ('%d episode%s waiting' % (n, '' if n == 1 else 's') if n else '',
                                               short(best.get('name'), record.get('title'))) if x),
             'tint': 'FF0A84FF', 'glyph': 'check.png'},
            {'label': 'Choose Another Version', 'detail': 'Every version, with its real picture size', 'tint': 'FF636366', 'glyph': 'list.png'},
            {'label': 'Keep Looking for %s' % asked, 'detail': 'Asks again tomorrow · nothing downloads', 'tint': 'FF636366', 'glyph': 'arrow-rotate-right.png'},
            {'label': 'Always Use the Best', 'detail': 'Every season of this show', 'tint': 'FF636366', 'glyph': 'star.png'}]
    spec = {'heading': 'Season %s isn’t in real %s' % (season, asked), 'sub': why, 'rows': rows}
    return spec, ['best', 'versions', 'looking', 'always']


def height_word(size):
    """'640x480' -> '480p' (the chip is narrow; the grey line keeps the exact size)."""
    try:
        height = int(str(size).lower().split('x')[1])
    except (IndexError, ValueError):
        return str(size)
    return '4K' if height >= 2000 else '%dp' % height


def versions_sheet(record, season):
    """Board C: (choice_sheet spec, version names). Each row: the version, its seeds and size, and a chip with the real
    picture size a copy found (orange) or the quality its name says (grey)."""
    rows, names = [], []
    for v in record.get('versions') or []:
        real = _lower_than_named(record, v.get('name'))
        bits = ['%d seed%s' % (int(v.get('seeds') or 0), '' if int(v.get('seeds') or 0) == 1 else 's')]
        if v.get('size'):
            bits.append('%.1f GB' % float(v['size']))
        if real:
            bits.insert(0, 'Says %s · really %s' % (word(v.get('quality')), real.replace('x', '×')))
        rows.append({'label': short(v.get('name'), record.get('title')), 'detail': ' · '.join(bits),
                     'tag': height_word(real) if real else word(v.get('quality')), 'tag_kind': 'warn' if real else ''})
        names.append(v.get('name') or '')
    spec = {'heading': 'Season %s versions' % season, 'sub': 'Best first. Sizes a copy has checked are shown as numbers.',
            'rows': rows}
    return spec, names
