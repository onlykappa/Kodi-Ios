"""F1 (PR #24 roadmap): a video is made AirPlay-ready while it is copied from AllDebrid to Google Drive.

Build-356 log 7249de4d: every re-packaged file crossed the phone three times (AllDebrid -> Drive, then Drive -> phone ->
Drive for the re-package), and 27 episodes waited behind one re-package. The converter already writes its output as a
stream (a fragmented, indexed MP4 through drive_prepare.Sink), so for a file whose picture is only copied it can read the
AllDebrid link directly, through the Drive stream's local block cache (DriveStream.add_external), and the result lands on
Drive ready, with the preparation marker, in the show's folder. No second trip, no "Up next" wait.

Only files that would need a re-package take this path (a compatible H.264 / HEVC picture in an MKV, or an MP4 with its
index at the end). A file that needs a real re-encode, or already opens fast, is copied as before (copy() returns None)
and the usual preparation decides. Anything that goes wrong here that is not the network also falls back to the plain
copy, so a download never depends on this path. Nothing is put in place on Drive before it is verified against the source
(same checks as a preparation: marker, size, picture, duration, tracks, seeks).
"""
import hashlib
import json
import threading
import time
import types
import urllib.parse

import drive_prepare
import driveupload
import prepare_downloads as prep
import resume_store

LANES = 3            # converters at once (the native test runs three; each has its own Drive upload)
TRIES = 3            # starts per file before it is copied plainly instead
_gate = threading.BoundedSemaphore(LANES)


def slot_for(key):
    return 'f1-' + hashlib.sha1(str(key).encode('utf-8')).hexdigest()[:16]


def _probe(native, url, going):
    """native.probe with this copy's own stop check (Native.probe reads self.keep_going, which the queue owns)."""
    if hasattr(native, 'lib'):
        return prep.Native.probe(types.SimpleNamespace(lib=native.lib, keep_going=going), url)
    return native.probe(url)


class LowQuality(RuntimeError):
    """ISSUE-236: the file is lower than the quality the owner chose; the copy ends here, before anything reaches Drive."""
    low_quality = True


def quality_problem(before, quality):
    """'' or why this probed picture is not the quality chosen (prepare_downloads.below_wanted)."""
    if quality and prep.below_wanted(before, quality):
        return 'Not the quality you picked: %sx%s, you chose %s' % (before.get('width'), before.get('height'), quality)
    return ''


def check_quality(q, with_link, key, going, quality):
    """Probe the AllDebrid file (a few seconds of reads) and raise LowQuality when it is lower than `quality`. Used when
    the file is not made ready on its way (F1 off), so a plain copy is checked too."""
    native, stream = getattr(q, 'native', None), getattr(q, 'stream', None)
    if not quality or not (native and stream and hasattr(stream, 'add_external')):
        return
    source = stream.add_external('debrid-' + slot_for(key), with_link)
    why = quality_problem(_probe(native, source, going), quality)
    if why:
        raise LowQuality(why)


def wanted(before, layout):
    """True when the file would need a re-package: picture copied, and it does not open fast as it is."""
    return prep.streamable_video(before) and (layout or {}).get('fast_open') is False


