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


class CleanCard(unittest.TestCase):
    """Owner, 2026-11-21 (the approved rows, ISSUE-437): compact hairline rows. No LIVE word and no Watch button; each team's logo at its edge with its short name
    under it, its score beside the logo in the condensed score font; the white clock, the football and the grey situation line in the middle."""
    def setUp(self):
        self.xml = lp.page(portrait)
        self.root = ET.fromstring(self.xml)
        self.w = portrait.WIDTH - 2 * lp.PAD

    def test_there_is_no_live_word_and_no_play_button(self):
        self.assertNotIn('<label>LIVE</label>', self.xml)
        self.assertNotIn('Watch', self.xml)

    def test_the_middle_column_is_centred_on_the_page_with_room_for_the_clock(self):
        mw = self.w - 2 * lp.COL
        self.assertEqual(lp.PAD + lp.COL + mw / 2, portrait.WIDTH / 2)
        self.assertGreaterEqual(mw, 300)                                                     # "Q4 · 14:14" and the football fit side by side

    def test_scores_sit_beside_the_logos_in_the_score_font(self):
        self.assertIn('<left>188</left><top>%d</top><width>%d</width><height>%d</height>' % (lp.SCORE_Y, lp.SCORE_W, lp.SCORE_H), self.xml)
        self.assertIn('<font>p_score</font>', self.xml)
        self.assertGreaterEqual(lp.SCORE_W, 150)                                             # three digits (an NBA score) fit
        self.assertGreater(188, 54 + lp.LOGO)                                                # a clear gap between the away logo and its score

    def test_rows_are_compact_and_everything_fits_inside_the_row(self):
        self.assertEqual(lp.ROW_H, 239)                                                      # 89 pt, measured from the owner's reference
        self.assertLessEqual(lp.NAME_Y + lp.NAME_H, lp.ROW_H)
        self.assertLessEqual(lp.LOGO_Y + lp.LOGO, lp.NAME_Y)
        self.assertLessEqual(lp.SCORE_Y + lp.SCORE_H, lp.ROW_H)

    def test_football_icon_shows_only_on_the_side_that_has_the_ball(self):
        for side in 'ah':
            self.assertIn('String.IsEqual(Window().Property(g.1.ball),%s)' % side, self.xml)
        self.assertIn('football.png', self.xml)

    def test_the_yard_line_turns_red_only_in_the_red_zone(self):
        self.assertIn('String.IsEqual(Window().Property(g.1.rz),true)', self.xml)
        self.assertIn('!String.IsEqual(Window().Property(g.1.rz),true)', self.xml)
        self.assertIn('FFFF453A', self.xml)

    def test_a_header_has_no_line_under_it_and_a_row_only_has_one_when_no_header_sits_above(self):
        self.assertIn('<visible>String.IsEmpty(Window().Property(g.2.gn))</visible>', self.xml)   # a row's own hairline: none where its league's header is
        self.assertIn('Window().Property(g.2.hp)', self.xml)
        self.assertIn('Window().Property(g.2.gs)', self.xml)

    def test_headers_are_not_buttons(self):
        for with_sub in (False, True):
            self.assertNotIn('type="button"', lp.header(portrait, 2, with_sub))                # a header only labels its league; it is not tappable


