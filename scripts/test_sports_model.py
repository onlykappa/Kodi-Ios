"""Sports data contract and shared rules (DEC-055, DEC-056, DEC-057): ordering, day grouping, wording, the sample provider."""
import calendar
import sys
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import sports_model as sm  # noqa: E402

NOW = calendar.timegm((2026, 11, 15, 18, 45, 0))   # Sunday 6:45 PM UTC


def provider(offset=0, **kw):
    return sm.Sample(now=NOW, offset=offset, **kw)


class Wording(unittest.TestCase):
    def test_clock_and_days(self):
        self.assertEqual(sm.clock_text(NOW + 45 * 60, 0), '7:30 PM')
        self.assertEqual(sm.clock_text(calendar.timegm((2026, 11, 21, 12, 30, 0)), 0), '12:30 PM')
        self.assertEqual(sm.clock_text(calendar.timegm((2026, 11, 21, 0, 5, 0)), 0), '12:05 AM')
        self.assertEqual(sm.clock_text(NOW, -5 * 3600), '1:45 PM')   # the phone's own time zone
        self.assertEqual(sm.day_label(NOW + 3600, NOW, 0), 'Today')
        self.assertEqual(sm.day_label(NOW + 24 * 3600, NOW, 0), 'Tomorrow')
        self.assertEqual(sm.day_label(calendar.timegm((2026, 11, 21, 12, 30, 0)), NOW, 0), 'Sat, Nov 21')
        # 1 AM UTC tomorrow is still "Today" on a phone five hours west
        self.assertEqual(sm.day_label(calendar.timegm((2026, 11, 16, 1, 0, 0)), NOW, -5 * 3600), 'Today')

    def test_in_n_min_only_inside_the_hour_before_the_start(self):
        self.assertEqual(sm.soon_text(NOW + 45 * 60, NOW), 'in 45 min')
        self.assertEqual(sm.soon_text(NOW + 20, NOW), 'in 1 min')
        self.assertEqual(sm.soon_text(NOW + 2 * 3600, NOW), '')
        self.assertEqual(sm.soon_text(NOW - 60, NOW), '')

    def test_updated_wording(self):
        self.assertEqual(sm.updated_text(NOW - 20, NOW, 0), 'Updated just now')
        self.assertEqual(sm.updated_text(NOW - 5 * 60, NOW, 0), 'Updated 5 min ago')
        self.assertEqual(sm.updated_text(NOW - 2 * 3600, NOW, 0), 'Updated at 4:45 PM')
        self.assertEqual(sm.updated_text(NOW - 2 * 86400, NOW, 0), 'Updated Fri, Nov 13')

    def test_counts_and_versus(self):
        self.assertEqual([sm.sources_text(n) for n in (0, 1, 3)], ['No sources yet', '1 source', '3 sources'])
        self.assertEqual(sm.count_text(1, 'game'), '1 game')
        self.assertEqual(sm.count_text(3, 'league'), '3 leagues')
        p = provider()
        self.assertEqual(sm.versus(p.game('epl-1')), 'Arsenal vs Chelsea')
        self.assertEqual(sm.versus(p.game('nfl-2')), 'Kansas City Chiefs at Buffalo Bills')


