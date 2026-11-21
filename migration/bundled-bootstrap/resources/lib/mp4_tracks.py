"""The subtitle tracks an MP4 carries, read from its moov box (owner, 2026-11-20: "it says CC was on for the lanterns but they were not").

Kodi's track list gives a language and a name, never what kind of subtitle a stream is. Whether Kodi can draw it depends on that kind: tx3g (mov_text) is
text Kodi shows; wvtt (WebVTT), stpp (TTML) and c608/c708 (closed-caption data) may not be drawn at all, and a picture subtitle needs another
path. This reads the sample entry of every subtitle-like track from the first bytes of the file (the app's playback cache already holds them) so the
log says exactly what a video carries. Pure: it only parses bytes.
"""
import struct

SUBTITLE_HANDLERS = (b'sbtl', b'subt', b'text', b'clcp')


def _boxes(data, start, end):
    at = start
    while at + 8 <= end:
        size, kind = struct.unpack_from('>I4s', data, at)
        header = 8
        if size == 1 and at + 16 <= end:
            size = struct.unpack_from('>Q', data, at + 8)[0]
            header = 16
        elif size == 0:
            size = end - at
        if size < header or at + size > end + 0:   # a box cut off by the end of what was read: stop
            if size >= header and kind == b'moov':
                yield kind, at + header, end   # a moov we only have the start of: walk what is there
            return
        yield kind, at + header, at + size
        at += size


def _find(data, start, end, kind):
    return next(((a, b) for k, a, b in _boxes(data, start, end) if k == kind), None)


def _language(code):
    if not code or code == 0x55c4:
        return 'und'
    return ''.join(chr(((code >> shift) & 31) + 0x60) for shift in (10, 5, 0))


def subtitle_tracks(data):
    """[{'id', 'handler', 'codec', 'language', 'samples'}] for each subtitle-like track in the moov of `data`; [] when there is none or it is not in `data`."""
    out = []
    data = bytes(data)
    moov = _find(data, 0, len(data), b'moov')
    if not moov:
        return out
    fragmented = _find(data, moov[0], moov[1], b'mvex') is not None   # a fragmented file keeps its samples in moof boxes: the moov counts 0 for every track
    for kind, a, b in _boxes(data, moov[0], moov[1]):
        if kind != b'trak':
            continue
        try:
            info = {'id': 0, 'handler': '', 'codec': '', 'language': '', 'samples': None}
            tkhd = _find(data, a, b, b'tkhd')
            if tkhd:
                version = data[tkhd[0]]
                info['id'] = struct.unpack_from('>I', data, tkhd[0] + (20 if version == 1 else 12))[0]
            mdia = _find(data, a, b, b'mdia')
            if not mdia:
                continue
            mdhd = _find(data, mdia[0], mdia[1], b'mdhd')
            if mdhd:
                version = data[mdhd[0]]
                info['language'] = _language(struct.unpack_from('>H', data, mdhd[0] + (32 if version == 1 else 20))[0])
            hdlr = _find(data, mdia[0], mdia[1], b'hdlr')
            handler = bytes(data[hdlr[0] + 8:hdlr[0] + 12]) if hdlr else b''
            if handler not in SUBTITLE_HANDLERS:
                continue
            info['handler'] = handler.decode('ascii', 'replace')
            minf = _find(data, mdia[0], mdia[1], b'minf')
            stbl = _find(data, minf[0], minf[1], b'stbl') if minf else None
            stsd = _find(data, stbl[0], stbl[1], b'stsd') if stbl else None
            if stsd:
                info['codec'] = bytes(data[stsd[0] + 12:stsd[0] + 16]).decode('ascii', 'replace')
            stsz = _find(data, stbl[0], stbl[1], b'stsz') if stbl else None
            if stsz and not fragmented and stsz[0] + 12 <= stsz[1]:   # how many subtitle samples the track holds: 0 or 1 is an empty track that draws nothing
                info['samples'] = struct.unpack_from('>I', data, stsz[0] + 8)[0]
            out.append(info)
        except (struct.error, IndexError):
            continue
    return out