class DarkCrests(unittest.TestCase):
    """Owner, 2026-11-21 (ESPN logos on a black page): the dark-page logo first (Iowa's own is black), the plain one when there is none."""
    def test_dark_address(self):
        self.assertEqual(ctl.dark_crest('https://a.espncdn.com/i/teamlogos/ncaa/500/2294.png'), 'https://a.espncdn.com/i/teamlogos/ncaa/500-dark/2294.png')
        self.assertEqual(ctl.dark_crest('https://example.com/x.png'), '')
        self.assertEqual(ctl.dark_crest(''), '')

    def png(self, pixel, size=8):
        import struct
        import zlib
        rows = b''.join(b'\0' + bytes(c for _ in range(size) for c in pixel) for _ in range(size))
        chunk = lambda tag, data: struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')

    def test_only_a_near_black_logo_gets_the_dark_version(self):
        import tempfile
        black, green = 'https://a.espncdn.com/i/teamlogos/ncaa/500/2294.png', 'https://a.espncdn.com/i/teamlogos/ncaa/500/2429.png'
        asked = []

        def get(url):
            asked.append(url)
            if 'w=96' in url:   # the small version measured first
                return self.png((0, 0, 0, 255)) if '2294' in url else self.png((0, 80, 53, 255))
            return b'\x89PNG' + b'0' * 200
        got = ctl.with_crests({'g.1.a.crest': black, 'g.1.h.crest': green}, tempfile.mkdtemp(), get=get)
        self.assertTrue(got['g.1.a.crest'] and got['g.1.h.crest'])
        self.assertIn('https://a.espncdn.com/i/teamlogos/ncaa/500-dark/2294.png', asked)    # Iowa: the dark-page logo
        self.assertIn(green, asked)                                                         # Charlotte green keeps its own colours
        self.assertNotIn('https://a.espncdn.com/i/teamlogos/ncaa/500-dark/2429.png', asked)

    def test_a_missing_dark_logo_falls_back_to_the_plain_one(self):
        import tempfile
        url, asked = 'https://a.espncdn.com/i/teamlogos/ncaa/500/1.png', []

        def get(u):
            asked.append(u)
            if 'w=96' in u:
                return self.png((0, 0, 0, 255))
            if '500-dark' in u:
                raise OSError('404')
            return b'\x89PNG' + b'0' * 200
        got = ctl.with_crests({'g.1.a.crest': url}, tempfile.mkdtemp(), get=get)
        self.assertTrue(got['g.1.a.crest'].endswith('.png'))
        self.assertEqual(asked[-1], url)

    def test_the_measurement_is_remembered(self):
        import tempfile
        import sports_logos
        profile, calls = tempfile.mkdtemp(), []
        url = 'https://a.espncdn.com/i/teamlogos/ncaa/500/2294.png'
        get = lambda u: calls.append(u) or self.png((0, 0, 0, 255))
        self.assertTrue(sports_logos.needs_dark(profile, url, get))
        self.assertTrue(sports_logos.needs_dark(profile, url, get))
        self.assertEqual(len(calls), 1)
        self.assertAlmostEqual(sports_logos.brightness(self.png((255, 255, 255, 255))), 1.0, places=2)
        self.assertIsNone(sports_logos.brightness(b'\x89PNG not really'))


class EventRow(unittest.TestCase):
    """Owner, 2026-11-21: Formula 1 (the Las Vegas race) was on and not listed. An event has one title and no two teams: its row says the title and the session."""
    def test_an_event_without_a_second_side_carries_its_title(self):
        game={'id':'espn:F1:600','league':'F1','league_name':'Formula 1','sport':'Motorsport','state':'live','start':0,'sources':[],'clock':'Race','title':'Heineken Las Vegas Grand Prix',
              'away':{'name':'Heineken Las Vegas Grand Prix','short':'Heineken Las Vegas Grand Prix','code':'F1','score':None},'home':{'name':'','short':'','code':'','score':None}}
        p=ctl.game_props(1,game,True)
        self.assertEqual((p['g.1.et'],p['g.1.clock'],p['g.1.h.name'],p['g.1.gn']),('Heineken Las Vegas Grand Prix','Race','','Formula 1'))
        two=ctl.game_props(1,dict(game,home={'name':'B','short':'B','code':'B','score':1},away={'name':'A','short':'A','code':'A','score':2}),True)
        self.assertEqual(two['g.1.et'],'')                                                  # a two-team game never shows the event row
    def test_the_page_draws_the_event_row_only_when_there_is_no_home_team(self):
        xml=lp.page(portrait)
        self.assertIn('String.IsEmpty(Window().Property(g.1.h.name))',xml);self.assertIn('Window().Property(g.1.et)',xml)
        self.assertIn('!String.IsEmpty(Window().Property(g.1.h.name))',xml)               # and the two-team layout only when there is one


