"""Sports: several add-ons' answers become one list of games (DEC-055): one game, one line per distinct stream, Best / Also good."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import sports_merge as mg  # noqa: E402
import sports_model as sm  # noqa: E402

START = 1_800_000_000
ORDER = ['The Loop', 'Loop TV', 'Loop Guide', 'Sports Hub']


def rec(addon, away='Arsenal', home='Chelsea', quality='1080p', language='English', league='EPL', start=START, state='upcoming', **kw):
    base = {'addon': addon, 'league': league, 'league_name': 'Premier League', 'sport': 'Soccer', 'state': state, 'start': start,
            'away': {'code': away[:3].upper(), 'name': away, 'score': None}, 'home': {'code': home[:3].upper(), 'name': home, 'score': None},
            'joiner': 'vs', 'clock': '', 'left': None, 'quality': quality, 'language': language, 'play': 'plugin://%s/%s' % (addon, quality)}
    base.update(kw)
    return base


class Teams(unittest.TestCase):
    def test_the_same_team_spelled_differently(self):
        for a, b in (('Man City', 'Manchester City'), ('Brighton & Hove Albion', 'Brighton and Hove Albion FC'),
                     ('Borussia Mönchengladbach', 'Borussia Monchengladbach'), ('The Lakers', 'Lakers'), ('Boston Celtics', 'boston celtics')):
            self.assertTrue(mg.same_team(a, b), (a, b))

    def test_different_teams_stay_apart(self):
        for a, b in (('Chelsea', 'Chelsea Women'), ('Manchester City', 'Manchester United'), ('Arsenal', 'Chelsea'), ('', 'Chelsea'),
                     ('Real Madrid', 'Real Sociedad'), ('Inter', 'Inter Miami')):
            self.assertFalse(mg.same_team(a, b), (a, b))

    def test_quality_rank(self):
        self.assertEqual([mg.quality_rank(q) for q in ('2160p', '4K', '1080p', '1080', '720p', '480p', '', 'HD?')], [4, 4, 3, 3, 2, 1, 0, 0])


class Games(unittest.TestCase):
    def test_one_game_from_three_add_ons_is_one_game(self):
        games = mg.merge([rec('Loop TV', 'Man City', 'Brighton & Hove Albion', start=START + 600), rec('The Loop', 'Manchester City', 'Brighton and Hove Albion FC'),
                          rec('Sports Hub', 'Manchester City', 'Brighton & Hove Albion', start=START - 300)], ORDER)
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]['start'], START - 300)   # the earliest start
        self.assertEqual(games[0]['away']['name'], 'Manchester City')   # the add-on that ranks first supplies the names

    def test_different_games_or_a_different_day_do_not_merge(self):
        games = mg.merge([rec('The Loop'), rec('The Loop', 'Real Sociedad', 'Athletic Club', league='LIGA'), rec('Loop TV', start=START + 24 * 3600),
                          rec('Loop TV', 'Arsenal', 'Chelsea', league='UCL')], ORDER)
        self.assertEqual(len(games), 4)

    def test_the_game_id_is_stable(self):
        a = mg.merge([rec('The Loop')], ORDER)[0]['id']
        b = mg.merge([rec('Loop TV', 'ARSENAL FC', 'Chelsea FC')], ORDER)[0]['id']
        self.assertEqual(a, b)
        self.assertTrue(a.startswith('epl-'))

    def test_live_wins_and_the_score_comes_from_the_first_add_on_that_has_one(self):
        games = mg.merge([rec('The Loop', state='live', clock='67′', left=0.26), rec('Loop TV', state='live', away_score=None)], ORDER)
        self.assertEqual((games[0]['state'], games[0]['clock'], games[0]['left']), ('live', '67′', 0.26))
        first = rec('The Loop', state='live')
        second = rec('Loop TV', state='live')
        second['away']['score'], second['home']['score'] = 2, 1
        game = mg.merge([first, second], ORDER)[0]
        self.assertEqual((game['away']['score'], game['home']['score']), (2, 1))
        both = rec('The Loop', state='live')
        both['away']['score'], both['home']['score'] = 3, 3
        self.assertEqual(mg.merge([both, second], ORDER)[0]['away']['score'], 3)   # the add-on that ranks first wins a disagreement

    def test_the_result_has_the_contract_shape(self):
        for g in mg.merge([rec('The Loop'), rec('Loop TV', quality='720p')], ORDER):
            self.assertTrue({'id', 'league', 'league_name', 'sport', 'state', 'away', 'home', 'joiner', 'start', 'clock', 'left', 'sources'} <= set(g))
            for t in (g['away'], g['home']):
                self.assertTrue({'code', 'name', 'score', 'crest'} <= set(t))
            for s in g['sources']:
                self.assertTrue({'id', 'addon', 'quality', 'language', 'tag', 'also', 'play'} <= set(s))


class Sources(unittest.TestCase):
    def sources(self, *records):
        return mg.merge(list(records), ORDER)[0]['sources']

    def test_async_plugin_choices_remain_separate_and_are_not_ranked_as_known_quality(self):
        sources=self.sources(rec('Loop A',quality='',language='',play='fixture-a',separate_source=True),
                             rec('Loop B',quality='',language='',play='fixture-b',separate_source=True),
                             rec('Loop A',quality='',language='',play='fixture-c',separate_source=True))
        self.assertEqual(len(sources),3)
        self.assertEqual(len({s['id'] for s in sources}),3)
        self.assertFalse(any(s['tag'] for s in sources))
        self.assertEqual({s['play'] for s in sources},{'fixture-a','fixture-b','fixture-c'})

    def test_the_same_stream_in_several_add_ons_is_one_line_naming_the_others(self):
        s = self.sources(rec('Loop TV'), rec('The Loop'), rec('Sports Hub'))
        self.assertEqual(len(s), 1)
        self.assertEqual((s[0]['addon'], s[0]['also'], s[0]['tag']), ('The Loop', ['Loop TV', 'Sports Hub'], 'best'))
        self.assertEqual(s[0]['play'], 'plugin://The Loop/1080p')

    def test_different_choices_stay_separate_best_first_with_one_also_good(self):
        s = self.sources(rec('The Loop', quality='720p'), rec('Loop TV', quality='1080p'), rec('Sports Hub', quality='480p', language='Spanish'),
                         rec('Loop Guide', quality='1080p', language='German'))
        self.assertEqual([(x['addon'], x['quality'], x['language'], x['tag']) for x in s],
                         [('Loop TV', '1080p', 'English', 'best'), ('Loop Guide', '1080p', 'German', 'good'),
                          ('The Loop', '720p', 'English', ''), ('Sports Hub', '480p', 'Spanish', '')])

    def test_the_viewers_language_comes_before_another_language_at_the_same_size(self):
        s = self.sources(rec('The Loop', language='German'), rec('Loop TV', language='English'))
        self.assertEqual((s[0]['language'], s[1]['language']), ('English', 'German'))
        none = mg.merge([rec('The Loop', language='German'), rec('Loop TV', language='English')], ORDER, language='')[0]['sources']
        self.assertEqual(none[0]['addon'], 'The Loop')   # no language wanted: the add-on order decides

    def test_a_weak_second_source_is_not_recommended(self):
        s = self.sources(rec('The Loop', quality='1080p'), rec('Loop TV', quality='480p'))
        self.assertEqual([x['tag'] for x in s], ['best', ''])

    def test_a_game_without_a_playable_stream_has_no_sources(self):
        g = mg.merge([rec('The Loop', play='')], ORDER)[0]
        self.assertEqual(g['sources'], [])

    def test_exactly_one_best_per_game_and_never_two_good(self):
        s = self.sources(*[rec(a, quality=q, language=l) for a, q, l in (('The Loop', '1080p', 'English'), ('Loop TV', '720p', 'English'),
                                                                        ('Loop Guide', '720p', 'Spanish'), ('Sports Hub', '1080p', 'German'))])
        tags = [x['tag'] for x in s]
        self.assertEqual((tags.count('best'), tags.count('good')), (1, 1))

    def test_the_merged_games_work_with_the_page_helpers(self):
        games = mg.merge([rec('The Loop', state='live', left=0.5, clock='Q2'), rec('Loop TV', 'Lakers', 'Warriors', league='NBA', state='live', left=0.1)], ORDER)
        self.assertEqual([g['league'] for g in sm.order_live(games)], ['NBA', 'EPL'])
        self.assertEqual(sm.league_codes(games), ['All', 'EPL', 'NBA'])


if __name__ == '__main__':
    unittest.main()