class Ordering(unittest.TestCase):
    def test_live_closest_to_the_end_first_unknown_last(self):
        self.assertEqual([g['id'] for g in provider().live_games()], ['ucl-1', 'nba-1', 'nfl-1', 'nhl-1'])
        games = [dict(id='a', left=None, start=5), dict(id='b', left=0.5, start=9), dict(id='c', left=None, start=2), dict(id='d', left=0.1, start=1)]
        self.assertEqual([g['id'] for g in sm.order_live(games)], ['d', 'b', 'c', 'a'])

    def test_upcoming_by_day_soonest_first(self):
        days = sm.group_by_day(provider().upcoming_games(), NOW, 0)
        self.assertEqual([(d, len(g)) for d, g in days], [('Today', 3), ('Tomorrow', 2), ('Sat, Nov 21', 1)])
        self.assertEqual([g['id'] for g in days[0][1]], ['epl-1', 'liga-1', 'nba-2'])

    def test_day_grouping_follows_the_phones_zone(self):
        p = provider(offset=-5 * 3600)
        days = sm.group_by_day(p.upcoming_games(), NOW, -5 * 3600)
        self.assertEqual([d for d, _ in days][:2], ['Today', 'Tomorrow'])
        self.assertEqual(sm.clock_text(p.game('liga-1')['start'], 0), '8:00 PM')              # 75 min after the 6:45 PM sample time
        self.assertEqual(sm.clock_text(p.game('liga-1')['start'], -5 * 3600), '3:00 PM')     # the same moment on a phone five hours west

    def test_leagues_live_sports_first_then_fixed_order(self):
        order = sm.order_leagues(provider().leagues())
        self.assertEqual([s for s, _ in order], ['Soccer', 'Basketball', 'American football', 'Hockey', 'Baseball', 'Golf', 'Combat sports', 'Motorsport'])
        self.assertEqual([l['code'] for l in dict(order)['Soccer']], ['UCL', 'EPL', 'LIGA', 'BUN'])   # live first, then the soonest game
        self.assertEqual([l['code'] for l in dict(order)['Basketball']], ['NBA', 'WNBA'])
        self.assertEqual(sum(len(l) for _, l in order), 13)
        # a sport that goes live moves up: baseball with a live game comes before the others without
        leagues = provider().leagues()
        next(l for l in leagues if l['code'] == 'MLB')['live'] = 1
        self.assertEqual([s for s, _ in sm.order_leagues(leagues)][:5], ['Soccer', 'Basketball', 'American football', 'Hockey', 'Baseball'])
        leagues = [l for l in leagues if l['sport'] != 'Hockey']
        next(l for l in leagues if l['code'] == 'F1')['live'] = 2
        self.assertEqual([s for s, _ in sm.order_leagues(leagues)][:4], ['Soccer', 'Basketball', 'American football', 'Baseball'])

    def test_league_rows_say_live_and_next(self):
        p = provider()
        by = {l['code']: l for l in p.leagues()}
        d = lambda code: sm.league_detail(by[code], NOW, 0)
        self.assertEqual(d('NBA'), ('1 live', 'next today 9:15 PM'))
        self.assertEqual(d('NFL'), ('1 live', 'next tomorrow 8:15 PM'))
        self.assertEqual(d('EPL'), ('', 'Next today 7:30 PM'))
        self.assertEqual(d('UCL'), ('1 live', ''))
        self.assertEqual(d('BUN'), ('', ''))

    def test_league_filter_and_chips(self):
        p = provider()
        self.assertEqual(sm.league_codes(p.live_games()), ['All', 'NBA', 'NFL', 'NHL', 'UCL'])
        self.assertEqual(sm.league_codes(p.upcoming_games()), ['All', 'EPL', 'LIGA', 'NBA', 'NFL', 'NHL'])
        self.assertEqual([g['id'] for g in p.upcoming_games('EPL')], ['epl-1', 'epl-2'])
        self.assertEqual([g['id'] for g in p.live_games('NBA')], ['nba-1'])
        self.assertEqual(p.live_games('WNBA'), [])


class Provider(unittest.TestCase):
    def test_overview_matches_the_landing_board(self):
        o = provider().overview()
        self.assertEqual((o['live'], o['leagues'], o['more_today']), (4, 13, 2))
        self.assertEqual(o['live_sports'], ['American football', 'Basketball', 'Hockey', 'Soccer'])
        self.assertEqual(o['next'], NOW + 45 * 60)

    def test_games_have_the_documented_shape(self):
        for g in provider().live_games() + provider().upcoming_games():
            self.assertTrue({'id', 'league', 'league_name', 'sport', 'state', 'away', 'home', 'joiner', 'start', 'clock', 'left', 'sources'} <= set(g))
            self.assertIn(g['joiner'], ('vs', 'at'))
            for t in (g['away'], g['home']):
                self.assertTrue({'code', 'name', 'score', 'crest'} <= set(t))
            for s in g['sources']:
                self.assertTrue({'id', 'addon', 'quality', 'language', 'tag', 'also', 'play'} <= set(s))
                self.assertIn(s['tag'], ('best', 'good', ''))
            if g['sources']:
                self.assertEqual([s['tag'] for s in g['sources']].count('best'), 1)   # one Best per game
        self.assertTrue(all(g['state'] == 'live' and g['clock'] and g['away']['score'] is not None for g in provider().live_games()))
        self.assertTrue(all(g['state'] == 'upcoming' for g in provider().upcoming_games()))

    def test_a_provider_hands_out_copies(self):
        p = provider()
        p.live_games()[0]['sources'].clear()
        p.upcoming_games()[0]['league'] = 'XX'
        p.game('nba-1')['away']['score'] = 0
        self.assertEqual(len(p.live_games()[0]['sources']), 3)
        self.assertEqual(p.upcoming_games()[0]['league'], 'EPL')
        self.assertEqual(p.game('nba-1')['away']['score'], 88)

    def test_unavailable_raises_for_every_call(self):
        p = provider(fail=True)
        for call in (p.overview, p.live_games, p.upcoming_games, p.leagues, p.refresh, lambda: p.game('epl-1')):
            with self.assertRaises(sm.SportsUnavailable):
                call()