class Grouping(unittest.TestCase):
    """Owner, 2026-11-21: NFL games with NFL games, NBA with NBA; a header (logo, name, chevron) over each league's first game; live games only."""
    def game(self, league, n, **kw):
        g = {'id': '%s-%d' % (league, n), 'league': league, 'league_name': kw.pop('league_name', league), 'sport': 'x', 'state': 'live', 'start': 0, 'sources': [],
             'away': {'name': 'Away Team', 'short': 'Away', 'code': 'AWY', 'score': 1}, 'home': {'name': 'Home Team', 'short': 'Home', 'code': 'HOM', 'score': 2}}
        g.update(kw)
        return g

    def test_leagues_are_together_big_ones_first_and_the_order_inside_is_kept(self):
        games = [self.game('NBA', 1), self.game('EPL', 1), self.game('NFL', 1), self.game('NBA', 2), self.game('NFL', 2), self.game('LIGA', 1), self.game('EPL', 2)]
        self.assertEqual([g['id'] for g in ctl.grouped(games)], ['NFL-1', 'NFL-2', 'NBA-1', 'NBA-2', 'EPL-1', 'EPL-2', 'LIGA-1'])

    def test_only_the_first_game_of_a_league_carries_its_header(self):
        p, _ = props([self.game('NBA', 1), self.game('NFL', 1), self.game('NBA', 2)], 'All')
        self.assertEqual([p['g.%d.gn' % n] for n in (1, 2, 3)], ['NFL', 'NBA', ''])
        self.assertEqual([p['g.%d.id' % n] for n in (1, 2, 3)], ['NFL-1', 'NBA-1', 'NBA-2'])
        self.assertEqual(p['g.3.gl'], '')

    def test_header_titles(self):
        self.assertEqual(ctl.league_title(self.game('NCAAF', 1, league_name='College Football')), ('NCAAF', 'College Football'))
        self.assertEqual(ctl.league_title(self.game('NBA', 1)), ('NBA', ''))
        self.assertEqual(ctl.league_title(self.game('EPL', 1, league_name='Premier League')), ('Premier League', ''))
        self.assertEqual(ctl.league_title(self.game('UCL', 1, league_name='UEFA Champions League')), ('UCL', ''))

    def test_the_subtitle_header_and_the_plain_one_are_told_apart(self):
        p, _ = props([self.game('NCAAF', 1, league_name='College Football'), self.game('NBA', 1)], 'All')
        by = {p['g.%d.gn' % n]: (p['g.%d.gs' % n], p['g.%d.hp' % n]) for n in (1, 2)}
        self.assertEqual(by, {'NBA': ('', 'true'), 'NCAAF': ('College Football', '')})

    def test_a_name_that_does_not_fit_is_its_code(self):
        team = lambda short, code: {'short': short, 'name': short, 'code': code}
        self.assertEqual(ctl.team_label(team('Western KY', 'WKU')), 'Western KY')
        self.assertEqual(ctl.team_label(team('North Carolina', 'UNC')), 'UNC')
        self.assertEqual(ctl.team_label(team('Tennessee Tech', 'TNTC')), 'TNTC')
        self.assertEqual(ctl.team_label(team('Mississippi State Bulldogs', '')), 'Mississippi State Bulldogs')   # no code to use

    def test_football_situation_and_possession_follow_the_data(self):
        game = self.game('NCAAF', 1, detail='2nd & 10', yard='WVU 45', ball='h')
        p, _ = props([game], 'All')
        self.assertEqual((p['g.1.dn'], p['g.1.yd'], p['g.1.ball'], p['g.1.rz']), ('2nd & 10', 'WVU 45', 'h', ''))
        game = self.game('NCAAF', 1, detail='1st & 10', yard='JSU 15', ball='a', redzone=True)
        p, _ = props([game], 'All')
        self.assertEqual((p['g.1.ball'], p['g.1.rz']), ('a', 'true'))
        p, _ = props([self.game('NCAAF', 1, ball='x')], 'All')
        self.assertEqual((p['g.1.ball'], p['g.1.dn']), ('', ''))                          # no possession known: no football

    def test_headers_get_the_dark_league_logo_and_college_leagues_a_glyph(self):
        import tempfile
        p, _ = props([self.game('NHL', 1), self.game('NCAAF', 1)], 'All')
        got = ctl.with_crests(dict(p), tempfile.mkdtemp(), get=lambda url: b'\x89PNG' + b'0' * 200)
        self.assertTrue(got['g.1.gl'].endswith('NHL-dark.png'))
        self.assertEqual(got['g.2.gl'], ctl.FOOTBALL_ICON)


