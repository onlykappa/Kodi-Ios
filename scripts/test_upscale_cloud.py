"""AI Upscale copies on Drive (upscale_cloud.process_one, DEC-039/040/042) with a fake converter, Drive and phone."""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
LIB = Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
import picture  # noqa: E402
import upscale_queue as uq  # noqa: E402
import upscale_cloud  # noqa: E402


class Stop(Exception):
    pass


class FakeDrive:
    def __init__(self):
        self.calls = []

    def folder(self, parts):
        return 'staging'

    def call(self, method, url, body=None, headers=None):
        self.calls.append((method, url, json.loads(body) if body else None))
        if method == 'GET':
            return 200, {}, json.dumps({'parents': ['show-folder']})
        return 200, {}, b'{}'


def fake_modules(log):
    class Sink:
        def __init__(self, drive, parent, name, keep_going, on_file, **kw):
            self.on_file, self.name = on_file, name

        def finish(self):
            self.on_file('0', {'id': 'copy1', 'size': 5000000000, 'md5Checksum': 'x'})
            self.on_file('2', {'id': 'side1'})

        def close(self):
            log.append('closed')
    dp = types.SimpleNamespace(Sink=Sink, discard=lambda drive, i: log.append(('discard', i)), bin=lambda drive, i: log.append(('bin', i)))
    du = types.SimpleNamespace(TOP='Kodi', API='https://drive/files', Stop=Stop)
    return {'drive_prepare': dp, 'driveupload': du, 'drivelibrary': types.SimpleNamespace(display_title=lambda n: 'Naruto S01E03')}


class Native:
    upscales = True

    def __init__(self, model=2, out=(3840, 2160), state=None, fail=None):
        self.model, self.out, self.fail = model, out, fail
        self.state = state or {'charging': 1, 'battery': 0.8, 'thermal': 'nominal', 'low_power': 0}
        self.calls = []

    SUPPORT = {'os26': 1, 'video': {'supported': 1, 'fits': 1, 'scale': 2}}

    def device_state(self):
        return self.state

    def upscale_support(self, w, h, label, engine=0):
        return getattr(self, 'support', self.SUPPORT)

    def upscale_model(self, w, h, label, engine, start=False):
        self.calls.append(('model', start))
        return self.model

    def convert_to(self, source, sink, keep_going, progress, paused, waiting, upscale=None):
        self.calls.append(('convert', source, upscale))
        progress(0, 50, 100)
        if self.fail:
            raise self.fail

    def probe(self, url):
        return {'ready': True, 'width': self.out[0], 'height': self.out[1]}


def queue(profile, native):
    prep = {'jobs': {'s': {'status': 'done', 'prepared_id': 'orig1', 'source': {'id': 'orig1', 'name': 'Naruto S01E03.mp4'},
                           'probe': {'width': 1920, 'height': 1080, 'duration': 1400, 'hdr': False}}}}
    return types.SimpleNamespace(profile=profile, drive=FakeDrive(), native=native, state=prep, log=lambda m: None,
                                 notify=mock.Mock(), stream=types.SimpleNamespace(url=lambda i: 'http://drive/' + i, forget=lambda i: None))


SHOW = {'tmdb': '31910', 'type': 'tv'}


def settings(label='4K UHD'):
    data = picture.load('/nonexistent')
    data['shows']['tv:31910'] = {'upscale': label, 'saturation': 0}
    return data


