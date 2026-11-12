"""DEC-039: the upscale queue step's decisions, the copy chosen for playback and the AirPlay Picture menu state."""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'))
import picture as pc
import upscale_queue as uq


def job(id_, w=1920, h=1080, hdr=False, status='done', name='Naruto S01E03.mp4', duration=1400):
    return {'status': status, 'prepared_id': id_, 'source': {'id': 'orig-' + id_, 'name': name},
            'probe': {'width': w, 'height': h, 'hdr': hdr, 'duration': duration}}


NARUTO = {'type': 'episode', 'tmdb': '31910', 'show': 'Naruto Shippūden'}
LANTERNS = {'type': 'episode', 'tmdb': '1', 'show': 'Lanterns'}
CHARGING = {'battery': 0.5, 'charging': 1, 'thermal': 'nominal', 'low_power': 0}


class Plan(unittest.TestCase):
    def setUp(self):
        self.settings = pc.load(tempfile.mkdtemp())
        pc.apply(self.settings, 'show', NARUTO, upscale='4K UHD')

    def media(self, j):
        return NARUTO if 'Naruto' in j['source']['name'] else LANTERNS

    def test_only_shows_that_ask_and_only_sizes_above(self):
        prep = {'jobs': {'a': job('a'), 'b': job('b', name='Lanterns S01E01.mp4'), 'c': job('c', 3840, 2160),
                         'd': job('d', hdr=True), 'e': job('e', status='waiting'), 'f': job('f', 1280, 720)}}
        data = {'copies': {}}
        added = uq.plan(prep, data, self.settings, self.media)
        self.assertEqual(sorted(added), ['a', 'f'])            # Lanterns is Off; 4K, HDR and unprepared never
        self.assertEqual(data['copies']['a']['label'], '4K UHD')
        self.assertEqual(uq.plan(prep, data, self.settings, self.media), [])   # not twice

    def test_automatic_default_for_new_downloads(self):
        self.settings['downloads'].update(prepare=True, size='1440p')
        data = {'copies': {}}
        uq.plan({'jobs': {'b': job('b', name='Lanterns S01E01.mp4')}}, data, self.settings, self.media)
        self.assertEqual(data['copies']['b']['label'], '1440p')
        pc.apply(self.settings, 'show', LANTERNS, upscale='Off')
        data = {'copies': {}}
        self.assertEqual(uq.plan({'jobs': {'b': job('b', name='Lanterns S01E01.mp4')}}, data, self.settings, self.media), [])

    def test_a_new_size_replaces_a_ready_copy(self):
        data = {'copies': {'a': {'label': '1440p', 'status': 'ready', 'copy_id': 'old'}}}
        uq.plan({'jobs': {'a': job('a')}}, data, self.settings, self.media)
        self.assertEqual(data['copies']['a']['status'], 'waiting')
        self.assertEqual(data['copies']['a']['previous_copy'], 'old')


class Phone(unittest.TestCase):
    def setUp(self):
        self.settings = pc.load(tempfile.mkdtemp())

    def test_only_while_charging(self):
        self.assertEqual(uq.may_run(dict(CHARGING, charging=0), self.settings), (False, 'Waiting for a charger'))
        self.assertEqual(uq.may_run(dict(CHARGING, charging=-1), self.settings), (False, 'Waiting for a charger'))
        self.assertEqual(uq.may_run(CHARGING, self.settings), (True, ''))

    def test_low_battery_without_a_charger(self):
        self.settings['downloads']['only_charging'] = False
        self.assertEqual(uq.may_run({'battery': 0.15, 'charging': 0}, self.settings)[0], False)
        self.assertEqual(uq.may_run({'battery': 0.6, 'charging': 0}, self.settings), (True, ''))

    def test_heat_and_low_power(self):
        self.assertEqual(uq.may_run(dict(CHARGING, thermal='serious'), self.settings)[1], 'Phone is warm · waiting')
        self.assertEqual(uq.may_run(dict(CHARGING, low_power=1), self.settings)[1], 'Low Power Mode is on')
        self.assertTrue(uq.may_run(dict(CHARGING, thermal='fair'), self.settings)[0])

    def test_drive_space(self):
        entry = {'label': '4K UHD', 'duration': 1400, 'width': 1920, 'height': 1080}
        ok, needed = uq.drive_room(10 * 1024 ** 3, entry)
        self.assertTrue(ok)
        self.assertTrue(2.5e9 < needed < 3.5e9, needed)        # ~2.9 GB for 24 min at 16 Mbit/s
        self.assertFalse(uq.drive_room(needed, entry)[0])       # the reserve too
        self.assertTrue(uq.drive_room(None, entry)[0])