class Properties(unittest.TestCase):
    def test_the_approved_board(self):
        p, chosen = props()
        self.assertEqual((p['state'], chosen, p['sub']), ('ok', 'All', '4 games on now · updated just now'))
        self.assertEqual([p['chip.%d' % n] for n in range(5)], ['All', 'NBA', 'NFL', 'NHL', 'UCL'])
        self.assertEqual((p['chip.0.on'], p['chip.1.on'], p['chips.rows']), ('true', '', '1'))
        # grouped by league, the big leagues first (owner, 2026-11-21): NFL, NBA, NHL, then the rest
        self.assertEqual([p['g.%d.gn' % n] for n in (1, 2, 3, 4)], ['NFL', 'NBA', 'NHL', 'UCL'])
        self.assertEqual((p['g.4.clock'], p['g.4.a.name'], p['g.4.h.name']), ('67′', 'Borussia Mönchengladbach', 'Brighton & Hove Albion'))
        self.assertEqual((p['g.4.a.score'], p['g.4.h.score']), ('2', '1'))   # a score beside each logo
        self.assertEqual((p['g.2.clock'], p['g.2.a.score'], p['g.2.h.score']), ('Q3 · 4:12', '88', '91'))

    def test_unused_slots_are_cleared_so_nothing_stale_stays(self):
        p, _ = props()
        for g in (5, 12):
            self.assertEqual([v for k, v in p.items() if k.startswith('g.%d.' % g) and v], [])
        self.assertEqual((p['g.3.a.score'], p['g.3.h.score']), ('1', '1'))   # the NHL row: a score, cleared when the slot is empty
        self.assertEqual(p['g.3.a.name'], 'Toronto Maple Leafs')   # away and home alike: the card's two names (sample NHL game)

    def test_a_tie_has_no_leader_and_a_game_without_sources_can_be_searched(self):
        games = SAMPLE.live_games()
        nhl = next(g for g in games if g['league'] == 'NHL')
        nhl['sources'] = []
        p, _ = props(games)
        row = next(g for g in range(1, 5) if p['g.%d.gn' % g] == 'NHL')
        self.assertTrue(p['g.%d.id' % row])   # a tap on the card opens the game page, where the sources are looked for

    def test_no_source_rows_on_the_live_page_any_more(self):
        # Owner, 2026-11-20: the Live Now cards carry no sources and no buttons; a tap opens the game page, where Play is.
        game = SAMPLE.live_games()[0]
        game['sources'] = [dict(game['sources'][0], id='s%d' % i) for i in range(7)]
        p, _ = props([game])
        self.assertFalse([k for k in p if '.s.' in k])

    def test_a_league_chip_filters_and_a_stale_choice_falls_back_to_all(self):
        p, chosen = props(chosen='NBA')
        self.assertEqual((chosen, p['sub'], p['chip.1.on'], p['chip.0.on'], p['g.1.gn'], p['g.2.gn']), ('NBA', '1 game on now · updated just now', 'true', '', 'NBA', ''))
        p, chosen = props(chosen='WNBA')
        self.assertEqual((chosen, p['sub']), ('All', '4 games on now · updated just now'))

    def test_chip_rows_follow_the_number_of_chips(self):
        self.assertEqual(props(many(4))[0]['chips.rows'], '1')      # All + 4 = 5 chips
        self.assertEqual(props(many(5))[0]['chips.rows'], '2')      # 6 chips wrap to a second row
        self.assertEqual(props(many(12))[0]['chips.rows'], '3')     # 13 chips
        p = props(many(14))[0]
        self.assertEqual((p['chips.rows'], p['chip.14'], p['chip.14.on']), ('3', 'L13', ''))   # 15 chips is the most
        self.assertEqual(props(many(20))[0]['chip.14'], 'L13')

    def test_more_games_than_rows_says_so(self):
        p, _ = props(many(32))
        self.assertEqual(p['more'], '2 more games not shown.')
        self.assertTrue(p['g.30.a.name'])
        self.assertEqual(props(many(30))[0]['more'], '')
        self.assertEqual(props(many(31))[0]['more'], '1 more game not shown.')

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
        self.assertEqual((p['state'], Counting.refreshed, len(slots)), ('ok', 1, 0))   # no sources on this page any more: a tap opens the game


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
            env['onClick'](window,lp.CARD0)
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
        self.assertEqual(sorted(k for k in given if k.startswith('g.') and k not in read and not k.endswith('.id') and not k.endswith('h.name')), [])   # the card's id is what a tap reads   # nothing is set that is never drawn

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
        names = [c for c in self.root.iter('control') if c.get('type') == 'label' and '.short' in (c.findtext('label') or '')]
        self.assertTrue(names)
        for c in names:
            self.assertEqual(c.findtext('scroll'), 'false')
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
        self.assertIsNone(ctl.control_target(lp.CARD0 + lp.GAMES))
        ranges = [(lp.CARD0, lp.CARD0 + lp.GAMES), (lp.CHIP0, lp.CHIP0 + 3 * lp.CHIP_IDS), (lp.LIST, lp.LIST + 1), (lp.BACK, lp.BACK + 1)]
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


