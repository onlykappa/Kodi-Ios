"""Sports on the phone (owner, 2026-11-20): ESPN for every list, time, score and league; Crew only for one game's sources when its page asks."""
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import sports_espn  # noqa: E402
import sports_hybrid  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_provider  # noqa: E402

NOW = 1_794_768_300


def event(eid, away, home, start, state='pre', league_path='hockey/nhl'):
    return {'id': eid, 'date': start, 'competitions': [{'status': {'type': {'state': state}}, 'competitors': [
        {'homeAway': 'away', 'score': '0', 'team': {'id': eid + 'a', 'displayName': away, 'shortDisplayName': away.split()[-1], 'abbreviation': 'AWY'}},
        {'homeAway': 'home', 'score': '0', 'team': {'id': eid + 'h', 'displayName': home, 'shortDisplayName': home.split()[-1], 'abbreviation': 'HOM'}}]}]}


def board(*events):
    return {'events': list(events)}


class Espn(sports_espn.EspnProvider):
    """ESPN with canned answers: one NHL game tomorrow, and one UFC card with no two-team game."""
    def __init__(self):
        body = board(event('e1', 'Los Angeles Kings', 'Toronto Maple Leafs', '2026-11-20T23:00Z'))
        def fetch(url):
            if 'mma/ufc' in url:
                return {'events': [{'id': 'u1', 'name': 'UFC 1', 'date': '2026-11-21T01:00Z', 'status': {'type': {'state': 'pre'}},
                                   'competitions': [{'competitors': [{'athlete': {'displayName': 'A Fighter'}}, {'athlete': {'displayName': 'B Fighter'}}]}]}]}
            if 'hockey/nhl' in url:
                return body
            return {'events': []}
        super().__init__(fetch=fetch, clock=lambda: NOW)


def provider(crew):
    espn = Espn()
    espn.ttl = sports_hybrid.TTL
    return sports_hybrid.HybridProvider(espn, crew, clock=lambda: NOW)


def wait_until(predicate, seconds=2.0):
    end = threading.Event()
    for _ in range(int(seconds / 0.01)):
        if predicate():
            return True
        end.wait(0.01)
    return predicate()


class Lists(unittest.TestCase):
    def test_games_and_leagues_come_from_espn_including_ufc(self):
        p = provider(lambda game: [])
        games = p.upcoming_games()
        self.assertEqual([sm.versus(g) for g in games], ['Los Angeles Kings at Toronto Maple Leafs', 'A Fighter vs B Fighter'])
        self.assertEqual({g['league'] for g in games}, {'NHL', 'UFC'})
        self.assertIn('UFC', {l['code'] for l in p.leagues()})

    def test_lists_never_start_crew(self):
        calls = []
        p = provider(lambda game: calls.append(game) or [])
        p.upcoming_games(); p.live_games(); p.overview(); p.leagues()
        self.assertEqual(calls, [])

    def test_no_sources_until_a_page_asks(self):
        p = provider(lambda game: [{'addon': 'The Loop', 'quality': '1080p', 'language': 'English', 'play': '{}'}])
        game = p.upcoming_games()[0]
        self.assertEqual(game['sources'], [])


class Sources(unittest.TestCase):
    def test_a_search_finds_sources_for_that_game(self):
        source = {'addon': 'The Loop', 'quality': '1080p', 'language': 'English', 'play': '{}'}
        p = provider(lambda game: [source])
        gid = p.upcoming_games()[0]['id']
        token = p.request_game(gid)
        self.assertTrue(wait_until(lambda: not p.searching_game(gid, token)))
        self.assertFalse(p.game_search_failed(token))
        self.assertEqual(p.game(gid)['sources'], [source])
        self.assertEqual(p.upcoming_games()[0]['sources'], [source])   # the list shows the count now

    def test_crew_that_cannot_answer_is_a_plain_failure_not_an_empty_list(self):
        def down(game):
            raise sm.SportsUnavailable('open Sports to search for sources')
        p = provider(down)
        gid = p.upcoming_games()[0]['id']
        token = p.request_game(gid)
        self.assertTrue(wait_until(lambda: p.game_search_failed(token)))
        self.assertFalse(p.searching_game(gid, token))
        self.assertEqual(p.game(gid)['sources'], [])

    def test_a_search_that_finds_nothing_says_none_yet_not_an_error(self):
        p = provider(lambda game: [])
        gid = p.upcoming_games()[0]['id']
        token = p.request_game(gid)
        self.assertTrue(wait_until(lambda: not p.searching_game(gid, token)))
        self.assertFalse(p.game_search_failed(token))

    def test_a_game_that_is_no_longer_listed_cannot_be_searched(self):
        with self.assertRaises(sm.SportsUnavailable):
            provider(lambda game: []).request_game('espn:NHL:missing')

    def test_cancel_forgets_the_search(self):
        p = provider(lambda game: [])
        gid = p.upcoming_games()[0]['id']
        token = p.request_game(gid)
        p.cancel_game_search(token)
        self.assertFalse(p.searching_game(gid, token))
        self.assertFalse(p.game_search_failed(token))


class CrewForOneGame(unittest.TestCase):
    def test_crew_is_matched_to_the_game_by_league_start_and_teams(self):
        import sports_merge
        game = {'id': 'g', 'league': 'NHL', 'start': NOW, 'away': {'name': 'Los Angeles Kings'}, 'home': {'name': 'Toronto Maple Leafs'}}
        source = {'addon': 'The Loop', 'quality': '720p', 'language': 'English', 'play': '{"x":1}'}
        crew_game = dict(game, id='crew-1', sources=[source])
        class FakeCrew:
            def __init__(self, **kwargs):
                pass
            def refresh(self):
                pass
            def live_games(self):
                return []
            def upcoming_games(self):
                return [crew_game, dict(crew_game, id='other', away={'name': 'Boston Bruins'})]
        with patch('sports_jet.JetProvider', FakeCrew):
            self.assertEqual(sports_provider.crew_sources(game), [source])
            self.assertEqual(sports_provider.crew_sources(dict(game, away={'name': 'Pittsburgh Penguins'})), [])   # no such game in Crew
        self.assertTrue(sports_merge.same_game(game, crew_game))


class Refresh(unittest.TestCase):
    def test_espn_answers_are_reused_for_eight_seconds_so_scores_stay_live(self):
        seen = []
        clock = [NOW]
        espn = sports_espn.EspnProvider(fetch=lambda url: seen.append(url) or board(), clock=lambda: clock[0])
        espn.ttl = sports_hybrid.TTL
        espn.overview()
        clock[0] = NOW + 3
        espn.overview()
        n_first = len(seen)
        clock[0] = NOW + 9
        espn.overview()
        self.assertGreater(len(seen), n_first)   # asked again after eight seconds
        self.assertLessEqual(sports_hybrid.TTL, 10)


if __name__ == '__main__':
    unittest.main()