def track_timescales(data):
    """{track id: media timescale} for every track in the moov of `data` (the index's times are in these units); {} when not there."""
    out = {}
    data = bytes(data)
    moov = _find(data, 0, len(data), b'moov')
    if not moov:
        return out
    for kind, a, b in _boxes(data, moov[0], moov[1]):
        if kind != b'trak':
            continue
        try:
            tkhd = _find(data, a, b, b'tkhd')
            mdia = _find(data, a, b, b'mdia')
            mdhd = _find(data, mdia[0], mdia[1], b'mdhd') if mdia else None
            if not tkhd or not mdhd:
                continue
            ident = struct.unpack_from('>I', data, tkhd[0] + (20 if data[tkhd[0]] == 1 else 12))[0]
            scale = struct.unpack_from('>I', data, mdhd[0] + (20 if data[mdhd[0]] == 1 else 12))[0]
            if scale:
                out[ident] = scale
        except (struct.error, IndexError):
            continue
    return out


def fragment_spans(mfra, scales):
    """{track id: (first, last)} in seconds: when the first and the last fragment holding samples of the track begin, from the tfra times of a fragmented
    file's mfra and the tracks' timescales. Build 622 asked "are the captions there?"; this also says where they sit against the video's own span, so
    cues at the wrong times (or none beyond the start) show in the log. {} when unreadable."""
    out = {}
    try:
        mfra = bytes(mfra)
        at, end = 8, len(mfra) - 16
        while at + 8 <= end:
            length, kind = struct.unpack_from('>I4s', mfra, at)
            if length < 8 or at + length > end:
                break
            if kind == b'tfra' and length >= 24:
                version = mfra[at + 8]
                track, sizes, count = struct.unpack_from('>III', mfra, at + 12)
                width = 8 if version == 1 else 4
                step = 2 * width + (((sizes >> 4) & 3) + 1) + (((sizes >> 2) & 3) + 1) + ((sizes & 3) + 1)
                scale = scales.get(track)
                if count and scale and 24 + count * step <= length:
                    fmt = '>Q' if version == 1 else '>I'
                    first = struct.unpack_from(fmt, mfra, at + 24)[0]
                    last = struct.unpack_from(fmt, mfra, at + 24 + (count - 1) * step)[0]
                    out[track] = (first / scale, last / scale)
            at += length
    except (struct.error, IndexError):
        return {}
    return out


def fragment_entries(mfra, limit=3):
    """{track id: [(time in track units, moof offset)]} for the first `limit` entries of each tfra in a fragmented file's mfra; {} when unreadable."""
    out = {}
    try:
        mfra = bytes(mfra)
        at, end = 8, len(mfra) - 16
        while at + 8 <= end:
            length, kind = struct.unpack_from('>I4s', mfra, at)
            if length < 8 or at + length > end:
                break
            if kind == b'tfra' and length >= 24:
                version = mfra[at + 8]
                track, sizes, count = struct.unpack_from('>III', mfra, at + 12)
                width = 8 if version == 1 else 4
                step = 2 * width + (((sizes >> 4) & 3) + 1) + (((sizes >> 2) & 3) + 1) + ((sizes & 3) + 1)
                fmt = '>QQ' if version == 1 else '>II'
                rows = []
                for n in range(min(limit, count)):
                    if 24 + (n + 1) * step > length:
                        break
                    rows.append(struct.unpack_from(fmt, mfra, at + 24 + n * step))
                out[track] = rows
            at += length
    except (struct.error, IndexError):
        return {}
    return out


