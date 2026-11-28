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


def _epoch_of(text):
    return se._epoch(text)


def body(*events):
    return {'leagues': [{'name': 'x'}], 'events': list(events)}


class Parse(unittest.TestCase):
    def go(self, code, events):
        entry = next(e for e in se.LEAGUES if e[0] == code)
        return se.parse(entry[0], entry[1], entry[2], entry[4], entry[5], body(*events), NOW)

    def test_missing_live_score_is_unknown(self):
        live, _, _ = self.go('NBA', [event('1', '2025-11-16T17:00Z', 'in', team('IND', 'Indiana Pacers', '', False), team('PHI', 'Philadelphia 76ers', ''), period=1, clock='9:00')])
        self.assertIsNone(live[0]['away']['score'])
        self.assertIsNone(live[0]['home']['score'])

    def test_a_live_football_game_has_its_situation_yard_line_and_who_has_the_ball(self):
        """Owner, 2026-11-21 (the Live Now rows): ESPN's down and distance, yard line, red zone flag and the team that has the ball (a team id)."""
        away, home = team('UTC', 'Chattanooga', '0', False), team('ALA', 'Alabama', '47')
        away['team']['id'], home['team']['id'] = '236', '333'
        ev = event('9', '2025-11-16T17:00Z', 'in', away, home, period=4, clock='5:18', kind='STATUS_IN_PROGRESS')
        ev['competitions'][0]['situation'] = {'shortDownDistanceText': '2nd & 2', 'possessionText': 'ALA 31', 'isRedZone': False, 'possession': '333'}
        g = self.go('NCAAF', [ev])[0][0]
        self.assertEqual((g['detail'], g['yard'], g['ball'], g.get('redzone')), ('2nd & 2', 'ALA 31', 'h', None))
        ev['competitions'][0]['situation'] = {'shortDownDistanceText': '1st & Goal', 'possessionText': 'CHAT 4', 'isRedZone': True, 'possession': '236'}
        g = self.go('NCAAF', [ev])[0][0]
        self.assertEqual((g['detail'], g['ball'], g['redzone']), ('1st & Goal', 'a', True))
        ev['competitions'][0]['situation'] = {'possession': '999'}
        g = self.go('NCAAF', [ev])[0][0]
        self.assertEqual((g.get('detail'), g['ball']), (None, ''))   # a team id that is neither side: no football
        ev['competitions'][0].pop('situation')
        g = self.go('NCAAF', [ev])[0][0]
        self.assertNotIn('ball', g)

    def test_a_race_weekend_is_live_while_its_race_is_in_progress(self):
        """Owner, 2026-11-21: "it says there is no f1 streams and there is? vegas is rn". ESPN's F1 event status is FINAL from the first practice while the
        Race competition is IN PROGRESS (the real answer of that evening)."""
        def comp(kind,date,state):
            return {'type':{'abbreviation':kind},'date':date,'status':{'type':{'state':state}}}
        def weekend(race_state,qual_state='post'):
            return {'id':'600','name':'Heineken Las Vegas Grand Prix','date':'2026-11-20T00:30Z','status':{'type':{'state':'post','name':'STATUS_FINAL'}},
                    'competitions':[comp('FP1','2026-11-20T00:30Z','post'),comp('Qual','2026-11-21T04:00Z',qual_state),comp('Race','2026-11-22T04:00Z',race_state)]}
        entry=next(e for e in se.LEAGUES if e[0]=='F1')
        run=lambda ev:se.parse(entry[0],entry[1],entry[2],entry[4],entry[5],body(ev),NOW)
        live,up,done=run(weekend('in'))
        self.assertEqual((len(live),len(up),done),(1,0,0));self.assertEqual((live[0]['league'],live[0]['title'],live[0]['clock'],live[0]['state']),('F1','Heineken Las Vegas Grand Prix','Race','live'))
        live,up,done=run(weekend('pre',qual_state='in'));self.assertEqual((len(live),live[0]['clock']),(1,'Qualifying'))      # qualifying on: the weekend is live
        live,up,done=run(weekend('post'));self.assertEqual((len(live),len(up),done),(0,0,1))                                    # every session over: finished
        far=weekend('pre');far['competitions'][1]['status']['type']['state']='post'
        live,up,done=se.parse(entry[0],entry[1],entry[2],entry[4],entry[5],body(far),_epoch_of('2026-11-21T05:00Z'));self.assertEqual((len(live),len(up),done),(0,1,0))   # the race still to come: upcoming at ITS time
        self.assertEqual(up[0]['start'],_epoch_of('2026-11-22T04:00Z'))
        # the session on now: the game starts at ITS time (listings are matched by it), and the series' own logo stands for the event
        live,up,done=run(weekend('pre',qual_state='in'));self.assertEqual(live[0]['start'],_epoch_of('2026-11-21T04:00Z'))
        self.assertEqual(live[0]['away']['crest'],'https://a.espncdn.com/i/teamlogos/leagues/500-dark/f1.png');self.assertEqual(live[0]['home']['crest'],'')
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
        p.refresh(block=True)   # the service's loop: always asks again
        self.assertEqual(len(p.calls), 2 * count)   # both requests of every league again

    def test_each_league_is_asked_for_today_and_tomorrow_with_no_date_range(self):
        p = self.provider(answers=self.answers())
        p.live_games()
        nba = [u for u in p.calls if 'basketball/nba' in u]
        self.assertEqual(len(nba), 3)      # the plain scoreboard (it lags), today's date, tomorrow's date
        self.assertTrue(nba[0].endswith('/scoreboard'))
        self.assertRegex(nba[1], r'scoreboard\?dates=\d{8}$')
        self.assertRegex(nba[2], r'scoreboard\?dates=\d{8}$')
        self.assertLess(nba[1].split('dates=')[-1], nba[2].split('dates=')[-1])
        self.assertFalse(any('-' in u.split('dates=')[-1] for u in p.calls if 'dates=' in u))   # the feed answers a range with HTTP 400
        # the same event in both answers is one game
        self.assertEqual(len([g for g in p.upcoming_games('NBA')]), 2)

    def test_todays_games_show_when_the_plain_scoreboard_still_answers_yesterday(self):
        # ISSUE-399 (owner, 2026-11-20 7:24 AM Pacific): ESPN's plain scoreboard still answered the finished 2026-11-19 slate at 10:25 ET, so the page said
        # "Nothing live, next game tomorrow" while that day's games were on Apple Sports. Today's own date is asked as well.
        import time as _t
        now = int(_t.mktime((2026, 11, 20, 15, 25, 0, 0, 0, 0))) - _t.timezone   # 15:25 UTC on the 20th (10:25 ET)
        asked = []
        late = int(_t.mktime((2026, 11, 21, 0, 0, 0, 0, 0, 0))) - _t.timezone     # 00:00 UTC on the 21st: 4 PM Pacific on the 20th, a game still to come

        def fetch(url):
            asked.append(url)
            if 'basketball/nba' not in url:
                return body()
            if url.endswith('/scoreboard'):   # the lagging plain answer: only the day before, finished
                return body(event('old', '2026-11-20T01:00Z', 'post', team('GSW', 'Golden State Warriors', '90', False), team('MEM', 'Memphis Grizzlies', '95'), kind='STATUS_FINAL'))
            if url.endswith('dates=20261120'):
                return body(event('today1', _t.strftime('%Y-%m-%dT%H:%MZ', _t.gmtime(late)), 'pre', team('CHA', 'Charlotte Hornets', '0', False), team('ATL', 'Atlanta Hawks')))
            return body()
        p = se.EspnProvider(fetch=fetch, clock=lambda: now)
        nba = [g['id'] for g in p.upcoming_games('NBA')]
        self.assertEqual(nba, ['espn:NBA:today1'])
        self.assertTrue(any(u.endswith('dates=20261120') for u in asked) and any(u.endswith('dates=20261121') for u in asked))

    def test_the_feeds_day_is_the_us_eastern_day(self):
        import time as _t
        now = int(_t.mktime((2026, 11, 21, 3, 0, 0, 0, 0, 0))) - _t.timezone     # 03:00 UTC on the 21st = 22:00 ET on the 20th
        asked = []
        p = se.EspnProvider(fetch=lambda url: asked.append(url) or body(), clock=lambda: now)
        try:
            p.live_games()
        except Exception:
            pass
        nba = [u.split('dates=')[-1] for u in asked if 'basketball/nba' in u and 'dates=' in u]
        self.assertEqual(nba, ['20261120', '20261121'])

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
        self.assertEqual(props['g.1.gn'], 'NBA')
        self.assertEqual(props['g.1.clock'], 'Q4 · 1:00')
        self.assertEqual(slots, {})   # no sources yet: nothing to play

    def test_espn_is_the_provider_only_when_asked_for(self):   # DEC-061: the phone uses JetExtractors; KODI_IOS_SPORTS=espn keeps this feed
        import os
        import sports_provider
        old = os.environ.get('KODI_IOS_SPORTS')
        try:
            os.environ['KODI_IOS_SPORTS'] = 'espn'
            sports_provider.reset()
            self.assertIsInstance(__import__('sports_filter').unwrap(sports_provider.get()), se.EspnProvider)   # the league filter wraps it
        finally:
            os.environ.pop('KODI_IOS_SPORTS', None) if old is None else os.environ.__setitem__('KODI_IOS_SPORTS', old)
            sports_provider.reset()


class FirstFrameNeverWaits(unittest.TestCase):
    def test_a_stale_answer_is_shown_at_once_under_quick(self):
        import threading
        t = [1000]
        gate, asked, slow = threading.Event(), [], []

        def fetch(url):
            asked.append(url)
            if slow:   # after the first answer: ESPN is slow
                gate.wait(5)
            return body()
        p = se.EspnProvider(fetch=fetch, clock=lambda: t[0])
        p.overview()
        first = len(asked)
        slow.append(1)
        t[0] += p.ttl + 5
        done = []
        worker = threading.Thread(target=lambda: done.append(self._quick(p)), daemon=True)
        worker.start()
        worker.join(2)
        gate.set()
        self.assertTrue(done, 'quick() read waited for ESPN')
        self.assertGreaterEqual(first, 1)

    @staticmethod
    def _quick(p):
        with p.quick():
            return p.overview()


if __name__ == '__main__':
    unittest.main()
