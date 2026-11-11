"""Search Settings (board 11) and Add-on Updates (board 12): matching and bold, breadcrumbs, the two portrait pages'
XML, and the routes into them. Run: python3 -B scripts/test_search_updates.py"""
import importlib.util,sys,types,unittest,xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
LIB = BOOT / 'resources/lib'
sys.path.insert(0, str(LIB))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


find = load('settings_find_t', LIB / 'settings_find.py')
outdated = load('addon_outdated_t', LIB / 'addon_outdated.py')
sp = load('settings_page_t', LIB / 'settings_page.py')
index = load('settings_search_t', LIB / 'settings_search.py')
default = load('default_t', BOOT / 'default.py')
portrait = load('portrait_t', LIB / 'portrait.py')
PORTRAIT = types.SimpleNamespace(**portrait.__dict__)


def control_ids(xml):
    return [c.get('id') for c in ET.fromstring(xml.split('?>', 1)[1]).iter('control') if c.get('id')]


class FindMatches(unittest.TestCase):
    def test_matching_ignores_case_and_accents_and_bolds_the_typed_part(self):
        self.assertEqual(find.bold('Subtitle Language', 'subtit'), '[B]Subtit[/B]le Language')
        self.assertEqual(find.bold('Download Subtitles For', 'SUBTIT'), 'Download [B]Subtit[/B]les For')
        self.assertEqual(find.bold('Ünïcode Größe', 'unicode'), '[B]Ünïcode[/B] Größe')

    def test_bold_keeps_the_original_text_and_merges_overlaps(self):
        self.assertEqual(find.bold('Subtitles', 'subt sub'), '[B]Subt[/B]itles')   # 'sub' lies inside 'subt': one span
        self.assertEqual(find.bold('Play Play', 'play'), '[B]Play[/B] [B]Play[/B]')
        self.assertEqual(find.bold('Video', ''), 'Video')
        self.assertEqual(find.bold('Video', 'audio'), 'Video')
        self.assertEqual(find.bold('', 'x'), '')

    def test_every_word_must_match_and_the_label_ranks_first(self):
        entries = [('Subtitle Size', 'Player › Subtitles', 'a'), ('Player', 'Settings', 'b'),
                   ('Subtitle Language', 'Player › Language', 'c')]
        self.assertEqual([f[0] for f in find.search(entries, 'player')], ['Player', 'Subtitle Size', 'Subtitle Language'])
        self.assertEqual([f[0] for f in find.search(entries, 'subtitle size')], ['Subtitle Size'])
        self.assertEqual(find.search(entries, 'subtitle zebra'), [])
        self.assertEqual(find.search(entries, '   '), [])

    def test_results_are_unique_and_limited(self):
        entries = [('Same', 'Here', 'x')] * 3 + [('Item %d' % n, 'Here', 'y') for n in range(100)]
        self.assertEqual(len(find.search(entries, 'here')), 60)
        self.assertEqual(find.search(entries, 'same'), [('Same', 'Here', 'x')])
        self.assertEqual(len(find.search(entries, 'here', limit=5)), 5)

    def test_breadcrumb_is_section_then_category_and_skips_empty_parts(self):
        self.assertEqual(find.crumb('Player', 'Subtitles'), 'Player › Subtitles')
        self.assertEqual(find.crumb('Settings'), 'Settings')
        self.assertEqual(find.crumb('', 'Library'), 'Library')
        self.assertEqual(find.crumb('Customisation', ''), 'Customisation')

    def test_the_index_uses_breadcrumbs_not_dots(self):
        crumbs = [w for _, w, _ in index.page_entries(sp)]
        self.assertTrue(crumbs)
        self.assertFalse(any('·' in w for w in crumbs))
        self.assertIn('Library › iPhone Files', crumbs)
        self.assertIn('Customisation › Home Screen', crumbs)


class SearchPage(unittest.TestCase):
    def setUp(self):
        self.xml = sp.search_window(PORTRAIT)

    def test_xml_is_well_formed_with_unique_ids_and_the_named_controls(self):
        ids = control_ids(self.xml)
        self.assertEqual(len(ids), len(set(ids)))
        root = ET.fromstring(self.xml.split('?>', 1)[1])
        self.assertEqual(root.get('type'), 'dialog')
        edit = [c for c in root.iter('control') if c.get('type') == 'edit']
        self.assertEqual([c.get('id') for c in edit], [str(sp.SEARCH_FIELD)])
        self.assertIn(str(sp.SEARCH_LIST), ids)
        self.assertIn('9001', ids)

    def test_the_mockup_text_and_the_empty_state_are_there(self):
        self.assertIn('Search Settings', self.xml)
        self.assertIn('No settings match', self.xml)
        self.assertIn('Try a shorter word or check the spelling.', self.xml)
        self.assertIn('Window().Property(empty)', self.xml)
        self.assertIn('$INFO[ListItem.Label]', self.xml)
        self.assertIn('$INFO[ListItem.Label2]', self.xml)

    def test_the_script_reads_the_same_controls_and_the_row_routes_here(self):
        ctl = (BOOT / 'settings_search.py').read_text()
        self.assertIn('settings_page.SEARCH_FIELD', ctl)
        self.assertIn('settings_page.SEARCH_LIST', ctl)
        self.assertIn('getControl(FIELD).getText()', ctl)
        self.assertIn('settings_find.bold(label,query)', ctl)
        self.assertEqual(sp.SEARCH, 'RunScript(service.kodi.ios.bootstrap,settings_search)')

    def test_each_result_carries_an_action_that_the_script_runs(self):
        ctl = (BOOT / 'settings_search.py').read_text()
        self.assertIn("self.chosen=self.found[index][2]", ctl)
        self.assertIn("xbmc.executebuiltin(action)", ctl)
        self.assertEqual(index.kodi_entries('<settings><section id="player" label="14200"><category id="subtitles" label="1"/>'
                                            '</section></settings>', {14200: 'Player', 1: 'Subtitles'}.get)[0][2],
                         'ActivateWindow(playersettings,subtitles)')


