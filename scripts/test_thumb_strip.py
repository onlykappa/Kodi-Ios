"""The seek bar's preview strip: the Python rules (thumb_strip.py) and the native maker (remux/src/kr_thumbs.c, compiled here on the host against the system FFmpeg and
run on a video whose colour is its time, so every picture proves which moment it came from). Owner, 2026-11-23."""
import ctypes, os, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import thumb_strip as ts

NOW = 1_000_000.0


def pixel(path, x, y, width=320, height=180):
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

    def fill(self, link, n=ts.COUNT, done=True):
        folder = os.path.join(self.root, ts.key(link)); os.makedirs(folder, exist_ok=True)
        for i in range(n): Path(folder, '%d.jpg' % i).write_bytes(b'x')
        if done: Path(folder, 'done').write_text('101\n')
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
    def test_show_points_the_card_at_the_folder_or_clears_it(self):
        class Home:
            props = {}
            def setProperty(self, k, v): self.props[k] = v
            def clearProperty(self, k): self.props.pop(k, None)
        home = Home()
        self.assertFalse(ts.show(home, LINK, self.root)); self.assertNotIn(ts.PROPERTY, home.props)
        self.fill(LINK, 12, done=False)
        self.assertTrue(ts.show(home, LINK, self.root)); self.assertEqual(home.props[ts.PROPERTY], ts.special_path(LINK))
        self.assertFalse(ts.show(home, '', self.root)); self.assertNotIn(ts.PROPERTY, home.props)
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
    def test_make_calls_the_framework_cancels_it_when_a_video_opens_and_logs_no_address(self):
        calls = {'cancel': 0}
        seen = {}
        def make_fn(url, folder, w, h, q, pause, out, n):   # a plain function takes .argtypes like the framework's ctypes function does
            seen['args'] = (url, folder, w, h, q, pause)
            time.sleep(0.4); out.value = b'|made=101|bytes=20971520|seconds=40.0'; return 101
        def cancel_fn(): calls['cancel'] += 1
        class Lib:
            kodi_thumbs_make = staticmethod(make_fn); kodi_thumbs_cancel = staticmethod(cancel_fn)
        logs = []
        lib = Lib()
        n = ts.make(lib, LINK, self.root, logs.append, stop=lambda: True, poll=0.05)
        self.assertEqual(n, 101); self.assertGreaterEqual(calls['cancel'], 1)
        self.assertEqual(seen['args'][0], b'https://dl.example.invalid/secret-token/Episode.mkv')   # headers dropped, as the speech check does
        self.assertEqual(seen['args'][2:], (ts.WIDTH, ts.HEIGHT, ts.QUALITY, ts.PAUSE_MS))
        self.assertTrue(logs and all('secret-token' not in l and 'dl.example' not in l for l in logs)); self.assertIn('101 of 101', logs[-1])
    def test_an_old_framework_or_a_local_address_makes_nothing(self):
        self.assertFalse(ts.available(object())); self.assertEqual(ts.make(object(), LINK, self.root), -1)
        class Lib:
            kodi_thumbs_make = staticmethod(lambda *a: (_ for _ in ()).throw(AssertionError('must not be called')))
            kodi_thumbs_cancel = staticmethod(lambda: None)
        self.assertEqual(ts.make(Lib(), '/private/var/mobile/x.mkv', self.root), -1)


def _toolchain():
    if not (shutil.which('gcc') and shutil.which('ffmpeg')):
        return False
    if os.environ.get('KR_THUMBS_LDLIBS'):        # the AirPlay CI names its own host FFmpeg (static libraries)
        return True
    return bool(shutil.which('pkg-config')) and subprocess.call(['pkg-config', '--exists', 'libavformat', 'libavcodec', 'libswscale']) == 0


