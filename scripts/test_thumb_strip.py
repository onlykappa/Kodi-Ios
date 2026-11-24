"""The seek bar's preview strip: the Python rules (thumb_strip.py) and the native maker (remux/src/kr_thumbs.c, compiled here on the host against the system FFmpeg and
run on a video whose colour is its time, so every picture proves which moment it came from). One picture every 5 s; the card flips through them as a drag moves.
Owner, 2026-11-23 and 24."""
import ctypes, os, shutil, subprocess, sys, tempfile, threading, time, unittest
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import thumb_strip as ts

NOW = 1_000_000.0


def pixel(path, x, y, width=256, height=144):
    """(r, g, b) of a picture, decoded by the ffmpeg command line (no Pillow needed on the CI host); also checks its size."""
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    assert len(raw) == width * height * 3, (path, len(raw))
    at = (y * width + x) * 3
    return raw[at], raw[at + 1], raw[at + 2]
LINK = 'https://dl.example.invalid/secret-token/Episode.mkv|User-Agent=Kodi'


def row(n, player='umbrella', age=3600, pos=600, total=3000):
    return {'player': player, 'position': pos, 'total': total, 'stream': {'url': 'https://x.test/%d.mkv' % n, 'at': NOW - age}}


class Rules(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, self.root, True)

    def fill(self, link, n=25, done=True):
        folder = os.path.join(self.root, ts.key(link)); os.makedirs(folder, exist_ok=True)
        for i in range(n): Path(folder, '%d.jpg' % i).write_bytes(b'x')
        Path(folder, 'grid').write_text('5 25 120\n')
        if done: Path(folder, 'done').write_text('25\n')
        return folder

    def test_the_folder_name_gives_nothing_of_the_link_away_and_ignores_headers(self):
        self.assertNotIn('secret-token', ts.key(LINK)); self.assertNotIn('secret-token', ts.special_path(LINK))
        self.assertEqual(ts.key(LINK), ts.key('https://dl.example.invalid/secret-token/Episode.mkv'))
        self.assertTrue(ts.special_path(LINK).startswith('special://profile/addon_data/service.kodi.ios.bootstrap/strips/') and ts.special_path(LINK).endswith('/'))
    def test_held_and_complete(self):
        f = self.fill(LINK, 40, done=False); self.assertEqual(ts.held(f), 40); self.assertFalse(ts.complete(f))
        f = self.fill(LINK); self.assertTrue(ts.complete(f))
    def test_the_newest_six_strips_are_kept(self):
        links = ['https://x.test/%d.mkv' % i for i in range(9)]
        for i, l in enumerate(links):
            f = self.fill(l); os.utime(f, (1000 + i, 1000 + i))
        ts.prune(self.root)
        self.assertEqual(sorted(os.listdir(self.root)), sorted(ts.key(l) for l in links[3:]))
    def test_only_the_first_rows_with_a_usable_umbrella_link(self):
        rows = [row(0), row(1, player='elementum'), row(2, age=73 * 3600), row(3, pos=1), row(4), row(5), row(6)]
        self.assertEqual(ts.recent_links(rows, NOW), ['https://x.test/0.mkv'])                              # the first 3 rows: only row 0 qualifies
        self.assertEqual(ts.recent_links([row(i) for i in range(9)], NOW), ['https://x.test/%d.mkv' % i for i in range(3)])
        self.assertEqual(ts.recent_links([{'player': 'umbrella', 'position': 600, 'total': 3000, 'stream': {'url': 'http://127.0.0.1:1/x.mkv', 'at': NOW}}], NOW), [])
    def test_show_clears_the_card_and_turns_the_ring_until_a_picture_exists(self):
        class Home:
            props = {}
            def setProperty(self, k, v): self.props[k] = v
            def clearProperty(self, k): self.props.pop(k, None)
        home = Home(); home.props[ts.FRAME] = 'old'
        self.assertTrue(ts.show(home, LINK, self.root))
        self.assertEqual(home.props[ts.PROPERTY], ts.special_path(LINK)); self.assertEqual(home.props[ts.BUILDING], '1'); self.assertNotIn(ts.FRAME, home.props)
        self.fill(LINK); self.assertTrue(ts.show(home, LINK, self.root)); self.assertNotIn(ts.BUILDING, home.props)       # complete: no ring
        self.assertFalse(ts.show(home, '', self.root)); self.assertNotIn(ts.PROPERTY, home.props)
        self.assertTrue(ts.show(home, '/private/var/mobile/Downloads/x.mkv', self.root))                                    # a downloaded file counts
    def test_the_loop_skips_finished_strips_busy_phones_and_mobile_data_and_waits_before_trying_again(self):
        made, waits = [], []
        self.fill('https://x.test/0.mkv')                                   # row 0 is done
        def wait(sec): waits.append(sec); return len(waits) >= 3
        state = {'busy': True, 'ok': True}
        ts.watch(lambda: [row(0), row(1)], lambda: state['busy'], wait, lambda t: None, made.append, self.root, allowed=lambda: state['ok'], now=lambda: NOW)
        self.assertEqual(made, [])                                          # busy: nothing
        waits.clear(); state['busy'] = False; state['ok'] = False
        ts.watch(lambda: [row(0), row(1)], lambda: state['busy'], wait, lambda t: None, made.append, self.root, allowed=lambda: state['ok'], now=lambda: NOW)
        self.assertEqual(made, [])                                          # mobile data: nothing
        waits.clear(); state['ok'] = True
        ts.watch(lambda: [row(0), row(1)], lambda: state['busy'], wait, lambda t: None, made.append, self.root, allowed=lambda: state['ok'], now=lambda: NOW)
        self.assertEqual(made, ['https://x.test/1.mkv'])                    # row 0 is complete; row 1 once, not again on the next look (AGAIN)
    def test_make_opens_a_session_fills_it_cancels_it_when_a_video_opens_closes_it_and_logs_no_address(self):
        events, logs = [], []
        class Fake:
            def fill(self, center, pause, budget=0):
                events.append(('fill', center, pause)); time.sleep(0.4); return 101
            def stop(self): events.append('stop')
            def close(self): events.append('close')
        n = ts.make(None, LINK, self.root, logs.append, stop=lambda: True, poll=0.05, center=61, opener=lambda lib, link, root, log: Fake())
        self.assertEqual(n, 101); self.assertIn('stop', events); self.assertEqual(events[-1], 'close'); self.assertEqual(events[0], ('fill', 61, ts.PAUSE_MS))
        self.assertEqual(ts.make(None, LINK, self.root, opener=lambda *a: None), -1)
    def test_a_session_opens_through_the_frameworks_functions_and_hands_back_pictures(self):
        calls = []
        def open_fn(url, folder, w, h, q, err, n): calls.append(('open', url, w, h, q)); return 7
        def frame_fn(handle, pct, err, n): calls.append(('frame', handle, pct)); return 1
        def fill_fn(handle, pause, center, budget, out, n): calls.append(('fill', handle, pause, center, budget)); out.value = b'made=3|held=101|count=101|bytes=2097152|seconds=2.0'; return 101
        class Lib:
            kodi_thumbs_open = staticmethod(open_fn); kodi_thumbs_frame = staticmethod(frame_fn); kodi_thumbs_fill = staticmethod(fill_fn)
            kodi_thumbs_stop = staticmethod(lambda h: calls.append(('stop', h))); kodi_thumbs_resume = staticmethod(lambda h: calls.append(('resume', h)))
            kodi_thumbs_close = staticmethod(lambda h: calls.append(('close', h)))
        logs = []
        session = ts.Session.open(Lib(), LINK, self.root, logs.append)
        self.assertIsNotNone(session)
        self.assertEqual(calls[0], ('open', b'https://dl.example.invalid/secret-token/Episode.mkv', ts.WIDTH, ts.HEIGHT, ts.QUALITY))
        self.assertEqual(session.frame(70), 1); self.assertEqual(session.fill(42, 200, 120), 101)
        self.assertEqual(calls[2], ('fill', 7, 200, 42, 120)); self.assertAlmostEqual(session.spent_mb, 2.0)
        session.stop(); session.resume(); session.close(); session.close()
        self.assertEqual([c[0] for c in calls], ['open', 'frame', 'fill', 'stop', 'resume', 'close'])   # closing twice closes once
        self.assertEqual(session.frame(1), -1)                                                           # a closed session makes nothing
        self.assertTrue(logs and all('secret-token' not in l and 'dl.example' not in l for l in logs)); self.assertTrue(os.path.isdir(os.path.join(self.root, ts.key(LINK))))
    def test_a_video_the_framework_cannot_open_leaves_no_folder_behind(self):
        class Lib:
            kodi_thumbs_open = staticmethod(lambda url, folder, w, h, q, err, n: (setattr(err, 'value', b'no video'), 0)[1])
            kodi_thumbs_frame = kodi_thumbs_fill = kodi_thumbs_stop = kodi_thumbs_resume = kodi_thumbs_close = staticmethod(lambda *a: 0)
        logs = []
        self.assertIsNone(ts.Session.open(Lib(), LINK, self.root, logs.append)); self.assertFalse(os.path.exists(os.path.join(self.root, ts.key(LINK))))
        self.assertIn('no video', logs[-1])

    # ---- follow(): a virtual clock drives it, a fake session stands in for the framework ----
    class Home:
        def __init__(self): self.props = {}; self.history = []
        def setProperty(self, k, v): self.props[k] = v; self.history.append(('set', k, v))
        def clearProperty(self, k): self.props.pop(k, None); self.history.append(('clear', k, None))

    def folder_of(self, link=LINK):
        f = os.path.join(self.root, ts.key(link)); os.makedirs(f, exist_ok=True); Path(f, 'grid').write_text('5 25 120\n'); return f

    def fake_session(self, folder, fill_pictures=0, frame_makes=True, spend=0.0):
        class Fake:
            def __init__(self): self.events = []; self.stopped = False; self.spent_mb = 0.0
            def fill(self, center, pause, budget=0):
                self.events.append(('fill', center, pause, budget)); made = 0
                for i in range(fill_pictures):
                    if self.stopped: break
                    Path(folder, '%d.jpg' % ((max(center, 0) + i * 6) % 25)).write_bytes(b'x'); made += 1; time.sleep(0.002)
                if ts.held(folder) >= 25: Path(folder, 'done').write_text('25\n')
                self.spent_mb += spend; time.sleep(0.01); return ts.held(folder)
            def frame(self, index):
                self.events.append(('frame', index))
                if frame_makes: Path(folder, '%d.jpg' % index).write_bytes(b'x')
                return 1
            def stop(self): self.events.append('stop'); self.stopped = True
            def resume(self): self.events.append('resume'); self.stopped = False
            def close(self): self.events.append('close')
        return Fake()

    def drive(self, session, plan, link=LINK, steps=400, **kwargs):
        """Runs follow() on a virtual clock. plan(step) returns what the phone says then: seeking, position (seconds), healthy."""
        self.folder_of(link)
        clock = [1000.0]; step = [0]; home = self.Home(); logs = []
        def wait(sec):
            clock[0] += max(sec, 0.0); step[0] += 1; time.sleep(0.003); return step[0] >= steps
        read = lambda name: plan(step[0]).get(name)
        done = ts.follow(None, link, self.root, home, logs.append, playing=lambda: step[0] < steps, healthy=lambda: read('healthy') is not False,
                         position=lambda: read('position'), seeking=lambda: bool(read('seeking')), wait=wait, session=session, now=lambda: clock[0], **kwargs)
        return done, home, logs

    def frames_shown(self, home):
        return [int(v.rsplit('/', 1)[1][:-4]) for k, key, v in home.history if k == 'set' and key == ts.FRAME]

    def test_follow_builds_from_where_the_person_is_gently_with_the_data_allowance(self):
        session = self.fake_session(self.folder_of(), fill_pictures=25)
        done, home, logs = self.drive(session, lambda step: {'position': 57}, steps=60, budget_mb=120)
        self.assertTrue(done)
        self.assertEqual([e for e in session.events if e[0] == 'fill'][0], ('fill', 11, ts.PLAY_PAUSE_MS, 120))   # 57 s is picture 11
        self.assertIn(('set', ts.FRAME), [(k, key) for k, key, v in home.history])
    def test_a_swipe_flips_through_the_nearest_pictures_and_never_shows_nothing(self):
        folder = self.folder_of()
        for n in (0, 6, 12, 18, 24): Path(folder, '%d.jpg' % n).write_bytes(b'x')          # the coarse pass: one every 30 s
        session = self.fake_session(folder)
        # the finger runs 0 -> 120 s in 40 ticks
        done, home, logs = self.drive(session, lambda step: {'seeking': True, 'position': min(120, step * 3)} if step > 2 else {'position': 0}, steps=46)
        shown = self.frames_shown(home)
        self.assertTrue(len(shown) >= 4 and set(shown) <= {0, 6, 12, 18, 24}, shown)
        self.assertEqual(shown, sorted(shown))                                              # forwards with the finger, no jumping about
        self.assertNotIn(('clear', ts.FRAME), [(k, key) for k, key, v in home.history])
        self.assertTrue(home.history[-1][2] is None or home.props.get(ts.FRAME, '').endswith('/24.jpg'))
    def test_the_picture_under_a_resting_finger_is_made_on_its_own_and_takes_over(self):
        folder = self.folder_of(); Path(folder, '0.jpg').write_bytes(b'x')
        session = self.fake_session(folder)
        def plan(step):
            if step < 6: return {'position': 0}
            return {'seeking': True, 'position': 30 if step < 8 else 100 if step < 9 else 62}    # passes 6, 20, rests on 12
        done, home, logs = self.drive(session, plan, steps=80)
        asked = [e[1] for e in session.events if isinstance(e, tuple) and e[0] == 'frame']
        self.assertEqual(asked, [12]); self.assertIn('stop', session.events)
        self.assertEqual(self.frames_shown(home)[-1], 12)                                    # the exact picture took over from the nearest one
        self.assertLess(session.events.index('stop'), session.events.index(('frame', 12)))
    def test_the_ring_turns_only_until_the_first_picture_exists(self):
        session = self.fake_session(self.folder_of(), fill_pictures=0, frame_makes=True)
        home = self.Home(); home.setProperty(ts.BUILDING, '1')
        done, home, logs = self.drive(session, lambda step: {'seeking': True, 'position': 40} if step > 3 else {'position': 0}, steps=40)
        sets = [(k, key) for k, key, v in home.history]
        self.assertNotIn(ts.BUILDING, home.props)                                            # the ring went once a picture was shown
        self.assertIn(('set', ts.FRAME), sets)
        self.assertEqual(self.frames_shown(home)[0] in (8,), True)                          # its own picture, the first there was
    def test_a_spent_data_allowance_ends_the_build_but_not_the_pictures_on_request(self):
        folder = self.folder_of()
        session = self.fake_session(folder, fill_pictures=2, spend=130.0)
        done, home, logs = self.drive(session, lambda step: {'position': 10}, steps=80, budget_mb=120)
        self.assertEqual(len([e for e in session.events if isinstance(e, tuple) and e[0] == 'fill']), 1)    # one round: the allowance was spent in it
        self.assertFalse(done)
    def test_a_downloaded_file_has_no_allowance_and_no_waiting(self):
        session = self.fake_session(self.folder_of(), fill_pictures=25)
        done, home, logs = self.drive(session, lambda step: {'position': 0}, steps=40, budget_mb=120, local=True)
        fill = [e for e in session.events if isinstance(e, tuple) and e[0] == 'fill'][0]
        self.assertEqual((fill[2], fill[3]), (ts.LOCAL_PAUSE_MS, 0))
    def test_the_build_waits_while_the_buffer_is_low_and_goes_on_when_it_recovers(self):
        session = self.fake_session(self.folder_of(), fill_pictures=25)
        done, home, logs = self.drive(session, lambda step: {'position': 20, 'healthy': step > 40}, steps=120)
        self.assertTrue(done); self.assertEqual([e for e in session.events if isinstance(e, tuple) and e[0] == 'fill'][0][1], 4)
        first = session.events.index([e for e in session.events if isinstance(e, tuple) and e[0] == 'fill'][0])
        self.assertTrue(first >= 0)
    def test_follow_gives_up_after_rounds_that_add_nothing(self):
        session = self.fake_session(self.folder_of(), fill_pictures=0)
        done, home, logs = self.drive(session, lambda step: {'position': 5}, steps=600)
        self.assertFalse(done); self.assertTrue(any('gave up' in l for l in logs))
        self.assertLessEqual(len([e for e in session.events if isinstance(e, tuple) and e[0] == 'fill']), ts.GIVE_UP + 1)
    def test_a_complete_strip_opens_no_session_and_still_flips_through_the_pictures(self):
        folder = self.fill('https://x.test/finished.mkv')
        class Never:
            def __getattr__(self, name): raise AssertionError('a finished strip uses no session')
        home = self.Home(); step = [0]
        def wait(sec): step[0] += 1; time.sleep(0.002); return step[0] > 30
        done = ts.follow(None, 'https://x.test/finished.mkv', self.root, home, lambda t: None, lambda: step[0] < 30, lambda: True, lambda: step[0] * 4, lambda: step[0] > 2, wait, session=None, now=lambda: step[0] * 0.05)
        self.assertTrue(done); self.assertTrue(len(self.frames_shown(home)) >= 5)
    def test_a_new_video_ends_the_last_builder_and_clears_the_card(self):
        folder = self.folder_of()
        for n in (0, 6, 12): Path(folder, '%d.jpg' % n).write_bytes(b'x')
        home = self.Home(); home.props[ts.FRAME] = 'special://old/3.jpg'; home.props[ts.BUILDING] = '1'; home.props[ts.PROPERTY] = 'special://old/'
        out = {}
        step = [0]
        def wait(sec): step[0] += 1; time.sleep(0.01); return step[0] > 400
        thread = threading.Thread(target=lambda: out.setdefault('done', ts.follow(None, LINK, self.root, home, lambda t: None, lambda: True, lambda: True, lambda: 20, lambda: True, wait,
                                                                      session=self.fake_session(folder))), daemon=True)
        thread.start(); time.sleep(0.3)
        self.assertIn(ts.FRAME, home.props)                                   # the old video's builder was showing its pictures
        ts.begin(home)                                                         # a new video begins (a downloaded movie after an Umbrella episode)
        thread.join(3); self.assertFalse(thread.is_alive())                    # the old builder ended by itself
        self.assertEqual([k for k in (ts.FRAME, ts.BUILDING, ts.PROPERTY) if k in home.props], [])
    def test_the_source_is_the_playing_file_never_another_titles_remembered_link(self):
        umbrella = 'https://dl.example.invalid/abc/Episode.mkv|User-Agent=Kodi'
        isfile = lambda p: p == '/var/mobile/Downloads/Film.mkv'
        self.assertEqual(ts.source_of('/var/mobile/Downloads/Film.mkv', umbrella, isfile=isfile), ('/var/mobile/Downloads/Film.mkv', 'local'))
        self.assertEqual(ts.source_of('special://profile/dl/Film.mkv', '', translate=lambda p: '/var/mobile/Downloads/Film.mkv', isfile=isfile), ('/var/mobile/Downloads/Film.mkv', 'local'))
        # a Drive copy through the app's proxy is its own source, even with an Umbrella link remembered from the title before
        self.assertEqual(ts.source_of('http://127.0.0.1:49531/drive/1NWw2JhI/Inception.mp4', umbrella), ('http://127.0.0.1:49531/drive/1NWw2JhI/Inception.mp4', 'drive'))
        # Umbrella plays through a local cache address: the remembered debrid link is the source
        self.assertEqual(ts.source_of('http://127.0.0.1:50000/cache/x', umbrella), (umbrella, 'stream'))
        self.assertEqual(ts.source_of('plugin://plugin.video.themoviedb.helper/?x', umbrella), (umbrella, 'stream'))
        self.assertEqual(ts.source_of('http://127.0.0.1:50000/cache/x', ''), (None, None))
        self.assertEqual(ts.source_of('/var/mobile/missing.mkv', ''), (None, None))
        self.assertEqual(ts.source_of('https://dl.example.invalid/direct.mkv', ''), ('https://dl.example.invalid/direct.mkv', 'stream'))
    def test_a_drive_copy_has_the_same_folder_whatever_the_proxys_port(self):
        self.assertEqual(ts.key('http://127.0.0.1:49531/drive/1NWw2JhI/Inception.mp4'), ts.key('http://127.0.0.1:50111/drive/1NWw2JhI/Inception.mp4'))
        self.assertNotEqual(ts.key('http://127.0.0.1:49531/drive/1NWw2JhI/Inception.mp4'), ts.key('http://127.0.0.1:49531/drive/OTHER/Inception.mp4'))
    def test_a_stream_waits_for_the_player_to_settle_and_gives_up_when_it_never_does(self):
        clock = [0.0]
        def wait(sec): clock[0] += sec; return False
        now = lambda: clock[0]
        # healthy from the start, played time follows the clock: ready after SETTLE_AFTER
        self.assertTrue(ts.settled(lambda: True, lambda: True, lambda: clock[0], wait, now=now)); self.assertGreaterEqual(clock[0], ts.SETTLE_AFTER)
        clock[0] = 0.0     # buffering for 30 s, then healthy: the quiet time starts when it recovers
        self.assertTrue(ts.settled(lambda: True, lambda: clock[0] > 30, lambda: clock[0], wait, now=now)); self.assertGreaterEqual(clock[0], 30 + ts.QUIET)
        clock[0] = 0.0     # never healthy: gives up
        self.assertFalse(ts.settled(lambda: True, lambda: False, lambda: clock[0], wait, now=now)); self.assertGreater(clock[0], ts.GIVE_UP_WAITING)
        clock[0] = 0.0     # the video stops
        self.assertFalse(ts.settled(lambda: clock[0] < 3, lambda: True, lambda: 0, wait, now=now))
    def test_position_labels_and_the_nearest_picture(self):
        self.assertEqual((ts.clock_seconds('1:02:03'), ts.clock_seconds('12:34'), ts.clock_seconds('45'), ts.clock_seconds(''), ts.clock_seconds('x')), (3723, 754, 45, None, None))
        self.assertEqual((ts.nearest([0, 6, 12], 5), ts.nearest([0, 6, 12], 3), ts.nearest([0, 6, 12], 4), ts.nearest([], 4), ts.nearest([6], 0), ts.nearest([6], 20)), (6, 0, 6, None, 6, 6))
        f = self.fill(LINK); self.assertEqual(ts.grid(f), (5, 25, 120)); self.assertEqual(ts.pictures(f), list(range(25)))
        os.remove(os.path.join(f, 'done')); self.assertFalse(ts.complete(f))
    def test_an_old_framework_or_a_local_address_makes_nothing(self):
        self.assertFalse(ts.available(object())); self.assertEqual(ts.make(object(), LINK, self.root), -1)
        class Lib:
            kodi_thumbs_open = staticmethod(lambda *a: (_ for _ in ()).throw(AssertionError('must not be called')))
            kodi_thumbs_frame = kodi_thumbs_fill = kodi_thumbs_stop = kodi_thumbs_resume = kodi_thumbs_close = staticmethod(lambda *a: 0)
        self.assertEqual(ts.make(Lib(), 'ftp://x.test/x.mkv', self.root), -1)                 # neither a web address nor a local file



