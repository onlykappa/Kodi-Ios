"""ISSUE-231 (owner, build 374: "I selected 1080p ... 480p is ass"): a season built at a chosen quality keeps it.
Before the download the picker leaves out versions whose own name says a lower quality, that are upscales of a lower one
or are far too small; after the copy, a file whose real picture is lower is not kept and its version is left out next time."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
spec = importlib.util.spec_from_file_location('deck_picker', ROOT / 'migration/deck-picker/deck_picker.py')
dp = importlib.util.module_from_spec(spec)
sys.modules.setdefault('xbmc', types.SimpleNamespace(log=lambda *a, **k: None, LOGINFO=1))
spec.loader.exec_module(dp)
import prepare_downloads as prep  # noqa: E402
import debrid_drive  # noqa: E402


def item(name, size, quality='1080p', tags='', multi=False, seeds=50):
    return {'idx': 0, 'name': name, 'size': size, 'quality': quality, 'tags_text': tags, 'multi': multi, 'seeds': seeds, 'peers': 0, 'providers': []}


class BeforeTheDownload(unittest.TestCase):
    def test_versions_that_are_not_really_the_chosen_quality_are_left_out(self):
        upscale = item('Naruto Shippuden Episode 006 Mission Cleared_2.25x_1920x1080_alq-10.mkv', 0.6)
        dvd = item('Naruto_Shippuden_-_001-002_[v2][DVD][576p][10bit].mkv', 0.5)
        starved = item('Show.S01E01.1080p.WEB.x264.mkv', 0.12, tags='x264')            # 0.7 Mbit/s for 23 min of H.264
        real = item('Naruto Shippuden - Vol.01 (BDRip 1080p x264 AAC)/ep01.mkv', 1.2, tags='x264')
        small_hevc = item('[SubsPlease] Naruto Shippuden - 01 (1080p) [HEVC].mkv', 0.35, tags='HEVC')
        for it, why in ((upscale, 'upscale'), (dvd, 'SD'), (starved, 'too small')):
            self.assertIn(why, dp.below_quality(it, '1080p', 23))
        self.assertEqual(dp.below_quality(real, '1080p', 23), '')
        self.assertEqual(dp.below_quality(small_hevc, '1080p', 23), '')                 # a small HEVC anime encode is fine
        self.assertEqual(dp.below_quality(dvd, '480p', 23), '')                          # asking for SD is allowed
        best = dp.auto_choose([dict(upscale, seeds=500), dict(dvd, seeds=400), dict(real, seeds=5)],
                              {'quality': '1080p', 'strict_quality': True, 'runtime': 23})
        self.assertEqual(best['name'], real['name'])                                     # fewer seeds, but really 1080p
        # ISSUE-236 (owner: "only grab the lower quality if it's the absolute only one available"): with nothing really
        # 1080p, the best that exists is taken and marked as a fallback.
        only = dp.auto_choose([upscale, dvd], {'quality': '1080p', 'strict_quality': True, 'runtime': 23})
        self.assertTrue(only['fallback'])

    def test_a_version_found_lower_after_its_copy_is_used_only_when_nothing_else_exists(self):
        pack = item('Naruto Shippuden (001-500) [Complete Series + Movies (1080p)]/Naruto Shippuden Episode 001 Homecoming.mkv', 0.26, seeds=232)
        real720 = item('Naruto.Shippuden.S01E01.720p.WEB.x264.mkv', 0.6, quality='720p', tags='x264', seeds=4)
        want = {'quality': '1080p', 'strict_quality': True, 'runtime': 23}
        self.assertEqual(dp.auto_choose([pack, real720], want)['name'], pack['name'])          # its name and size pass: tried first
        self.assertFalse(dp.auto_choose([pack, real720], want).get('fallback'))
        lower = dict(want, lower_names=[pack['name']])                                          # its copy was 640x480
        best = dp.auto_choose([pack, real720], lower)
        self.assertEqual((best['name'], best['fallback']), (real720['name'], True))             # the next best, said so
        best = dp.auto_choose([pack], lower)
        self.assertEqual((best['name'], best['fallback']), (pack['name'], True))                # the absolute only one: taken
        rt = (LIB / 'episode_watch_runtime.py').read_text()
        self.assertIn("request['lower_names']", rt);self.assertIn("and not j.get('low_quality')][-20:]", rt)
        cloud = (LIB / 'elementum_cloud.py').read_text()
        self.assertIn("wanted['_fallback'] = bool(selected.get('fallback'))", cloud)
        self.assertIn("and not (auto or {}).get('_fallback')", cloud)


class RepairQuality(unittest.TestCase):
    """ISSUE-237 (owner log f63389f1, build 376): Repair searched Naruto S1 E5/E6 at "any quality" (the show's ready
    episodes were 480p) and took "..._2.25x_1920x1080_alq-10", an uploader's upscale of the DVD episode."""
    def test_repair_uses_the_quality_chosen_for_the_show(self):
        import episode_watch
        import library_repair
        with tempfile.TemporaryDirectory() as profile:
            ready = [{'id': 'x', 'quality': '480p'}]
            self.assertEqual(library_repair.chosen(profile, '31910', ready), '480p')        # nothing chosen: what it has
            self.assertEqual(library_repair.chosen(profile, '31910', []), None)
            episode_watch.plan_season(profile, '31910', 'Naruto Shippuuden', 1, [5, 6], '1080p', now=1)
            self.assertEqual(library_repair.chosen(profile, '31910', ready), '1080p')
        self.assertEqual(library_repair.tries_for('1080p'), ['1080p'])                    # no "any quality" pass after it
        self.assertEqual(library_repair.tries_for(''), [None])
        page = (ROOT / 'migration/bundled-bootstrap/library_repair_page.py').read_text()
        self.assertIn("library_repair.tries_for(a.get('quality'))", page)
        manager = (ROOT / 'migration/bundled-bootstrap/library_manager.py').read_text()
        self.assertGreaterEqual(manager.count('library_repair.chosen(profile, tmdb, '), 2)
        self.assertNotIn('library_repair.qualities(', manager)

    def test_a_fallback_takes_a_real_lower_version_before_a_fake_1080p(self):
        upscale = item('Naruto Shippuden Episode 005 The Kazekage Stands Tall_2.25x_1920x1080_alq-10.mp4', 4.14, seeds=232)
        real720 = item('Naruto.Shippuden.S01E05.720p.WEB.x264.mkv', 0.6, quality='720p', tags='x264', seeds=4)
        dvd = item('Naruto Shippuden Episode 005 The Kazekage Stands Tall.mkv', 0.26, quality='480p', seeds=232)
        want = {'quality': '1080p', 'strict_quality': True, 'runtime': 23}
        best = dp.auto_choose([upscale, real720, dvd], want)
        self.assertEqual((best['name'], best['fallback']), (real720['name'], True))
        best = dp.auto_choose([upscale, dvd], want)
        self.assertEqual((best['name'], best['fallback']), (dvd['name'], True))          # the original, not it blown up 16x
        best = dp.auto_choose([upscale], want)
        self.assertEqual((best['name'], best['fallback']), (upscale['name'], True))      # the absolute only one: taken


