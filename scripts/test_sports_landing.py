"""Sports landing page (DEC-054, DEC-057; approved board 2): the properties the page shows, its wording, its XML and its routes."""
import calendar
import importlib.util
import re
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.dont_write_bytecode = True
sys.path.insert(0, str(BOOT / 'resources/lib'))
import portrait  # noqa: E402
import sports_model as sm  # noqa: E402
import sports_page as sp  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ctl = load('sports_controller', BOOT / 'sports.py')
NOW = calendar.timegm((2026, 11, 15, 18, 45, 0))


def overview(**kw):
    base = sm.Sample(now=NOW, offset=0).overview()
    base.update(kw)
    return base


class Wording(unittest.TestCase):
    def test_sports_line(self):
        self.assertEqual(ctl.sports_line([]), '')
        self.assertEqual(ctl.sports_line(['Hockey']), 'Hockey')
        self.assertEqual(ctl.sports_line(['Hockey', 'Soccer']), 'Soccer and Hockey')
        self.assertEqual(ctl.sports_line(['Hockey', 'American football', 'Basketball', 'Soccer']), 'Soccer, Basketball\nand 2 more')

    def test_lines_wrap_at_spaces_and_never_exceed_two(self):
        self.assertEqual(sp.split_lines('Nothing live right now. Next game starts at 7:30 PM.', sp.FIT_BIG),
                         ['Nothing live right now. Next game', 'starts at 7:30 PM.'])
        self.assertEqual(sp.split_lines('Checking today’s games', sp.FIT_HALF), ['Checking today’s', 'games'])
        self.assertEqual(sp.split_lines('12 leagues', sp.FIT_HALF), ['12 leagues'])
        self.assertEqual(len(sp.split_lines('a bb ccc dddd eeeee ffffff ggggggg hhhhhhhh iiiiiiiii', 6)), 2)
        self.assertEqual(sp.split_lines('', 10), [])