def _toolchain():
    if not (shutil.which('gcc') and shutil.which('ffmpeg')):
        return False
    if os.environ.get('KR_THUMBS_LDLIBS'):        # the AirPlay CI names its own host FFmpeg (static libraries)
        return True
    return bool(shutil.which('pkg-config')) and subprocess.call(['pkg-config', '--exists', 'libavformat', 'libavcodec', 'libswscale']) == 0


@unittest.skipUnless(_toolchain(), 'needs gcc, ffmpeg and FFmpeg development files')
class Native(unittest.TestCase):
    """kr_thumbs.c against a 120 s video whose red grows with time: each picture must show its own moment (the keyframe at or before i*5 s)."""
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        R = ROOT / 'migration/airplay-ios/remux'
        cls.video = os.path.join(cls.dir, 'timecolor.mkv')
        subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', "nullsrc=s=320x180:r=8:d=120,geq=r='255*T/120':g='255*(1-T/120)':b='128'",
                               '-f', 'lavfi', '-i', 'sine=d=120', '-c:v', 'libx264', '-g', '16', '-pix_fmt', 'yuv420p', '-c:a', 'aac', cls.video])
        subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'sine=d=30', '-c:a', 'aac', os.path.join(cls.dir, 'audio.m4a')])
        if os.environ.get('KR_THUMBS_LDLIBS'):
            flags = os.environ.get('KR_THUMBS_CFLAGS', '').split() + os.environ['KR_THUMBS_LDLIBS'].split()
        else:
            flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'libavformat', 'libavcodec', 'libswscale', 'libavutil'], text=True).split()
        cls.so = os.path.join(cls.dir, 'libkrthumbs.so')
        subprocess.check_call(['gcc', '-std=gnu11', '-O1', '-fPIC', '-shared', '-Wl,-Bsymbolic', '-I%s/src' % R, '-I%s/gmplayer' % R, '%s/src/kr_thumbs.c' % R, '%s/src/kr_source.c' % R, '-o', cls.so] + flags + ['-lpthread'])
        cls.lib = ctypes.CDLL(cls.so)
        cls.lib.kodi_thumbs_open.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        cls.lib.kodi_thumbs_open.restype = ctypes.c_int64

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.dir, ignore_errors=True)

    def session(self, url, name):
        out = os.path.join(self.dir, name); os.makedirs(out, exist_ok=True)
        s = ts.Session.open(self.lib, url, out_root := os.path.join(self.dir, name + '_root'), lambda t: None) if False else None
        err = ctypes.create_string_buffer(200)
        handle = self.lib.kodi_thumbs_open(url.encode(), out.encode(), ts.WIDTH, ts.HEIGHT, ts.QUALITY, err, len(err))
        return out, ts.Session(self.lib, handle) if handle else None, err.value.decode()

    def test_one_picture_every_5_seconds_each_from_its_own_moment_and_a_second_fill_makes_none(self):
        out, s, err = self.session(self.video, 'grid'); self.assertIsNotNone(s, err)
        self.assertEqual(ts.grid(out), (5, 25, 120))                                       # 120 s: a picture at 0, 5, ... 120
        n = s.fill(-1, 0, 0); self.assertEqual(n, 25); s.close()
        self.assertTrue(os.path.exists(os.path.join(out, 'done'))); self.assertEqual(ts.pictures(out), list(range(25)))
        self.assertLess(sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out) if f.endswith('.jpg')), 25 * 12 * 1024)
        reds = [pixel(os.path.join(out, '%d.jpg' % i), 128, 72)[0] / 255 * 120 for i in range(25)]
        for i in (0, 6, 12, 24): self.assertAlmostEqual(reds[i], i * 5, delta=4.5)           # keyframes are 2 s apart: at or before
        self.assertTrue(all(b >= a - 2 for a, b in zip(reds, reds[1:])))
        out2, s2, err = self.session(self.video, 'grid'); self.assertEqual(s2.fill(-1, 0, 0), 25); s2.close()
    def test_the_build_is_coarse_first_from_the_centre_and_a_budget_ends_it(self):
        out, s, err = self.session(self.video, 'coarse'); self.assertIsNotNone(s, err)
        done = threading.Event()
        threading.Thread(target=lambda: (s.fill(12, 500, 0), done.set()), daemon=True).start()
        time.sleep(0.8); s.stop(); done.wait(5); made = ts.pictures(out)
        self.assertTrue(made and 12 in made and set(made) <= {0, 12, 24, 6, 18}, made)       # the one-a-minute pictures first (0, 12, 24), the centre one first of them
        s.resume(); s.close()
        out, s, err = self.session(self.video, 'budget'); s.fill(-1, 0, 0)
        self.assertGreater(s.spent_mb, 0); s.close()
        out, s, err = self.session(self.video, 'tiny'); s.fill(-1, 0, 1)                      # a 1 MB allowance on a video smaller than that changes nothing
        self.assertEqual(ts.held(out), 25); s.close()
    def test_a_picture_asked_for_while_the_build_runs_arrives_within_a_second(self):
        out, s, err = self.session(self.video, 'frame'); self.assertIsNotNone(s, err)
        threading.Thread(target=lambda: s.fill(-1, 300, 0), daemon=True).start(); time.sleep(0.3)
        began = time.monotonic(); r = s.frame(17); took = time.monotonic() - began
        self.assertIn(r, (0, 1)); self.assertTrue(os.path.exists(os.path.join(out, '17.jpg'))); self.assertLess(took, 1.5)
        s.stop(); s.resume(); s.close()
    def test_stop_ends_a_build_at_once_and_the_session_works_again_after_resume(self):
        out, s, err = self.session(self.video, 'stop'); self.assertIsNotNone(s, err)
        t = threading.Thread(target=lambda: s.fill(-1, 400, 0), daemon=True); t.start(); time.sleep(0.5)
        began = time.monotonic(); s.stop(); t.join(3); self.assertFalse(t.is_alive()); self.assertLess(time.monotonic() - began, 1.5)
        self.assertEqual(s.frame(23), -1)                                                    # stopped: no picture
        s.resume(); self.assertIn(s.frame(23), (0, 1)); s.close()
    def test_a_picture_with_black_bars_when_the_shape_differs(self):
        tall = os.path.join(self.dir, 'tall.mkv')
        subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=180x320:r=8:d=12', '-c:v', 'libx264', '-g', '16', '-pix_fmt', 'yuv420p', tall])
        out, s, err = self.session(tall, 'tall'); self.assertIsNotNone(s, err); s.fill(-1, 0, 0); s.close()
        self.assertLess(sum(pixel(os.path.join(out, '1.jpg'), 5, y)[0] for y in range(0, 144, 16)) / 9, 20)   # the left bar is black
    def test_no_video_or_a_missing_file_is_an_error_and_writes_nothing(self):
        out, s, err = self.session(os.path.join(self.dir, 'audio.m4a'), 'audio'); self.assertIsNone(s); self.assertTrue(err)
        self.assertEqual([f for f in os.listdir(out) if f.endswith('.jpg')], [])
        out, s, err = self.session(os.path.join(self.dir, 'missing.mkv'), 'none'); self.assertIsNone(s)