def copy(q, profile, with_link, name, size, parent, going, progress, key, log=lambda text: None, hold=lambda: False,
         clock=time.monotonic, quality=''):
    """Make `name` (size bytes, read through with_link) ready on Drive in folder `parent`.
    Returns {'id', 'name', 'size'} of the ready Drive file, or None when it should be copied plainly.
    Raises driveupload.Stop (paused / cancelled) and network errors (the caller waits and tries again; the upload carries
    on from its checkpoint)."""
    native, stream = getattr(q, 'native', None), getattr(q, 'stream', None)
    if not (native and stream and getattr(native, 'outputs', False) and hasattr(stream, 'add_external')):
        return None
    while not _gate.acquire(timeout=1):
        if not going():
            raise driveupload.Stop('Download paused')
    slot, item = slot_for(key), 'debrid-' + slot_for(key)
    outputs, sink, staged = {}, None, None
    try:
        source = stream.add_external(item, with_link)
        before = _probe(native, source, going)
        why = quality_problem(before, quality)   # ISSUE-236 (owner log 58fc390e): never copy 640x480 for a 1080p season
        if why:
            raise LowQuality(why)
        layout = q.layout_probe(source, int(size), going) if prep.streamable_video(before) else {}
        if not wanted(before, layout):
            return None
        log('%s: made ready while it copies (%s, %sx%s, %s)' % (name, before.get('codec'), before.get('width'),
                                                                 before.get('height'), layout.get('layout_reason', 'index')))
        staging = q.drive.folder([driveupload.TOP, '.Preparation'])
        identity = ('debrid', name, int(size))
        resumes = bool(getattr(native, 'resumes', False))
        checkpoint = resume_store.load(profile, slot, identity) if resumes else None
        if checkpoint:
            checkpoint = resume_store.fit(checkpoint, resume_store.confirmed(q.drive, checkpoint), True)
        if not checkpoint:
            resume_store.clear(profile, slot)
        sink = drive_prepare.Sink(q.drive, staging, slot, going, lambda track, result: outputs.__setitem__(track, result),
                                  hold=hold, spool=str(resume_store.folder(profile)) if resumes else None,
                                  checkpoint=checkpoint, keep_pieces=False,
                                  on_checkpoint=lambda cp: resume_store.save(profile, slot, identity, cp))
        if hasattr(stream, 'widen'):
            stream.widen(item)
        seen = [0.0, 0.0]

        def made(stage, n, t):
            # The card's percentage: how much of the film is made (the upload follows it closely), at most once a second.
            if stage in (0, 2) and t:
                seen[0] = max(seen[0], min(1.0, float(n) / t))
            now = clock()
            if now - seen[1] >= 1:
                seen[1] = now
                progress(int(min(0.97, seen[0]) * size), size)
        native.convert_to(source, sink, going, made, None, None, resume=checkpoint['mark'] if checkpoint else None)
        sink.finish()
        resume_store.clear(profile, slot)
        main = outputs['0']
        staged = main['id']
        target = stream.url(staged)
        after = _probe(native, target, going)
        if not after.get('ready') or (before.get('width'), before.get('height'), before.get('hdr')) != (
                after.get('width'), after.get('height'), after.get('hdr')):
            raise RuntimeError('Prepared video did not preserve resolution/HDR')
        native.verify(source, target)   # duration, every track, middle and end seeks, both over HTTP
        base = name.rsplit('.', 1)[0]
        for track, side in outputs.items():   # picture-subtitle files written beside the movie
            if track == '0':
                continue
            status, _, _ = q.drive.call('PATCH', driveupload.API + '/' + urllib.parse.quote(side['id'], safe='') +
                                        '?addParents=' + urllib.parse.quote(parent, safe='') +
                                        '&removeParents=' + urllib.parse.quote(staging, safe=''),
                                        json.dumps({'name': base + side['name'][len(slot):]}).encode(),
                                        {'Content-Type': 'application/json'})
            if status != 200:
                raise RuntimeError('Subtitle save: HTTP %d' % status)
        new = drive_prepare.promote(q.drive, {'name': name}, main, parent, staging)
        staged = None
        progress(size, size)
        return {'id': new.get('id') or main['id'], 'name': new.get('name') or base + '.mp4', 'size': int(main['size'])}
    except driveupload.Stop:
        if staged:   # stopped while checking a finished file: it is made again next time, nothing unverified stays
            for side in outputs.values():
                try:
                    drive_prepare.discard(q.drive, side['id'])
                except Exception:
                    pass
        raise
    except prep.ResumeFailed as error:
        resume_store.clear(profile, slot)
        log('%s: could not carry on where it stopped (%s); it starts again' % (name, error))
        raise driveupload.Stop('Starting again')
    except Exception as error:
        import debrid_drive
        if staged:   # made but not verified: never left behind, never put in place
            for side in outputs.values():
                try:
                    drive_prepare.discard(q.drive, side['id'])
                except Exception:
                    pass
            resume_store.clear(profile, slot)
        if debrid_drive.network_error(error) or getattr(error, 'low_quality', False):
            # ISSUE-244 (owner log 3df2f247: six 640x480 episodes "not made ready while copying (LowQuality …); copying it
            # as it is", each copied in full and sent to the Trash minutes later): a refused quality is never copied.
            raise
        resume_store.clear(profile, slot)
        log('%s: not made ready while copying (%s: %s); copying it as it is' % (name, type(error).__name__, str(error)[:120]))
        return None
    finally:
        if sink is not None and (staged or '0' not in outputs):
            try:
                sink.close()
                sink.tracks.clear()
            except Exception:
                pass
        for ident in (item, staged or (outputs.get('0') or {}).get('id')):
            if ident:
                stream.forget(ident)
        if hasattr(stream, 'unwide'):
            stream.unwide(item)
        _gate.release()
