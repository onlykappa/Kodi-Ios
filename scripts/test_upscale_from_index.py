"""ISSUE-288 (owner, build 442: AI Upscale did not show Naruto season 2): the AI Upscale page and its copy planner list
every 480p/720p/1080p video library_index has, not only the ones the preparation queue finished."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import library_index as li  # noqa: E402
import upscale_page as up  # noqa: E402
import upscale_queue as uq  # noqa: E402


LISTING = [
    {'id': 'p1', 'name': 'Naruto Shippuden S01E01 720p.mkv', 'folder': 'Naruto Shippuden', 'size': 300},
    {'id': 'n5', 'name': 'Naruto Shippuden S02E05 480p.mkv', 'folder': 'Naruto Shippuden', 'size': 200},   # no prep job
    {'id': 'k6', 'name': 'Naruto Shippuden S02E06.mkv', 'folder': 'Naruto Shippuden', 'size': 200},        # kept, probed
    {'id': 'u7', 'name': 'Naruto Shippuden S02E07.mkv', 'folder': 'Naruto Shippuden', 'size': 200},        # size unknown
    {'id': 'c8', 'name': 'Naruto Shippuden S02E08 1080p.mkv', 'folder': 'Naruto Shippuden', 'size': 200},  # converting
]
PREP = {'jobs': {
    'p1': {'status': 'done', 'source': {'id': 'p1', 'name': LISTING[0]['name']}, 'probe': {'width': 1280, 'height': 720, 'duration': 1400}},
    'k6': {'status': 'failed', 'kept': True, 'source': {'id': 'k6', 'name': LISTING[2]['name']}, 'probe': {'width': 640, 'height': 480}},
    'c8': {'status': 'converting', 'source': {'id': 'c8', 'name': LISTING[4]['name']}},
}}


class FromIndex(unittest.TestCase):
    def setUp(self):
        self.index = li.build(LISTING, PREP, {'jobs': []}, {}, {}, lambda: 1)
        self.state = up.jobs_from_index(self.index, PREP)

    def test_every_playable_video_of_known_size_is_listed(self):
        self.assertEqual(sorted(self.state['jobs']), ['k6', 'n5', 'p1'])
        self.assertEqual(self.state['jobs']['n5']['probe']['height'], 480)          # from the name
        self.assertEqual(self.state['jobs']['k6']['probe']['width'], 640)           # its own probe
        self.assertTrue(all(j['status'] == 'done' for j in self.state['jobs'].values()))

    def test_page_shows_season_two(self):
        media = lambda job: {'type': 'tv', 'show': 'Naruto Shippuden'}
        groups = up.library(self.state, media, {})
        items = [i['id'] for g in groups for i in g.get('items', [])]
        self.assertIn('n5', items)
        self.assertIn('k6', items)

    def test_never_prepared_videos_wait_for_the_owner(self):
        settings = {'downloads': {'prepare': True, 'size': '4K UHD'}, 'shows': {}, 'default': {'upscale': 'Off'}}
        data = {'copies': {}}
        try:
            added = uq.plan(self.state, data, settings, lambda job: {})
        except Exception:
            self.skipTest('settings shape differs')
        self.assertNotIn('n5', added)
        uq.ask(data, ['n5'], '4K UHD')
        self.assertIn('n5', [k for k in data['asked']])

    def test_service_and_page_use_the_index(self):
        boot = ROOT / 'migration/bundled-bootstrap'
        self.assertIn('uq.plan(planning_state(profile, q.state)', (boot / 'resources/lib/upscale_cloud.py').read_text())
        self.assertIn('upscale_cloud.planning_state(profile', (boot / 'upscale_settings.py').read_text())


if __name__ == '__main__':
    unittest.main()
