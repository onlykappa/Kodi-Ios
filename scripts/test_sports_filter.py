"""Sports league filter (owner-approved board B): one choice for every Sports page, default every league on."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap'))
import sports_filter as sf  # noqa: E402

GAMES = [{'id': 1, 'league': 'NFL', 'sport': 'American football'}, {'id': 2, 'league': 'NBA', 'sport': 'Basketball'},
         {'id': 3, 'league': 'NCAAF', 'sport': 'American football'}, {'id': 4, 'league': 'MLS', 'sport': 'Soccer'}]
ROWS = sf.known(GAMES)


class Filter(unittest.TestCase):
    def test_default_shows_everything_and_says_nothing(self):
        self.assertEqual(sf.games(GAMES, set()), GAMES)
        self.assertEqual(sf.summary(set(), ROWS), '')
        self.assertFalse(sf.active(set(), [c for _, c, _ in ROWS]))

    def test_only_nfl(self):
        off = sf.only_codes([c for _, c, _ in ROWS], ['NFL'])
        self.assertEqual([g['id'] for g in sf.games(GAMES, off)], [1])
        self.assertEqual(sf.summary(off, ROWS), 'Showing NFL')
        self.assertEqual(sf.count_on(off, [c for _, c, _ in ROWS]), 1)

    def test_two_and_many(self):
        codes = [c for _, c, _ in ROWS]
        self.assertEqual(sf.summary(sf.only_codes(codes, ['NFL', 'NBA']), ROWS), 'Showing NFL and NBA')
        self.assertEqual(sf.summary({'MLS'}, ROWS), 'Showing 3 leagues')

    def test_only_sport_and_nothing_selected(self):
        off = sf.only_sport(ROWS, 'American football')
        self.assertEqual([g['id'] for g in sf.games(GAMES, off)], [1, 3])
        none = sf.all_off([c for _, c, _ in ROWS])
        self.assertEqual(sf.games(GAMES, none), [])
        self.assertEqual(sf.summary(none, ROWS), 'No leagues selected')

    def test_a_new_league_appears_switched_on(self):
        self.assertEqual(len(sf.games(GAMES + [{'id': 9, 'league': 'F1', 'sport': 'Motorsport'}], {'NFL'})), 4)

    def test_toggle_and_saved_choice(self):
        self.assertEqual(sf.toggled(set(), 'NBA'), {'NBA'})
        self.assertEqual(sf.toggled({'NBA'}, 'NBA'), set())
        with tempfile.TemporaryDirectory() as profile:
            self.assertEqual(sf.load(profile), set())
            sf.save(profile, {'NBA', 'MLS'})
            self.assertEqual(sf.load(profile), {'NBA', 'MLS'})
            Path(sf.path(profile)).write_text('not json')
            self.assertEqual(sf.load(profile), set())   # a damaged file shows everything

class Provider(unittest.TestCase):
    """The wrapper every page reads: lists and counts follow the choice together."""
    def setUp(self):
        import sports_model as sm
        self.sm = sm
        self.now = 1_700_000_000
        self.base = sm.Sample(now=self.now)
        self.codes = [c for _, c, _ in sf.known(self.base.leagues() + self.base.live_games() + self.base.upcoming_games())]

    def wrapped(self, off):
        return sf.FilteredProvider(self.base, off=lambda: set(off), clock=lambda: self.now)

    def test_no_filter_is_the_real_provider(self):
        p = self.wrapped([])
        self.assertEqual(p.overview(), self.base.overview())
        self.assertEqual(p.live_games(), self.base.live_games())

    def test_only_nba_changes_every_list_and_count(self):
        p = self.wrapped([c for c in self.codes if c != 'NBA'])
        self.assertTrue(p.live_games() and all(g['league'] == 'NBA' for g in p.live_games()))
        self.assertTrue(all(g['league'] == 'NBA' for g in p.upcoming_games()))
        ov = p.overview()
        self.assertEqual((ov['live'], ov['live_sports'], ov['leagues']), (len(p.live_games()), ['Basketball'], 1))
        self.assertEqual([l['code'] for l in p.leagues()], ['NBA'])
        self.assertGreaterEqual(ov['next'], self.now)

    def test_nothing_on_says_no_next_game(self):
        ov = self.wrapped(self.codes).overview()
        self.assertEqual((ov['live'], ov['next'], ov['leagues']), (0, None, 0))

    def test_the_edit_sheet_still_lists_every_league(self):
        p = self.wrapped(self.codes)
        self.assertEqual(p.leagues(), [])
        self.assertTrue({'NBA', 'NFL', 'UFC', 'F1'} <= {r['code'] for r in p.all_leagues()})

    def test_everything_else_is_the_real_providers(self):
        self.assertEqual(self.wrapped([]).game('nba-1'), self.base.game('nba-1'))

    def test_pages_get_the_wrapper(self):
        src = (ROOT / 'migration/bundled-bootstrap/resources/lib/sports_provider.py').read_text()
        self.assertIn('return sports_filter.wrap(_get())', src)

class EditSheet(unittest.TestCase):
    ROWS = [{'code': 'NFL', 'name': 'NFL', 'sport': 'American football'}, {'code': 'NCAAF', 'name': 'College Football', 'sport': 'American football'},
            {'code': 'NBA', 'name': 'NBA', 'sport': 'Basketball'}, {'code': 'MLS', 'name': 'MLS', 'sport': 'Soccer'},
            {'code': 'EPL', 'name': 'Premier League', 'sport': 'Soccer'}, {'code': 'UFC', 'name': 'UFC', 'sport': 'Combat sports'},
            {'code': 'PGA', 'name': 'PGA Tour', 'sport': 'Golf'}, {'code': 'F1', 'name': 'Formula 1', 'sport': 'Motorsport'}]

    def test_the_sheet_lists_every_sport_then_its_leagues_by_name(self):
        items = sf.sheet_items(self.ROWS, {'MLS'}, {'EPL': '/x/EPL.png'}, now=1_700_000_000)
        heads = [i['title'] for i in items if i['kind'] == 'head']
        self.assertEqual(heads, ['American football', 'Basketball', 'Soccer', 'Golf', 'Combat sports', 'Motorsport'])   # a steady order, golf and combat included
        rows = {i['code']: i for i in items if i['kind'] == 'row'}
        self.assertEqual([i['code'] for i in items if i['sport'] == 'American football' and i['kind'] == 'row'], ['NCAAF', 'NFL'])
        self.assertEqual((rows['EPL']['on'], rows['MLS']['on']), ('on', 'off'))
        self.assertEqual((rows['EPL']['logo'], rows['MLS']['logo']), ('/x/EPL.png', ''))
        self.assertTrue(all(r['detail'] for r in rows.values()))   # a second line, so the name is centred beside the logo
        self.assertEqual([rows[c]['pos'] for c in ('MLS', 'EPL')], ['first', 'last'])   # by name: MLS, Premier League
        self.assertEqual(rows['PGA']['pos'], 'only')

    def test_properties_fill_the_slots_and_clear_the_rest(self):
        items = sf.sheet_items(self.ROWS, set(), now=1_700_000_000)
        props = sf.sheet_props(items)
        self.assertEqual((props['item.0.kind'], props['item.0.title']), ('head', 'American football'))
        self.assertEqual(props['item.%d.kind' % len(items)], '')
        self.assertEqual(len([k for k in props if k.endswith('.kind')]), sf.EDIT_SLOTS)
        self.assertIn('Games from leagues that are off are hidden', props['edit.help'])

    def test_every_league_the_data_layer_lists_fits_the_sheet(self):
        import sports_espn
        rows = [{'code': c, 'name': n, 'sport': s} for c, n, s, *_ in sports_espn.LEAGUES]
        self.assertLessEqual(len(sf.sheet_items(rows, set())), sf.EDIT_SLOTS)


class EditActions(unittest.TestCase):
    ROWS = EditSheet.ROWS

    def test_flip_all_on_all_off(self):
        import sports_edit
        a = sports_edit.apply
        self.assertEqual(a(set(), self.ROWS, 'flip', 'NBA'), {'NBA'})
        self.assertEqual(a({'NBA'}, self.ROWS, 'flip', 'NBA'), set())
        self.assertEqual(a(set(), self.ROWS, 'only', 'Soccer'), set())   # no per-sport "Only" any more (owner): an unknown action changes nothing
        self.assertEqual(a({'NBA'}, self.ROWS, 'all_on'), set())
        self.assertEqual(a(set(), self.ROWS, 'all_off'), {r['code'] for r in self.ROWS})
        self.assertEqual(a({'NBA'}, self.ROWS, 'nonsense'), {'NBA'})

    def test_it_is_a_page_the_app_can_run(self):
        default = (ROOT / 'migration/bundled-bootstrap/default.py').read_text()
        self.assertIn("'sports_edit'", default)

    def test_the_sheet_xml_is_well_formed_with_unique_ids_and_real_hit_areas(self):
        import re
        import xml.dom.minidom
        import portrait
        page = portrait.sports_edit_page
        text = page.page(portrait)
        xml.dom.minidom.parseString(text.encode())
        ids = re.findall(r'<control type="\w+" id="(\d+)"', text)
        self.assertEqual(len(ids), len(set(ids)))
        for ident in (page.DONE, page.ALL_ON, page.ALL_OFF, page.ROW0, page.ROW0 + page.SLOTS - 1):
            self.assertIn(str(ident), ids)
        self.assertNotIn('!(', text)
        self.assertNotIn('>Only<', text)
        for height in re.findall(r'<control type="button" id="(?:%d|%d)"><left>\d+</left><top>\d+</top><width>\d+</width><height>(\d+)</height>' % (
                page.ALL_ON, page.ALL_OFF), text):
            self.assertGreaterEqual(int(height), 118)   # 44 pt


class NewLeagues(unittest.TestCase):
    """Golf, UFC and F1 (owner: include them in the app's data)."""
    def parse(self, code, body):
        import sports_espn as espn
        row = next(r for r in espn.LEAGUES if r[0] == code)
        return espn.parse(row[0], row[1], row[2], row[4], row[5], body, 1_700_000_000)

    def test_the_leagues_are_listed_with_their_sports(self):
        import sports_espn as espn
        listed = {r[0]: r[2] for r in espn.LEAGUES}
        self.assertEqual((listed['PGA'], listed['LPGA'], listed['UFC'], listed['F1']), ('Golf', 'Golf', 'Combat sports', 'Motorsport'))

    def test_a_tournament_in_progress_is_live_with_its_round_and_its_title(self):
        body = {'events': [{'id': '9', 'name': 'The RSM Classic', 'date': '2023-11-14T05:00Z', 'status': {'type': {'state': 'in'}},
                            'competitions': [{'status': {'period': 2}, 'competitors': []}]}]}
        live, upcoming, _ = self.parse('PGA', body)
        self.assertEqual((len(live), len(upcoming)), (1, 0))
        game = live[0]
        import sports_model as sm
        self.assertEqual((sm.versus(game), game['clock'], game['home']['name'], game['league']), ('The RSM Classic', 'Round 2', '', 'PGA'))

    def test_a_race_weekend_is_one_upcoming_title(self):
        body = {'events': [{'id': '5', 'name': 'Las Vegas Grand Prix', 'date': '2023-11-17T00:30Z', 'status': {'type': {'state': 'pre'}},
                            'competitions': [{'status': {}, 'competitors': []}]}]}
        _, upcoming, _ = self.parse('F1', body)
        import sports_model as sm
        self.assertEqual([(g['id'], sm.versus(g), g['state']) for g in upcoming], [('espn:F1:5', 'Las Vegas Grand Prix', 'upcoming')])

    def test_a_fight_card_shows_its_main_event(self):
        fight = lambda a, b: {'status': {}, 'competitors': [{'athlete': {'displayName': a}}, {'athlete': {'displayName': b}}]}
        body = {'events': [{'id': '7', 'name': 'UFC Fight Night', 'date': '2023-11-18T15:00Z', 'status': {'type': {'state': 'pre'}},
                            'competitions': [fight('Prelim A', 'Prelim B'), fight('Jiri Prochazka', 'Navajo Stirling')]}]}
        _, upcoming, _ = self.parse('UFC', body)
        import sports_model as sm
        self.assertEqual(sm.versus(upcoming[0]), 'Jiri Prochazka vs Navajo Stirling')

    def test_team_colour_short_name_and_week_come_through(self):
        body = {'events': [{'id': '1', 'date': '2026-11-20T18:00Z', 'week': {'number': 11}, 'competitions': [{
            'status': {'type': {'state': 'pre'}}, 'competitors': [
                {'homeAway': 'home', 'team': {'id': '34', 'displayName': 'Houston Texans', 'shortDisplayName': 'Texans', 'abbreviation': 'HOU', 'color': '03202f'}},
                {'homeAway': 'away', 'team': {'id': '11', 'displayName': 'Indianapolis Colts', 'name': 'Colts', 'abbreviation': 'IND'}}]}]}]}
        import sports_espn as espn
        _, upcoming, _ = espn.parse('NFL', 'NFL', 'American football', 'at', (4, 15), body, 0)
        game = upcoming[0]
        self.assertEqual((game['home']['short'], game['home']['color'], game['away']['short'], game['away']['color'], game['week']), ('Texans', '03202f', 'Colts', '', 11))

    def test_finished_and_odd_events_are_skipped(self):
        body = {'events': [{'id': '1', 'name': 'Done', 'date': '2023-11-10T05:00Z', 'status': {'type': {'state': 'post'}}, 'competitions': [{}]},
                           {'id': '2', 'date': 'not a date', 'status': {'type': {'state': 'pre'}}}, {}, None]}
        live, upcoming, finished = self.parse('PGA', body)
        self.assertEqual((live, upcoming, finished), ([], [], 1))


if __name__ == '__main__':
    unittest.main()
