"""Conservative subtitle matching, independent of Kodi and of the menu layout.

Cues are seconds on the video's clock. Embedded picture tracks with no cue metadata stay unchecked;
this module never claims to recognise speech from a stream's language tag. Callers may supply measured
speech intervals (or an offset with its confidence) when available. No network/media scanning runs here.
"""
import bisect
import json
import re

LANGUAGES = {'eng': 'en', 'english': 'en', 'spa': 'es', 'spanish': 'es', 'fre': 'fr', 'fra': 'fr', 'french': 'fr',
             'ger': 'de', 'deu': 'de', 'german': 'de', 'ita': 'it', 'italian': 'it', 'por': 'pt', 'portuguese': 'pt',
             'jpn': 'ja', 'japanese': 'ja', 'kor': 'ko', 'korean': 'ko', 'chi': 'zh', 'zho': 'zh', 'chinese': 'zh',
             'dut': 'nl', 'nld': 'nl', 'dutch': 'nl', 'rus': 'ru', 'russian': 'ru', 'ara': 'ar', 'arabic': 'ar',
             'swe': 'sv', 'swedish': 'sv', 'dan': 'da', 'danish': 'da', 'nor': 'no', 'norwegian': 'no',
             'fin': 'fi', 'finnish': 'fi', 'pol': 'pl', 'polish': 'pl', 'tur': 'tr', 'turkish': 'tr',
             'gre': 'el', 'ell': 'el', 'greek': 'el', 'heb': 'he', 'hebrew': 'he', 'hin': 'hi', 'hindi': 'hi',
             'cze': 'cs', 'ces': 'cs', 'czech': 'cs', 'hun': 'hu', 'hungarian': 'hu', 'rum': 'ro', 'ron': 'ro', 'romanian': 'ro'}
TEXT_EXT = ('.srt', '.vtt', '.ass', '.ssa', '.sub')
STAMP = r'(?:\d{1,3}:)?\d{2}:\d{2}[,.]\d{1,3}'
RANGE = re.compile(r'(' + STAMP + r')\s*-->\s*(' + STAMP + r')')
EPISODE = re.compile(r'(?i)(?:\bs(\d{1,2})[ ._-]*e(\d{1,3})\b|\b(\d{1,2})x(\d{1,3})\b)')
ABSOLUTE = re.compile(r'(?i)(?:\bepisode[ ._-]*(\d{1,4})\b|[ ._-]+-[ ._-]+(\d{1,4})(?=[ ._\[]|$))')


class Mismatch(ValueError):
    """A subtitle was read successfully but clearly belongs to something else."""


def language(value):
    word = str(value or '').lower().split('-')[0].strip()
    return LANGUAGES.get(word, word if len(word) == 2 and word != 'un' else '')


def _seconds(value):
    parts = str(value).replace(',', '.').split(':')
    return sum(float(p) * 60 ** n for n, p in enumerate(reversed(parts)))


def cue_times(data, filename=''):
    """Read SRT, VTT, ASS/SSA, MicroDVD text .sub, or VobSub .idx cue times. No subtitle text is retained."""
    if isinstance(data, bytes):
        data = data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig', 'replace')
    text = str(data or '')
    cues = [(_seconds(m[1]), _seconds(m[2])) for m in RANGE.finditer(text)]
    if not cues:
        for line in text.splitlines():
            line = line.strip()
            if line.lower().startswith('dialogue:'):
                fields = line.split(',', 3)
                try:
                    cues.append((_seconds(fields[1]), _seconds(fields[2])))
                except (IndexError, ValueError):
                    continue
        if not cues:
            frame_rows = re.findall(r'(?m)^\{(\d+)\}\{(\d+)\}([^\r\n]*)', text)
            fps = 25.0
            if frame_rows and frame_rows[0][:2] in (('1', '1'), ('0', '0')):
                try:
                    fps = float(frame_rows.pop(0)[2])
                except ValueError:
                    pass
            if not 1 <= fps <= 240:
                fps = 25.0
            cues = [(int(a) / fps, int(b) / fps) for a, b, _ in frame_rows]
        if not cues and str(filename).lower().endswith('.idx'):
            for h, m, s, ms in re.findall(r'(?i)timestamp:\s*(\d+):(\d+):(\d+):(\d+)', text):
                start = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
                cues.append((start, start + .1))  # IDX gives starts, not the bitmap's display duration.
    return sorted((a, b) for a, b in cues if b > a)


def _intervals(values):
    out = []
    for cue in values or []:
        try:
            a, b = (cue['start'], cue['end']) if isinstance(cue, dict) else cue[:2]
            a, b = float(a), float(b)
            if b > a:
                out.append((a, b))
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return sorted(out)


