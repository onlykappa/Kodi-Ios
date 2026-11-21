"""Sports › Live Now (DEC-055, DEC-057; approved boards 6-9, option B): the properties, the taps and the page's structure."""
import calendar
import copy
import importlib.util
import re
import sys
import unittest
import threading
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BOOT / 'resources/lib'))
import portrait  # noqa: E402
import sports_live_page as lp  # noqa: E402
import sports_model as sm  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ctl = load('sports_live_controller', BOOT / 'sports_live.py')
NOW = calendar.timegm((2026, 11, 15, 18, 45, 0))
SAMPLE = sm.Sample(now=NOW, offset=0)


def many(n):
    """n live games from the sample ones, each with its own id and a different league."""
    out = []
    for i in range(n):
        g = copy.deepcopy(SAMPLE.live[i % 4])
        g['id'] = 'x%d' % i
        g['league'] = 'L%02d' % i
        g['left'] = i / 100.0
        out.append(g)
    return out


def props(games=None, chosen='All', upcoming=None):
    return ctl.props_for(SAMPLE.live_games() if games is None else games, chosen, upcoming if upcoming is not None else [], NOW, 0, NOW)


class Wording(unittest.TestCase):
    def test_monogram_and_also_line(self):
        self.assertEqual([ctl.mono(n) for n in ('The Loop', 'Loop TV', 'Loop Guide', 'Sports Hub', 'Solo')], ['TL', 'LT', 'LG', 'SH', 'SO'])
        self.assertEqual(ctl.also_text([]), '')
        self.assertEqual(ctl.also_text(['Loop TV']), 'Also on Loop TV')
        self.assertEqual(ctl.also_text(['Loop TV', 'Sports Hub']), 'Also on Loop TV, Sports Hub')
        self.assertEqual(ctl.also_text(['Loop TV', 'Sports Hub', 'Loop Guide']), 'Also on 3 add-ons')   # one line, never under the play button
        self.assertEqual(ctl.sub_text(4, 'Updated just now'), '4 games on now · updated just now')
        self.assertEqual(ctl.sub_text(1, 'Updated at 6:45 PM'), '1 game on now · updated at 6:45 PM')