class AfterTheCopy(unittest.TestCase):
    def test_the_real_picture_decides(self):
        self.assertTrue(prep.below_wanted({'width': 640, 'height': 480}, '1080p'))
        self.assertFalse(prep.below_wanted({'width': 1440, 'height': 1080}, '1080p'))      # 4:3 1080p
        self.assertFalse(prep.below_wanted({'width': 1920, 'height': 800}, '1080p'))       # scope 1080p
        self.assertTrue(prep.below_wanted({'width': 1280, 'height': 720}, '1080p'))
        self.assertFalse(prep.below_wanted({'width': 640, 'height': 480}, ''))             # no quality chosen: never
        self.assertFalse(prep.below_wanted({'width': 640, 'height': 480}, '480p'))

    def test_a_low_copy_ends_failed_and_its_version_is_left_out_next_time(self):
        with tempfile.TemporaryDirectory() as p:
            debrid_drive.queue(p, {'id': 'a' * 40, 'name': 'Naruto Shippuden (001-500) [Complete Series + Movies (1080p)]'}, 'episode',
                               'Naruto Shippuuden', '1', '1', show_tmdb='31910', quality='1080p')
            state = debrid_drive.load(p)
            state['jobs'][0].update(status='done', files=[{'path': 'x', 'done': True, 'drive_id': 'd1'}])
            debrid_drive.save(p, state)
            job, quality = debrid_drive.wanted_quality(debrid_drive.load(p), 'd1')
            self.assertEqual(quality, '1080p')
            debrid_drive.refuse_low_quality(p, 'd1', 'Not the quality you picked: 640x480, you chose 1080p')
            after = debrid_drive.load(p)['jobs'][0]
            self.assertEqual((after['status'], after['low_quality']), ('failed', True))
            found = debrid_drive.problems(debrid_drive.load(p))
            self.assertEqual(found[0]['kind'], 'source')
            spec2 = importlib.util.spec_from_file_location('copy_problems', ROOT / 'migration/bundled-bootstrap/copy_problems.py')
            cp = importlib.util.module_from_spec(spec2);spec2.loader.exec_module(cp)
            self.assertEqual(cp.plain(found[0]), ('Not the quality you picked', 'source'))
        # The next automatic search for the episode leaves that version out (failed, not cancelled).
        rt = (LIB / 'episode_watch_runtime.py').read_text()
        self.assertIn("j.get('status')=='failed' and 'cancel' not in str(j.get('error','')).lower()", rt)

    def test_the_guard_is_wired(self):
        cloud = (LIB / 'prepare_cloud.py').read_text()
        self.assertIn('prep.below_wanted(before,wanted)', cloud);self.assertIn('debrid_drive.refuse_low_quality', cloud)
        self.assertLess(cloud.index('prep.below_wanted(before,wanted)'), cloud.index('if q.skip_compatible(slot,job,item,before)'))
        self.assertIn("quality=((auto or {}).get('profile') or {}).get('quality')", (LIB / 'elementum_cloud.py').read_text())