class AddonUpdatesPage(unittest.TestCase):
    def setUp(self):
        self.xml = sp.addon_updates_page(PORTRAIT)

    def test_xml_is_well_formed_with_unique_ids(self):
        ids = control_ids(self.xml)
        self.assertEqual(len(ids), len(set(ids)))
        for n in range(1, sp.UPDATE_ROWS + 1):
            self.assertIn(str(sp.UPDATE_ROW + n), ids)
        for check in sp.UPDATE_CHECK:
            self.assertIn(str(check), ids)
        self.assertIn('9001', ids)

    def test_empty_state_copy_and_the_tick_are_there(self):
        self.assertIn('Property(heading)', self.xml);self.assertIn('Everything Is Up to Date', (ROOT/'migration/bundled-bootstrap/addon_updates.py').read_text())
        self.assertIn('check.png', self.xml)
        self.assertIn('$INFO[Window().Property(checked)]', self.xml)
        self.assertIn('$INFO[Window().Property(button)]', self.xml)
        self.assertIn("'Check Now'", (BOOT / 'addon_updates.py').read_text())

    def test_the_script_fills_the_properties_this_page_reads(self):
        script = (BOOT / 'addon_updates.py').read_text()
        for key in ("'rows'", "'upd.%d.name'", "'upd.%d.icon'", "'checked'", "'button'"):
            self.assertIn(key, script)
        self.assertIn('settings_page.UPDATE_ROW', script)
        self.assertIn('settings_page.UPDATE_CHECK', script)
        self.assertIn("'UpdateAddonRepos'", script)
        self.assertIn('addon_outdated.LISTING', script)   # the directory the script reads
        self.assertIn("'Files.GetDirectory'", script)

    def test_a_row_opens_kodis_add_on_list_the_old_way(self):
        script = (BOOT / 'addon_updates.py').read_text()
        self.assertIn("OPEN_LIST='ActivateWindow(addonbrowser,addons://outdated/,return)'", script)


class Routes(unittest.TestCase):
    def test_settings_home_row_9102_opens_the_updates_page(self):
        self.assertEqual(sp.ADDON_UPDATES, 'RunScript(service.kodi.ios.bootstrap,addon_updates)')
        self.assertIn(sp.ADDON_UPDATES, sp.R(9102, 'Add-on Updates Available', sp.ADDON_UPDATES)[2])

    def test_both_scripts_are_registered_bootstrap_pages(self):
        for page in ('settings_search', 'addon_updates'):
            self.assertIn(page, default.PAGES)
            self.assertTrue((BOOT / (page + '.py')).is_file())
        path, argv = default.target(['service.kodi.ios.bootstrap', 'addon_updates'])
        self.assertEqual(Path(path), BOOT / 'addon_updates.py')
        self.assertEqual(argv, [path])


class OutdatedAddOns(unittest.TestCase):
    def test_lists_add_ons_in_kodis_order_and_skips_its_own_entries(self):
        files = [{'file': 'addons://outdated/script.trakt', 'label': 'Trakt', 'thumbnail': '/a.png'},
                 {'file': 'addons://update_all/', 'label': 'Update all'},
                 {'file': 'addons://update_allowed/', 'label': 'Allow updates'},
                 {'file': 'addons://outdated/plugin.video.x', 'label': 'X'}, {'file': 'addons://outdated/', 'label': ''}]
        self.assertEqual(outdated.updates(files), [{'id': 'script.trakt', 'name': 'Trakt', 'icon': '/a.png'},
                                                   {'id': 'plugin.video.x', 'name': 'X', 'icon': ''}])
        self.assertEqual(outdated.updates(None), [])

    def test_times_read_as_words(self):
        self.assertEqual(outdated.ago(0), 'just now')
        self.assertEqual(outdated.ago(59), 'just now')
        self.assertEqual(outdated.ago(60), '1 minute ago')
        self.assertEqual(outdated.ago(7200), '2 hours ago')
        self.assertEqual(outdated.ago(90000), '1 day ago')
        self.assertEqual(outdated.ago(-5), 'just now')

    def test_status_lines(self):
        self.assertEqual(outdated.status(1000 - 120, 1000, 0),
                         'Checked 2 minutes ago. Add-ons update on their own when a new version is out.')
        self.assertEqual(outdated.status(None, 1000, 0),
                         'Tap Check Now to look for updates. Add-ons update on their own when a new version is out.')
        self.assertEqual(outdated.status(1000, 1000, 2), 'Checked just now. Tap an add-on to update it.')
        self.assertIn('Could not read', outdated.status(None, 0, 0, failed=True))

    def test_the_stamp_round_trips_and_a_bad_stamp_is_none(self):
        self.assertEqual(outdated.parse_stamp(outdated.stamp_text(1234.9)), 1234.0)
        self.assertIsNone(outdated.parse_stamp('not json'))
        self.assertIsNone(outdated.parse_stamp(''))


if __name__ == '__main__':
    unittest.main()