def moof_samples(data, offset, scales):
    """{track id: [(start s, duration s, size bytes)]} for the samples of every track in the moof that begins at `offset` of the file, where `data` holds
    the file's bytes from `offset` on. Reads tfhd, tfdt and trun (default sizes and durations included). {} when it is not a moof."""
    out = {}
    try:
        data = bytes(data)
        size, kind = struct.unpack_from('>I4s', data, 0)
        if kind != b'moof':
            return out
        for k, a, b in _boxes(data, 8, min(size, len(data))):
            if k != b'traf':
                continue
            track = flags = default_duration = default_size = base = None
            default_duration = default_size = 0
            decode = 0
            samples = []
            for k2, a2, b2 in _boxes(data, a, b):
                if k2 == b'tfhd':
                    flags = struct.unpack_from('>I', data, a2)[0] & 0xFFFFFF
                    track = struct.unpack_from('>I', data, a2 + 4)[0]
                    at = a2 + 8
                    if flags & 1:
                        at += 8
                    if flags & 2:
                        at += 4
                    if flags & 8:
                        default_duration = struct.unpack_from('>I', data, at)[0]
                        at += 4
                    if flags & 0x10:
                        default_size = struct.unpack_from('>I', data, at)[0]
                elif k2 == b'tfdt':
                    version = data[a2]
                    decode = struct.unpack_from('>Q' if version == 1 else '>I', data, a2 + 4)[0]
                elif k2 == b'trun':
                    tflags = struct.unpack_from('>I', data, a2)[0] & 0xFFFFFF
                    count = struct.unpack_from('>I', data, a2 + 4)[0]
                    at = a2 + 8
                    if tflags & 1:
                        at += 4
                    if tflags & 4:
                        at += 4
                    for _ in range(min(count, 5000)):
                        duration, length = default_duration, default_size
                        if tflags & 0x100:
                            duration = struct.unpack_from('>I', data, at)[0]
                            at += 4
                        if tflags & 0x200:
                            length = struct.unpack_from('>I', data, at)[0]
                            at += 4
                        if tflags & 0x400:
                            at += 4
                        if tflags & 0x800:
                            at += 4
                        samples.append((decode, duration, length))
                        decode += duration
            scale = scales.get(track)
            if track is not None and scale:
                out.setdefault(track, []).extend((start / scale, duration / scale, length) for start, duration, length in samples)
    except (struct.error, IndexError):
        return out
    return out


def cue_summary(samples, empty=2):
    """One short phrase for a subtitle track's samples in one fragment: how many hold text (a tx3g sample of `empty` bytes or fewer is the blank that clears
    the screen), the first text sample's start and its length, and the total time the text is up. 'no samples' for an empty list."""
    if not samples:
        return 'no samples'
    text = [(start, duration, length) for start, duration, length in samples if length > empty]
    if not text:
        return '%d samples, none with text' % len(samples)
    return '%d samples, %d with text, first text at %.1f s (%d bytes), %.1f s of text' % (
        len(samples), len(text), text[0][0], text[0][2], sum(d for _, d, _ in text))


def fragment_counts(mfra):
    """{track id: how many fragments hold samples of it} from a fragmented MP4's mfra box (its fragment index, at the end of the file); {} when unreadable.
    Build 622 (owner log ac85bba1: The Lanterns' captions "on" and nothing drawn): a fragmented file's moov counts no samples, so an empty embedded subtitle
    track could not be told from a full one. A track in at most one fragment of a long video holds no real captions."""
    out = {}
    try:
        mfra = bytes(mfra)
        at, end = 8, len(mfra) - 16
        while at + 8 <= end:
            length, kind = struct.unpack_from('>I4s', mfra, at)
            if length < 8 or at + length > end:
                break
            if kind == b'tfra' and length >= 24:
                track, sizes, count = struct.unpack_from('>III', mfra, at + 12)
                out[track] = int(count)
            at += length
    except (struct.error, IndexError):
        return {}
    return out