class Properties(unittest.TestCase):
    def test_the_approved_board(self):
        props = ctl.props_for(overview(), NOW, 0)
        self.assertEqual((props['state'], props['sub']), ('ok', 'Updated just now'))
        self.assertEqual((props['live.mode'], props['live.badge'], props['live.title'], props['live.detail']), ('live', '4 live', 'Live right now', 'Soccer, Basketball and 2 more'))
        self.assertEqual((props['up.d1'], props['up.d2'], props['up.lines']), ('Next at 7:30 PM', '2 more today', '2'))
        self.assertEqual((props['lg.d1'], props['lg.lines']), ('13 leagues', '1'))
        counted = ctl.props_for(dict(overview(), upcoming=59), NOW, 0)   # mockup A1: "59 games · 2 more today"
        self.assertEqual((counted['up.d1'], counted['up.d2']), ('59 games · 2 more', 'today'))
        self.assertNotIn('fin', props)   # the Finished today row is not in the mockup

    def test_nothing_live_goes_grey_and_says_when_the_next_game_starts(self):
        props = ctl.props_for(overview(live=0, live_sports=[]), NOW, 0)
        self.assertEqual((props['live.mode'], props['live.badge']), ('idle', ''))
        self.assertEqual((props['live.title'], props['live.detail']), ('Nothing live right now', 'Next game starts at 7:30 PM.'))
        tomorrow = ctl.props_for(overview(live=0, live_sports=[], next=NOW + 24 * 3600), NOW, 0)
        self.assertIn('starts tomorrow at 6:45 PM.', tomorrow['live.detail'])
        none = ctl.props_for(overview(live=0, live_sports=[], next=None), NOW, 0)
        self.assertEqual((none['live.title'], none['live.detail']), ('Nothing live right now', ''))
        self.assertEqual((none['up.d1'], none['up.d2'], none['up.lines']), ('No games', 'coming up', '2'))   # never "No games coming" / "up"

    def test_the_upcoming_tile_when_the_next_game_is_not_today(self):
        props = ctl.props_for(overview(next=NOW + 24 * 3600 + 3600, more_today=0), NOW, 0)
        self.assertEqual((props['up.d1'], props['up.d2']), ('Next tomorrow', '7:45 PM'))
        far = ctl.props_for(overview(next=calendar.timegm((2026, 11, 21, 12, 30, 0))), NOW, 0)
        self.assertEqual((far['up.d1'], far['up.d2']), ('Next Sat, Nov 21', '12:30 PM'))
        one = ctl.props_for(overview(more_today=0), NOW, 0)
        self.assertEqual((one['up.d2'], one['up.lines']), ('', '1'))

    def test_up_next_rows_are_the_next_three_games_in_the_upcoming_rows_shape(self):
        games = [{'state': 'upcoming', 'league': 'NFL', 'start': NOW + n * 3600, 'joiner': 'at', 'away': {'name': 'Away %d' % n},
                  'home': {'name': 'Home %d' % n}, 'sources': []} for n in (5, 2, 9, 3)]
        games.append({'state': 'upcoming', 'league': 'NBA', 'start': NOW - 3600, 'joiner': 'at', 'away': {'name': 'Past'}, 'home': {'name': 'Game'}, 'sources': []})
        props = ctl.next_props(games, NOW, 0, {'NFL': '/logo/NFL.png'})
        self.assertEqual([props['next.%d.title' % n] for n in range(3)], ['Away 2 at Home 2', 'Away 3 at Home 3', 'Away 5 at Home 5'])   # soonest first, past games left out
        self.assertEqual([props['next.%d.pos' % n] for n in range(3)], ['first', 'mid', 'last'])
        self.assertEqual((props['next.0.clock.main'], props['next.0.clock.ampm'], props['next.0.sources'], props['next.0.logo']), ('8:45', 'PM', 'Today', '/logo/NFL.png'))
        self.assertEqual(ctl.next_props(games[:1], NOW, 0)['next.1.lines'], '')   # fewer games than rows: the rest stay empty
        self.assertEqual(ctl.next_props(games[:1], NOW, 0)['next.0.pos'], 'only')

    def test_one_league(self):
        props = ctl.props_for(overview(leagues=1), NOW, 0)
        self.assertEqual(props['lg.d1'], '1 league')

    def test_updating_keeps_the_shape(self):
        last = ctl.props_for(overview(), NOW, 0)
        props = ctl.props_updating(last)
        self.assertEqual((props['sub'], props['live.badge'], props['live.mode']), ('Updating', '', 'live'))
        self.assertEqual(props['live.title'], 'Live right now')   # the card keeps what it showed while the answer is on its way
        self.assertEqual((props['up.d1'], props['up.d2'], props['up.lines']), ('Checking today’s', 'games', '2'))
        self.assertEqual(props['lg.d1'], 'Checking leagues')
        self.assertEqual(ctl.props_updating()['live.title'], 'Checking what is on')

    def test_no_answer_is_the_cant_load_state_and_a_refresh_asks_again(self):
        down = ctl.load(sm.Sample(now=NOW, fail=True), now=NOW, offset=0)
        self.assertEqual((down['state'], down['sub'], down['err.title'], down['err.button']), ('error', 'Not updated', 'Can’t load sports right now', 'Try again'))

        class Counting(sm.Sample):
            refreshed = 0

            def refresh(self):
                Counting.refreshed += 1
        ok = ctl.load(Counting(now=NOW), now=NOW, offset=0, refresh=True)
        self.assertEqual((ok['state'], Counting.refreshed), ('ok', 1))


