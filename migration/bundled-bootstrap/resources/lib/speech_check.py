"""ISSUE-347 (owner: "match subtitle check needs to be added"): subtitles checked against the words actually spoken.

The phone listens to two short stretches of the playing video's sound (KodiAirPlay's kodi_speech_words: Apple's
speech recognition, on the phone only) and each candidate subtitle is compared with those words:

- the words agree at some shift: the subtitle is for this video (and this dub); a shift of 0.4 s or more is taken out
  of the file before it is turned on;
- plenty of words were heard and almost none are in the subtitle: it is for something else (another release, the
  original script of a dub) and is skipped;
- too few words, or the sound is in another language than the subtitles: no claim either way.

Only runs when the audio track is in the subtitle language (recognising French speech with an English recognizer
says nothing). Pure functions here; listen() is the only one that touches the framework.
"""
import bisect
import json
import re

MIN_WORDS = 12          # content words heard before any claim is made
MISMATCH = .12          # at most this share of them found in the subtitle at its best shift: not for this video
ALIGNED = .30           # at least this share: the subtitle matches, and its best shift can be trusted
SHIFT_FROM = .4         # seconds; smaller shifts are left alone
SEARCH = 120            # seconds either way
SLACK = .6              # a word may be heard this long before or after its cue
STRETCH = 30            # seconds of sound per sample (build 616 log: 45 s over Drive took 20-38 s and heard 7 and 2 words; the recognizer needs far less)
BYTE_BUDGET = 24 * 1024 * 1024   # per sample: a 4K stream is not read for long (was 48 MB: two samples read 96 MB of a 4K file)
LOCALES = {'en': 'en-US', 'es': 'es-ES', 'fr': 'fr-FR', 'de': 'de-DE', 'it': 'it-IT', 'pt': 'pt-BR', 'ja': 'ja-JP',
           'ko': 'ko-KR', 'zh': 'zh-CN', 'nl': 'nl-NL', 'ru': 'ru-RU', 'ar': 'ar-SA', 'sv': 'sv-SE', 'da': 'da-DK',
           'no': 'nb-NO', 'fi': 'fi-FI', 'pl': 'pl-PL', 'tr': 'tr-TR', 'el': 'el-GR', 'he': 'he-IL', 'hi': 'hi-IN',
           'cs': 'cs-CZ', 'hu': 'hu-HU', 'ro': 'ro-RO'}
STOP = set('the and you that this was for are with his her they have not but what all were when your can said there '
           'she him one our out get got just did its yeah okay well now how who why let'.split())
TAGS = re.compile(r'<[^>]*>|\{[^}]*\}|\\[Nnh]')
WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)?", re.UNICODE)
STAMP = r'(?:(\d{1,3}):)?(\d{1,2}):(\d{2})[,.](\d{1,3})'
RANGE = re.compile(STAMP + r'\s*-->\s*' + STAMP)
ASS_TIME = re.compile(r'(\d+):(\d{2}):(\d{2})[.,](\d{1,3})')


def words_of(text):
    """Lower-case words of a line, markup removed, short and very common words left out."""
    out = []
    for w in WORD.findall(TAGS.sub(' ', str(text or '')).lower()):
        w = w.replace("'", '')
        if len(w) >= 3 and w not in STOP:
            out.append(w)
    return out


def _stamp(h, m, s, frac):
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(frac) / (10 ** len(frac))