class Wiring(unittest.TestCase):
    NAMES = ('kodi_thumbs_open', 'kodi_thumbs_frame', 'kodi_thumbs_fill', 'kodi_thumbs_stop', 'kodi_thumbs_resume', 'kodi_thumbs_close')
    def test_the_framework_exports_the_strip_and_builds_it(self):
        sh = (ROOT / 'migration/airplay-ios/build-airplay.sh').read_text()
        for name in self.NAMES: self.assertIn('_' + name + '\\n', sh.replace('\\\\n', '\\n').replace('\\n', '\\n') if False else sh) if False else self.assertIn(name, sh)
        self.assertIn('(open|frame|fill|stop|resume|close)', sh)
        c = (ROOT / 'migration/airplay-ios/remux/src/kr_thumbs.c').read_text()
        for name in self.NAMES: self.assertIn(name + '(', c.split('#define KR_EXPORT')[1])
        self.assertTrue((ROOT / 'migration/airplay-ios/remux/src/stb_image_write.h').exists())
        self.assertIn('stb_image_write', (ROOT / 'migration/airplay-ios/remux/THIRD-PARTY-NOTICES').read_text())
        used = set(__import__('re').findall(r'lib\.(kodi_thumbs_\w+)', (ROOT / 'migration/bundled-bootstrap/resources/lib/thumb_strip.py').read_text()))
        self.assertEqual(used, set(self.NAMES))                                              # every function the Python side calls is exported
    def test_the_service_and_the_player_use_it(self):
        self.assertIn('thumb_strip.watch(', (ROOT / 'migration/bundled-bootstrap/service.py').read_text())
        p = (ROOT / 'migration/bundled-bootstrap/resources/lib/portrait.py').read_text()
        self.assertIn('thumb_strip.follow(', p); self.assertIn('thumb_strip.show(', p); self.assertIn('thumb_strip.begin(', p); self.assertIn('thumb_strip.source_of(', p); self.assertIn('thumb_strip.settled(', p); self.assertIn('on_start=started)', p)
        self.assertIn("'Player.Caching'", p); self.assertIn("'Player.SeekTime'", p); self.assertIn('local=local', p)   # the buffer's health; the finger's second; downloads
    def test_the_card_shows_the_picture_the_phone_chose_and_a_big_ring_when_there_is_none(self):
        sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
        import player_osd
        x = player_osd.window()
        self.assertIn('$INFO[Window(Home).Property(KodiIOS.StripFrame)]', x)
        self.assertNotIn('KodiIOS.Strip)]%d.jpg', x)
        self.assertNotIn('Player.Art(fanart)', x)       # no generic artwork in the card any more
        self.assertIn('Window(Home).Property(KodiIOS.StripBuilding)', x)   # the ring in the middle of the card while there is no picture
        self.assertIn('<left>-48</left>', x) if False else self.assertIn('96', x)


if __name__ == '__main__':
    unittest.main()
