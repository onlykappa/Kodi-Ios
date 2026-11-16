"""Sports from ESPN's public scoreboard feed (DEC-059): the answers are turned into the contract of sports_model.py; one league failing never fails the rest."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap'))
import sports_espn as se  # noqa: E402
import sports_model as sm  # noqa: E402

NOW = 1763316000   # 2025-11-16 18:00 UTC: whatever, relative times below


def team(abbr, name, score='0', home=True):
    return {'homeAway': 'home' if home else 'away', 'score': score,
            'team': {'abbreviation': abbr, 'displayName': name, 'logo': 'https://a.espncdn.com/%s.png' % abbr.lower()}}


def event(eid, when, state, away, home, period=0, clock='', kind='STATUS_SCHEDULED', detail=''):
    return {'id': eid, 'date': when, 'competitions': [{'status': {'period': period, 'displayClock': clock, 'type': {'state': state, 'name': kind, 'shortDetail': detail}},
                                                       'competitors': [home, away]}]}


def body(*events):
    return {'leagues': [{'name': 'x'}], 'events': list(events)}


class Parse(unittest.TestCase):
    def go(self, code, events):
        entry = next(e for e in se.LEAGUES if e[0] == code)
        return se.parse(entry[0], entry[1], entry[2], entry[4], entry[5], body(*events), NOW)

    def test_a_live_nba_game_has_score_clock_and_what_is_left(self):
        live, up, done = self.go('NBA', [event('1', '2025-11-16T17:00Z', 'in', team('IND', 'Indiana Pacers', '88', False), team('PHI', 'Philadelphia 76ers', '91'),
                                                period=3, clock='8:41', kind='STATUS_IN_PROGRESS')])
        g = live[0]
        self.assertEqual((g['league'], g['sport'], g['state'], g['joiner']), ('NBA', 'Basketball', 'live', 'at'))
        self.assertEqual((g['away']['code'], g['away']['score'], g['home']['score']), ('IND', 88, 91))
        self.assertEqual(g['clock'], 'Q3 · 8:41')
        self.assertAlmostEqual(g['left'], (12 * 60 + 521) / (48 * 60.0), places=3)   # one period and 8:41 of the third to go
        self.assertEqual(g['sources'], [])
        self.assertEqual(g['id'], 'espn:NBA:1')
        self.assertEqual((up, done), ([], 0))

    def test_upcoming_finished_and_odd_events(self):
        events = [event('2', '2025-11-16T23:30Z', 'pre', team('LAL', 'Los Angeles Lakers', '0', False), team('GSW', 'Golden State Warriors')),
                  event('3', '2025-11-16T01:00Z', 'post', team('A', 'A', '0', False), team('B', 'B'), kind='STATUS_FINAL'),
                  {'id': '4'}, {'id': '5', 'date': 'nonsense', 'competitions': []},
                  event('6', '2025-11-14T01:00Z', 'pre', team('C', 'C', '0', False), team('D', 'D'))]   # long overdue: not shown
        live, up, done = self.go('NBA', events)
        self.assertEqual([g['id'] for g in up], ['espn:NBA:2'])
        self.assertEqual((live, done), ([], 1))
        self.assertIsNone(up[0]['home']['score'])   # no score before the game

    def test_clocks_for_each_sport(self):
        hockey = self.go('NHL', [event('h', '2025-11-16T17:00Z', 'in', team('BOS', 'Boston Bruins', '1', False), team('NYR', 'New York Rangers', '2'), period=2, clock='12:10')])[0][0]
        self.assertEqual(hockey['clock'], 'P2 · 12:10')
        soccer = self.go('EPL', [event('s', '2025-11-16T17:00Z', 'in', team('CHE', 'Chelsea', '0', False), team('ARS', 'Arsenal', '1'), period=2, clock="67'")])[0][0]
        self.assertEqual((soccer['clock'], soccer['joiner']), ("67'", 'vs'))
        self.assertAlmostEqual(soccer['left'], 1 - 67 / 90.0, places=3)
        half = self.go('EPL', [event('t', '2025-11-16T17:00Z', 'in', team('CHE', 'Chelsea', '0', False), team('ARS', 'Arsenal', '1'), kind='STATUS_HALFTIME')])[0][0]
        self.assertEqual(half['clock'], 'Half')
        baseball = self.go('MLB', [event('b', '2025-11-16T17:00Z', 'in', team('NYY', 'Yankees', '2', False), team('BOS', 'Red Sox', '3'), period=7, detail='Top 7th')])[0][0]
        self.assertEqual(baseball['clock'], 'Top 7th')
        self.assertTrue(0 < baseball['left'] < 0.4)
        overtime = self.go('NFL', [event('o', '2025-11-16T17:00Z', 'in', team('KC', 'Chiefs', '24', False), team('BUF', 'Bills', '24'), period=5, clock='4:00')])[0][0]
        self.assertEqual((overtime['clock'], overtime['left']), ('OT · 4:00', 0.02))
        college = self.go('NCAAB', [event('c', '2025-11-16T17:00Z', 'in', team('DUKE', 'Duke', '30', False), team('UNC', 'North Carolina', '31'), period=1, clock='3:00')])[0][0]
        self.assertEqual(college['clock'], 'H1 · 3:00')
        self.assertEqual(college['away']['code'], 'DUKE')   # four letters stay whole
        self.assertEqual(self.go('NBA', [event('e', '2025-11-16T17:00Z', 'in', team('A', 'A', '1', False), team('B', 'B'), period=2, clock='0:00')])[0][0]['clock'], 'End of Q2')


class Provider(unittest.TestCase):
    def provider(self, fail=(), answers=None, clock=lambda: NOW):
        calls = []

        def fetch(url):
            calls.append(url)
            for path in fail:
                if path in url:
                    raise OSError('down')
            return (answers or {}).get(next((e[3] for e in se.LEAGUES if e[3] in url), ''), body())
        p = se.EspnProvider(fetch=fetch, clock=clock)
        p.calls = calls
        return p

    def answers(self):
        return {'basketball/nba': body(event('1', '2025-11-16T17:00Z', 'in', team('IND', 'Indiana Pacers', '88', False), team('PHI', 'Philadelphia 76ers', '91'), period=4, clock='1:00'),
                                       event('2', '2025-11-16T23:30Z', 'pre', team('LAL', 'Lakers', '0', False), team('GSW', 'Warriors')),
                                       event('3', '2025-11-17T23:30Z', 'pre', team('MIA', 'Heat', '0', False), team('NYK', 'Knicks'))),
                'soccer/eng.1': body(event('4', '2025-11-16T19:00Z', 'pre', team('CHE', 'Chelsea', '0', False), team('ARS', 'Arsenal')))}

    def test_the_contract_over_two_leagues(self):
        p = self.provider(answers=self.answers())
        live = p.live_games()
        self.assertEqual([g['id'] for g in live], ['espn:NBA:1'])
        up = p.upcoming_games()
        self.assertEqual([g['id'] for g in up], ['espn:EPL:4', 'espn:NBA:2', 'espn:NBA:3'])   # soonest first
        self.assertEqual([g['id'] for g in p.upcoming_games('NBA')], ['espn:NBA:2', 'espn:NBA:3'])
        leagues = {lg['code']: lg for lg in p.leagues()}
        self.assertEqual((leagues['NBA']['live'], leagues['NBA']['next']), (1, up[1]['start']))
        self.assertEqual((leagues['EPL']['live'], leagues['NFL']['next']), (0, None))
        o = p.overview()
        self.assertEqual((o['live'], o['live_sports'], o['leagues'], o['updated']), (1, ['Basketball'], len(se.LEAGUES), NOW))
        self.assertEqual(o['next'], up[0]['start'])
        self.assertEqual(p.game('espn:NBA:2')['away']['name'], 'Lakers')
        self.assertIsNone(p.game('nope'))
        for g in live + up:   # every game fits the contract the pages read
            self.assertTrue({'id', 'league', 'league_name', 'sport', 'state', 'away', 'home', 'joiner', 'start', 'sources'} <= set(g))

    def test_the_answer_is_reused_for_a_moment_and_refresh_asks_again(self):
        p = self.provider(answers=self.answers())
        p.live_games()
        count = len(p.calls)
        p.upcoming_games()
        p.overview()
        self.assertEqual(len(p.calls), count)          # one fetch per page load, not three
        p.refresh()
        self.assertEqual(len(p.calls), 2 * count)   # both requests of every league again

    def test_each_league_is_asked_for_today_and_tomorrow_with_no_date_range(self):
        p = self.provider(answers=self.answers())
        p.live_games()
        nba = [u for u in p.calls if 'basketball/nba' in u]
        self.assertEqual(len(nba), 2)
        self.assertTrue(nba[0].endswith('/scoreboard'))
        self.assertRegex(nba[1], r'scoreboard\?dates=\d{8}$')
        self.assertFalse(any('-' in u.split('dates=')[-1] for u in p.calls if 'dates=' in u))   # the feed answers a range with HTTP 400
        # the same event in both answers is one game
        self.assertEqual(len([g for g in p.upcoming_games('NBA')]), 2)

    def test_tomorrow_failing_keeps_the_first_answer(self):
        answers = self.answers()
        calls = []

        def fetch(url):
            calls.append(url)
            if 'dates=' in url:
                raise OSError('slow')
            return answers.get(next((e[3] for e in se.LEAGUES if e[3] in url), ''), body())
        p = se.EspnProvider(fetch=fetch, clock=lambda: NOW)
        self.assertEqual(len(p.live_games()), 1)
        self.assertIn('NBA', [lg['code'] for lg in p.leagues()])

    def test_one_league_failing_never_fails_the_rest(self):
        p = self.provider(fail=('football/nfl',), answers=self.answers())
        self.assertEqual(len(p.live_games()), 1)
        self.assertNotIn('NFL', [lg['code'] for lg in p.leagues()])

    def test_nothing_answering_says_unavailable_but_a_good_earlier_answer_stays(self):
        t = [NOW]
        good = self.provider(answers=self.answers(), clock=lambda: t[0])
        good.live_games()
        down = se.EspnProvider(fetch=lambda url: (_ for _ in ()).throw(OSError('offline')), clock=lambda: t[0])
        with self.assertRaises(sm.SportsUnavailable):
            down.live_games()
        down.snapshot = good.snapshot
        t[0] += 3600
        self.assertEqual(len(down.live_games()), 1)   # the hour-old answer, rather than an error page

    def test_the_page_pipeline_accepts_these_games(self):
        import sports_live
        p = self.provider(answers=self.answers())
        props, chosen, slots = sports_live.load(p, now=NOW, offset=0)
        self.assertEqual(props['state'], 'ok')
        self.assertEqual(props['g.1.league'], 'NBA')
        self.assertEqual(props['g.1.clock'], 'Q4 · 1:00')
        self.assertEqual(slots, {})   # no sources yet: nothing to play

    def test_espn_is_the_provider_only_when_asked_for(self):   # DEC-061: the phone uses JetExtractors; KODI_IOS_SPORTS=espn keeps this feed
        import os
        import sports_provider
        old = os.environ.get('KODI_IOS_SPORTS')
        try:
            os.environ['KODI_IOS_SPORTS'] = 'espn'
            sports_provider.reset()
            self.assertIsInstance(sports_provider.get(), se.EspnProvider)
        finally:
            os.environ.pop('KODI_IOS_SPORTS', None) if old is None else os.environ.__setitem__('KODI_IOS_SPORTS', old)
            sports_provider.reset()


if __name__ == '__main__':
    unittest.main()