class Door(unittest.TestCase):
    def test_sample_data_is_opt_in_so_invented_games_never_reach_a_phone(self):
        import os
        import sports_provider as sp
        sp.reset()
        os.environ.pop('KODI_IOS_SPORTS', None)
        import sports_espn
        from unittest.mock import patch
        with patch.object(sports_espn, 'fetch_json', side_effect=OSError('offline')):   # the real provider with no answer: the pages say "Can't load"
            with self.assertRaises(sm.SportsUnavailable):
                sp.get().overview()
        sp.reset()
        os.environ['KODI_IOS_SPORTS'] = 'quiet'
        try:
            self.assertEqual(sp.get().live_games(), [])
            self.assertTrue(sp.get().upcoming_games())
        finally:
            os.environ.pop('KODI_IOS_SPORTS', None)
            sp.reset()

    def test_pages_get_the_sample_provider_and_play_logs(self):
        import os
        import sports_provider as sp
        sp.reset()
        os.environ['KODI_IOS_SPORTS'] = 'sample'
        p = sp.get()
        self.assertIs(p, sp.get())
        self.assertTrue(p.live_games())
        lines = []
        src = p.live_games()[0]['sources'][0]
        self.assertEqual(sp.play(src, lines.append), src['play'])
        self.assertIn('Loop TV', lines[0])
        os.environ['KODI_IOS_SPORTS'] = 'down'
        try:
            with self.assertRaises(sm.SportsUnavailable):
                sp.get().overview()
        finally:
            os.environ.pop('KODI_IOS_SPORTS', None)
            sp.reset()


class GameRules(unittest.TestCase):
    def test_game_status_uses_countdown_days_and_local_offset(self):
        self.assertEqual(sm.start_text(NOW+45*60,NOW,0),'Starts in 45 min')
        self.assertEqual(sm.start_text(NOW+2*3600,NOW,0),'Starts today')
        self.assertEqual(sm.start_text(NOW+24*3600,NOW,0),'Starts tomorrow')
        self.assertEqual(sm.start_text(NOW-1,NOW,0),'Started')
        self.assertEqual(sm.start_text(NOW+45*60,NOW,-5*3600),'Starts in 45 min')

    def test_source_ranking_is_stable_and_does_not_rewrite_play_values(self):
        plain={'tag':'','play':object()};good={'tag':'good','play':object()}
        best1={'tag':'best','play':object()};best2={'tag':'best','play':object()}
        sources=[plain,good,best1,best2]
        self.assertEqual(sm.order_sources(sources),[best1,best2,good,plain])
        self.assertEqual(sources,[plain,good,best1,best2])
        self.assertIs(sm.order_sources(sources)[0],best1)


class KodiClock(unittest.TestCase):
    """Times follow the phone's own clock as Kodi shows it, even when Python believes the zone is UTC."""
    def fake(self, shown):
        import sys, types
        return unittest.mock.patch.dict(sys.modules, {'xbmc': types.SimpleNamespace(getInfoLabel=lambda label: shown)})

    def test_offset_from_kodis_local_time(self):
        import time
        now = 1_794_768_300   # 2026-11-15 18:45:00 UTC
        with self.fake('13:45:00'):
            self.assertEqual(sm.kodi_offset(now), -5 * 3600)    # New York in winter
        with self.fake('03:15:00'):
            self.assertEqual(sm.kodi_offset(now), 8 * 3600 + 30 * 60)   # a half-hour zone, across midnight
        with self.fake('20:44:58'):
            self.assertEqual(sm.kodi_offset(now), 2 * 3600)     # seconds apart between the two clocks round to the quarter hour
        with self.fake('nonsense'):
            self.assertIsNone(sm.kodi_offset(now))

    def test_the_device_offset_prefers_kodi_for_now_and_python_for_other_moments(self):
        import time
        with self.fake('%s' % time.strftime('%H:%M:%S', time.gmtime(time.time() + 9 * 3600))):
            self.assertEqual(sm.device_offset(), 9 * 3600)
            python_only = sm.device_offset(time.time() + 86400 * 100)   # another moment: Python's own table, not the fake clock
            self.assertEqual(python_only, sm.device_offset(time.time() + 86400 * 100))
        self.assertIsNotNone(sm.device_offset())   # outside Kodi: Python's table


if __name__ == '__main__':
    unittest.main()
