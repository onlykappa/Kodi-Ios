"""Sports from JetExtractors (DEC-061, ISSUE-363): JetItems become merged games with sources; slow or failing scrapers never fail the rest; play
descriptors round-trip; the JetProxy path keeps '?' inside the address out of the query."""
import json
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import sports_jet as sj  # noqa: E402
import sports_model as sm  # noqa: E402

NOW = 1763316000


class Link:   # the attributes of jetextractors.models.JetLink that the adapter reads
    def __init__(self, address, name='', links=False):
        self.address, self.name, self.links = address, name, links

    def to_dict(self):
        return {'address': self.address, 'name': self.name}


def item(title, start=None, league=None, status=None, links=None):
    return NS(title=title, links=links if links is not None else [Link('https://x/1', 'Stream 1 [English, HD]')],
              starttime=datetime.fromtimestamp(start) if start else None, league=league, status=status)


class Ext:
    def __init__(self, name, items=None, error=None, delay=0):
        self.name, self.items, self.error, self.delay = name, items or [], error, delay

    def get_items(self):
        time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.items


def provider(*exts, wait=2):
    return sj.JetProvider(loader=lambda: (list(exts), 'test'), clock=lambda: NOW, wait=wait)


class Parsing(unittest.TestCase):
    def test_titles(self):
        self.assertEqual(sj.teams('Arsenal vs Chelsea'), ('Arsenal', 'Chelsea', 'vs'))
        self.assertEqual(sj.teams('Bills @ Chiefs'), ('Bills', 'Chiefs', 'at'))
        self.assertEqual(sj.teams('Lakers at Celtics'), ('Lakers', 'Celtics', 'at'))
        self.assertIsNone(sj.teams('ESPN HD'))

    def test_leagues_and_quality(self):
        self.assertEqual(sj.league_of('NBA')[:2], ('NBA', 'NBA'))
        self.assertEqual(sj.league_of('English Premier League')[0], 'EPL')
        self.assertEqual(sj.league_of('Padel')[0], 'PADEL')
        self.assertEqual((sj.quality_of('Stream 2 [English, HD, 40 viewers]'), sj.language_of('Stream 2 [English, HD]')), ('720p', 'English'))
        self.assertEqual(sj.quality_of('1080p feed'), '1080p')

    def test_state(self):
        mk = lambda **kw: item('A vs B', **kw)
        self.assertEqual(sj.state_of(mk(), NOW + 3600, NOW), 'upcoming')
        self.assertEqual(sj.state_of(mk(), NOW - 600 - 3600, NOW), 'live')
        self.assertIsNone(sj.state_of(mk(), NOW - 9 * 3600, NOW))
        self.assertEqual(sj.state_of(mk(status='LIVE'), None, NOW), 'live')
        self.assertIsNone(sj.state_of(mk(status='Ended (Nov 1)'), NOW - 100, NOW))
        self.assertIsNone(sj.state_of(mk(), None, NOW))

    def test_records_one_per_stream_and_descriptor_roundtrip(self):
        it = item('Arsenal vs Chelsea', NOW + 7200, 'Premier League', links=[Link('https://a/1', 'HD'), Link('https://a/2', 'Stream 2', links=True)])
        recs = sj.records(it, 'Streamed', NOW)
        self.assertEqual(len(recs), 2)
        self.assertEqual((recs[0]['league'], recs[0]['sport'], recs[0]['state']), ('EPL', 'Soccer', 'upcoming'))
        self.assertEqual(json.loads(recs[1]['play'])['l']['address'], 'https://a/2')
        self.assertEqual(sj.records(item('ESPN HD', NOW + 60), 'X', NOW), [])
        self.assertEqual(sj.records(item('A vs B', NOW + 60, links=[]), 'X', NOW), [])


class Provider(unittest.TestCase):
    def test_two_scrapers_one_game_two_sources_and_leagues(self):
        a = Ext('A', [item('Arsenal vs Chelsea', NOW + 7200, 'Premier League'), item('Lakers vs Celtics', NOW - 1800, 'NBA', 'LIVE')])
        b = Ext('B', [item('Arsenal FC vs Chelsea FC', NOW + 7200, 'EPL', links=[Link('https://b/1', '1080p')])])
        p = provider(a, b)
        up = p.upcoming_games()
        self.assertEqual(len(up), 1)
        self.assertEqual(len(up[0]['sources']), 2)
        self.assertEqual(up[0]['sources'][0]['tag'], 'best')
        self.assertEqual([g['league'] for g in p.live_games()], ['NBA'])
        self.assertEqual(sorted(l['code'] for l in p.leagues()), ['EPL', 'NBA'])
        self.assertEqual(p.game(up[0]['id'])['id'], up[0]['id'])
        ov = p.overview()
        self.assertEqual((ov['live'], ov['leagues']), (1, 2))

    def test_failing_scraper_does_not_fail_the_rest(self):
        p = provider(Ext('Bad', error=RuntimeError('boom')), Ext('Good', [item('A vs B', NOW + 900, 'NBA')]))
        self.assertEqual(len(p.upcoming_games()), 1)

    def test_nothing_anywhere_says_unavailable(self):
        with self.assertRaises(sm.SportsUnavailable):
            provider(Ext('Bad', error=RuntimeError('boom'))).live_games()
        with self.assertRaises(sm.SportsUnavailable):
            sj.JetProvider(loader=lambda: ([], 'missing'), clock=lambda: NOW, wait=1).live_games()

    def test_slow_scraper_is_left_to_finish_in_the_background(self):
        p = provider(Ext('Fast', [item('A vs B', NOW + 900, 'NBA')]), Ext('Slow', [item('C vs D', NOW + 900, 'NBA')], delay=1.5), wait=0.3)
        self.assertEqual(len(p.upcoming_games()), 1)
        time.sleep(1.6)
        self.assertEqual(len(p.upcoming_games()), 2)


class Playing(unittest.TestCase):
    def test_proxy_path(self):
        path = sj.proxy_path('https://h/live.m3u8?token=a&b=1', {'Referer': 'https://r/'})
        self.assertTrue(path.startswith('plugin://plugin.video.jetproxy/play/https://h/live.m3u8%3Ftoken%3Da%26b%3D1?h='))
        self.assertEqual(sj.proxy_path('https://h/x.m3u8', {}), 'plugin://plugin.video.jetproxy/play/https://h/x.m3u8')

    def test_provider_door_plays_jet_descriptors_only(self):
        import sports_provider
        self.assertEqual(sports_provider.play({'id': 's', 'play': 'sample-play'}), 'sample-play')


if __name__ == '__main__':
    unittest.main()
