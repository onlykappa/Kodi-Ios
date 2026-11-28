"""ISSUE-501: Library status shows a downloaded season as one row, 'Show · Season 2 · 3 of 10 episodes', not one row per episode."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import library_rows as lr
import onepace_show


def item(title, state, pct=0, sub=''):
    return {'kind': 'row', 'label': title, 'label2': sub, 'props': {'kind': 'row', 'state': state, 'pct': str(pct), 'ring': 'ring_00.png'}, 'row': {'title': title}}


class Seasons(unittest.TestCase):
    def test_titles_in_both_orders(self):
        self.assertEqual(lr.season_of('Naruto · S2 E48'), ('Naruto', 2, 48)); self.assertEqual(lr.season_of('S2 E48 · Naruto Shippuden'), ('Naruto Shippuden', 2, 48))
        self.assertIsNone(lr.season_of('Interstellar')); self.assertIsNone(lr.season_of(''))

    def test_a_season_is_one_row_with_the_count_and_the_whole_share(self):
        items = [item('Heat', 'downloading', 10, 'Downloading'), item('Naruto · S2 E5', 'waiting', 0, 'Prepares next'), item('Naruto · S2 E3', 'downloading', 50, 'Downloading · 7.2 MB/s · 4 min'),
                 item('Naruto · S2 E4', 'waiting', 0, 'Prepares next'), item('S1 E3 · Solo', 'waiting', 0, 'Prepares next')]
        out = lr.group_seasons(items, [{'title': 'Naruto · S2 E1'}, {'title': 'Naruto · S2 E2'}])
        self.assertEqual([o['label'] for o in out], ['Heat', 'Naruto · Season 2', 'S1 E3 · Solo'])           # one episode alone stays; the season stands where its first episode stood
        season = out[1]
        self.assertEqual(season['label2'], 'Downloading · 2 of 5 episodes · 7.2 MB/s · 4 min'); self.assertEqual((season['props']['pct'], season['props']['season_group']), ('50', 'true'))
        self.assertEqual(season['row']['title'], 'Naruto · S2 E3')   # the downloading episode leads and keeps its actions

    def test_waiting_only_and_nothing_to_group(self):
        out = lr.group_seasons([item('Show · S1 E2', 'waiting', 0, 'Prepares next'), item('Show · S1 E3', 'waiting', 0, 'Prepares next')])
        self.assertEqual((len(out), out[0]['label'], out[0]['label2']), (1, 'Show · Season 1', 'Prepares next'.split(' · ')[0] + ' · 0 of 2 episodes'))
        single = [item('Show · S1 E2', 'waiting')]; self.assertEqual(lr.group_seasons(single), single); self.assertEqual(lr.group_seasons([]), [])

    def test_problems_and_films_are_left_alone(self):
        rows = [item('Show · S1 E2', 'problem'), item('Show · S1 E3', 'problem'), item('Heat', 'waiting')]
        self.assertEqual(lr.group_seasons(rows), rows)

    def test_one_pace_uses_the_arc_name(self):
        self.assertEqual(lr.season_name('One Pace', 1, lambda n: 'Romance Dawn'), 'One Pace · Romance Dawn'); self.assertEqual(lr.season_name('One Pace', 1), 'One Pace · Season 1')
        self.assertEqual(lr.season_name('Naruto', 2, lambda n: 'x'), 'Naruto · Season 2')

    def test_the_arc_name_is_read_from_the_saved_copy_without_the_network(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(onepace_show.arc_name(tmp, 1), '')
            onepace_show.write_json(onepace_show.folder(tmp) / onepace_show.CACHE, {'seasons': [{'season': 1, 'title': 'Romance Dawn'}]})
            self.assertEqual(onepace_show.arc_name(tmp, 1), 'Romance Dawn'); self.assertEqual(onepace_show.arc_name(tmp, 2), '')

    def test_the_page_groups_before_it_pools(self):
        text = (ROOT / 'migration/bundled-bootstrap/library_status.py').read_text()
        self.assertIn('library_rows.pools(library_rows.group_seasons(items,', text)


if __name__ == '__main__':
    unittest.main()