@unittest.skipUnless(_toolchain(), 'needs gcc, ffmpeg and FFmpeg development files')
class Native(unittest.TestCase):
    """kr_thumbs.c against a 40 s video whose red grows with time: each picture must show the moment of its percent (at or before it, to the keyframe)."""
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        R = ROOT / 'migration/airplay-ios/remux'
        cls.video = os.path.join(cls.dir, 'timecolor.mkv')
        subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', "nullsrc=s=320x180:r=24:d=40,geq=r='255*T/40':g='255*(1-T/40)':b='128'",
                               '-f', 'lavfi', '-i', 'sine=d=40', '-c:v', 'libx264', '-g', '48', '-pix_fmt', 'yuv420p', '-c:a', 'aac', cls.video])
        subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'sine=d=30', '-c:a', 'aac', os.path.join(cls.dir, 'audio.m4a')])
        main = os.path.join(cls.dir, 'main.c')
        Path(main).write_text('#include "kr_thumbs.h"\n#include <stdio.h>\n#include <stdlib.h>\nint main(int c,char**v){kr_thumbs_result r={0};char e[200]="";'
                              'int n=kr_thumbs_make(v[1],v[2],320,180,60,0,NULL,NULL,&r,e,sizeof e);printf("%d %d %lld %s\\n",n,r.made,(long long)r.bytes,e);return n<0;}\n')
        if os.environ.get('KR_THUMBS_LDLIBS'):
            flags = os.environ.get('KR_THUMBS_CFLAGS', '').split() + os.environ['KR_THUMBS_LDLIBS'].split()
        else:
            flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'libavformat', 'libavcodec', 'libswscale', 'libavutil'], text=True).split()
        cls.exe = os.path.join(cls.dir, 'thumbs')
        subprocess.check_call(['gcc', '-std=gnu11', '-O1', '-I%s/src' % R, '-I%s/gmplayer' % R, main, '%s/src/kr_thumbs.c' % R, '%s/src/kr_source.c' % R, '-o', cls.exe] + flags + ['-lpthread'])

    @classmethod
    def tearDownClass(cls): shutil.rmtree(cls.dir, ignore_errors=True)

    def run_exe(self, url, out):
        os.makedirs(out, exist_ok=True)
        p = subprocess.run([self.exe, url, out], capture_output=True, text=True)
        return p.returncode, p.stdout.split()

    def test_101_small_pictures_each_from_its_own_moment_then_a_second_run_makes_none(self):
        out = os.path.join(self.dir, 'out'); code, fields = self.run_exe(self.video, out)
        self.assertEqual((code, fields[0], fields[1]), (0, '101', '101'))
        files = sorted(os.listdir(out)); self.assertIn('done', files)
        self.assertEqual(len([f for f in files if f.endswith('.jpg')]), 101)
        self.assertLess(sum(os.path.getsize(os.path.join(out, f)) for f in files), 101 * 20 * 1024)       # a few KB each
        reds = []
        for n in range(101):
            px = pixel(os.path.join(out, '%d.jpg' % n), 160, 90); reds.append(px[0] / 255 * 40)
        # the picture of 50 % shows about 20 s (keyframes are 2 s apart: at or before it), the first the start, the last near the end; never backwards by more than noise
        self.assertAlmostEqual(reds[50], 20.0, delta=3.5); self.assertLess(reds[0], 3.0); self.assertGreater(reds[100], 34.0)
        self.assertTrue(all(b >= a - 1.5 for a, b in zip(reds, reds[1:])))
        code, fields = self.run_exe(self.video, out); self.assertEqual((code, fields[0], fields[1]), (0, '101', '0'))   # resumed: nothing made again
    def test_a_picture_with_black_bars_when_the_shape_differs(self):
        wide = os.path.join(self.dir, 'tall.mkv')
        subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=180x320:r=24:d=12', '-c:v', 'libx264', '-g', '24', '-pix_fmt', 'yuv420p', wide])
        out = os.path.join(self.dir, 'out_tall'); code, fields = self.run_exe(wide, out); self.assertEqual(code, 0)
        self.assertLess(sum(pixel(os.path.join(out, '50.jpg'), 5, y)[0] for y in range(0, 180, 20)) / 9, 20)             # the left bar is black
    def test_no_video_or_a_missing_file_is_an_error_and_writes_nothing(self):
        out = os.path.join(self.dir, 'out_audio'); code, _ = self.run_exe(os.path.join(self.dir, 'audio.m4a'), out); self.assertNotEqual(code, 0)
        self.assertEqual([f for f in os.listdir(out) if f.endswith('.jpg')], [])
        out = os.path.join(self.dir, 'out_none'); code, _ = self.run_exe(os.path.join(self.dir, 'missing.mkv'), out); self.assertNotEqual(code, 0)


class Wiring(unittest.TestCase):
    def test_the_framework_exports_the_strip_and_builds_it(self):
        sh = (ROOT / 'migration/airplay-ios/build-airplay.sh').read_text()
        self.assertIn("printf '_kodi_thumbs_make\\n_kodi_thumbs_cancel\\n'", sh)
        self.assertIn('kodi_thumbs_make', sh); self.assertIn("_kr_thumbs_make$", sh)
        c = (ROOT / 'migration/airplay-ios/remux/src/kr_thumbs.c').read_text()
        for name in ('kodi_thumbs_make', 'kodi_thumbs_cancel'):
            self.assertIn('visibility("default"))) ' + ('int ' if name.endswith('make') else 'void ') + name, c)
        self.assertTrue((ROOT / 'migration/airplay-ios/remux/src/stb_image_write.h').exists())
        self.assertIn('stb_image_write', (ROOT / 'migration/airplay-ios/remux/THIRD-PARTY-NOTICES').read_text())
        # every kodi_thumbs_* the Python side calls is exported
        used = set(__import__('re').findall(r'lib\.(kodi_thumbs_\w+)', (ROOT / 'migration/bundled-bootstrap/resources/lib/thumb_strip.py').read_text()))
        self.assertEqual(used, {'kodi_thumbs_make', 'kodi_thumbs_cancel'})
    def test_the_service_and_the_player_use_it(self):
        self.assertIn('thumb_strip.watch(', (ROOT / 'migration/bundled-bootstrap/service.py').read_text())
        p = (ROOT / 'migration/bundled-bootstrap/resources/lib/portrait.py').read_text()
        self.assertIn('thumb_strip.show(', p); self.assertIn('on_start=started)', p)
    def test_the_card_reads_the_playing_titles_picture_for_its_percent(self):
        sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
        import player_osd
        x = player_osd.window()
        for n in (0, 50, 100):
            self.assertIn('$INFO[Window(Home).Property(KodiIOS.Strip)]%d.jpg' % n, x)
        self.assertNotIn('Player.Art(fanart)', x)       # no generic artwork in the card any more


if __name__ == '__main__':
    unittest.main()
