"""End-to-end check of AI Upscale (owner, 2026-11-13: "ensure the upscaler and everything works"). The real decisions
and service step run together: the per-show choice (Settings › AI Upscale › one show, V3), the queue (upscale_queue),
the service pass (upscale_cloud.process_one) with the charger / battery / heat / Drive-space rules, one copy at a time,
failures and their back-off, the copy that plays (choose), the Picture menu's AirPlay state (menu_state), the pages'
chips (upscale_page), a copy deleted on Drive being made again, and Remove the copies. KodiAirPlay, Drive and the
phone are simulated (evidence class: host simulation, never the phone).
"""
import json, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import picture, upscale_cloud, upscale_page as up, upscale_queue as uq  # noqa: E402

SHOW = 'Naruto Shippuden'


class Drive:
    def __init__(self):
        self.files, self.trash, self.n = {}, [], 0

    def folder(self, parts):
        return 'staging'

    def call(self, method, url, body=None, headers=None):
        if method == 'GET':
            return 200, {}, json.dumps({'parents': ['show-folder']})
        return 200, {}, b'{}'


class Native:
    """KodiAirPlay as the queue step sees it: device state, AI support, the model, the converter."""
    upscales = True
    SUPPORT = {'os26': 1, 'video': {'supported': 1, 'fits': 1, 'scale': 2}}

    def __init__(self):
        self.state = {'charging': 0, 'battery': 0.9, 'thermal': 'nominal', 'low_power': 0}
        self.model, self.converts, self.fail_next = 0, [], 0

    def device_state(self):
        return dict(self.state)

    def upscale_support(self, w, h, label, engine=0):
        return self.SUPPORT

    def upscale_model(self, w, h, label, engine, start=False):
        if start and self.model == 0:
            self.model = 1   # downloading; the test finishes it
        return self.model

    def convert_to(self, source, sink, keep_going, progress, paused, waiting, upscale=None):
        assert upscale and upscale[0] * upscale[1] <= 3840 * 2160, upscale   # never larger than 4K UHD (no 7680x4320)
        self.converts.append((source, upscale))
        progress(0, 50, 100)
        if self.fail_next:
            self.fail_next -= 1
            raise RuntimeError('VTFrameProcessor error -12345')
        progress(0, 100, 100)

    def probe(self, url):
        return {'ready': True, 'width': 3840, 'height': 2160}


def fake_modules(drive):
    class Sink:
        def __init__(self, d, parent, name, keep_going, on_file, **kw):
            self.on_file, self.name = on_file, name

        def finish(self):
            drive.n += 1
            ident = 'copy%d' % drive.n
            drive.files[ident] = self.name
            self.on_file('0', {'id': ident, 'size': 2400000000, 'md5Checksum': 'x'})

        def close(self):
            pass

    def bin_(d, ident):
        drive.trash.append(ident)
        drive.files.pop(ident, None)
    dp = types.SimpleNamespace(Sink=Sink, discard=lambda d, i: None, bin=bin_)
    du = types.SimpleNamespace(TOP='Kodi', API='https://drive/files', Stop=type('Stop', (Exception,), {}))
    return {'drive_prepare': dp, 'driveupload': du, 'drivelibrary': types.SimpleNamespace(display_title=lambda n: n)}


def library():
    jobs = {}
    for n in range(1, 7):
        jobs['e%d' % n] = {'status': 'done', 'prepared_id': 'ep%d' % n, 'source': {'id': 'ep%d' % n, 'name': '%s S01E%02d.mkv' % (SHOW, n)},
                           'probe': {'width': 1920, 'height': 1080, 'duration': 1400, 'hdr': False}}
    jobs['m4k'] = {'status': 'done', 'prepared_id': 'film4k', 'source': {'id': 'film4k', 'name': 'Dune 2024.mkv'},
                   'probe': {'width': 3840, 'height': 2160, 'duration': 9000, 'hdr': False}}
    jobs['mhdr'] = {'status': 'done', 'prepared_id': 'filmhdr', 'source': {'id': 'filmhdr', 'name': 'Arrival 2016.mkv'},
                    'probe': {'width': 1920, 'height': 1080, 'duration': 7000, 'hdr': True}}
    return {'jobs': jobs}


def media_for(job):
    name = job['source']['name']
    if name.startswith(SHOW):
        return {'type': 'tv', 'show': SHOW, 'tmdb': '31910', 'drive_id': job['prepared_id'], 'season': 1,
                'episode': int(name.split('E')[-1].split('.')[0])}
    return {'type': 'movie', 'show': name.rsplit(' ', 1)[0], 'drive_id': job['prepared_id']}


