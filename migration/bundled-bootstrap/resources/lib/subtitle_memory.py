"""A subtitle the viewer downloaded stays on for that video (owner, build 634 log f75957fe: "if i have them on and exit the show and go back in it says they
are on but they are not ... they dont work unless i press download and apply").

Two parts. The menu keeps what it downloads in the profile (special://temp is emptied at every start) and writes, per video, which file is the viewer's
(`remember`). When a video starts, the service asks `at_start`: a remembered file is put on again; otherwise, when Kodi came up on an embedded track whose cues
have no length (mp4_tracks.zero_length: it reports "on" and draws nothing), subtitles are turned off, so the menu and the CC button say what is true. The identity
of a video is its show, season and episode, or its title and year, or its file's name: whatever Kodi's own labels give, the same in the menu and in the service."""
import json
import os
import time

KEEP = 60
INDEX = 'subtitle-memory.json'


STORE = 'special://profile/addon_data/plugin.video.kodi.ios.watch/continue.json'


def known_from(read, title, now=time.time):
    """The show, season and episode Continue Watching holds for the video playing now ({} when it does not agree): Kodi's own labels for an Umbrella stream say
    only 'Episode 8', so a subtitle downloaded for it was filed under the stream's link and lost when the link changed (build 646 log d8f39741)."""
    try:
        data = json.loads(read(STORE) or '{}')
        entry = (data.get('items') or {}).get(data.get('current')) or {}
        if entry.get('kind') == 'movie' or now() - float(entry.get('played') or 0) > 6 * 3600:
            return {}
        if str(entry.get('title') or '').strip().lower() != str(title or '').strip().lower() or not entry.get('tvshowtitle'):
            return {}
        return {'show': str(entry['tvshowtitle']), 'season': str(entry.get('season') or ''), 'episode': str(entry.get('episode') or '')}
    except Exception:
        return {}


def identity(label, playing_file='', known=None):
    """A key for the video playing, from Kodi's info labels (label(name) -> text); '' when nothing identifies it. `known`: known_from() for a stream whose labels
    lack the show."""
    show, season, episode = label('VideoPlayer.TVShowTitle').strip(), label('VideoPlayer.Season').strip(), label('VideoPlayer.Episode').strip()
    if not (show and season and episode) and known and known.get('show') and known.get('season') and known.get('episode'):
        show, season, episode = known['show'].strip(), known['season'].strip(), known['episode'].strip()
    if show and season and episode:
        return 'tv|%s|%s|%s' % (show.lower(), season, episode)
    title, year = label('VideoPlayer.Title').strip(), label('VideoPlayer.Year').strip()
    if title and year:
        return 'film|%s|%s' % (title.lower(), year)
    name = os.path.basename(str(playing_file or '').split('|')[0].split('?')[0])
    return 'file|' + name.lower() if name else ''


def _load(root):
    try:
        with open(os.path.join(root, INDEX), encoding='utf-8') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def remember(root, key, path, name='', lang='', now=time.time):
    """Keep `path` (a subtitle file under `root`) as this video's subtitle. The oldest entries and their files beyond KEEP go."""
    if not key or not path or not os.path.isfile(path):
        return False
    data = _load(root)
    data[key] = {'path': path, 'name': name, 'lang': lang, 'at': int(now())}
    if len(data) > KEEP:
        for old in sorted(data, key=lambda k: data[k].get('at', 0))[:len(data) - KEEP]:
            gone = data.pop(old)
            if not any(e.get('path') == gone.get('path') for e in data.values()):
                try:
                    os.remove(gone.get('path', ''))
                except OSError:
                    pass
    try:
        os.makedirs(root, exist_ok=True)
        temp = os.path.join(root, INDEX + '.tmp')
        with open(temp, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, separators=(',', ':'))
        os.replace(temp, os.path.join(root, INDEX))
    except OSError:
        return False
    return True


def recall(root, key):
    """The remembered subtitle for this video: {'path', 'name', 'lang'} when its file is still there, else None."""
    entry = _load(root).get(key) if key else None
    if isinstance(entry, dict) and os.path.isfile(str(entry.get('path') or '')):
        return entry
    return None


def forget(root, key):
    data = _load(root)
    if key in data:
        del data[key]
        try:
            with open(os.path.join(root, INDEX), 'w', encoding='utf-8') as handle:
                json.dump(data, handle, separators=(',', ':'))
        except OSError:
            pass


def at_start(root, label, playing_file, set_subtitles, show_subtitles, current, zero_length, log, known=None):
    """What to do when a video starts. current() -> (enabled, index of Kodi's current subtitle stream, external?); zero_length() -> True when that embedded
    stream's cues have no length, False when they have, None when unknown. Returns 'remembered', 'off' or 'left'."""
    key = identity(label, playing_file, known)
    found = recall(root, key)
    if found:
        set_subtitles(found['path'])
        show_subtitles(True)
        log('subtitle memory: the subtitles you downloaded for this video are on again')
        return 'remembered'
    enabled, index, external = current()
    if enabled and not external and zero_length(index):
        show_subtitles(False)
        log('subtitle memory: the video came up on an embedded subtitle whose cues have no length (nothing would show); subtitles turned off')
        return 'off'
    return 'left'
