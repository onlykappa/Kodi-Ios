"""ISSUE-291: one fake library agrees on all three backend consumers, even with missing/stale telemetry."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'migration/bundled-bootstrap/resources/lib'), str(ROOT / 'migration/bundled-bootstrap')]
import library_index as li
import library_rows
import prepare_downloads
import debrid_drive
import work_state as ws
import transfers
import notifications

NOW = 1000.0


class SharedIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.profile = self.tmp.name
        listing = [{'id': 'ep%d' % n, 'name': 'Rick.and.Morty.S03E%02d.mkv' % n, 'size': 100} for n in (2, 3, 4)]
        self.prep = {'library': {'items': listing}, 'jobs': {
            'ep2': {'source': listing[0], 'status': 'running'},
            'ep3': {'source': listing[1], 'status': 'failed', 'blocked': True, 'error': 'Cannot keep these tracks'},
            'ep4': {'source': listing[2], 'status': 'done'}},
            'current': {'running': True, 'title': listing[0]['name'], 'progress': 20, 'updated': NOW}}
        self.debrid = {'jobs': [{'hash': 'fixture-copy', 'title': 'Rick and Morty', 'season': '3', 'episode': '1',
                                'status': 'copying', 'size': 100, 'copied': 30}],
                       'lanes': {'0': {'job': 'fixture-copy:3:1', 'name': 'wrong old title', 'stage': 'copying',
                                       'sent': 30, 'total': 100, 'updated': NOW, 'slot': 0}}}
        prepare_downloads.save(self.profile, self.prep)
        debrid_drive.save(self.profile, self.debrid)
        self.index = li.refresh(self.profile, clock=lambda: NOW)

    def test_counts_titles_and_states_are_identical(self):
        state = ws.build({'prep': self.prep, 'debrid': self.debrid, 'index': self.index}, NOW)
        ws.save(self.profile, state)
        with patch('time.time', return_value=NOW):
            current = ws.current(self.profile, NOW)
        view = library_rows.with_model(prepare_downloads.library_view({'jobs': {}}), current)
        queue = [j for _, j in transfers.model_entries(current)]
        notices = [notifications.transfer_card(j) for j in current['jobs']]
        self.assertEqual(current['library_counts'], {'total': 4, 'ready': 1, 'working': 2, 'copying': 1,
                                                     'converting': 1, 'kept': 0, 'problems': 1, 'hidden': 0, 'cancelled': 0})
        self.assertEqual(view['library_counts'], current['library_counts'])
        self.assertEqual(view['library_videos'], current['library_videos'])
        wanted = {e['key']: li.entry_title(e) for e in self.index['videos'] if e['state'] in li.WORKING}
        for rows in (queue, notices, view['rows']['preparing'] + view['rows']['downloading']):
            self.assertEqual({j['key']: j['title'] for j in rows}, wanted)
            self.assertEqual({j['library_state'] for j in rows}, {'copying', 'converting'})
        props = library_rows.page_properties(view, index=self.index)
        self.assertEqual((props['headline'], props['count.working']), ('1 of 4 ready', '2'))

    def test_a_movie_copy_being_made_ready_shows_as_running(self):
        """ISSUE-310 (owner, build 477: Iron Man 4K copied and was made ready for AirPlay; Library status and Running now
        showed nothing running). A movie's job id is "hash::"; its index entry is season 0, episode 0."""
        debrid = {'jobs': [{'hash': 'film', 'title': 'Iron Man', 'year': '2008', 'kind': 'movie', 'season': '', 'episode': '',
                            'status': 'copying', 'size': 6035021543, 'copied': 5101308600}],
                  'lanes': {'0': {'job': 'film::', 'name': 'Iron.Man.2008.IMAX.2160p.4K.WEB.x265.mkv', 'stage': 'copying',
                                  'mode': 'ready', 'sent': 5101308600, 'total': 6035021543, 'updated': NOW, 'slot': 0,
                                  'rate': 2e6, 'eta_s': 400}}}
        debrid_drive.save(self.profile, debrid)
        prepare_downloads.save(self.profile, {'library': {'items': []}, 'jobs': {}})
        index = li.refresh(self.profile, clock=lambda: NOW)
        state = ws.build({'debrid': debrid, 'index': index}, NOW)
        film = [e['key'] for e in index['videos'] if e['title'] == 'Iron Man'][0]
        self.assertNotIn(film, [j['key'] for j in state['drive_next']])                 # not demoted to "queued"
        card = [j for j in state['jobs'] if j.get('key') == film][0]
        self.assertEqual(card['state'], ws.RUNNING)
        # Owner: "ensure all screens use the library index": Library status, the Queue/Transfers, Running now and the
        # bell all show the film as running, from the same record.
        ws.save(self.profile, state)
        with patch('time.time', return_value=NOW):
            current = ws.current(self.profile, NOW)
        view = library_rows.with_model(prepare_downloads.library_view({'jobs': {}}), current)
        queue = [j for _, j in transfers.model_entries(current)]
        running = [notifications.transfer_card(j) for j in current['jobs']]
        for rows in (queue, running, view['rows']['downloading']):
            self.assertIn(film, [j['key'] for j in rows])
        self.assertEqual(ws.bell_properties(current)['Notices.Active'], 'true')
        self.assertEqual((card['kind'], card['step'], card['pct']), ('copy', 'Getting it ready for Kodi and AirPlay', 84))

    def test_no_measurement_never_hides_an_indexed_copy(self):
        state = ws.build({'index': self.index}, NOW)
        self.assertEqual(len(state['next']) + len(state['drive_next']), 2)
        self.assertEqual(state['drive_next'][0]['title'], 'S3 E1 · Rick and Morty')
        self.assertEqual(state['running'], 0)
        props, _, _, _ = transfers.page_state({}, NOW, 'up', [], model=state)
        self.assertEqual(props['next.1.title'], 'S3 E1 · Rick and Morty')

    def test_a_season_pack_matches_each_live_lane_to_its_own_episode(self):
        copies = {'jobs': [{'hash': 'PACK', 'title': 'Rick and Morty', 'kind': 'season', 'season': '3',
                            'episode': '', 'episodes': [1, 2, 3], 'status': 'copying'}],
                  'lanes': {str(n): {'job': 'PACK:3:', 'name': 'Rick and Morty', 'stage': 'copying',
                                    'file': 'Rick.and.Morty.S03E%02d.mkv' % (n + 1),
                                    'sent': 10 * (n + 1), 'total': 100, 'count': 3, 'slot': n, 'updated': NOW}
                            for n in range(2)}}
        index = li.build([], {}, copies, clock=lambda: NOW)
        state = ws.build({'debrid': copies, 'index': index}, NOW)
        self.assertEqual(state['running'], 2)
        self.assertEqual({j['title']: j['slot'] for j in state['jobs']},
                         {'S3 E1 · Rick and Morty': 0, 'S3 E2 · Rick and Morty': 1})
        self.assertEqual([j['title'] for j in state['drive_next']], ['S3 E3 · Rick and Morty'])

    def test_every_service_pass_refreshes_even_without_file_changes_and_survives_error(self):
        ticks = iter([False, False, False, True])
        real = li.refresh
        calls = []
        def refresh(*args):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError('synthetic transient read failure')
            return real(*args)
        props, logs = {}, []
        with patch.object(li, 'refresh', side_effect=refresh):
            li.publish(self.profile, lambda _: next(ticks), clock=lambda: NOW, set_property=props.__setitem__, log=logs.append)
        self.assertEqual(len(calls), 3)
        self.assertIn(li.PROPERTY, props)
        self.assertIn('synthetic transient', logs[0])
        source = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('target=library_index.publish,args=(profile,', source)
        self.assertIn("'set_property':xbmcgui.Window(10000).setProperty", source)


if __name__ == '__main__':
    unittest.main()