def cues(data, name=''):
    """[(start, end, set of words)] of an SRT / WebVTT / ASS file (bytes or text)."""
    text = data.decode('utf-8-sig', 'replace') if isinstance(data, bytes) else str(data or '')
    out = []
    if str(name).lower().endswith(('.ass', '.ssa')) or '[Events]' in text:
        fields = None
        for line in text.splitlines():
            if line.startswith('Format:') and fields is None and 'Start' in line:
                fields = [f.strip() for f in line[7:].split(',')]
            elif line.startswith('Dialogue:') and fields:
                parts = line[9:].split(',', len(fields) - 1)
                if len(parts) < len(fields):
                    continue
                row = dict(zip(fields, parts))
                a, b = ASS_TIME.match(row.get('Start', '').strip()), ASS_TIME.match(row.get('End', '').strip())
                if a and b:
                    out.append((_stamp(*a.groups()), _stamp(*b.groups()), set(words_of(row.get('Text', '')))))
        return sorted(out, key=lambda c: c[0])
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = RANGE.search(line)
        if not m:
            continue
        g = m.groups()
        body = []
        for follow in lines[i + 1:]:
            if not follow.strip():
                break
            body.append(follow)
        out.append((_stamp(*g[:4]), _stamp(*g[4:]), set(words_of(' '.join(body)))))
    return sorted(out, key=lambda c: c[0])


def heard(result):
    """[(time, word)] of kodi_speech_words' JSON results (one or more), content words only."""
    out = []
    for r in result if isinstance(result, list) else [result]:
        for item in (r or {}).get('words') or []:
            for w in words_of(item.get('w')):
                try:
                    out.append((float(item.get('t')) + float(item.get('d') or 0) / 2, w))
                except (TypeError, ValueError):
                    continue
    return sorted(out)


def compare(spoken, subtitle):
    """How a subtitle's text fits the spoken words: {'heard', 'agreement', 'offset', 'confident'} or None (too few
    words). offset: seconds to add to every cue. agreement: the share of spoken words found in a cue at that shift."""
    if len(spoken) < MIN_WORDS or not subtitle:
        return None
    where = {}
    for a, b, ws in subtitle:
        for w in ws:
            where.setdefault(w, []).append((a, b))
    for spans in where.values():
        spans.sort()

    def hits(shift):
        n = 0
        for t, w in spoken:
            spans = where.get(w)
            if not spans:
                continue
            at = t - shift
            k = bisect.bisect_right(spans, (at + SLACK, float('inf'))) - 1
            while k >= 0 and spans[k][0] >= at - 30:
                if spans[k][0] - SLACK <= at <= spans[k][1] + SLACK:
                    n += 1
                    break
                k -= 1
        return n
    coarse = [(hits(s / 2), s / 2) for s in range(-2 * SEARCH, 2 * SEARCH + 1)]
    best, shift = max(coarse, key=lambda p: (p[0], -abs(p[1])))
    # The words fit over a run of shifts (a cue lasts longer than its words): take the middle of that run.
    k = coarse.index((best, shift))
    lo = hi = k
    while lo > 0 and coarse[lo - 1][0] == best:
        lo -= 1
    while hi + 1 < len(coarse) and coarse[hi + 1][0] == best:
        hi += 1
    middle = (coarse[lo][1] + coarse[hi][1]) / 2
    refined = [(hits(middle + n / 10), middle + n / 10) for n in range(-10, 11)]
    top = max(v for v, _ in refined)
    peak = [s for v, s in refined if v == top]
    shift = round((min(peak) + max(peak)) / 2, 1)
    # Another shift, away from that run, that explains the words almost as well: the timing is not established.
    rival = max((v for v, s in coarse if s < coarse[lo][1] - 3 or s > coarse[hi][1] + 3), default=0)
    agreement = top / len(spoken)
    return {'heard': len(spoken), 'agreement': round(agreement, 3), 'offset': shift,
            'confident': agreement >= ALIGNED and rival <= top * .6}


def verdict(fit):
    """('mismatch' | 'shift' | 'fits' | 'unknown', seconds to add)."""
    if not fit:
        return 'unknown', 0.0
    if fit['agreement'] <= MISMATCH:
        return 'mismatch', 0.0
    if fit['confident'] and abs(fit['offset']) >= SHIFT_FROM:
        return 'shift', fit['offset']
    return ('fits' if fit['agreement'] >= ALIGNED else 'unknown'), 0.0