class UploadAndReadBack(unittest.TestCase):
    """ISSUE-232 (owner log 47e2276a): the card follows the upload once the movie is made; a read-back that failed while the
    Drive stream had a read problem waits as network trouble."""
    def test_each_confirmed_piece_tells_the_page(self):
        import drive_prepare
        sink = drive_prepare.Sink.__new__(drive_prepare.Sink)
        sink.marks = [];sink.sent = 0;sink.clock = lambda: 1.0
        seen = []
        sink.on_confirmed = lambda: seen.append(sink.sent)
        sink._confirmed({'offset': 4 * 1024 * 1024}, 0)
        sink._confirmed({'offset': 8 * 1024 * 1024}, 1)                                 # a subtitle track: not the movie
        self.assertEqual(seen, [4 * 1024 * 1024])
        cloud = (LIB / 'prepare_cloud.py').read_text()
        self.assertIn("Uploading to Google Drive · %d%%", cloud);self.assertIn('sink.on_confirmed=upload_tick', cloud)

    def test_a_failed_read_back_during_network_trouble_waits(self):
        cloud = (LIB / 'prepare_cloud.py').read_text()
        self.assertIn("read_trouble='validation failed' in str(error).lower() and bool((q.stream.stats() if q.stream else {}).get('read_error'))", cloud)
        self.assertIn('(debrid_drive.network_error(error) or read_trouble)', cloud)


class DeletedMidConversion(unittest.TestCase):
    """ISSUE-233 (owner log 1ae21097: "deleting stuff seems to bug out if it's mid conversion"): after Naruto was deleted, 32
    "Drive video is unavailable or incomplete" failures came back every minute for the deleted episodes."""
    def test_a_deleted_video_is_gone_not_failed(self):
        class D:
            def __init__(self, status, body):self.status, self.body = status, body
            def call(self, *a, **k):return self.status, {}, json.dumps(self.body).encode()
        with self.assertRaises(prep.SourceGone):prep.metadata(D(200, {'id': 'x', 'trashed': True, 'md5Checksum': 'm', 'size': '5'}), 'x')
        with self.assertRaises(prep.SourceGone):prep.metadata(D(404, {}), 'x')
        with self.assertRaises(RuntimeError) as other:prep.metadata(D(500, {}), 'x')
        self.assertNotIsInstance(other.exception, prep.SourceGone)                        # Drive trouble is still retried

    def test_deleting_takes_videos_out_of_the_queue_and_stops_the_running_one(self):
        with tempfile.TemporaryDirectory() as p:
            state = {'jobs': {'a': {'source': {'id': 'a', 'name': 'N.S01E24.mkv', 'parents': ['show']}, 'status': 'waiting'},
                              'b': {'source': {'id': 'b', 'name': 'N.S01E25.mkv', 'parents': ['show']}, 'status': 'failed', 'error': 'x'},
                              'c': {'source': {'id': 'c', 'name': 'Other.mkv', 'parents': ['other']}, 'status': 'waiting'}},
                     'current': {'running': True, 'title': 'N.S01E24.mkv'}}
            prep.save(p, state)
            with mock.patch.object(prep, 'running_id', return_value='a'):
                self.assertEqual(prep.forget(p, folder_id='show'), 2)                      # a whole show folder
                self.assertTrue(prep.interrupts(p))                                         # the running conversion stops
            shown = prep.apply_to(prep.load(p), prep.pending_requests(p), 1)
            self.assertEqual({k: j['status'] for k, j in shown['jobs'].items()}, {'a': 'superseded', 'b': 'superseded', 'c': 'waiting'})
            self.assertEqual([x['id'] for x in prep.preparation_problems(shown)], [])         # not listed as problems
        cloud = (LIB / 'prepare_cloud.py').read_text()
        self.assertIn('except prep.SourceGone as error:', cloud)
        self.assertIn('prepare_downloads.forget(profile, removed)', (ROOT / 'migration/bundled-bootstrap/library_manager.py').read_text())
        self.assertIn('prepare_downloads.forget(', (ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_remove.py').read_text())


class RefreshLists(unittest.TestCase):
    """ISSUE-234 (owner: "library status doesn't really refresh, it's awful"): with videos waiting, a Refresh's inspection is
    deferred (ISSUE-230), and nothing was listed at all, so the page sat on "Checking…"."""
    def test_a_refresh_lists_at_once_and_keeps_the_inspection_for_later(self):
        src = (LIB / 'prepare_downloads.py').read_text()
        self.assertIn('if listing_only and inspection:', src);self.assertIn('inspection=False;self.inspection_pending=True', src)
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn("preparation.scan(can_prepare,force=True,listing_only=True)", service)
        self.assertIn("preparation.marker_time()!=getattr(preparation,'listed_for',None)", service)
        with tempfile.TemporaryDirectory() as p:
            q = prep.Queue.__new__(prep.Queue);q.profile = p
            self.assertEqual(q.marker_time(), 0.0)
            prep.request_check(p, inspect=True)
            self.assertGreater(q.marker_time(), 0)


if __name__ == '__main__':
    unittest.main()
