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
            if stsz and stsz[0] + 12 <= stsz[1]:   # how many subtitle samples the track holds: 0 or 1 is an empty track that draws nothing
                info['samples'] = struct.unpack_from('>I', data, stsz[0] + 8)[0]
            out.append(info)
        except (struct.error, IndexError):
            continue
    return out


def describe(tracks):
    """One log line: 'tracks in file: #3 eng tx3g (sbtl); #4 eng c608 (clcp)'."""
    if not tracks:
        return 'no subtitle track in the first bytes of the file'
    return '; '.join('#%s %s %s (%s)%s' % (t['id'], t['language'], t['codec'] or '?', t['handler'],
                                           '' if t.get('samples') is None else ', %d samples' % t['samples']) for t in tracks)