class Page(unittest.TestCase):
    xml = sp.page(portrait)
    root = ET.fromstring(xml.split('\n', 1)[1])

    def test_ids_are_unique_and_the_buttons_are_there(self):
        ids = [c.get('id') for c in self.root.iter('control') if c.get('id')]
        self.assertEqual(len(ids), len(set(ids)))
        for ident in (sp.BACK, sp.REFRESH, sp.LIVE, sp.UPCOMING, sp.LEAGUES, sp.SEE_ALL, sp.NEXT, sp.RETRY):
            self.assertIn(str(ident), ids)

    def test_every_property_the_page_reads_is_set_by_the_controller(self):
        read = set(re.findall(r'Window\(\)\.Property\(([\w.]+)\)', self.xml))
        given = set(ctl.props_for(overview(), NOW, 0)) | set(ctl.props_for(overview(live=0), NOW, 0)) | set(ctl.ERROR) | set(ctl.props_updating()) | set(ctl.next_props([], NOW, 0))
        self.assertEqual(sorted(read - given), [])

    def test_kodi_condition_rules(self):
        for cond in re.findall(r'<visible[^>]*>(.*?)</visible>', self.xml):
            self.assertNotIn('$INFO', cond)
            self.assertNotIn('!(', cond)

    def test_hit_areas_are_at_least_44_pt(self):
        for c in self.root.iter('control'):
            if c.get('type') == 'button':
                h, w = int(c.findtext('height')), int(c.findtext('width'))
                self.assertGreaterEqual(h, 118, c.get('id'))
                self.assertGreaterEqual(w, 118, c.get('id'))

    def test_the_skin_gets_the_window_and_the_textures(self):
        files = sp.files(portrait)
        self.assertEqual(sorted(files), sorted(['portrait/IOSSports.xml'] + ['extras/portrait/%s.png' % n for n in (
            'sports_live', 'sports_idle', 'sports_up', 'sports_lg', 'sports_big_mask', 'sports_half_mask')]))
        for name, data in files.items():
            if name.endswith('.png'):
                self.assertTrue(data.startswith(b'\x89PNG'), name)
        self.assertIn('IOSSports.xml', portrait.sports_page.WINDOW)


class Skin(unittest.TestCase):
    def test_portrait_loads_its_sports_pages_from_a_clean_path(self):
        """The rig's sync and the phone load portrait.py by path, with nothing else imported: a page module that imports another
        by name must find it (sync once failed with "No module named 'sports_page'")."""
        code = ("import importlib.util as i;s=i.spec_from_file_location('portrait_clean',%r);m=i.module_from_spec(s);s.loader.exec_module(m);"
                "print(m.sports_page.WINDOW,m.sports_live_page.WINDOW)") % str(BOOT / 'resources/lib/portrait.py')
        done = subprocess.run([sys.executable, '-B', '-I', '-c', code], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr[-600:])
        self.assertEqual(done.stdout.split(), ['IOSSports.xml', 'IOSSportsLive.xml'])


class Routes(unittest.TestCase):
    def test_library_has_the_sports_row_between_tv_shows_and_favourites(self):
        names = [n for n, _, _ in portrait.LIBRARY]
        self.assertEqual(names[names.index('TV Shows') + 1:names.index('Favourites')], ['Sports'])
        self.assertIn('RunScript(service.kodi.ios.bootstrap,sports)', dict((n, a) for n, _, a in portrait.LIBRARY)['Sports'])

    def test_only_pages_that_exist_are_started(self):
        self.assertTrue(ctl.available('sports'))
        self.assertTrue(ctl.available('sports_live'))
        self.assertFalse(ctl.available('sports_no_such_page'))   # an unknown name would run the recovery script
        self.assertEqual(set(ctl.ROUTES.values()), {'sports_live', 'sports_upcoming', 'sports_leagues'})


class NoCrewWindow(unittest.TestCase):
    """Owner, 2026-11-20: "no more Crew UI". The hub no longer opens Crew's own menu window under itself."""
    def test_the_hub_does_not_open_crews_container(self):
        text = (BOOT / 'sports.py').read_text()
        self.assertNotIn('sports_crew_context', text)
        self.assertNotIn('crew_context', text)
        self.assertNotIn('plugin.video.thecrew', text)


if __name__ == '__main__':
    unittest.main()
