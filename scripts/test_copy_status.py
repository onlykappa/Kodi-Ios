"""ISSUE-273/274/275 (owner screenshots and log 3848afa9, build 424): copy cards smooth and saying "Getting it ready", a graph
for every copy lane, one release per season, and copies before new preparations."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(ROOT / 'migration/deck-picker'))
import work_state  # noqa: E402
import transfer_history  # noqa: E402
import deck_picker as dp  # noqa: E402


def lane(**kw):
    base = {'stage': 'copying', 'name': 'Naruto Shippuuden', 'sent': 50 * 2**20, 'total': 100 * 2**20, 'rate_own': 2 * 2**20,
            'rate': 2 * 2**20, 'updated': 1000.0, 'job': 'h:2:48', 'count': 1, 'index': 1, 'slot': 0}
    base.update(kw)
    return base


class Card(unittest.TestCase):
    def card(self, current, now):
        job = {'hash': 'h', 'season': '2', 'episode': '48', 'status': 'copying', 'title': 'Naruto Shippuuden', 'kind': 'episode'}
        return work_state._copy({'jobs': [job], 'current': current}, now)

    def test_the_bar_glides_between_reports_and_never_jumps_ahead(self):
        self.assertEqual(self.card(lane(), 1000)['pct'], 50)
        self.assertEqual(self.card(lane(), 1005)['pct'], 60)          # 2 MB/s for 5 s of 100 MB
        self.assertEqual(self.card(lane(), 1010)['pct'], 70)
        far = self.card(lane(), 1000 + work_state.MAX_GLIDE + 10)['pct']
        self.assertEqual(far, 50 + int(100 * 2 * work_state.MAX_GLIDE / 100))   # at most MAX_GLIDE s of glide
        self.assertLess(self.card(lane(sent=99 * 2**20), 1010)['pct'], 100)

    def test_a_copy_made_ready_on_its_way_says_so(self):
        c = self.card(lane(mode='ready'), 1000)
        self.assertTrue(c['step'].startswith('Getting it ready for Kodi and AirPlay'))
        quiet = self.card(lane(mode='ready'), 1000 + work_state.COPY_QUIET + 61)
        self.assertTrue(quiet['wait'].startswith('Getting it ready · waiting for Google Drive'))


class Graphs(unittest.TestCase):
    def test_every_copy_lane_has_its_own_graph(self):
        lanes = {'0': lane(job='h:2:48'), '1': lane(job='h:2:49', slot=1), '2': lane(job='h:2:50', slot=2, updated=0)}
        out = transfer_history.activity([], lanes['0'], {}, lanes, now=1010)
        self.assertEqual(sorted(out), ['up', 'up.1'])                  # lane 2 has not reported for 60 s
        self.assertEqual((out['up']['job'], out['up.1']['job']), ('h:2:48', 'h:2:49'))
        data = transfer_history.track({}, 1010, out)
        self.assertEqual(sorted(data['jobs']), ['up', 'up.1'])
        self.assertEqual(transfer_history.running(data, 1010), ['up', 'up.1'])
        src = (ROOT / 'migration/bundled-bootstrap/library_status.py').read_text()
        self.assertIn("v.get('job')==s['live_job']", src)


class OneReleasePerSeason(unittest.TestCase):
    def item(self, name, quality='480p', seeds=20, size=0.2):
        return {'idx': 0, 'name': name, 'size': size, 'quality': quality, 'tags_text': '', 'multi': False, 'seeds': seeds, 'peers': 0, 'providers': []}

    def test_the_seasons_release_goes_first_at_equal_quality(self):
        self.assertEqual(dp.release_group('[Anime Time] Naruto Shippuden - 049.mkv'), 'anime time')
        self.assertEqual(dp.release_group('Naruto.Shippuden.S02E33.480p.NF.WEB-DL-Emmid.mkv'), 'emmid')
        same = self.item('[Anime Time] Naruto Shippuden - 051 - X.mkv', seeds=5)
        other = self.item('[Erai-raws] Naruto Shippuuden - 051 [480p].mkv', seeds=90, size=0.35)
        want = {'quality': '480p', 'season_names': ['[Anime Time] Naruto Shippuden Complete/[Anime Time] Naruto Shippuden - 048 - Bonds.mkv']}
        self.assertEqual(dp.auto_choose([other, same], want)['name'], same['name'])
        better = self.item('[Erai-raws] Naruto Shippuuden - 051 [720p].mkv', quality='720p', seeds=90)
        self.assertEqual(dp.auto_choose([better, same], dict(want, quality='720p'))['name'], better['name'])   # never over quality


class CopiesFirst(unittest.TestCase):
    def test_preparation_waits_while_copies_run_unless_watched_next(self):
        import prepare_cloud
        src = (LIB / 'prepare_cloud.py').read_text()
        self.assertIn("copies_running(q)", src);self.assertIn("prep.watch_next(pair[1])", src)
        q = mock.Mock();q.clock = lambda: 1000;q.profile = '/x'
        with mock.patch('debrid_drive.load', return_value={'lanes': {'0': lane(updated=990)}}):
            self.assertTrue(prepare_cloud.copies_running(q))
        with mock.patch('debrid_drive.load', return_value={'lanes': {'0': lane(updated=900)}}):
            self.assertFalse(prepare_cloud.copies_running(q))
        self.assertEqual(work_state.COPY_PREP_WAIT, 'Starts when the downloads finish')


if __name__ == '__main__':
    unittest.main()
