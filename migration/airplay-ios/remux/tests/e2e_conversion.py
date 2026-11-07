"""End-to-end conversion test: the real KodiAirPlay converter (built for this computer) and the add-on's real queue
(prepare_cloud.process_one, drive_prepare.Sink, resume_store, driveupload.sender over HTTP) against a local Google
Drive stand-in that serves byte ranges and takes resumable uploads the way Google does (it keeps only whole 256 KiB
steps of an unfinished upload, can run slowly, and forgets upload sessions on request).

usage: e2e_conversion.py LIBKODIAIRPLAY.so FIXTURES_DIR [scenario ...]
Every scenario prints PASS/FAIL lines; the exit code is the number of failures."""
import ctypes, hashlib, http.server, json, os, shutil, socketserver, sys, tempfile, threading, time, traceback, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode = True
sys.path.insert(0, str(LIB))
import driveupload, drive_prepare, prepare_downloads as prep, resume_store  # noqa: E402

STEP = 256 * 1024
failures = []
LAST_SIZE = [0]   # the size of the last prepared movie
SKIPS = []        # runs that carried on past a mark (Drive's bytes kept)
LAST_DATA = [b'']


def check(ok, what):
    print(('PASS ' if ok else 'FAIL ') + what, flush=True)
    if not ok:failures.append(what)


class FakeDrive:
    def __init__(self):
        self.files, self.sessions, self.lock = {}, {}, threading.Lock()
        self.number = 0
        self.upload_rate = 0         # bytes/s for upload bodies (0: as fast as possible)
        self.served = {}             # id -> bytes read through /media
        self.puts = 0
        self.requests = {}           # id -> [(first, last)] ranges asked for

    def add(self, file_id, name, data, parents=('movies',), folder=False):
        self.files[file_id] = dict(id=file_id, name=name, data=bytes(data), parents=list(parents), appProperties={},
                                   version='1', trashed=False, mimeType='application/vnd.google-apps.folder' if folder else 'video/x-matroska')

    def meta(self, file_id):
        f = self.files[file_id]
        return dict({k: v for k, v in f.items() if k != 'data'}, size=str(len(f['data'])), md5Checksum=hashlib.md5(f['data']).hexdigest())


