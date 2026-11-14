"""AI Upscale copies on Google Drive (DEC-039/DEC-040/DEC-042): the preparation queue's step that makes them.

Between conversions (one AI engine at a time) the service calls process_one(). It plans a copy for every prepared
720p/1080p download whose show (or the default for new downloads) asks for a larger size (upscale_queue.plan), then
makes the oldest one due:
  1. the phone must be allowed to (charger, battery, Low Power Mode, heat: upscale_queue.may_run) and Drive must have
     room (upscale_queue.drive_room); the AI model is fetched first when the iPhone does not have it yet;
  2. the prepared original is read from Drive and converted with the upscaler (KodiAirPlay r48: convert_to(...,
     upscale=(box width, box height, engine, kbps))) straight into Drive's .Preparation folder (drive_prepare.Sink, the
     same pieces the conversion uses; nothing is kept on the phone);
  3. the copy is checked (it is the size asked for, it plays: probe) and moved beside the original as
     '<name> [AI 4K UHD].mp4' (upscale_queue.copy_name); the original is kept (DEC-040: AirPlay of the original keeps
     working, and Off plays it);
  4. upscale-copies.json says 'ready' with the copy's Drive id; a copy at another size it replaces goes to the bin.
A stop (Kodi closing, the owner's Pause, the phone getting hot) leaves it 'waiting'; it starts over next time. Other
errors retry with upscale_queue.failed's back-off; HDR, already-this-size and no-AI-engine are final ('blocked').
"""
import json
import time
import urllib.parse

import picture
import upscale_queue as uq

ENGINE_AUTO = 0
MODEL_READY = 2
SIDECAR_NOTE = 'subtitle sidecars are not kept for a copy (the original keeps them)'


def device(native):
    try:
        return native.device_state() or {}
    except Exception:
        return {}


def _status_text(entry, why):
    entry['note'] = why
    return entry


def _prep_waiting(q):
    """A video waits to be prepared (it goes before an AI Upscale copy)."""
    try:
        now = time.time()
        return any(j.get('status') in ('waiting', 'paused') and not j.get('kept') and not j.get('blocked')
                   and j.get('retry_after', 0) <= now for j in list((q.state.get('jobs') or {}).values()))
    except Exception:
        return False


def _on_screen():
    try:
        import app_state
        return app_state.foreground()
    except Exception:
        return True


# ISSUE-241 (owner log 1ae21097: Phony S1 E2, 1920x1080 to 4K, failed after 2 min with "video conversion: encode: Generic
# error in an external library"): that is FFmpeg's AVERROR_EXTERNAL from Apple's hardware encoder (VideoToolbox), which
# refuses frames once its session is gone: iOS ends encoder sessions and GPU work (the upscaler runs on the GPU) while an
# app is in the background, and under memory pressure. A fresh session normally works, so it is not the video's fault.
ENCODER_TROUBLE = ('Generic error in an external library', 'Insufficient Permission', 'kVTInvalidSessionErr', '-12903',
                   '-12902', '-12905', 'GPU work from background')


def _encoder_trouble(error):
    return any(word in str(error) for word in ENCODER_TROUBLE)


