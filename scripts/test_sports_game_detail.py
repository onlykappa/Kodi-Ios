"""ESPN summary reader for the game Info page: parsing, window properties and caching, all on trimmed fixtures (no network)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap'))
import sports_game_detail as gd  # noqa: E402


def stat(name, value, label=None):
    return {'name': name, 'displayValue': str(value), 'label': label or name}


def team(side, abbr, color, values):
    return {'homeAway': side, 'team': {'abbreviation': abbr, 'shortDisplayName': abbr.title(), 'color': color, 'logo': 'https://img/%s.png' % abbr},
            'statistics': [stat(k, v) for k, v in values.items()]}


FOOT = ('totalYards', 'yardsPerPlay', 'netPassingYards', 'rushingYards', 'firstDowns')
SUMMARY = {
    'boxscore': {'teams': [team('away', 'JAX', '006778', dict(zip(FOOT, (300, 5.5, 200, 100, 18)))), team('home', 'HOU', '03202f', dict(zip(FOOT, (100, 3.0, 60, 40, 8))))],
                 'players': [{'team': {'shortDisplayName': 'Jaguars', 'logo': 'https://img/jax.png'},
                              'statistics': [{'name': 'passing', 'labels': ['C/ATT', 'YDS', 'TD'], 'athletes': [{'athlete': {'shortName': 'T. Lawrence', 'position': {'abbreviation': 'QB'}}, 'stats': ['20/30', '250', '2']}]}]}]},
    'pickcenter': [{'provider': {'name': 'Book'}, 'spread': 3.5, 'overUnder': 44.5, 'awayTeamOdds': {'favorite': True, 'moneyLine': -160, 'spreadOdds': -110}, 'homeTeamOdds': {'moneyLine': 135, 'spreadOdds': -110},
                    'overOdds': -105, 'underOdds': -115}],
    'drives': {'previous': [{'displayResult': 'Touchdown', 'description': '8 plays, 75 yards', 'isScore': True, 'team': {'shortDisplayName': 'Jaguars', 'color': '006778'}, 'start': {'period': {'number': 1}}}]},
}
GAME = {'id': 'espn:NFL:401873083', 'league': 'NFL', 'state': 'post'}


class Parse(unittest.TestCase):
    def test_fixture_becomes_rows(self):
        d = gd.parse(SUMMARY, GAME)
        self.assertEqual(d['stats'][0]['share'], 75)
        self.assertEqual(d['odds']['rows'][0]['spread'], '-3.5')
        self.assertEqual(d['odds']['rows'][1]['spread'], '+3.5')
        self.assertEqual(d['blocks'][0]['rows'][0]['name'], 'T. Lawrence')
        self.assertEqual((d['plays'][0]['title'], d['plays'][0]['when'], d['plays'][0]['score']), ('Touchdown', 'Q1', True))

    def test_empty_summary_is_all_empty(self):
        d = gd.parse({}, GAME)
        self.assertEqual((d['odds'], d['stats'], d['blocks'], d['plays']), (None, [], [], []))

    def test_event_id_and_url(self):
        self.assertEqual(gd.event_id(GAME), '401873083')
        self.assertEqual(gd.event_id({'id': 'f1:abc'}), '')
        self.assertEqual(gd.url_for({'id': 'f1:abc', 'league': 'F1'}), '')


class Props(unittest.TestCase):
    def test_ready_props_and_bars(self):
        out, bars = gd.props(gd.parse(SUMMARY, GAME), 'ready', {'https://img/jax.png': '/tmp/jax.png'})
        self.assertEqual((out['detail'], out['ts.0.away'], out['ts.0.home']), ('ready', '300', '100'))
        self.assertEqual(out['blk.0.logo'], '/tmp/jax.png')
        self.assertEqual(out['play.0.score'], 'true')
        self.assertEqual(bars[9100], 75)
        self.assertEqual(out['ts.9.label'], '')

    def test_loading_and_none_have_no_content(self):
        for state in ('loading', 'none'):
            out, bars = gd.props(None, state)
            self.assertEqual((out['detail'], out['ts.0.label'], bars), (state, '', {}))


class Fetch(unittest.TestCase):
    def setUp(self):
        gd._cache.clear()

    def test_cached_then_refreshed_and_stale_on_failure(self):
        calls, now = [], [1000]

        def get(url):
            calls.append(url)
            if len(calls) == 3:
                raise OSError('down')
            return SUMMARY
        first = gd.fetch(GAME, get, lambda: now[0])
        self.assertIsNotNone(first)
        gd.fetch(GAME, get, lambda: now[0] + 5)
        self.assertEqual(len(calls), 1)
        now[0] += 700
        self.assertIsNotNone(gd.fetch(GAME, get, lambda: now[0]))
        now[0] += 700
        self.assertIsNotNone(gd.fetch(GAME, get, lambda: now[0]))   # ESPN down: the held copy
        self.assertEqual(len(calls), 3)

    def test_no_event_number_means_no_request(self):
        self.assertIsNone(gd.fetch({'id': 'f1:x', 'league': 'F1'}, lambda u: 1 / 0))


if __name__ == '__main__':
    unittest.main()