def handler_for(drive):
    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'
        def log_message(self, *a):pass
        def reply(self, status, body=b'', headers=None):
            self.send_response(status)
            for k, v in (headers or {}).items():self.send_header(k, v)
            self.send_header('Content-Length', str(len(body)));self.end_headers()
            if body and self.command != 'HEAD':self.wfile.write(body)
        def body(self):
            n = int(self.headers.get('Content-Length') or 0);out = bytearray()
            while len(out) < n:
                chunk = self.rfile.read(min(65536, n - len(out)))
                if not chunk:break
                out += chunk
                if drive.upload_rate and self.path.startswith('/upload/session/'):time.sleep(len(chunk) / drive.upload_rate)
            return bytes(out)
        def do_GET(self):
            u = urllib.parse.urlsplit(self.path);q = dict(urllib.parse.parse_qsl(u.query))
            if u.path.startswith('/media/'):
                fid = u.path.split('/')[2]
                if fid not in drive.files:return self.reply(404)
                data = drive.files[fid]['data'];rng = self.headers.get('Range')
                a, b = 0, len(data) - 1
                if rng:
                    a = int(rng[6:].split('-')[0]);e = rng[6:].split('-')[1];b = int(e) if e else len(data) - 1
                    b = min(b, len(data) - 1)
                    if a >= len(data):return self.reply(416, b'', {'Content-Range': 'bytes */%d' % len(data)})
                part = data[a:b + 1];drive.requests.setdefault(fid, []).append((a, b))
                self.send_response(206 if rng else 200)
                for k, v in {'Content-Range': 'bytes %d-%d/%d' % (a, b, len(data)), 'Accept-Ranges': 'bytes', 'Content-Type': 'video/mp4', 'Content-Length': str(len(part))}.items():self.send_header(k, v)
                self.end_headers()
                # Count only what the reader takes: it closes the connection when it seeks elsewhere.
                try:
                    for at in range(0, len(part), 16384):
                        self.wfile.write(part[at:at + 16384]);self.wfile.flush()
                        drive.served[fid] = drive.served.get(fid, 0) + len(part[at:at + 16384])
                except (BrokenPipeError, ConnectionResetError):self.close_connection = True
                return
            if u.path == '/drive/v3/files':
                text = q.get('q', '');name = text.split("name='")[1].split("'")[0] if "name='" in text else None
                parent = text.split("' in parents")[0].rsplit("'", 1)[-1] if "in parents" in text else None
                found = [{'id': f['id']} for f in drive.files.values() if not f['trashed'] and (name is None or f['name'] == name) and (parent is None or parent in f['parents'])]
                return self.reply(200, json.dumps({'files': found}).encode())
            if u.path.startswith('/drive/v3/files/'):
                fid = u.path.rsplit('/', 1)[1]
                if fid not in drive.files:return self.reply(404)
                return self.reply(200, json.dumps(drive.meta(fid)).encode(), {'ETag': drive.files[fid]['version']})
            return self.reply(404)
        def do_POST(self):
            u = urllib.parse.urlsplit(self.path);data = self.body()
            if u.path == '/drive/v3/files':
                m = json.loads(data);drive.number += 1;fid = 'folder-%d' % drive.number
                drive.add(fid, m['name'], b'', m.get('parents', ['root']), folder=True)
                return self.reply(200, json.dumps({'id': fid}).encode())
            if u.path == '/upload/drive/v3/files':
                m = json.loads(data);drive.number += 1;n = str(drive.number)
                drive.sessions[n] = dict(meta=m, data=bytearray())
                return self.reply(200, b'', {'Location': 'http://127.0.0.1:%d/upload/session/%s' % (self.server.server_port, n)})
            return self.reply(404)
        def do_PUT(self):
            u = urllib.parse.urlsplit(self.path);n = u.path.rsplit('/', 1)[1];s = drive.sessions.get(n)
            cr = self.headers.get('Content-Range', '')
            try:data = self.body()
            except Exception:data = b''
            if s is None:return self.reply(404)
            drive.puts += 1
            if s.get('done'):return self.reply(200, json.dumps(drive.meta(s['done'])).encode())
            spec, total = cr[6:].split('/')
            if spec != '*':
                a = int(spec.split('-')[0])
                if a == len(s['data']):s['data'] += data
            final = total != '*' and len(s['data']) == int(total)
            if final:
                drive.number += 1;fid = 'file-%d' % drive.number
                drive.add(fid, s['meta']['name'], bytes(s['data']), s['meta'].get('parents', ['root']))
                drive.files[fid]['mimeType'] = 'video/mp4';s['done'] = fid
                return self.reply(200, json.dumps(drive.meta(fid)).encode())
            del s['data'][len(s['data']) // STEP * STEP:]   # Google keeps whole 256 KiB steps of an unfinished upload
            headers = {'Range': 'bytes=0-%d' % (len(s['data']) - 1)} if s['data'] else {}
            return self.reply(308, b'', headers)
        def do_PATCH(self):
            u = urllib.parse.urlsplit(self.path);q = dict(urllib.parse.parse_qsl(u.query));fid = u.path.rsplit('/', 1)[1]
            data = self.body()
            if fid not in drive.files:return self.reply(404)
            f = drive.files[fid];change = json.loads(data) if data else {}
            if 'appProperties' in change:f['appProperties'].update(change.pop('appProperties'))
            f.update(change)
            if q.get('addParents'):f['parents'] = [p for p in f['parents'] if p != q.get('removeParents')] + [q['addParents']]
            f['version'] = str(int(f['version']) + 1)
            return self.reply(200, json.dumps(drive.meta(fid)).encode())
        def do_DELETE(self):
            fid = urllib.parse.urlsplit(self.path).path.rsplit('/', 1)[1]
            if drive.files.pop(fid, None) is None:return self.reply(404)
            return self.reply(204)
    return H


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


class Stream:
    """prepare_cloud's view of drive_stream.DriveStream: a loopback URL per Drive file."""
    def __init__(self, port):self.port = port;self.hold = lambda: False
    def url(self, file_id):return 'http://127.0.0.1:%d/media/%s' % (self.port, file_id)
    def forget(self, file_id):pass
    def stats(self):return {}


def setup(fixtures, name, port_holder):
    drive = FakeDrive();srv = Server(('127.0.0.1', 0), handler_for(drive));port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:%d' % port
    driveupload.API = base + '/drive/v3/files';driveupload.UPLOAD = base + '/upload/drive/v3/files'
    drive.add('movies', 'Movies', b'', ['root'], folder=True)
    drive.add('source', name, (Path(fixtures) / name).read_bytes())
    port_holder.append(srv)
    return drive, port


def queue(profile, drive, port, native, lines):
    client = driveupload.Drive(lambda: 'token', driveupload.sender(None))
    q = prep.Queue(profile, client, native, stream=Stream(port), log=lines.append)
    if 'jobs' not in q.state or not q.state['jobs']:
        item = prep.metadata(client, 'source')
        q.state['jobs'] = {prep.key(item): {'source': item, 'status': 'waiting'}};q.commit()
    return q


def run_until_done(q, keep_going=lambda: True, rounds=6):
    for _ in range(rounds):
        if q.process_one(keep_going):return True
        job = next(iter(q.state['jobs'].values()))
        if job.get('status') in ('failed',) or job.get('blocked'):return False
    return False


def prepared_file(drive):
    out = [f for f in drive.files.values() if f['name'].endswith('.mp4') and not f['trashed'] and 'movies' in f['parents']]
    return out[0] if out else None


def scenario(lib_path, fixtures, name, interrupt_at=None, expire=False, corrupt=False, upload_rate=0, small_pieces=True,
             hdr=False, expect_same_as=None, may_restart=False, killed_mid_piece=0, kodi_reads=None):
    servers = [];drive, port = setup(fixtures, name, servers);drive.upload_rate = upload_rate
    profile = tempfile.mkdtemp();lines = []
    lib = ctypes.CDLL(lib_path)
    if hdr:lib.kr_video_set_hdr_encoder(b'libx265');lib.kr_video_set_encoder(b'mpeg4')
    lib.kodi_airplay_prepare_keep_image_subs(1)
    native = prep.Native(lib)
    label = '%s%s%s%s%s' % (name, ' interrupted' if interrupt_at else '', ' +expired session' if expire else '', ' +bad mark' if corrupt else '', ' slow %d KB/s' % (upload_rate // 1024) if upload_rate else '')
    started = time.monotonic()
    try:
        q = queue(profile, drive, port, native, lines)
        if interrupt_at:
            # Kodi closed after interrupt_at bytes went up: everything in memory is gone, only files on disk stay.
            def going():return sum(len(s['data']) for s in drive.sessions.values()) < interrupt_at
            first = q.process_one(going)
            check(not first, '%s: the first run stopped when Kodi "closed"' % label)
            slot = next(iter(q.state['jobs']))
            saved = resume_store.load(profile, slot, prep.identity(q.state['jobs'][slot]['source']))
            check(saved is not None, '%s: a checkpoint was saved before the stop' % label)
            if saved and expire:drive.sessions.clear()
            if saved and killed_mid_piece:
                # Killed while a piece was going up: Google kept whole 256 KiB steps of it (the same bytes a straight run
                # makes there).
                session = next(iter(drive.sessions.values()));have = len(session['data'])
                kept = resume_store.pieces_from(saved.get('pieces') or [], have, have + killed_mid_piece)
                session['data'] += kept if kept is not None else LAST_DATA[0][have:have + killed_mid_piece]
            if saved and corrupt:
                path = resume_store.folder(profile) / (slot + '.json');d = json.loads(path.read_text())
                d['mark'] = d['mark'].replace('layout ', 'layout 9/');path.write_text(json.dumps(d))
            del q
            q = queue(profile, drive, port, prep.Native(lib), lines)
        done = run_until_done(q)
        check(done, '%s: finished (%.1f s)%s' % (label, time.monotonic() - started, '' if done else ': ' + ' | '.join(lines[-4:])))
        resumed = any('carrying on from byte' in l for l in lines) and not any('cannot carry on' in l for l in lines)
        if interrupt_at and may_restart:
            print('INFO %s: %s' % (label, 'carried on' if resumed else 'started again (re-encoded picture past its mark)'))
        elif interrupt_at:
            want = not (expire or corrupt)
            skipped = [l for l in lines if 'past the mark already on Drive' in l and ' 0 bytes past' not in l]
            if skipped:SKIPS.append(label)
            check(resumed == want, '%s: %s%s' % (label, 'carried on from its checkpoint' if want else 'started again (the checkpoint could not be used)',
                  '' if resumed == want else ': ' + ' | '.join(l for l in lines if 'carry' in l or 'carrying' in l or 'failed' in l)[:600]))
        out = prepared_file(drive)
        check(out is not None, '%s: the prepared movie is in the movie\'s folder' % label)
        if not out:return None
        check(drive.files['source']['trashed'], '%s: the original went to the bin' % label)
        check(out['appProperties'].get(prep.PROPERTY) == prep.PROFILE, '%s: marked prepared' % label)
        size = len(out['data']);read = drive.served.get(out['id'], 0)
        asks = drive.requests.get(out['id'], [])
        if os.environ.get('E2E_SHOW_READS'):print('   reads of the prepared file:', len(asks), asks[:40])
        # On the phone each read costs a Drive request and up to an 8 MB block (drive_stream): count requests.
        check(len(asks) <= 40, '%s: checking it took %d reads of the Drive file (by its index, not every fragment)' % (label, len(asks)))
        # Taken bytes (socket buffers let ~a few hundred KB more through than the reader used).
        # Byte counts are exact only with small loopback buffers (E2E_EXACT_BYTES=1 after lowering net.ipv4.tcp_rmem/wmem);
        # the number of reads above tells the same story everywhere (1,305 before r31, 14 now, for long_big.mkv).
        if size > 40 * 1024 * 1024 and os.environ.get('E2E_EXACT_BYTES'):
            check(read <= size // 3, '%s: checking it took %d of %d bytes (by its index, not reading it all)' % (label, read, size))
        if kodi_reads is not None and shutil.which('ffmpeg'):
            # r32: read like Kodi's player (a stock FFmpeg demuxing it over HTTP in play order). With all of a
            # fragment's picture then all its sound it jumped back and forth: 189 requests for long_big.mkv (r31).
            before = len(drive.requests.get(out['id'], []))
            import subprocess
            subprocess.run(['ffmpeg', '-v', 'error', '-i', 'http://127.0.0.1:%d/media/%s' % (port, out['id']), '-map', '0', '-c', 'copy', '-f', 'null', '-'],
                           capture_output=True, timeout=600)
            played = len(drive.requests.get(out['id'], [])) - before
            check(played <= kodi_reads, '%s: played through like Kodi in %d requests (at most %d)' % (label, played, kodi_reads))
        sups = [f for f in drive.files.values() if f['name'].endswith('.sup') and 'movies' in f['parents']]
        if b'S_HDMV/PGS' in drive.files['source']['data'] or 'pgs' in name:
            check(bool(sups) and all(len(f['data']) > 0 for f in sups), '%s: picture subtitles saved beside it (%d)' % (label, len(sups)))
        check(not list(resume_store.folder(profile).glob('*')), '%s: nothing left on the phone afterwards' % label)
        if expect_same_as is not None:
            check(hashlib.md5(out['data']).hexdigest() == expect_same_as, '%s: byte for byte the movie of a straight run' % label)
        LAST_SIZE[0] = len(out['data'])
        if not interrupt_at:LAST_DATA[0] = out['data']
        return hashlib.md5(out['data']).hexdigest()
    except Exception:
        traceback.print_exc();check(False, '%s: raised' % label)
    finally:
        for s in servers:s.shutdown()
        shutil.rmtree(profile, ignore_errors=True)


def repack_scenario(lib_path, fixtures, name):
    """Build 192: a movie prepared in the older layout (profile v1) is re-packed into r32's layout, and stays playable."""
    servers = [];drive, port = setup(fixtures, name, servers);profile = tempfile.mkdtemp();lines = []
    try:
        lib = ctypes.CDLL(lib_path);lib.kodi_airplay_prepare_keep_image_subs(1)
        q = queue(profile, drive, port, prep.Native(lib), lines)
        check(run_until_done(q), 'repack %s: the first conversion finished' % name)
        first = prepared_file(drive)
        if not first:return
        # The same movie as an older build left it: in the movie folder, marked v1.
        data = first['data'];md5 = hashlib.md5(data).hexdigest()
        for key in list(drive.files):
            if key not in ('movies',):drive.files.pop(key)
        drive.add('source', name.rsplit('.', 1)[0] + '.mp4', data)
        drive.files['source']['appProperties'] = {prep.PROPERTY: 'source-resolution-mp4-v1', prep.CHECKSUM_PROPERTY: md5}
        old = prep.metadata(driveupload.Drive(lambda: 'token', driveupload.sender(None)), 'source')
        check(prep.ready(old) and prep.repack_due(old), 'repack %s: an older conversion still counts as ready, and is due a re-pack' % name)
        profile2 = tempfile.mkdtemp();q = prep.Queue(profile2, driveupload.Drive(lambda: 'token', driveupload.sender(None)), prep.Native(lib), stream=Stream(port), log=lines.append)
        q.state['jobs'] = {prep.key(old): {'source': old, 'status': 'waiting', 'repack': True}};q.commit()
        check(run_until_done(q), 'repack %s: re-packed%s' % (name, '' if q.state['jobs'] else ''))
        out = prepared_file(drive)
        check(out is not None and out['appProperties'].get(prep.PROPERTY) == prep.PROFILE, 'repack %s: the new file is marked %s' % (name, prep.PROFILE))
        check(drive.files['source']['trashed'], 'repack %s: the older file went to the bin' % name)
    except Exception:
        traceback.print_exc();check(False, 'repack %s: raised' % name)
    finally:
        for srv in servers:srv.shutdown()


def main():
    lib_path, fixtures = sys.argv[1], sys.argv[2]
    only = set(sys.argv[3:])
    # Pieces small enough for test films (the phone: 32 MB pieces, 96 MB past a mark).
    drive_prepare.MAIN_CHUNK = drive_prepare.CHUNK = 1024 * 1024;drive_prepare.MARK_CAP = 3 * 1024 * 1024
    def want(n):return not only or n in only
    # r32 sizes fragments from the bitrate (6-60 s); these short films would have only one or two, so no mark to carry
    # on from: the tests that interrupt them keep 6 s fragments (KR_PREP_FRAG_S). long_big and the HDR films use the
    # real sizing.
    os.environ['KR_PREP_FRAG_S'] = '6'
    if want('copy'):
        straight = scenario(lib_path, fixtures, 'long_pgs.mkv')
        scenario(lib_path, fixtures, 'long_pgs.mkv', interrupt_at=2 * 1024 * 1024, expect_same_as=straight)
        scenario(lib_path, fixtures, 'long_pgs.mkv', interrupt_at=2 * 1024 * 1024, expire=True, expect_same_as=straight)
        scenario(lib_path, fixtures, 'long_pgs.mkv', interrupt_at=2 * 1024 * 1024, corrupt=True, expect_same_as=straight)
    if want('long'):
        straight = scenario(lib_path, fixtures, 'long_seek.mkv')
        scenario(lib_path, fixtures, 'long_seek.mkv', interrupt_at=512 * 1024, expect_same_as=straight)
    if want('big'):
        os.environ.pop('KR_PREP_FRAG_S', None)
        # Phone proportions: fragments (~450 KB here, ~45 MB of 4K remux) above the piece size (256 KB / 32 MB), so Drive
        # is usually between two marks when Kodi closes. A copied picture carries on from anywhere.
        drive_prepare.MAIN_CHUNK = drive_prepare.CHUNK = 256 * 1024;drive_prepare.MARK_CAP = 8 * 1024 * 1024
        try:
            straight = scenario(lib_path, fixtures, 'long_big.mkv', kodi_reads=60)
            size = LAST_SIZE[0]
            for part in (0.21, 0.47, 0.83):
                scenario(lib_path, fixtures, 'long_big.mkv', interrupt_at=int(size * part), expect_same_as=straight)
                scenario(lib_path, fixtures, 'long_big.mkv', interrupt_at=int(size * part), expect_same_as=straight, killed_mid_piece=512 * 1024)
            check(len(SKIPS) >= 1, 'long_big.mkv: at least one run carried on with Drive already past its mark (%d)' % len(SKIPS))
        finally:
            drive_prepare.MAIN_CHUNK = drive_prepare.CHUNK = 1024 * 1024;drive_prepare.MARK_CAP = 3 * 1024 * 1024
            os.environ['KR_PREP_FRAG_S'] = '6'
    if want('audio'):
        scenario(lib_path, fixtures, 'h264_ac3_dts_srt.mkv')
    if want('hdr'):
        scenario(lib_path, fixtures, 'resume_av1_hdr.mkv', hdr=True)
        # A re-encode carries on only from where a 30 s unit starts; on the phone a 4K unit is several 32 MB pieces.
        # resume_av1_hdr_big.mkv (640x360, 24 fps) gives units of a few hundred KB: pieces of 256 KB keep that proportion.
        # MARK_CAP above a unit, as on the phone (8 x 32 MB): it carries on. Below a unit: it starts again, cleanly.
        drive_prepare.MAIN_CHUNK = drive_prepare.CHUNK = 256 * 1024;drive_prepare.MARK_CAP = 8 * 1024 * 1024
        try:
            straight = scenario(lib_path, fixtures, 'resume_av1_hdr_big.mkv', hdr=True)
            size = LAST_SIZE[0]
            for part in (0.4, 0.75):
                scenario(lib_path, fixtures, 'resume_av1_hdr_big.mkv', hdr=True, interrupt_at=int(size * part) // (256 * 1024) * (256 * 1024))
                scenario(lib_path, fixtures, 'resume_av1_hdr_big.mkv', hdr=True, interrupt_at=int(size * part) // (256 * 1024) * (256 * 1024), killed_mid_piece=512 * 1024)
            drive_prepare.MARK_CAP = 1024 * 1024
            scenario(lib_path, fixtures, 'resume_av1_hdr_big.mkv', hdr=True, interrupt_at=int(LAST_SIZE[0] * 0.75) // (256 * 1024) * (256 * 1024), expire=True)
        finally:drive_prepare.MAIN_CHUNK = drive_prepare.CHUNK = 1024 * 1024;drive_prepare.MARK_CAP = 3 * 1024 * 1024
    if want('repack'):
        repack_scenario(lib_path, fixtures, 'long_pgs.mkv')
    if want('slow'):
        # A slow line: pieces take longer than the 45 s base limit would allow if it were not scaled (here 2 s base).
        old = driveupload.STALL;driveupload.STALL = 2
        try:scenario(lib_path, fixtures, 'long_pgs.mkv', upload_rate=300 * 1024)
        finally:driveupload.STALL = old
    print('%d failed' % len(failures))
    return len(failures)


if __name__ == '__main__':
    sys.exit(main())