def process_one(q, keep_going, settings=None, media_for=lambda job: {}, free_bytes=None, clock=time.time, on_screen=_on_screen):
    """Plans and makes at most one copy. Returns True when it did work (a copy made, or a step that changed state)."""
    import drive_prepare
    import driveupload
    profile = q.profile
    settings = settings if settings is not None else picture.load(profile)
    data = uq.load(profile)
    # Settings › AI Upscale's status card reads this (the page does not load the native library itself).
    import upscale_page
    engine = upscale_page.engine_state(q.native)
    wants_model = data.pop('model_request', False)
    if wants_model and engine.get('model') == 0:
        q.native.upscale_model(1920, 1080, '4K UHD', ENGINE_AUTO, start=True)
        engine['model'] = 1
        q.log('upscale: downloading the AI model (asked for in Settings)')
    if data.get('engine') != engine or wants_model:
        data['engine'] = engine
        uq.save(profile, data)
    # Board C "Remove the copies…": each copy goes to Drive's Trash (30 days); waiting ones are dropped.
    removing = data.pop('remove', None) or []
    for original in removing:
        entry = data.get('copies', {}).get(original)
        if not entry:
            continue
        if entry.get('copy_id'):
            try:
                drive_prepare.bin(q.drive, entry['copy_id'])
            except Exception as error:
                q.log('upscale: a copy was not sent to the bin: %s' % error)
                data.setdefault('remove', []).append(original)   # tried again next pass
                continue
        entry.update(status='gone', copy_id=None, progress=0)
    if removing:
        uq.save(profile, data)
        q.log('upscale: %d copies removed (Settings › AI Upscale)' % len(removing))
    # DEC-044: Pause, Cancel this copy, Remove from Up next, the new order and Cancel All from the page.
    if uq.apply_control(profile, data, clock):
        uq.save(profile, data)
    if uq.paused(profile):
        return False
    added = uq.plan(q.state, data, settings, media_for, clock)
    if added:
        q.log('upscale: %d copy%s to make (%s)' % (len(added), '' if len(added) == 1 else ' copies',
                                                  ', '.join(data['copies'][k]['label'] for k in added)))
        uq.save(profile, data)
    key = uq.next_job(data, clock)
    if not key:
        return bool(added)
    entry = data['copies'][key]
    if entry.get('needs_screen') and not on_screen():
        # ISSUE-241: its encoder stopped while Kodi was in the background; it is made while Kodi is on screen.
        if entry.get('note') != 'Waits for Kodi to be open':
            _status_text(entry, 'Waits for Kodi to be open')
            uq.save(profile, data)
        return False
    native = q.native
    if not getattr(native, 'upscales', False):
        uq.failed(entry, 'AI Upscale is not available on this device (needs KodiAirPlay r48)', clock)
        uq.save(profile, data)
        return True
    allowed, why = uq.may_run(device(native), settings)
    if not allowed:
        if entry.get('note') != why:
            _status_text(entry, why)
            uq.save(profile, data)
        return False
    room, needed = uq.drive_room(free_bytes() if callable(free_bytes) else free_bytes, entry)
    if not room:
        if entry.get('note') != 'Not enough space on Google Drive':
            _status_text(entry, 'Not enough space on Google Drive')
            uq.save(profile, data)
        return False
    width, height = int(entry.get('width') or 0), int(entry.get('height') or 0)
    label = entry['label']
    size = picture.fitted(width or 1920, height or 1080, label)
    if not size:
        uq.failed(entry, 'The video is already this size', clock)
        uq.save(profile, data)
        return True
    # Only an AI model whose pictures are no larger than the size asked for (owner logs 0afdfd7b / 1ff17f50: the 4x image
    # model made 7680x4320 frames from 1080p and iOS closed Kodi). None fits: blocked, with the reason.
    try:
        engine, why = uq.pick_engine(native.upscale_support(width, height, label), width, height, label)
    except Exception as error:
        engine, why = None, 'not available on this device (%s)' % error
    if engine is None:
        uq.failed(entry, 'AI Upscale is ' + why, clock)
        uq.save(profile, data)
        q.log('upscale: %s' % why)
        return True
    # The AI model (Apple's, a one-time download per size) comes first.
    try:
        model = native.upscale_model(width, height, label, engine)
    except Exception as error:
        uq.failed(entry, error, clock)
        uq.save(profile, data)
        return True
    if model == -1:
        uq.failed(entry, 'AI Upscale is not available on this device for this size', clock)
        uq.save(profile, data)
        return True
    if model != MODEL_READY:
        if model == 0:
            native.upscale_model(width, height, label, engine, start=True)
            q.log('upscale: downloading the AI model for %s' % label)
        _status_text(entry, 'Downloading the AI model')
        uq.save(profile, data)
        return False
    entry.pop('note', None)
    entry['status'] = 'running'
    entry['started'] = clock()
    entry['progress'] = 0
    uq.save(profile, data)
    title = entry.get('name') or key
    try:
        import drivelibrary
        title = drivelibrary.display_title(title) or title
    except Exception:
        pass
    q.log('upscale: %s — %dx%d to %s (%dx%d)' % (title, width, height, label, size[0], size[1]))
    outputs = {}
    began = clock()
    marks = {'saved': 0.0}

    def on_file(track, result):
        outputs[track] = result

    def progress(stage, n, t):
        if not keep_going():
            raise driveupload.Stop('AI Upscale paused')
        if uq.cancelling(profile, key):
            raise driveupload.Stop('cancelled')
        # Owner (2026-11-13): everything ready before it is watched. A video waiting to be prepared goes first; this
        # copy stops and starts again later (owner log 20d8a992: one copy held 23 videos for 15 min).
        if not uq.paused(profile) and _prep_waiting(q):
            raise driveupload.Stop('a video waits to be prepared')
        # Pause (DEC-044 board A/B1): the converter holds where it is (going() False, held() True) until Resume, unless a
        # video waits to be prepared, which goes first; this copy then starts again later.
        while uq.paused(profile) and not uq.cancelling(profile, key) and not _prep_waiting(q):
            entry['note'] = 'Paused by you'
            time.sleep(1)
            if not keep_going():
                raise driveupload.Stop('AI Upscale paused')
        if uq.paused(profile) and not uq.cancelling(profile, key):
            raise driveupload.Stop('AI Upscale paused')   # a video waits to be prepared: it goes first
        entry.pop('note', None)
        if stage in (0, 2) and t:
            pct = int(100 * min(1.0, float(n) / t))
            if pct > entry.get('progress', 0):
                entry['progress'] = pct
                now = clock()
                if pct and now - began > 5:
                    entry['eta'] = _eta((now - began) * (100 - pct) / pct)
                if now - marks['saved'] >= 5:
                    marks['saved'] = now
                    uq.save(profile, data)

    staging = q.drive.folder([driveupload.TOP, '.Preparation'])
    sink = drive_prepare.Sink(q.drive, staging, 'upscale-' + key, keep_going, on_file,
                              hold=lambda: bool(getattr(q, 'paused', lambda: False)()))
    source = q.stream.url(key)
    try:
        try:
            bw, bh = picture.box(label)
            native.convert_to(source, sink, keep_going, progress, getattr(q, 'paused', None), None,
                              upscale=(bw, bh, engine, int(settings.get('downloads', {}).get('kbps') or 0)))
            sink.finish()
        except Exception:
            sink.close()
            raise
        finally:
            try:
                q.stream.forget(key)
            except Exception:
                pass
        main = outputs.get('0')
        if not main:
            raise RuntimeError('The converter gave no video')
        for track, side in outputs.items():
            if track != '0':
                try:
                    drive_prepare.discard(q.drive, side['id'])
                except Exception:
                    pass
        after = native.probe(q.stream.url(main['id']))
        got = (int(after.get('width') or 0), int(after.get('height') or 0))
        if not after.get('ready') or abs(got[0] - size[0]) > 2 or abs(got[1] - size[1]) > 2:
            drive_prepare.discard(q.drive, main['id'])
            raise RuntimeError('The copy is %dx%d, not %dx%d' % (got[0], got[1], size[0], size[1]))
        parent = original_parent(q.drive, key)
        name = uq.copy_name(entry.get('name') or title, label)
        move(q.drive, main['id'], parent, staging, name)
    except driveupload.Stop:
        if uq.cancelling(profile, key):
            uq.apply_control(profile, data, clock)       # DEC-044: cancelled by the owner; not made again
            uq.save(profile, data)
            q.log('upscale: %s — cancelled' % title)
            return True
        entry['status'] = 'waiting'
        entry['progress'] = 0
        entry.pop('eta', None)
        uq.save(profile, data)
        q.log('upscale: %s — stopped; it starts again later' % title)
        return False
    except Exception as error:
        if _encoder_trouble(error):
            screen = on_screen()
            entry['encoder_tries'] = entry.get('encoder_tries', 0) + (1 if screen else 0)
            if not screen or entry['encoder_tries'] <= 1:
                # In the background: it waits for Kodi to be on screen (not a failure). On screen: one more try with a new
                # encoder in 30 s; a second refusal on screen is a real failure (back-off below).
                entry['status'] = 'waiting'
                entry['progress'] = 0
                entry['retry_after'] = clock() + (0 if not screen else 30)
                entry['needs_screen'] = True
                entry['note'] = 'Waits for Kodi to be open' if not screen else 'Starting the AI engine again'
                entry.pop('eta', None)
                entry.pop('error', None)
                uq.save(profile, data)
                q.log('upscale: %s — the video encoder stopped (%s) while Kodi was %s; %s' % (
                    title, str(error)[:100], 'on screen' if screen else 'in the background',
                    'trying again in 30 s with a new encoder' if screen else 'it carries on when Kodi is open'))
                return False
        if _network_trouble(error):
            # ISSUE-198 / owner log (2026-11-13, "Source read: Input/output error" after 2 minutes on a Drive file streamed
            # through the loopback proxy): the network is not the video's fault. Wait 15 s up to 5 min, then start again
            # (the converter's resume mark is not used for AI Upscale yet, so it restarts from the beginning); it never
            # counts as a failure and never enters the long back-off.
            import debrid_drive
            entry['net_attempts'] = entry.get('net_attempts', 0) + 1
            wait = debrid_drive.net_wait(entry['net_attempts'])
            entry['status'] = 'waiting'
            entry['progress'] = 0
            entry['retry_after'] = clock() + wait
            entry['note'] = 'Waiting for the network'
            entry.pop('eta', None)
            entry.pop('error', None)
            uq.save(profile, data)
            q.log('upscale: %s — network trouble (%s); trying again in %d s' % (title, str(error)[:100], wait))
            return False
        uq.failed(entry, error, clock)
        uq.save(profile, data)
        q.log('upscale: %s — failed: %s' % (title, str(error)[:200]))
        return True
    entry.pop('net_attempts', None)
    entry.pop('encoder_tries', None)
    entry.pop('needs_screen', None)
    old = entry.get('previous_copy')
    entry.update(status='ready', copy_id=main['id'], size=int(main.get('size') or 0), progress=100,
                 finished=clock(), took=round(clock() - began))
    entry.pop('eta', None)
    entry.pop('error', None)
    entry.pop('previous_copy', None)
    uq.save(profile, data)
    if old and old != main['id']:
        try:
            drive_prepare.bin(q.drive, old)
        except Exception as error:
            q.log('upscale: the old copy was not sent to the bin: %s' % error)
    q.log('upscale: %s — %s copy ready (%.1f GB, %.0f min)' % (title, label, entry['size'] / 1e9, (clock() - began) / 60))
    try:
        q.notify('info', 'AI Upscale ready', '%s · %s' % (title, label))
    except Exception:
        pass
    return True