class Properties(unittest.TestCase):
    def test_the_approved_board(self):
        p, chosen = props()
        self.assertEqual((p['state'], chosen, p['sub']), ('ok', 'All', '4 games on now · updated just now'))
        self.assertEqual([p['chip.%d' % n] for n in range(5)], ['All', 'NBA', 'NFL', 'NHL', 'UCL'])
        self.assertEqual((p['chip.0.on'], p['chip.1.on'], p['chips.rows']), ('true', '', '1'))
        # closest to the end first: the soccer game, then basketball
        self.assertEqual((p['g.1.league'], p['g.1.clock'], p['g.1.a.name'], p['g.1.h.name']), ('UCL', '67′', 'Borussia Mönchengladbach', 'Brighton & Hove Albion'))
        self.assertEqual(p['g.1.score'], '2 – 1')   # the big score in the middle of the card (option B)
        self.assertEqual((p['g.2.league'], p['g.2.clock'], p['g.2.score']), ('NBA', 'Q3 · 4:12', '88 – 91'))

    def test_unused_slots_are_cleared_so_nothing_stale_stays(self):
        p, _ = props()
        for g in (5, 12):
            self.assertEqual([v for k, v in p.items() if k.startswith('g.%d.' % g) and v], [])
        self.assertEqual(p['g.4.score'], '1 – 1')   # the NHL card: a score, cleared when the slot is empty
        self.assertEqual(p['g.4.a.name'], 'Toronto Maple Leafs')   # away and home alike: the card's two names (sample NHL game)

    def test_a_tie_has_no_leader_and_a_game_without_sources_can_be_searched(self):
        games = SAMPLE.live_games()
        nhl = next(g for g in games if g['league'] == 'NHL')
        nhl['sources'] = []
        p, _ = props(games)
        row = next(g for g in range(1, 5) if p['g.%d.league' % g] == 'NHL')
        self.assertTrue(p['g.%d.id' % row])   # a tap on the card opens the game page, where the sources are looked for

    def test_no_source_rows_on_the_live_page_any_more(self):
        # Owner, 2026-11-20: the Live Now cards carry no sources and no buttons; a tap opens the game page, where Play is.
        game = SAMPLE.live_games()[0]
        game['sources'] = [dict(game['sources'][0], id='s%d' % i) for i in range(7)]
        p, _ = props([game])
        self.assertFalse([k for k in p if '.s.' in k])

    def test_a_league_chip_filters_and_a_stale_choice_falls_back_to_all(self):
        p, chosen = props(chosen='NBA')
        self.assertEqual((chosen, p['sub'], p['chip.1.on'], p['chip.0.on'], p['g.1.league'], p['g.2.league']), ('NBA', '1 game on now · updated just now', 'true', '', 'NBA', ''))
        p, chosen = props(chosen='WNBA')
        self.assertEqual((chosen, p['sub']), ('All', '4 games on now · updated just now'))

    def test_chip_rows_follow_the_number_of_chips(self):
        self.assertEqual(props(many(4))[0]['chips.rows'], '1')      # All + 4 = 5 chips
        self.assertEqual(props(many(5))[0]['chips.rows'], '2')      # 6 chips wrap to a second row
        self.assertEqual(props(many(12))[0]['chips.rows'], '3')     # 13 chips
        p = props(many(14))[0]
        self.assertEqual((p['chips.rows'], p['chip.14'], p['chip.14.on']), ('3', 'L13', ''))   # 15 chips is the most
        self.assertEqual(props(many(20))[0]['chip.14'], 'L13')

    def test_more_games_than_cards_says_so(self):
        p, _ = props(many(14))
        self.assertEqual(p['more'], '2 more games not shown. Pick a league above to narrow the list.')
        self.assertEqual(p['g.12.league'], 'L11')
        self.assertEqual(props(many(12))[0]['more'], '')
        self.assertEqual(props(many(13))[0]['more'], '1 more game not shown. Pick a league above to narrow the list.')

    def test_nothing_live_says_when_the_next_game_starts(self):
        p, _ = props([], upcoming=SAMPLE.upcoming_games())
        self.assertEqual((p['state'], p['none.title'], p['none.text'], p['none.button']), ('none', 'No games live right now', 'The next game starts at 7:30 PM.', 'See Upcoming'))
        self.assertEqual(p['chips.rows'], '0')
        far = [dict(g, start=NOW + 26 * 3600) for g in SAMPLE.upcoming_games()[:1]]
        self.assertEqual(props([], upcoming=far)[0]['none.text'], 'The next game starts tomorrow at 8:45 PM.')
        self.assertEqual(props([], upcoming=[])[0]['none.text'], 'Nothing is scheduled yet.')

    def test_no_answer_is_the_cant_load_state_and_refresh_asks_again(self):
        p, chosen, slots = ctl.load(sm.Sample(now=NOW, fail=True), 'NBA', now=NOW, offset=0)
        self.assertEqual((p['state'], p['err.title'], p['err.button'], chosen, slots), ('error', 'Can’t load live games right now', 'Try again', 'NBA', {}))

        class Counting(sm.Sample):
            refreshed = 0

            def refresh(self):
                Counting.refreshed += 1
        p, chosen, slots = ctl.load(Counting(now=NOW), 'All', now=NOW, offset=0, refresh=True)
        self.assertEqual((p['state'], Counting.refreshed, len(slots)), ('ok', 1, 9))