class MakesACopy(unittest.TestCase):
    def run_one(self, native, setting=None, free=None):
        log = []
        with tempfile.TemporaryDirectory() as profile, mock.patch.dict(sys.modules, fake_modules(log)):
            q = queue(profile, native)
            done = upscale_cloud.process_one(q, lambda: True, setting or settings(), lambda job: SHOW, free, clock=lambda: 1000.0)
            return done, uq.load(profile)['copies'].get('orig1'), q, log

    def test_a_1080p_episode_gets_a_4k_copy_beside_the_original(self):
        native = Native()
        done, entry, q, log = self.run_one(native)
        self.assertTrue(done)
        self.assertEqual((entry['status'], entry['copy_id'], entry['label']), ('ready', 'copy1', '4K UHD'))
        self.assertEqual(native.calls[-1], ('convert', 'http://drive/orig1', (3840, 2160, 2, 0)))
        moved = [c for c in q.drive.calls if c[0] == 'PATCH']
        self.assertIn('addParents=show-folder', moved[0][1])
        self.assertEqual(moved[0][2], {'name': 'Naruto S01E03 [AI 4K UHD].mp4'})
        self.assertIn(('discard', 'side1'), log)              # the copy keeps no subtitle sidecars
        self.assertNotIn(('bin', 'orig1'), log)               # the original stays (AirPlay, Off)
        q.notify.assert_called_once()

    def test_without_a_charger_nothing_starts_and_the_card_says_why(self):
        native = Native(state={'charging': 0, 'battery': 0.9, 'thermal': 'nominal'})
        done, entry, q, log = self.run_one(native)
        self.assertFalse(done)
        self.assertEqual((entry['status'], entry['note']), ('waiting', 'Waiting for a charger'))
        self.assertFalse([c for c in native.calls if c[0] == 'convert'])

    def test_a_hot_phone_or_full_drive_waits(self):
        done, entry, _, _ = self.run_one(Native(state={'charging': 1, 'thermal': 'serious'}))
        self.assertEqual(entry['note'], 'Phone is warm · waiting')
        done, entry, _, _ = self.run_one(Native(), free=1000)
        self.assertEqual(entry['note'], 'Not enough space on Google Drive')

    def test_the_model_is_downloaded_first(self):
        native = Native(model=0)
        done, entry, _, _ = self.run_one(native)
        # The first look is the Settings status card's (saved as 'engine'), then the copy's own check starts the download.
        self.assertEqual(native.calls, [('model', False), ('model', False), ('model', True)])
        self.assertEqual((entry['status'], entry['note']), ('waiting', 'Downloading the AI model'))

    def test_settings_can_ask_for_the_model_and_see_the_engine(self):
        log = []
        with tempfile.TemporaryDirectory() as profile, mock.patch.dict(sys.modules, fake_modules(log)):
            uq.save(profile, {'copies': {}, 'model_request': True})
            native = Native(model=0)
            q = queue(profile, native)
            upscale_cloud.process_one(q, lambda: True, settings(picture.OFF), lambda job: SHOW, clock=lambda: 1000.0)
            data = uq.load(profile)
        self.assertIn(('model', True), native.calls)
        self.assertEqual(data['engine'], {'upscales': True, 'model': 1})
        self.assertNotIn('model_request', data)

    def test_a_copy_of_the_wrong_size_is_thrown_away_and_retried_later(self):
        done, entry, _, log = self.run_one(Native(out=(1920, 1080)))
        self.assertEqual(entry['status'], 'failed')
        self.assertIn('not 3840x2160', entry['error'])
        self.assertIn(('discard', 'copy1'), log)
        self.assertGreater(entry['retry_after'], 1000)

    def test_a_stop_leaves_it_waiting(self):
        done, entry, _, log = self.run_one(Native(fail=Stop('paused')))
        self.assertEqual((entry['status'], entry['progress']), ('waiting', 0))
        self.assertIn('closed', log)

    def test_only_4x_models_block_a_1080p_copy_instead_of_closing_kodi(self):
        native = Native()
        native.support = {'os26': 1, 'image': {'supported': 1, 'fits': 1, 'scale': 4}, 'video': {'supported': 1, 'fits': 0, 'scale': 0}}
        done, entry, _, _ = self.run_one(native)
        self.assertEqual(entry['status'], 'blocked')
        self.assertIn('7680x4320', entry['error'])
        self.assertFalse([c for c in native.calls if c[0] == 'convert'])

    def test_no_upscaler_in_this_build_blocks_it(self):
        native = Native()
        native.upscales = False
        done, entry, _, _ = self.run_one(native)
        self.assertEqual(entry['status'], 'blocked')

    def test_off_makes_nothing(self):
        done, entry, _, _ = self.run_one(Native(), setting=settings(picture.OFF))
        self.assertFalse(done)
        self.assertIsNone(entry)