def with_fragment_counts(tracks, counts, minimum=10):
    """Give each subtitle track of a fragmented file its fragment count as `samples` (see subtitle_tracks) once the file has at least `minimum`
    fragments: fewer is too short a video to call a track empty."""
    if not counts or max(counts.values()) < minimum:
        return tracks
    for track in tracks:
        if track.get('samples') is None:
            track['samples'] = counts.get(track.get('id'), 0)
            track['fragments'] = True
    return tracks


def with_spans(tracks, spans):
    """Put `first` and `last` (seconds) on each subtitle track that has a span in `spans` (see fragment_spans)."""
    for track in tracks:
        if track.get('id') in spans:
            track['first'], track['last'] = spans[track['id']]
    return tracks


def span_text(first, last):
    return '%d s to %d s' % (round(first), round(last))


def video_span(tracks, spans):
    """The longest span among the tracks that are not subtitles: the picture's, to read the cues against."""
    ids = {t.get('id') for t in tracks}
    others = [v for k, v in spans.items() if k not in ids]
    return max(others, key=lambda v: v[1], default=None)


def describe(tracks, video=None):
    """One log line: 'tracks in file: #3 eng tx3g (sbtl); #4 eng c608 (clcp)'."""
    if not tracks:
        return 'no subtitle track in the first bytes of the file'
    line = '; '.join('#%s %s %s (%s)%s%s' % (t['id'], t['language'], t['codec'] or '?', t['handler'],
                                             '' if t.get('samples') is None else ', %d %s' % (t['samples'], 'fragments hold it' if t.get('fragments') else 'samples'),
                                             ', fragments from ' + span_text(t['first'], t['last']) if 'first' in t else '') for t in tracks)
    return line + (' | video fragments from ' + span_text(*video) if video else '')


def zero_length(samples, minimum=2, tiny=0.05):
    """True when a track's text cues have no length: at least `minimum` samples with text and together under `tiny` seconds of it. Build 634 log f75957fe: every
    text cue of the Lanterns' converted tracks was written with a length of 0 s (the next, blank sample begins at the same instant), so Kodi shows each for no time
    at all although it reports the track "on". samples: [(start s, duration s, size bytes)] from moof_samples."""
    text = [(a, d, z) for a, d, z in samples if z > 2]
    return len(text) >= minimum and sum(d for _, d, _ in text) < tiny


def probe(url, opener=None, timeout=3):
    """Read a fragmented MP4's subtitle tracks and its first fragments through `url` (the app's loopback proxy) and say which tracks have zero-length cues:
    {'tracks': [{'id', 'zero_length': bool}...] in the file's order, 'order': [ids]} or None when it cannot be read (not fragmented, not reachable)."""
    import urllib.request
    opener = opener or urllib.request.urlopen

    def get(first, last):
        with opener(urllib.request.Request(url, headers={'Range': 'bytes=%d-%d' % (first, last)}), timeout=timeout) as response:
            return response.read(last - first + 2), str(response.headers.get('Content-Range') or '')
    try:
        head, got = get(0, 1048575)
        total = int(got.rpartition('/')[2] or 0)
        tracks = subtitle_tracks(head)
        if not tracks or total <= 1048576:
            return None
        tail = get(total - 16, total - 1)[0]
        size = int.from_bytes(tail[-4:], 'big') if tail[-12:-8] == b'mfro' else 0
        if not 24 <= size <= 2 * 1024 * 1024:
            return None
        entries = fragment_entries(get(total - size, total - 1)[0], 3)
        scales = track_timescales(head)
        first = next((t['id'] for t in tracks if len(entries.get(t['id'], ())) > 1), None)
        seen = {t['id']: [] for t in tracks}
        for _, offset in entries.get(first, ()):
            found = moof_samples(get(offset, offset + 262143)[0], offset, scales)
            for t in tracks:
                seen[t['id']].extend(found.get(t['id'], []))
        return {'tracks': [{'id': t['id'], 'zero_length': zero_length(seen[t['id']])} for t in tracks], 'order': [t['id'] for t in tracks]}
    except Exception:
        return None