class Season(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.profile = self.tmp.name
        self.drive, self.native, self.clock = Drive(), Native(), [1000.0]
        self.q = types.SimpleNamespace(profile=self.profile, drive=self.drive, native=self.native, state=library(), log=lambda m: None,
                                       notify=mock.Mock(), stream=types.SimpleNamespace(url=lambda i: 'http://drive/' + i, forget=lambda i: None))

    def tearDown(self):
        self.tmp.cleanup()

    def step(self, free=None, n=1):
        with mock.patch.dict(sys.modules, fake_modules(self.drive)):
            for _ in range(n):
                upscale_cloud.process_one(self.q, lambda: True, picture.load(self.profile), media_for, free, clock=lambda: self.clock[0])
                self.clock[0] += 60

    def group(self):
        groups = up.library(self.q.state, media_for, uq.load(self.profile))
        return next(g for g in groups if g['title'] == SHOW), groups

    def copies(self):
        return uq.load(self.profile)['copies']

    def test_a_season_gets_its_copies_under_every_rule(self):
        g, groups = self.group()
        self.assertEqual(sum(x['kept'] for x in groups), 2)          # the 4K and the HDR film are kept as they are
        self.assertEqual(up.show_sizes(g), [picture.OFF, '1440p', '4K UHD'])
        self.assertNotIn('2K', picture.LABELS)                       # DEC-040
        # Settings › AI Upscale › Naruto: 4K.
        picture.save(self.profile, up.set_show(picture.load(self.profile), g, '4K UHD'))
        # No charger (only while charging is on by default): queued, nothing made, the card says why.
        self.step()
        c = self.copies()
        self.assertEqual(sorted(c), ['ep%d' % n for n in range(1, 7)])
        self.assertTrue(all(e['status'] == 'waiting' for e in c.values()))
        self.assertIn('Waiting for a charger', json.dumps(c))
        self.assertEqual(self.native.converts, [])
        # Charger in: the AI model downloads first, nothing converts meanwhile.
        self.native.state['charging'] = 1
        self.step()
        self.assertEqual((self.native.model, self.native.converts), (1, []))
        self.native.model = 2
        # The first copy fails once (a back-off), the others go one at a time.
        self.native.fail_next = 1
        self.step()
        self.assertEqual(self.copies()['ep1']['status'], 'failed')
        self.step(n=3)
        made = [k for k, e in self.copies().items() if e['status'] == 'ready']
        self.assertEqual(len(made), 3)                               # one per pass: one AI engine at a time
        # A hot phone holds it; so does a full Drive.
        self.native.state['thermal'] = 'serious'
        self.step(n=2)
        self.assertEqual(len([e for e in self.copies().values() if e['status'] == 'ready']), 3)
        self.native.state['thermal'] = 'nominal'
        self.step(free=10 ** 9)
        self.assertIn('Not enough space on Google Drive', json.dumps(self.copies()))
        # Room again; the failed one comes back after its back-off.
        self.clock[0] += 3600
        self.step(free=10 ** 12, n=6)
        c = self.copies()
        self.assertEqual({k: e['status'] for k, e in c.items()}, {'ep%d' % n: 'ready' for n in range(1, 7)})
        self.assertEqual(len(self.native.converts), 7)               # six copies + the failed try
        self.assertNotIn('film4k', c)
        self.assertNotIn('filmhdr', c)
        # The pages: every chip Ready; the Picture menu on AirPlay says the TV gets the copy; the copy plays.
        g, _ = self.group()
        view = up.show_view(picture.load(self.profile), g)
        self.assertEqual({r['chip'] for r in view['rows']}, {'Ready'})
        self.assertEqual(view['remove'], 'Remove the 4K copies…')
        data = uq.load(self.profile)
        self.assertEqual(uq.menu_state(data, 'ep3', 1920, 1080, '4K UHD'), {'state': 'ready', 'label': '4K UHD'})
        copy3 = c['ep3']['copy_id']
        self.assertEqual(uq.choose(data, 'ep3', '4K UHD', lambda i: i in self.drive.files), (copy3, '4K UHD'))
        self.assertEqual(uq.choose(data, 'ep3', '1440p', lambda i: True), ('ep3', None))   # never larger than chosen now
        # Someone deletes a copy on Drive: the original plays, and the next pass makes it again.
        self.drive.files.pop(copy3)
        self.assertEqual(uq.choose(data, 'ep3', '4K UHD', lambda i: i in self.drive.files), ('ep3', None))
        uq.save(self.profile, data)
        self.step(free=10 ** 12, n=2)
        self.assertEqual(self.copies()['ep3']['status'], 'ready')
        self.assertNotEqual(self.copies()['ep3']['copy_id'], copy3)
        # Remove the copies (V3): all go to the Trash, the show is Off, nothing is made again.
        settings, data = up.remove_copies(picture.load(self.profile), uq.load(self.profile), self.group()[0])
        picture.save(self.profile, settings)
        uq.save(self.profile, data)
        self.step(free=10 ** 12, n=3)
        self.assertEqual(len(self.drive.trash), 6)
        self.assertEqual({e['status'] for e in self.copies().values()}, {'gone'})
        converts = len(self.native.converts)
        self.step(free=10 ** 12, n=3)
        self.assertEqual(len(self.native.converts), converts)

    def test_new_downloads_setting_and_low_battery(self):
        settings = picture.load(self.profile)
        settings['downloads']['prepare'] = True                  # Upscale new downloads (720p and 1080p only)
        settings['downloads']['only_charging'] = False
        picture.save(self.profile, settings)
        self.native.model = 2
        self.native.state.update(charging=0, battery=0.1)
        self.step()
        self.assertIn('Battery low', json.dumps(self.copies()))
        self.assertEqual(self.native.converts, [])
        self.native.state.update(battery=0.6)
        self.step(free=10 ** 12, n=7)
        self.assertEqual(sorted(k for k, e in self.copies().items() if e['status'] == 'ready'), ['ep%d' % n for n in range(1, 7)])

    def test_a_phone_without_the_ai_engine_blocks_and_says_so(self):
        g, _ = self.group()
        picture.save(self.profile, up.set_show(picture.load(self.profile), g, '4K UHD'))
        self.native.state['charging'] = 1
        self.native.SUPPORT = {'os26': 0}
        self.step(n=2)
        c = self.copies()
        self.assertTrue(any(e['status'] == 'blocked' and 'iOS 26' in e.get('error', '') for e in c.values()), c)
        self.assertEqual(self.native.converts, [])


if __name__ == '__main__':
    unittest.main()