def media_lookup(profile, parse=None):
    """media_for(job) for plan(): the show a prepared Drive file belongs to. A download the app queued knows its show's
    TMDb id (debrid_drive's job, by the file's Drive id); any other file goes by the title in its name, which is also
    how picture.show_key names a show without TMDb."""
    try:
        import debrid_drive
        jobs = debrid_drive.load(profile).get('jobs', [])
    except Exception:
        jobs = []
    by_id = {}
    for job in jobs:
        for f in job.get('files') or []:
            if f.get('drive_id'):
                by_id[str(f['drive_id'])] = job

    def media_for(prep_job):
        ids = [str(prep_job.get('prepared_id') or ''), str((prep_job.get('source') or {}).get('id') or '')]
        name = (prep_job.get('source') or {}).get('name', '')
        found = next((by_id[i] for i in ids if i in by_id), None)
        if found and found.get('show_tmdb'):
            return {'tmdb': found['show_tmdb'], 'type': 'tv', 'show': found.get('title') or '', 'drive_id': ids[0] or ids[1],
                    'season': found.get('season') or '', 'episode': found.get('episode') or ''}
        info = {}
        if parse is not None:
            try:
                info = parse(name) or {}
            except Exception:
                info = {}
        kind = 'tv' if info.get('season') or info.get('episode') else 'movie'
        return {'type': kind, 'show': info.get('title') or '', 'drive_id': ids[0] or ids[1],
                'season': info.get('season') or '', 'episode': info.get('episode') or ''}
    return media_for


