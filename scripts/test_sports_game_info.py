"""Sports game page Info section (board D): venue, recent form, standings; all from ESPN fixtures, no network."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap'))
import sports_espn as espn  # noqa: E402
import sports_game_info as gi  # noqa: E402

NOW = 1_700_000_000


def stat(name, value):
    return {'name': name, 'displayValue': str(value), 'value': value}


def entry(team_id, name, w, l, pct, seed, soccer=False):
    stats = [stat('wins', w), stat('losses', l), stat('winPercent', pct), stat('playoffSeed', seed), stat('ties', 0)]
    if soccer:
        stats += [stat('points', 3 * w), stat('gamesPlayed', w + l)]
    return {'team': {'id': str(team_id), 'shortDisplayName': name, 'displayName': 'City ' + name, 'logos': [{'href': 'https://img/%s.png' % name}]}, 'stats': stats}


STAND = {'name': 'NFL', 'children': [
    {'name': 'AFC', 'children': [
        {'name': 'AFC South', 'standings': {'entries': [entry(1, 'Jaguars', 7, 2, '.778', 3), entry(2, 'Texans', 3, 6, '.333', 9), entry(3, 'Colts', 3, 7, '.300', 10), entry(4, 'Titans', 1, 8, '.111', 14)]}},
        {'name': 'AFC East', 'standings': {'entries': [entry(5, 'Bills', 8, 1, '.889', 1)]}}]},
    {'name': 'NFC', 'children': [{'name': 'NFC West', 'standings': {'entries': [entry(9, 'Rams', 6, 3, '.667', 2)]}}]}]}


def schedule(team_id, results):
    events = []
    for n, won in enumerate(results):
        mine = {'team': {'id': str(team_id)}, 'winner': won is True}
        other = {'team': {'id': '99'}, 'winner': won is False}
        events.append({'date': '2026-10-%02dT18:00Z' % (n + 1), 'competitions': [{'status': {'type': {'state': 'post'}}, 'competitors': [mine, other]}]})
    events.append({'date': '2026-12-01T18:00Z', 'competitions': [{'status': {'type': {'state': 'pre'}}, 'competitors': []}]})
    return {'events': list(reversed(events))}   # ESPN does not promise an order


class Form(unittest.TestCase):
    def test_last_five_oldest_first_and_ties_are_draws(self):
        body = schedule(1, [True, False, True, True, False, None, True])   # None: a draw
        self.assertEqual(gi.form(body, 1), ['W', 'W', 'L', 'D', 'W'])
        self.assertEqual(gi.form(schedule(1, [True, False]), 1), ['W', 'L'])

    def test_unplayed_and_broken_events_are_skipped(self):
        self.assertEqual(gi.form({'events': [{'competitions': [{}]}, {}]}, 1), [])
        self.assertEqual(gi.form(None, 1), [])


class Standings(unittest.TestCase):
    def test_division_first_then_wild_card_by_seed(self):
        table = gi.standings(STAND, [2, 3])
        names = [v['name'] for v in table['views']]
        self.assertEqual(names, ['Divisional', 'Wild Card'])
        div = table['views'][0]
        self.assertEqual(div['title'], 'Standings · AFC South')
        self.assertEqual([r['team'] for r in div['rows']], ['Jaguars', 'Texans', 'Colts', 'Titans'])
        self.assertEqual([r['me'] for r in div['rows']], [False, True, True, False])
        self.assertEqual(div['cols'], ('W', 'L', '', 'PCT'))
        wild = table['views'][1]
        self.assertEqual(wild['title'], 'Standings · AFC')
        self.assertEqual([r['team'] for r in wild['rows']][:2], ['Bills', 'Jaguars'])   # conference by playoff seed, NFC left out
        self.assertNotIn('Rams', [r['team'] for r in wild['rows']])

    def test_a_game_team_below_the_cut_stays_visible(self):
        entries = [entry(n, 'T%d' % n, 20 - n, n, '.5', n) for n in range(1, 13)]
        body = {'name': 'L', 'children': [{'name': 'Conf', 'standings': {'entries': entries}}]}
        rows = gi.standings(body, [12])['views'][0]['rows']
        self.assertEqual(len(rows), gi.ROWS)
        self.assertEqual(rows[-1]['team'], 'T12')

    def test_soccer_table_has_points_and_no_wild_card(self):
        body = {'name': 'English Premier League', 'children': [{'name': '2026-27 English Premier League', 'standings': {'entries': [entry(1, 'Arsenal', 9, 1, '.9', 1, True), entry(2, 'Fulham', 4, 6, '.4', 9, True)]}}]}
        table = gi.standings(body, [2])
        self.assertEqual(len(table['views']), 1)
        self.assertEqual(table['views'][0]['cols'], ('W', 'D', 'L', 'PTS'))
        self.assertEqual(table['views'][0]['title'], 'Standings · English Premier League')

    def test_no_table_for_a_team_that_is_not_listed(self):
        self.assertIsNone(gi.standings(STAND, [404]))
        self.assertIsNone(gi.standings({}, [1]))

    def test_long_names_fall_back_to_a_name_that_fits_one_line(self):
        row = gi._row({'team': {'id': '1', 'shortDisplayName': 'A' * 30, 'name': 'Wolves', 'displayName': 'Wolverhampton Wanderers'}, 'stats': []}, 1, set())
        self.assertEqual(row['team'], 'Wolves')


class Build(unittest.TestCase):
    def setUp(self):
        gi.forget()

    def game(self):
        return {'league': 'NFL', 'path': 'football/nfl', 'start': NOW, 'venue': ('NRG Stadium', 'Houston, TX'),
                'away': {'id': '3', 'name': 'Indianapolis Colts', 'record': '3-7', 'split': '1-4'},
                'home': {'id': '2', 'name': 'Houston Texans', 'record': '3-6', 'split': '2-2'}}

    def test_collects_venue_form_and_standings_with_one_fetch_each(self):
        urls = []

        def fetch(url):
            urls.append(url)
            if 'standings' in url:
                return STAND
            return schedule(int(url.split('/teams/')[1].split('/')[0]), [True, False, True, False, True])
        info = gi.build(self.game(), fetch, NOW)
        self.assertEqual((info['venue'], info['place']), ('NRG Stadium', 'Houston, TX'))
        self.assertEqual([f['side'] for f in info['form']], ['Away', 'Home'])
        self.assertEqual(info['form'][0]['results'], ['W', 'L', 'W', 'L', 'W'])
        self.assertEqual(info['standings']['views'][0]['rows'][1]['team'], 'Texans')
        gi.build(self.game(), fetch, NOW + 60)   # answered from the cache
        self.assertEqual(len(urls), 3)

    def test_a_feed_that_fails_leaves_that_part_out(self):
        def fetch(url):
            raise OSError('down')
        info = gi.build(self.game(), fetch, NOW)
        self.assertEqual([f['results'] for f in info['form']], [[], []])   # no dots, but the records the scoreboard gave stay
        self.assertEqual(info['form'][0]['record'], '3-7')
        self.assertIsNone(info['standings'])
        self.assertEqual(info['venue'], 'NRG Stadium')   # what the scoreboard already gave is still shown

    def test_scoreboard_carries_venue_records_and_team_ids(self):
        body = {'events': [{'id': '1', 'date': '2026-11-20T18:00Z', 'competitions': [{
            'status': {'type': {'state': 'pre'}}, 'venue': {'fullName': 'NRG Stadium', 'address': {'city': 'Houston', 'state': 'TX'}},
            'competitors': [
                {'homeAway': 'home', 'team': {'id': '34', 'displayName': 'Houston Texans', 'abbreviation': 'HOU'},
                 'records': [{'name': 'overall', 'type': 'total', 'summary': '3-6'}, {'type': 'home', 'summary': '2-2'}, {'type': 'road', 'summary': '1-4'}]},
                {'homeAway': 'away', 'team': {'id': '11', 'displayName': 'Indianapolis Colts', 'abbreviation': 'IND'},
                 'records': [{'name': 'overall', 'type': 'total', 'summary': '3-7'}, {'type': 'road', 'summary': '1-4'}]}]}]}]}
        _, upcoming, _ = espn.parse('NFL', 'NFL', 'American football', 'at', (4, 15), body, 0)
        game = upcoming[0]
        self.assertEqual(game['venue'], ('NRG Stadium', 'Houston, TX'))
        self.assertEqual((game['home']['id'], game['home']['record'], game['home']['split']), ('34', '3-6', '2-2'))
        self.assertEqual((game['away']['record'], game['away']['split']), ('3-7', '1-4'))
        self.assertEqual(game['path'], 'football/nfl')


class PageProperties(unittest.TestCase):
    """The facts window's properties and its XML (the game page only carries the Game info card)."""
    def setUp(self):
        import sports_game_facts
        import sports_game_facts_page as page
        self.facts, self.page = sports_game_facts, page
        self.game = {'id': 'g', 'league': 'NFL', 'start': NOW, 'sources': [], 'state': 'upcoming', 'joiner': 'at',
                     'away': {'code': 'IND', 'name': 'Colts'}, 'home': {'code': 'HOU', 'name': 'Texans'}}

    def props(self, info=None, view=0):
        return self.facts.info_props(self.game, info, view, NOW, 0)

    def test_nothing_is_shown_until_the_facts_arrive(self):
        props = self.props()
        for key in ('info.kickoff', 'info.venue', 'form.0.name', 'st.title', 'st.0.team', 'st.switch'):
            self.assertEqual(props[key], '', key)
        self.assertEqual(props['matchup'], 'Colts at Texans')

    def test_facts_fill_every_part_and_the_switch_picks_the_view(self):
        facts = gi.sample()
        props = self.props(facts)
        self.assertEqual((props['info.venue'], props['info.place']), ('NRG Stadium', 'Houston, TX'))
        self.assertTrue(props['info.kickoff'])
        self.assertEqual(props['form.0.line'], '3-7 · Away 1-4')
        self.assertEqual([props['form.1.d%d' % d] for d in range(5)], ['W', 'L', 'W', 'W', 'L'])
        self.assertEqual((props['st.title'], props['st.switch'], props['st.0.team'], props['st.0.me'], props['st.3.me']), ('Standings · AFC South', 'wild', 'Texans', 'true', 'true'))
        self.assertEqual(props['st.3.pos'], 'last')
        wild = self.props(facts, 1)
        self.assertEqual((wild['st.switch'], wild['st.0.team']), ('div', 'Bills'))
        self.assertEqual(self.props(facts, 2)['st.title'], props['st.title'])   # the view wraps

    def test_a_missing_part_hides_only_itself(self):
        facts = gi.sample()
        facts['standings'] = None
        props = self.props(facts)
        self.assertEqual((props['st.title'], props['st.0.team']), ('', ''))
        self.assertEqual(props['form.0.name'], 'Indianapolis Colts')

    def test_there_is_no_watch_on_row(self):
        text = (ROOT / 'migration/bundled-bootstrap/resources/lib/sports_game_facts_page.py').read_text()
        self.assertNotRegex(text, r'(?i)watch on')

    def test_page_xml_is_well_formed_and_ids_are_unique(self):
        import xml.dom.minidom
        import portrait
        xml_text = self.page.page(portrait)
        xml.dom.minidom.parseString(xml_text.encode())
        ids = re.findall(r'<control type="\w+" id="(\d+)"', xml_text)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn(str(self.page.STANDINGS_SWITCH), ids)
        self.assertNotIn('!(', xml_text)


if __name__ == '__main__':
    unittest.main()
