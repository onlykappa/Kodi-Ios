"""A league's page (DEC-057): Live Now or Upcoming, started on that league's chip."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOT = os.path.join(ROOT, 'migration', 'bundled-bootstrap')
sys.path[:0] = [BOOT, os.path.join(BOOT, 'resources', 'lib')]
import sports_league  # noqa: E402
import sports_model as sm  # noqa: E402


class Provider:
    def __init__(self, live=None, fail=False):
        self.live, self.fail = live or [], fail

    def live_games(self):
        if self.fail:
            raise sm.SportsUnavailable('down')
        return self.live


def game(league):
    return {'league': league}


class League(unittest.TestCase):
    def test_a_league_with_a_live_game_opens_live_now(self):
        self.assertEqual(sports_league.choose(Provider([game('NFL'), game('NBA')]), 'NBA'), 'live')

    def test_a_league_with_nothing_live_opens_upcoming(self):
        self.assertEqual(sports_league.choose(Provider([game('NFL')]), 'NHL'), 'upcoming')
        self.assertEqual(sports_league.choose(Provider(), 'NHL'), 'upcoming')

    def test_no_answer_opens_upcoming_which_shows_its_own_error(self):
        self.assertEqual(sports_league.choose(Provider(fail=True), 'NFL'), 'upcoming')

    def test_the_page_is_registered_so_the_leagues_tap_reaches_it(self):
        text = open(os.path.join(BOOT, 'default.py')).read()
        self.assertRegex(text, r"PAGES=\(.*'sports_league'")
        self.assertTrue(os.path.isfile(os.path.join(BOOT, 'sports_league.py')))

    def test_both_pages_start_on_the_league_given(self):
        live = open(os.path.join(BOOT, 'sports_live.py')).read()
        up = open(os.path.join(BOOT, 'sports_upcoming.py')).read()
        self.assertIn("(args[0] if args else 'All')", live)
        self.assertIn("self.league = args[0] if args else 'All'", up)

    def test_a_bad_code_opens_nothing(self):
        self.assertIsNone(sports_league.run(['../x']))
        self.assertIsNone(sports_league.run([]))


if __name__ == '__main__':
    unittest.main()