def _fmt_srt(t, dot=False):
    t = max(0.0, t)
    ms = int(round(t * 1000))
    return '%02d:%02d:%02d%s%03d' % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, '.' if dot else ',', ms % 1000)


def _fmt_ass(t):
    cs = int(round(max(0.0, t) * 100))
    return '%d:%02d:%02d.%02d' % (cs // 360000, cs // 6000 % 60, cs // 100 % 60, cs % 100)


def shift_file(data, name, seconds):
    """The subtitle file with every cue moved by `seconds` (SRT, WebVTT, ASS). Bytes in, bytes out."""
    raw = isinstance(data, bytes)
    text = data.decode('utf-8-sig', 'replace') if raw else str(data)
    if str(name).lower().endswith(('.ass', '.ssa')) or '[Events]' in text:
        def dialogue(line):
            if not line.startswith('Dialogue:'):
                return line
            parts = line.split(',', 3)
            if len(parts) < 4:
                return line
            for k in (1, 2):
                m = ASS_TIME.match(parts[k].strip())
                if m:
                    parts[k] = _fmt_ass(_stamp(*m.groups()) + seconds)
            return ','.join(parts)
        out = '\n'.join(dialogue(line) for line in text.split('\n'))
    else:
        def move(m):
            g = m.groups()
            dot = '.' in m.group(0)
            return '%s --> %s' % (_fmt_srt(_stamp(*g[:4]) + seconds, dot), _fmt_srt(_stamp(*g[4:]) + seconds, dot))
        out = RANGE.sub(move, text)
    return out.encode('utf-8') if raw else out


def wanted(video, audio_language):
    """Listen only when the sound is in the subtitles' language (and that language has a recognizer)."""
    import subtitle_match as sm
    lang = sm.language((video or {}).get('language'))
    return bool(lang and lang in LOCALES and sm.language(audio_language) == lang)


def places(duration):
    """Where to listen: two stretches inside the video, away from the opening and the credits."""
    d = float(duration or 0)
    if d < 4 * STRETCH:
        return [max(0.0, d / 2 - STRETCH / 2)] if d > STRETCH else []
    return [max(60.0, d * .3), d * .6]


def listen(lib, url, audio, lang, duration, log=lambda m: None):
    """[(time, word)] heard in the playing video, or [] when the phone cannot listen (older framework, permission
    not given, language not recognised on the phone, sound not readable)."""
    import ctypes
    if not lib or not hasattr(lib, 'kodi_speech_words'):
        log('speech check: this AirPlay framework cannot listen yet')
        return []
    lib.kodi_speech_authorize.argtypes = [ctypes.c_double]
    lib.kodi_speech_authorize.restype = ctypes.c_int
    lib.kodi_speech_words.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_longlong,
                                      ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    lib.kodi_speech_words.restype = ctypes.c_int
    if not lib.kodi_speech_authorize(60.0):
        log('speech check: speech recognition is not allowed (Settings > Kodi > Speech Recognition)')
        return []
    source = str(url or '').split('|')[0].encode('utf-8')
    results = []
    for at in places(duration):
        out = ctypes.create_string_buffer(256 * 1024)
        n = lib.kodi_speech_words(source, int(audio if audio is not None else -1), at, float(STRETCH), BYTE_BUDGET,
                                  LOCALES[lang].encode('ascii'), out, len(out))
        try:
            result = json.loads(out.value.decode('utf-8')) if n >= 0 else {'status': 'failed', 'why': 'answer too long'}
        except ValueError:
            result = {'status': 'failed', 'why': 'unreadable answer'}
        log('speech check: %s at %d s: %s' % (result.get('status'), at, result.get('why') or '%d words' % len(result.get('words') or [])))
        if result.get('status') == 'ok':
            results.append(result)
        elif result.get('status') in ('denied', 'not_on_device', 'unavailable'):
            break
    return heard(results)


PROPERTY = 'KodiIOS.SpeechHeard'


def framework(xbmcvfs):
    """The KodiAirPlay framework, or None (desktop Kodi, or not in this build)."""
    import ctypes
    import airplay
    path = airplay.library_path(xbmcvfs.translatePath('special://xbmc'))
    return ctypes.CDLL(path) if path else None


def for_playing(xbmc, xbmcgui, xbmcvfs, video, log=lambda m: None):
    """The words heard in the video playing now: listened to once per video (kept on the home window, which every
    script sees), [] when the check does not apply. Blocks while listening; call it off Kodi's main thread."""
    try:
        playing = xbmc.Player().getPlayingFile()
    except Exception:
        return []
    home = xbmcgui.Window(10000)
    try:
        saved = json.loads(home.getProperty(PROPERTY) or '{}')
    except ValueError:
        saved = {}
    if saved.get('file') == playing:
        return [tuple(x) for x in saved.get('heard') or []]
    import subtitle_match as sm
    audio = {}
    try:
        call = lambda m, p=None: json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m, 'params': p or {}}))).get('result')
        pid = next(p['playerid'] for p in call('Player.GetActivePlayers') or [] if p.get('type') == 'video')
        audio = (call('Player.GetProperties', {'playerid': pid, 'properties': ['currentaudiostream']}) or {}).get('currentaudiostream') or {}
    except Exception:
        pass
    words = []
    if not wanted(video, audio.get('language')):
        log('speech check: not listening (sound %s, subtitles %s)' % (audio.get('language') or 'unknown', (video or {}).get('language')))
    else:
        try:
            words = listen(framework(xbmcvfs), playing, audio.get('index'), sm.language(video.get('language')), video.get('duration'), log)
        except Exception as error:
            log('speech check: could not listen (%s)' % type(error).__name__)
    home.setProperty(PROPERTY, json.dumps({'file': playing, 'heard': words}))
    return words