class RemovesCopies(unittest.TestCase):
    def test_remove_sends_copies_to_the_bin_and_drops_waiting_ones(self):
        # V3, board C "Remove the copies…" (after the alert).
        log = []
        with tempfile.TemporaryDirectory() as profile, mock.patch.dict(sys.modules, fake_modules(log)):
            q = queue(profile, Native(state={'charging': 0, 'battery': 0.9, 'thermal': 'nominal'}))
            data = uq.load(profile)
            data['copies'] = {'a': {'status': 'ready', 'label': '4K UHD', 'copy_id': 'c-a'}, 'b': {'status': 'waiting', 'label': '4K UHD'}}
            data['remove'] = ['a', 'b']
            uq.save(profile, data)
            off = settings()
            off['shows'] = {}
            upscale_cloud.process_one(q, lambda: True, picture.load(profile), lambda job: SHOW, None, clock=lambda: 1000.0)
            after = uq.load(profile)
            self.assertIn(('bin', 'c-a'), log)
            self.assertEqual((after['copies']['a']['status'], after['copies']['b']['status']), ('gone', 'gone'))
            self.assertNotIn('remove', after)


class WhichShow(unittest.TestCase):
    def test_a_queued_download_knows_its_show_and_others_go_by_title(self):
        jobs = {'jobs': [{'show_tmdb': '31910', 'title': 'Naruto Shippuden', 'files': [{'drive_id': 'orig1'}]}]}
        with mock.patch.dict(sys.modules, {'debrid_drive': types.SimpleNamespace(load=lambda p: jobs)}):
            media_for = upscale_cloud.media_lookup('/p', parse=lambda n: {'title': 'Lanterns', 'season': 2, 'episode': 1})
        self.assertEqual(picture.show_key(media_for({'prepared_id': 'orig1'})), 'tv:31910')
        other = media_for({'prepared_id': 'x', 'source': {'id': 'x', 'name': 'Lanterns.S02E01.1080p.mkv'}})
        self.assertEqual((picture.show_key(other), picture.video_key(other)), ('title:lanterns', 'x'))


class PlaysTheCopy(unittest.TestCase):
    def test_a_ready_copy_plays_when_the_show_asks_and_the_library_hides_it(self):
        import drivelibrary
        self.assertFalse(drivelibrary.is_video('Naruto S01E03 [AI 4K UHD].mp4'))
        self.assertTrue(drivelibrary.is_video('Naruto S01E03.mp4'))
        sys.path.insert(0, str(LIB.parents[2] / 'import-overlays/plugin.video.kodi.ios.watch/resources/lib'))
        import ios_library
        path = 'plugin://plugin.googledrive/?action=play&item_id=orig1&driveid=d'
        params = {'tmdb_id': '31910', 'kind': 'episode', 'show': 'Naruto Shippuden'}
        with tempfile.TemporaryDirectory() as profile:
            self.assertEqual(ios_library.upscaled_path(path, params, profile), path)          # no copy yet
            uq.save(profile, {'copies': {'orig1': {'label': '4K UHD', 'status': 'ready', 'copy_id': 'copy1'}}})
            self.assertEqual(ios_library.upscaled_path(path, params, profile), path)          # AI Upscale off
            data = picture.load(profile)
            picture.apply(data, 'show', {'tmdb': '31910', 'type': 'tv'}, upscale='4K UHD')
            picture.save(profile, data)
            self.assertIn('item_id=copy1', ios_library.upscaled_path(path, params, profile))
            picture.apply(data, 'show', {'tmdb': '31910', 'type': 'tv'}, upscale='1440p')    # smaller than the copy
            picture.save(profile, data)
            self.assertIn('item_id=orig1', ios_library.upscaled_path(path, params, profile))


if __name__ == '__main__':
    unittest.main()