class Queue(unittest.TestCase):
    def test_one_at_a_time_running_first(self):
        data = {'copies': {'a': {'status': 'waiting', 'added': 1}, 'b': {'status': 'running', 'added': 2},
                           'c': {'status': 'waiting', 'added': 0}}}
        self.assertEqual(uq.next_job(data), 'b')
        data['copies']['b']['status'] = 'ready'
        self.assertEqual(uq.next_job(data), 'c')

    def test_killed_app_resumes(self):
        data = uq.recover({'copies': {'a': {'status': 'running'}, 'b': {'status': 'ready'}}})
        self.assertEqual(data['copies']['a']['status'], 'waiting')
        self.assertEqual(data['copies']['a']['resumed'], 1)
        self.assertEqual(data['copies']['b']['status'], 'ready')

    def test_failures_back_off_and_final_ones_stop(self):
        entry = uq.failed({'status': 'running'}, 'Drive upload: HTTP 503', clock=lambda: 100)
        self.assertEqual((entry['status'], entry['retry_after']), ('failed', 400))
        self.assertIsNone(uq.next_job({'copies': {'a': entry}}, clock=lambda: 200))
        self.assertEqual(uq.next_job({'copies': {'a': entry}}, clock=lambda: 500), 'a')
        for final in ('HDR video is kept as it is (not upscaled)', 'video conversion: AI upscaling is not available on this device'):
            self.assertEqual(uq.failed({}, final)['status'], 'blocked')

    def test_saved_state_round_trip(self):
        profile = tempfile.mkdtemp()
        data = uq.load(profile)
        data['copies']['a'] = {'status': 'ready', 'label': '4K UHD', 'copy_id': 'x'}
        uq.save(profile, data)
        self.assertEqual(uq.load(profile)['copies']['a']['copy_id'], 'x')


class Playback(unittest.TestCase):
    def setUp(self):
        self.data = {'copies': {'a': {'status': 'ready', 'label': '4K UHD', 'copy_id': 'copy-a'},
                                'b': {'status': 'running', 'label': '4K UHD'}}}

    def test_copy_plays_when_on_and_ready(self):
        self.assertEqual(uq.choose(self.data, 'a', '4K UHD', lambda i: True), ('copy-a', '4K UHD'))
        self.assertEqual(uq.choose(self.data, 'a', 'Off', lambda i: True), ('a', None))
        self.assertEqual(uq.choose(self.data, 'b', '4K UHD', lambda i: True), ('b', None))     # still preparing
        self.assertEqual(uq.choose(self.data, 'z', '4K UHD', lambda i: True), ('z', None))

    def test_never_larger_than_chosen_now(self):
        self.assertEqual(uq.choose(self.data, 'a', '1440p', lambda i: True), ('a', None))

    def test_copy_deleted_on_drive(self):
        self.assertEqual(uq.choose(self.data, 'a', '4K UHD', lambda i: False), ('a', None))
        self.assertEqual(self.data['copies']['a']['status'], 'gone')
        self.assertNotIn('copy_id', self.data['copies']['a'])
        uq.plan({'jobs': {'a': job('a')}}, self.data, dict(pc.load(tempfile.mkdtemp()), default={'upscale': '4K UHD', 'saturation': 0}), lambda j: {})
        self.assertEqual(self.data['copies']['a']['status'], 'waiting')                      # made again


class Menu(unittest.TestCase):
    def test_board_e_states(self):
        data = {'copies': {'a': {'status': 'ready', 'label': '4K UHD'}, 'b': {'status': 'running', 'label': '4K UHD', 'progress': 42, 'eta': 'about 18 min'}}}
        self.assertEqual(uq.menu_state(data, 'a', 1920, 1080, '4K UHD'), {'state': 'ready', 'label': '4K UHD'})
        self.assertEqual(uq.menu_state(data, 'b', 1920, 1080, '4K UHD'), {'state': 'preparing', 'label': '4K UHD', 'progress': 42, 'eta': 'about 18 min'})
        self.assertEqual(uq.menu_state(data, 'c', 1920, 1080, 'Off'), {'state': 'offer', 'label': '4K UHD'})
        self.assertEqual(uq.menu_state(data, 'c', 1920, 1080, '1440p'), {'state': 'offer', 'label': '1440p'})
        self.assertIsNone(uq.menu_state(data, 'd', 3840, 2160, '4K UHD'))
        self.assertEqual(uq.menu_state(data, 'c', 1920, 1080, '4K UHD', ai_available=False), {'state': 'unavailable'})
        self.assertEqual(uq.menu_state(data, 'a', 1920, 1080, '4K UHD', ai_available=False)['state'], 'ready')

    def test_copy_names(self):
        self.assertEqual(uq.copy_name('Naruto S01E03.mp4', '4K UHD'), 'Naruto S01E03 [AI 4K UHD].mp4')
        self.assertTrue(uq.is_copy_name('Naruto S01E03 [AI 4K UHD].mp4'))
        self.assertFalse(uq.is_copy_name('Naruto S01E03.mp4'))


if __name__ == '__main__':
    unittest.main()