class Taps(unittest.TestCase):
    def test_live_page_stops_when_child_requests_native_playback(self):
        stop=threading.Event();props={'KodiIOS.SportsNativeOwner':''};finished=threading.Event()
        home=SimpleNamespace(getProperty=lambda k:props.get(k,''))
        thread=threading.Thread(target=ctl.watch_handoff,args=(stop,home,'',finished.set),daemon=True)
        thread.start();props['KodiIOS.SportsNativeOwner']='fixture'
        self.assertTrue(finished.wait(2));stop.set();thread.join(2)
    def test_source_free_game_button_opens_targeted_search(self):
        import ast
        tree=ast.parse((BOOT/'sports_live.py').read_text())
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='onClick')
        game={'id':'espn:fixture','state':'live'};opened=[]
        provider=SimpleNamespace(game=lambda ident:game if ident==game['id'] else None)
        env={'lp':lp,'control_target':ctl.control_target,'sports_provider':SimpleNamespace(get=lambda:provider),
             'sm':sm,'log':lambda *args:None,'xbmcgui':SimpleNamespace()}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'live-onclick','exec'),env)
        window=SimpleNamespace(getProperty=lambda key:game['id'],slots={})
        with patch.dict(sys.modules,{'sports_game':SimpleNamespace(run=lambda selected,**kw:opened.append((selected,kw)))}):
            env['onClick'](window,lp.SEARCH0)
        self.assertEqual(opened,[(game,{'provider':provider,'search':True})])
    def test_native_live_source_closes_dialogs_before_dispatch(self):
        import sports_jet
        events = []
        launched = threading.Event()
        def play(source, log, launch):
            events.append('prepare')
            launch('sports_jet_run', 'play', 'fixture')
        def dispatch(*args):
            events.append('launch')
            launched.set()
        xbmc = SimpleNamespace(executebuiltin=lambda cmd: events.append(cmd), sleep=lambda ms: None)
        with patch.object(sports_jet, '_launch', side_effect=dispatch):
            ctl.play_source({}, SimpleNamespace(play=play), lambda: events.append('finish'), xbmc, lambda: events.append('error'), lambda msg: None)
            self.assertTrue(launched.wait(2))
        self.assertEqual(events, ['prepare', 'finish', 'Dialog.Close(all,true)', 'launch'])

    def test_direct_and_failed_live_source_keep_expected_behavior(self):
        events = []
        xbmc = SimpleNamespace(Player=lambda: SimpleNamespace(play=lambda url: events.append(url)))
        ctl.play_source({}, SimpleNamespace(play=lambda *a, **k: 'fixture'), lambda: events.append('closed'), xbmc, lambda: events.append('error'), lambda msg: None)
        def fail(*args, **kwargs): raise RuntimeError('private fixture')
        ctl.play_source({}, SimpleNamespace(play=fail), lambda: events.append('closed'), xbmc, lambda: events.append('error'), lambda msg: None)
        self.assertEqual(events, ['fixture', 'error'])

    def test_every_control_id_maps_back(self):
        self.assertEqual(ctl.control_target(lp.chip_id(1, 3)), ('chip', 3))
        self.assertEqual(ctl.control_target(lp.chip_id(2, 7)), ('chip', 7))
        self.assertEqual(ctl.control_target(lp.chip_id(3, 14)), ('chip', 14))
        self.assertIsNone(ctl.control_target(lp.BACK))
        self.assertEqual(ctl.control_target(lp.SEARCH0), ('search', 1))   # the cards are big tap targets now; sources play on the game page

    def test_a_tap_finds_the_source_on_screen(self):
        slots = ctl.slots_for(SAMPLE.live_games(), 'All')
        self.assertEqual(slots[(1, 1)]['addon'], 'Loop TV')
        self.assertEqual(slots[(2, 1)]['id'], 'The Loop|1080p|English')
        nba = ctl.slots_for(SAMPLE.live_games(), 'NBA')
        self.assertEqual(sorted(nba), [(1, 1), (1, 2)])
        self.assertEqual(nba[(1, 2)]['addon'], 'Loop TV')


