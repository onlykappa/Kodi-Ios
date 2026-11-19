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
            {'code': 'EPL', 'name': 'Premier League', 'sport': 'Soccer'}, {'code': 'UFC', 'name': 'UFC', 'sport': 'Combat sports'}]

    def test_step_one_lists_sports_with_their_counts(self):
        spec = sf.sports_spec(self.ROWS, {'NCAAF', 'MLS', 'EPL'})
        self.assertEqual([r['label'] for r in spec['rows']], ['American football', 'Basketball', 'Soccer', 'Combat sports'])
        self.assertEqual([r['detail'] for r in spec['rows']][:3], ['1 of 2 leagues on', '1 of 1 league on', '0 of 2 leagues on'])
        self.assertEqual([r['tag'] for r in spec['rows']][:3], ['Some', '', 'Off'])
        self.assertEqual(spec['rows'][1]['glyph'], 'basketball.png')   # every sport has an icon, never an empty tile
        self.assertEqual(spec['link'], 'Turn every league on')
        self.assertEqual(sf.sports_spec(self.ROWS, set())['link'], '')   # nothing off: nothing to turn on

    def test_step_two_has_a_switch_and_a_logo_per_league(self):
        spec, codes = sf.leagues_spec(self.ROWS, {'MLS'}, 'Soccer', {'EPL': '/x/EPL.png'})
        self.assertEqual(sorted(codes), ['EPL', 'MLS'])
        rows = {r['label']: r for r in spec['rows']}
        self.assertTrue(rows['Premier League']['switch'] and not rows['MLS']['switch'])
        self.assertEqual(rows['Premier League']['glyph'], '/x/EPL.png')
        self.assertEqual(rows['MLS']['glyph'], '')
        self.assertTrue(all(r['detail'] for r in spec['rows']))   # a second line, so the title is centred beside the logo

    def test_at_most_eight_rows_fit_the_sheet(self):
        many = [{'code': 'L%d' % n, 'name': 'League %d' % n, 'sport': 'S%d' % n} for n in range(12)]
        self.assertEqual(len(sf.sports_spec(many, set())['rows']), 8)

    def test_the_sheet_accepts_these_specs(self):
        import choice_sheet
        spec, _ = sf.leagues_spec(self.ROWS, set(), 'Soccer')
        props = choice_sheet.properties(spec)
        self.assertEqual((props['switches'], props['row.1.switch']), ('true', 'on'))
        self.assertEqual(choice_sheet.properties(sf.sports_spec(self.ROWS, set()))['row.1.label'], 'American football')

class EditScript(unittest.TestCase):
    """sports_edit.edit drives the two sheets and saves every flip at once."""
    ROWS = EditSheet.ROWS

    def run_edit(self, profile, answers, flips=()):
        import sports_edit
        asked = []
        script = iter(answers)
        def choose(spec, toggle=None):
            asked.append(spec['heading'])
            answer = next(script)
            if toggle is not None:
                for index in flips:
                    toggle(index)
            return answer
        return sports_edit.edit(self.ROWS, profile, {}, choose=choose), asked

    def test_turning_one_league_off_is_saved_and_reported(self):
        with tempfile.TemporaryDirectory() as profile:
            # step 1: Soccer (index 2) -> step 2: flip the first league (EPL, sorted by name) -> back -> step 1 Done (-1)
            changed, asked = self.run_edit(profile, [2, -1, -1], flips=[0])
            self.assertTrue(changed)
            self.assertEqual(asked, ['Leagues', 'Soccer', 'Leagues'])
            self.assertEqual(len(sf.load(profile)), 1)

    def test_turn_every_league_on(self):
        with tempfile.TemporaryDirectory() as profile:
            sf.save(profile, {'NBA', 'UFC'})
            changed, _ = self.run_edit(profile, [4, -1])    # the link row is index len(rows) = 4 sports
            self.assertTrue(changed)
            self.assertEqual(sf.load(profile), set())

    def test_leaving_without_a_change_reports_none(self):
        with tempfile.TemporaryDirectory() as profile:
            self.assertFalse(self.run_edit(profile, [-1])[0])

    def test_it_is_a_page_the_app_can_run(self):
        default = (ROOT / 'migration/bundled-bootstrap/default.py').read_text()
        self.assertIn("'sports_edit'", default)


if __name__ == '__main__':
    unittest.main()