def _network_trouble(error):
    """True for trouble that goes away by itself (a dropped read, a timeout, a 5xx), never for a final answer (HDR, wrong
    size, no engine) or a wrong-size copy."""
    import debrid_drive
    text = str(error)
    if any(word in text for word in ('HDR', 'already this size', 'not available on this device', 'needs iOS 26', 'The copy is ')):
        return False
    return bool(debrid_drive.network_error(error))


def _eta(seconds):
    seconds = int(max(0, seconds))
    if seconds >= 3600:
        return 'about %d h %d min' % (seconds // 3600, seconds % 3600 // 60)
    return 'about %d min' % max(1, seconds // 60)


def original_parent(drive, item_id):
    import driveupload
    status, _, body = drive.call('GET', driveupload.API + '/' + urllib.parse.quote(str(item_id), safe='') + '?fields=parents')
    if status != 200:
        raise RuntimeError('The original on Drive: HTTP %d' % status)
    parents = json.loads(body).get('parents') or []
    if not parents:
        raise RuntimeError('Drive did not describe the video folder')
    return parents[0]


def move(drive, item_id, parent, staging, name):
    """The copy leaves .Preparation for the original's folder, under its own name."""
    import driveupload
    status, _, _ = drive.call('PATCH', driveupload.API + '/' + urllib.parse.quote(str(item_id), safe='') +
                              '?addParents=' + urllib.parse.quote(parent, safe='') +
                              '&removeParents=' + urllib.parse.quote(staging, safe=''),
                              json.dumps({'name': name}).encode(), {'Content-Type': 'application/json'})
    if status != 200:
        raise RuntimeError('Moving the copy beside the original: HTTP %d' % status)