class Page(unittest.TestCase):
    xml = lp.page(portrait)
    root = ET.fromstring(xml.split('\n', 1)[1])

    def test_ids_are_unique_and_the_buttons_are_there(self):
        ids = [c.get('id') for c in self.root.iter('control') if c.get('id')]
        self.assertEqual(len(ids), len(set(ids)))
        for ident in (lp.BACK, lp.RETRY, lp.SEE_UPCOMING, lp.CARD0):   # no league chips any more (owner, 2026-11-20)
            self.assertIn(str(ident), ids)
        self.assertNotIn(str(lp.REFRESH), ids)   # no refresh button: the data is kept fresh for the person (owner, build 619)

    def test_every_property_the_page_reads_is_set_by_the_controller(self):
        read = set(re.findall(r'Window\(\)\.Property\(([\w.]+)\)', self.xml))
        given = set(props()[0]) | set(props([])[0]) | set(ctl.ERROR)
        self.assertEqual(sorted(read - given), [])
        self.assertEqual(sorted(k for k in given if k.startswith('g.') and k not in read and not k.endswith('.id')), [])   # the card's id is what a tap reads   # nothing is set that is never drawn

    def test_kodi_condition_rules(self):
        for cond in re.findall(r'<visible[^>]*>(.*?)</visible>', self.xml):
            self.assertNotIn('$INFO', cond)
            self.assertNotIn('!(', cond)

    def test_hit_areas_are_at_least_44_pt(self):
        for c in self.root.iter('control'):
            if c.get('type') == 'button':
                self.assertGreaterEqual(int(c.findtext('height')), 118, c.get('id'))
                self.assertGreaterEqual(int(c.findtext('width')), 118, c.get('id'))

    def test_names_wrap_and_nothing_scrolls_or_is_cut(self):
        names = [c for c in self.root.iter('control') if c.get('type') == 'label' and 'name' in (c.findtext('label') or '')]
        self.assertTrue(names)
        for c in names:
            self.assertEqual(c.findtext('wrapmultiline'), 'true')
        for c in self.root.iter('control'):
            if c.get('type') == 'label' and c.findtext('width') != 'auto':
                self.assertEqual(c.findtext('scroll'), 'false', c.findtext('label'))

    def test_the_skin_gets_the_window_and_the_route_exists(self):
        self.assertEqual(sorted(lp.files(portrait)), ['portrait/IOSSportsLive.xml'])
        self.assertIn('IOSSportsLive.xml', portrait.sports_live_page.WINDOW)
        import sports_routes
        self.assertTrue(sports_routes.available('sports_live'))


class CardTap(unittest.TestCase):
    """Owner, 2026-11-20: tapping a live game's team area opens its game page (Play once a source is found)."""
    def test_a_card_tap_routes_to_the_game_page_and_ids_do_not_collide(self):
        import sports_live_page as lp
        self.assertEqual(ctl.control_target(lp.CARD0), ('search', 1))
        self.assertEqual(ctl.control_target(lp.CARD0 + lp.GAMES - 1), ('search', lp.GAMES))
        self.assertEqual(ctl.control_target(lp.SEARCH0), ('search', 1))
        ranges = [(lp.CARD0, lp.CARD0 + lp.GAMES), (lp.SEARCH0, lp.SEARCH0 + lp.GAMES), (lp.CHIP0, lp.CHIP0 + 3 * lp.CHIP_IDS), (lp.PLAY0, lp.PLAY0 + 2 * lp.ALSO_IDS)]
        for i, (a, b) in enumerate(ranges):
            for c, d in ranges[i + 1:]:
                self.assertTrue(b <= c or d <= a, (a, b, c, d))


class Crests(unittest.TestCase):
    """Owner, 2026-11-20: real logos on the cards, never letters; a team without one shows an empty ring."""
    def test_crests_become_the_phones_copies_and_missing_ones_are_empty(self):
        nba = next(g for g in SAMPLE.live_games() if g['league'] == 'NBA')   # the sample basketball teams carry ESPN crest addresses
        p = ctl.game_props(1, nba)
        self.assertTrue(p['g.1.a.crest'].startswith('https://a.espncdn.com/'))
        import tempfile
        profile = tempfile.mkdtemp()   # a real folder: nothing is written beside the code or at the root
        got = ctl.with_crests(dict(p), profile, get=lambda url: b'\x89PNG' + b'0' * 200)
        for k in got:
            if k.endswith('.crest') and p[k]:
                self.assertTrue(got[k].endswith('.png'), k)
        def offline(url):
            raise OSError('offline')
        none = ctl.with_crests(dict(p), tempfile.mkdtemp(), get=offline)   # a fresh folder: nothing saved before
        self.assertTrue(all(none[k] == '' for k in none if k.endswith('.crest')))   # a failed download is an empty ring


if __name__ == '__main__':
    unittest.main()