def apply(original, tested, data, name, heard):
    """Checks a downloaded subtitle against the words heard: (data, rejected reason or None). Copies the result onto
    `original` (match_speech: mismatch / shift / fits / unknown, its agreement and the shift taken out)."""
    if not heard:
        return data, None
    fit = compare(heard, cues(data, name))
    how, seconds = verdict(fit)
    original.update(match_speech=how, match_speech_agreement=fit['agreement'] if fit else None, match_speech_shift=seconds)
    if how == 'mismatch':
        return data, 'Words do not match the speech'
    if how == 'shift':
        data = shift_file(data, name, seconds)
    if how in ('fits', 'shift'):
        tested['match_score'] = min(100, tested['match_score'] + 10)
        original['match_score'] = tested['match_score']
    return data, None


def best_fit(heard, files):
    """Of several downloaded subtitles, [(selected, name, data)], the one the heard words support best: (selected, name, data, how, seconds_to_add) where how is
    'fits' or 'shift', or None when none of them is established. Build 623 (owner: "download and apply ... they dont match and timing is off"): the first of
    13 results was applied and the check could not decide ('unknown'); the next few are now tried and the best supported one kept."""
    best = None
    for selected, name, data in files:
        try:
            fit = compare(heard, cues(data, name))
        except Exception:
            continue
        how, seconds = verdict(fit)
        if how in ('fits', 'shift') and (best is None or fit['agreement'] > best[0]):
            best = (fit['agreement'], selected, name, data, how, seconds)
    return best[1:] if best else None


def describe(selected):
    """The log words for what a check found (set on the result by apply): 'unknown (agreement 0.21, shift 0.0 s)'."""
    how = selected.get('match_speech')
    if not how:
        return 'no verdict'
    agreement = selected.get('match_speech_agreement')
    return '%s (agreement %s, shift %.1f s)' % (how, 'n/a' if agreement is None else '%.2f' % agreement, float(selected.get('match_speech_shift') or 0))