class FirstFrame(unittest.TestCase):
    """Owner, 2026-11-22 (log 71e31b26): Live Now took 3-5 s to show anything; it now draws the saved answer before the window opens, with no request."""
    class Page:
        def __init__(self):
            self.p = {}
        def setProperty(self, k, v):
            self.p[k] = v

    def test_the_saved_answer_is_drawn_with_the_crests_on_the_phone_and_no_request(self):
        import tempfile
        asked = []
        real = ctl.with_crests
        def spy(props, profile, get=None):
            asked.append(get)
            return real(props, profile, get=get)
        page = self.Page()
        provider_module = SimpleNamespace(get=lambda: SAMPLE)
        SAMPLE.has_answer = lambda: True
        try:
            with patch.object(ctl, 'with_crests', spy):
                self.assertTrue(ctl.first_frame(page, provider_module, 'All', tempfile.mkdtemp()))
        finally:
            del SAMPLE.has_answer
        self.assertEqual(asked, [ctl._offline])             # never the network
        self.assertEqual(page.p.get('state'), 'ok');self.assertTrue(page.drawn)
        self.assertTrue(page.p.get('g.1.id'))

    def test_nothing_saved_leaves_the_page_to_the_normal_load(self):
        page = self.Page()
        self.assertFalse(ctl.first_frame(page, SimpleNamespace(get=lambda: SimpleNamespace(has_answer=lambda: False)), 'All', '/tmp'))
        self.assertEqual(page.p, {})
        self.assertFalse(ctl.first_frame(page, SimpleNamespace(get=lambda: 1 / 0), 'All', '/tmp'))   # never raises


if __name__ == '__main__':
    unittest.main()