def estimate_offset(cues, speech):
    """(seconds to shift cues, confidence), only for a strong improvement against measured speech intervals.

    This is timing evidence, not a speech/text recognition claim. Sparse or already aligned evidence is unknown.
    Sampling bounds the work even for a long movie. Periodic/ambiguous evidence does not establish an offset.
    """
    cues, speech = _intervals(cues), _intervals(speech)
    if len(cues) < 8 or len(speech) < 8:
        return None, 0.0
    stride = max(1, len(cues) // 200)
    points = [(a + b) / 2 for a, b in cues[::stride][:200]]
    starts = [a for a, _ in speech]

    def fit(shift):
        hits = 0
        for point in points:
            at = point + shift
            n = bisect.bisect_right(starts, at + .75) - 1
            if n >= 0 and at <= speech[n][1] + .75:
                hits += 1
        return hits / len(points)
    baseline = fit(0)
    coarse = [(fit(n), n) for n in range(-180, 181, 2)]
    best, shift = max(coarse, key=lambda p: (p[0], -abs(p[1])))
    if baseline >= .6 or best < .75 or best - baseline < .35:
        return None, 0.0
    # More than one separate offset explains the cues: do not call it a measured mismatch.
    if any(value >= best - .05 and abs(n - shift) > 5 for value, n in coarse):
        return None, 0.0
    refined = [(fit(shift + n / 2), shift + n / 2) for n in range(-4, 5)]
    best = max(value for value, _ in refined)
    peak = [n for value, n in refined if value == best]
    shift = (min(peak) + max(peak)) / 2
    return round(shift, 1), round(best, 3)


def episode_identity(filename):
    # Keep separators so a language tag cannot be mistaken for the end of a word in a title.
    name = str(filename or '').rsplit('/', 1)[-1].replace('_', ' ')
    m = EPISODE.search(name)
    return (int(m[1] or m[3]), int(m[2] or m[4])) if m else None


def _file_language(filename):
    name = str(filename or '').rsplit('/', 1)[-1].lower()
    name = re.sub(r'\.(srt|vtt|ass|ssa|sub|idx|sup)$', '', name)
    tags = re.split(r'[ ._\[\]()-]+', name)
    for tag in reversed(tags[-4:]):
        if tag in {'forced', 'sdh', 'hi', 'cc', 'utf8', 'default', 'full'}:
            continue
        if tag in LANGUAGES or tag in LANGUAGES.values():
            return language(tag)
        break   # A title like It.2017 is not an Italian language suffix.
    return ''


# ISSUE-339 (owner, Naruto Shippuden 1x01 in English: "the subtitles … were near but not exactly what they say"): a
# subtitle written from the original-language script is a translation, not the English dub's words. Captions made from
# the English audio are marked CC / SDH / dub (or hearing impaired). When the video is dubbed (dubbed()), those come
# first and an unmarked track in the audio's language comes after them.
DUB_MARK = re.compile(r'(?i)(?:\b(?:dub|dubbed|dubtitles?|cc|sdh|closed[ ._-]?captions?|hearing[ ._-]?impaired)\b|\[cc\]|\(cc\))')


def dubbed(audio_streams, current_audio, subtitle_language):
    """True when the file carries audio in more than one language and the one playing is the subtitle language: the
    usual dual-audio anime or foreign release with its English dub on."""
    langs = {language(a.get('language')) for a in (audio_streams or []) if language(a.get('language'))}
    playing = language((current_audio or {}).get('language'))
    wanted = language(subtitle_language)
    return bool(wanted and playing == wanted and len(langs) > 1)


def dub_marked(track):
    text = ' '.join(str(t or '') for t in [track.get('name'), track.get('filename')] + list(track.get('releases') or []))
    return bool(track.get('isimpaired') or track.get('impaired') or DUB_MARK.search(text))


def assess(track, video):
    """Return score/rejected/reason/timing_checked/cue_count/offset_s for one track.

    track: filename/name/language, cues=[(start,end)] or data; isforced exempts intentionally short tracks.
    video: duration seconds, season/episode, language; optional absolute_episode and measured speech intervals.
    A distant opening/closing cue lowers rank, but credits/forced captions alone never prove a mismatch.
    """
    name = track.get('filename') or track.get('name') or ''
    names = [name] + list(track.get('releases') or [])
    expected = (video.get('season'), video.get('episode'))
    wanted_language = language(video.get('language'))
    declared = language(track.get('language'))
    tagged = _file_language(name)
    score, rejected, reason = 70, False, 'Timing not checked'

    def refuse(why):
        return {'score': 0, 'rejected': True, 'reason': why, 'timing_checked': checked,
                'cue_count': len(cues), 'offset_s': offset, 'offset_confidence': confidence}

    data = track.get('data')
    cues = _intervals(track.get('cues')) if 'cues' in track else cue_times(data, name) if data is not None else []
    picture_sub = str(name).lower().endswith('.sub') and isinstance(data, bytes) and (b'\x00' in data or data.startswith(b'\x00\x00\x01'))
    checked = bool(cues) or data is not None and not picture_sub and str(name).lower().endswith(TEXT_EXT + ('.idx',))
    offset, confidence = None, 0.0
    for candidate in names:
        episode = episode_identity(candidate)
        if episode and all(v is not None for v in expected):
            if episode != tuple(int(v) for v in expected):
                return refuse('Different episode')
            score += 8
        absolute = ABSOLUTE.search(str(candidate or ''))
        wanted = video.get('absolute_episode')
        if wanted is None and video.get('season') in (1, '1'):
            wanted = video.get('episode')
        if absolute and wanted is not None and int(absolute[1] or absolute[2]) != int(wanted):
            return refuse('Different episode')
    if tagged and declared and tagged != declared:
        return refuse('Language tag does not match')
    if wanted_language and (tagged or declared) and (tagged or declared) != wanted_language:
        return refuse('Different language')
    if wanted_language and (tagged or declared) == wanted_language:
        score += 10
    if video.get('dubbed'):   # ISSUE-339: the dub's own captions before a translation of the original script
        score += 12 if dub_marked(track) else -8
    forced = bool(track.get('isforced') or track.get('forced') or re.search(r'(?i)\bforced\b', name))
    duration = max(0.0, float(video.get('duration') or 0))
    if checked and not cues:
        return refuse('Empty subtitle track')
    if track.get('offset_s') is not None and float(track.get('offset_confidence') or 0) >= .75:
        offset, confidence = float(track['offset_s']), float(track['offset_confidence'])
        if abs(offset) >= 8:
            return refuse('Subtitles are out of sync')
    if cues:
        if duration:
            beyond = sum(1 for a, b in cues if a >= duration + 2 or b > duration + max(15, duration * .03))
            if beyond and (beyond / len(cues) >= .1 or cues[-1][0] > duration + 60):
                return refuse('Timing does not fit this video')
            if not forced and duration >= 600 and (len(cues) < 5 or cues[-1][1] - cues[0][0] < min(30, duration * .03)):
                return refuse('Subtitle track is too short')
            far_start = cues[0][0] > max(180, duration * .2)
            far_end = cues[-1][1] < duration * .55
            score -= 12 * int(far_start) + 12 * int(far_end)
            if not forced and far_start and far_end:
                return refuse('Timing does not fit this video')
        if offset is None:
            offset, confidence = estimate_offset(cues, video.get('speech') or [])
        if offset is not None and abs(offset) >= 8 and confidence >= .75:
            return refuse('Subtitles are out of sync')
        score += 10
        reason = ('Matches this episode' if video.get('episode') is not None else 'Timing fits this video') if duration else 'Video duration not known'
        checked = bool(duration)
        if score < 75:
            reason = 'Only part of this video has subtitles'
    return {'score': max(0, min(100, score)), 'rejected': rejected, 'reason': reason,
            'timing_checked': checked, 'cue_count': len(cues), 'offset_s': offset, 'offset_confidence': confidence}


def annotate(track, video):
    """A copy of a track with flat match_* fields for models and ListItem properties."""
    return dict(track, **{'match_' + k: v for k, v in assess(track, video).items()})


def rank(tracks, video):
    """Keep rejected rows for explanations, after usable tracks, in best-match order."""
    return sorted((annotate(t, video) for t in tracks), key=lambda t: (t['match_rejected'], -t['match_score']))


def preferred(tracks, current, enabled, video):
    """Best allowed stream index, or None for Off. An owner's Off choice stays Off."""
    if not enabled:
        return None
    usable = [t for t in rank(tracks, video) if not t['match_rejected']]
    if not usable:
        return None
    best = usable[0]
    # Keep the current track on a tie (e.g. two embedded DVD tracks with no timing evidence).
    return next((t.get('index') for t in usable if t.get('index') == current and t['match_score'] == best['match_score']),
                best.get('index'))


def choose_download(results, fetch, video, limit=5):
    """Validate before installing; try the next release after a mismatch or failed download.

    Release ranking is retained for equally good matches. At most five downloads per tap; providers have quotas.
    Assessments are copied back to result records for the Choose another model. Returns (result, name, bytes).
    """
    best, last_error = None, None
    candidates = rank(results, video)
    for result in candidates:
        original = next((r for r in results if r.get('source') == result.get('source') and r.get('id') == result.get('id')), result)
        original.update({k: v for k, v in result.items() if k.startswith('match_')})
    for result in candidates[:max(1, limit)]:
        original = next((r for r in results if r.get('source') == result.get('source') and r.get('id') == result.get('id')), result)
        if result['match_rejected']:
            last_error = Mismatch(result['match_reason'])
            continue
        try:
            got = fetch(original)
            if not got:
                raise Mismatch('No subtitle file for this episode')
            name, data = got
            tested = annotate(dict(original, filename=name, data=data), video)
            original.update({k: v for k, v in tested.items() if k.startswith('match_')})
            if tested['match_rejected']:
                last_error = Mismatch(tested['match_reason'])
                continue
            if best is None or tested['match_score'] > best[0]['match_score']:
                best = (original, name, data)
            if tested['match_score'] >= 85:
                break
        except Exception as error:
            last_error = error
    if best is not None:
        return best
    if last_error is not None:
        raise last_error
    raise Mismatch('No matching subtitle track')


class PlaybackMatcher:
    """One check per opened video; allow time for Kodi to publish its streams, preserve later manual choices."""
    def __init__(self):
        self.file, self.done, self.tries = '', False, 0

    def step(self, playing_file, snapshot, select, publish=lambda value: None):
        if playing_file != self.file:
            self.file, self.done, self.tries = playing_file, False, 0
            publish('[]')
        if not playing_file or self.done:
            return
        self.tries += 1
        if self.tries > 10:
            self.done = True
            return
        state = snapshot()
        streams, video = state.get('streams') or [], state.get('video') or {}
        if not streams or not video.get('duration'):
            if self.tries >= 10:
                self.done = True
            return
        models = rank(streams, video)
        # Export only indices and evidence: no playing URL, filename, subtitle text or account data.
        publish(json.dumps([dict(index=t.get('index'), **{k: v for k, v in t.items() if k.startswith('match_')})
                            for t in models], separators=(',', ':')))
        chosen = preferred(streams, state.get('current'), state.get('enabled'), video)
        # ISSUE-298 (review of PR #30): when no track is usable the owner's subtitles stay on; the reasons are published
        # above. Only a better usable track replaces the current one, never Off.
        if state.get('enabled') and chosen is not None and chosen != state.get('current'):
            select(chosen)
        self.done = True


def run(xbmc, xbmcgui, monitor):
    """Playback-start service hook. Kodi currently supplies names/languages, but no embedded subtitle cues."""
    matcher = PlaybackMatcher()
    home = xbmcgui.Window(10000)

    def rpc(method, params=None):
        response = json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1,
                                                             'method': method, 'params': params or {}})))
        if response.get('error'):
            raise ValueError('Kodi subtitle metadata is not available')
        return response.get('result')

    while not monitor.waitForAbort(2):
        try:
            playing = xbmc.Player().getPlayingFile() if xbmc.Player().isPlayingVideo() else ''
            player_id = [None]

            def snapshot():
                player_id[0] = next(p['playerid'] for p in rpc('Player.GetActivePlayers') if p.get('type') == 'video')
                props = rpc('Player.GetProperties', {'playerid': player_id[0],
                                                    'properties': ['subtitles', 'currentsubtitle', 'subtitleenabled',
                                                                   'audiostreams', 'currentaudiostream']}) or {}
                item = (rpc('Player.GetItem', {'playerid': player_id[0],
                                              'properties': ['file', 'title', 'season', 'episode']}) or {}).get('item') or {}
                preference = (rpc('Settings.GetSettingValue', {'setting': 'locale.subtitlelanguage'}) or {}).get('value')
                identity = episode_identity(item.get('file')) or episode_identity(item.get('title'))
                return {'streams': props.get('subtitles'), 'current': (props.get('currentsubtitle') or {}).get('index'),
                        'enabled': props.get('subtitleenabled'),
                        'video': {'duration': xbmc.Player().getTotalTime(), 'language': language(preference),
                                  'dubbed': dubbed(props.get('audiostreams'), props.get('currentaudiostream'), preference),
                                  'season': item.get('season') if item.get('season') is not None and item['season'] >= 0 else identity[0] if identity else None,
                                  'episode': item.get('episode') if item.get('episode') is not None and item['episode'] > 0 else identity[1] if identity else None}}

            def select(index):
                rpc('Player.SetSubtitle', {'playerid': player_id[0], 'subtitle': index if index is not None else 'off',
                                           'enable': index is not None})
            matcher.step(playing, snapshot, select, lambda value: home.setProperty('KodiIOS.SubtitleMatches', value))
        except Exception as error:
            if matcher.tries <= 1:
                xbmc.log('Kodi iOS subtitle match: metadata unavailable (%s)' % type(error).__name__, xbmc.LOGWARNING)
