"""Profiles and Favourites portrait pages (Settings > Profiles, Settings > Favourites; mockup board 09 and 10).

Pure logic (profiles_rows.py, favourites_rows.py), the XML the page builders write (settings_page.profiles_page and
favourites_page, built through portrait.build), and the scripts that fill it (profiles_page.py, favourites_page.py):
their ids, window properties and JSON-RPC calls must agree with the XML."""
import importlib.util
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
LIB = BOOT / 'resources/lib'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pr = load('profiles_rows_t', LIB / 'profiles_rows.py')
fr = load('favourites_rows_t', LIB / 'favourites_rows.py')
portrait = load('portrait_pf', LIB / 'portrait.py')
profiles_script = (BOOT / 'profiles_page.py').read_text()
favourites_script = (BOOT / 'favourites_page.py').read_text()


class ProfileRows(unittest.TestCase):
    def test_current_profile_is_marked_and_named(self):
        rows = pr.entries([{'label': 'Master user', 'thumbnail': 'special://masterprofile/thumb.jpg'},
                           {'label': 'kids', 'thumbnail': ''}], 'Master user')
        self.assertEqual([r['current'] for r in rows], [True, False])
        self.assertEqual(rows[0]['initials'], 'MU')
        self.assertEqual(rows[0]['thumb'], 'special://masterprofile/thumb.jpg')
        self.assertEqual(rows[1]['thumb'], '')

    def test_generic_kodi_picture_is_not_shown(self):
        self.assertEqual(pr.avatar('special://xbmc/media/DefaultUser.png'), '')
        self.assertEqual(pr.avatar(None), '')
        self.assertEqual(pr.avatar('/private/var/mobile/profile.jpg'), '/private/var/mobile/profile.jpg')

    def test_initials_follow_the_accounts_rule(self):
        self.assertEqual(pr.initials('kids room'), 'KR')
        self.assertEqual(pr.initials('master_user'), 'MU')
        self.assertEqual(pr.initials(''), '?')

    def test_nameless_profiles_are_left_out_and_rows_are_capped(self):
        many = [{'label': 'p%d' % n} for n in range(20)] + [{'label': ''}]
        rows = pr.entries(many, 'p0')
        self.assertEqual(len(rows), pr.MAX)
        self.assertNotIn('', [r['name'] for r in rows])

    def test_properties_cover_every_row_and_the_add_row(self):
        rows = pr.entries([{'label': 'a'}, {'label': 'b'}], 'b')
        props = pr.properties(rows)
        self.assertEqual(props['rows'], '3')   # two profiles and Add Profile
        self.assertEqual(props['profile.2.current'], 'true')
        self.assertEqual(props['profile.1.current'], '')
        self.assertEqual(props['profile.3.name'], '')
        self.assertEqual(len([k for k in props if k.startswith('profile.') and k.endswith('.name')]), pr.MAX)

    def test_switch_target_skips_the_current_profile_and_missing_rows(self):
        rows = pr.entries([{'label': 'a'}, {'label': 'b'}], 'a')
        self.assertEqual(pr.switch_target(rows, 1), '')          # already signed in
        self.assertEqual(pr.switch_target(rows, 2), 'b')
        self.assertEqual(pr.switch_target(rows, 3), '')          # the Add Profile row or beyond
        self.assertEqual(pr.switch_target(rows, 0), '')

    def test_wording_is_the_approved_mockup(self):
        self.assertEqual(pr.ADD, 'Add Profile')
        self.assertEqual(pr.SIGNED_IN, 'Signed in now')
        self.assertEqual(pr.FOOT, 'Each profile has its own watched history, favourites and Home rows.')


class FavouriteRows(unittest.TestCase):
    def test_window_favourite_runs_the_window_and_its_parameter(self):
        self.assertEqual(fr.action_for({'type': 'window', 'window': 'videos', 'windowparameter': 'plugin://x/?a=1'}),
                         'ActivateWindow(videos,"plugin://x/?a=1")')
        self.assertEqual(fr.action_for({'type': 'window', 'window': 'home'}), 'ActivateWindow(home)')

    def test_media_and_script_favourites_are_quoted_like_kodi_writes_them(self):
        self.assertEqual(fr.action_for({'type': 'media', 'path': '/a/b, c.mkv'}), 'PlayMedia("/a/b, c.mkv")')
        self.assertEqual(fr.action_for({'type': 'script', 'path': 'special://home/x.py'}), 'RunScript("special://home/x.py")')
        self.assertEqual(fr.quote('say "hi" \\ there'), '"say \\"hi\\" \\\\ there"')

    def test_favourites_iOS_cannot_open_are_left_out(self):
        self.assertEqual(fr.action_for({'type': 'androidapp', 'path': 'com.example'}), '')
        self.assertEqual(fr.action_for({'type': 'unknown'}), '')
        self.assertEqual(fr.action_for({'type': 'media', 'path': ''}), '')
        rows = fr.entries([{'type': 'unknown', 'title': 'x'}, {'type': 'media', 'path': '/m.mkv', 'title': 'Film'}])
        self.assertEqual([r['title'] for r in rows], ['Film'])

    def test_only_window_and_media_favourites_are_removable(self):
        rows = fr.entries([{'type': 'window', 'window': 'videos', 'title': 'a'}, {'type': 'media', 'path': '/m', 'title': 'b'},
                           {'type': 'script', 'path': 'script.py', 'title': 'c'}])
        self.assertEqual([r['removable'] for r in rows], [True, True, False])

    def test_remove_arguments_name_the_same_favourite(self):
        window = {'type': 'window', 'window': 'videos', 'windowparameter': 'plugin://x/', 'title': 'Movies', 'path': 'ignored'}
        self.assertEqual(fr.remove_args(window), {'title': 'Movies', 'type': 'window', 'window': 'videos', 'windowparameter': 'plugin://x/'})
        media = {'type': 'media', 'path': '/m.mkv', 'title': 'Film', 'thumbnail': 'x.jpg'}
        self.assertEqual(fr.remove_args(media), {'title': 'Film', 'type': 'media', 'path': '/m.mkv'})

    def test_grid_keeps_kodi_order_and_stops_at_the_cap(self):
        favs = [{'type': 'media', 'path': '/%d.mkv' % n, 'title': 't%d' % n} for n in range(fr.MAX + 5)]
        rows = fr.entries(favs)
        self.assertEqual(len(rows), fr.MAX)
        self.assertEqual([r['title'] for r in rows[:3]], ['t0', 't1', 't2'])

    def test_properties_fill_every_cell_and_count(self):
        rows = fr.entries([{'type': 'media', 'path': '/a', 'title': 'A', 'thumbnail': 't.jpg'}])
        props = fr.properties(rows)
        self.assertEqual((props['count'], props['fav.1.title'], props['fav.1.thumb'], props['fav.1.removable']), ('1', 'A', 't.jpg', 'true'))
        self.assertEqual(props['fav.2.title'], '')
        self.assertEqual(len([k for k in props if k.endswith('.title')]), fr.MAX)

    def test_grid_is_whole_rows_and_the_text_is_the_mockup(self):
        self.assertEqual(fr.MAX % 3, 0)
        self.assertEqual(fr.EMPTY, 'No favourites yet')
        self.assertEqual(fr.FOOT, 'Long-press a poster anywhere and choose Add to Favourites.')
        self.assertEqual(fr.READ, ['path', 'window', 'windowparameter', 'thumbnail'])


class PagesXml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        skin = Path(cls.tmp.name) / 'skin.arctic.fuse.3'
        (skin / '1080i').mkdir(parents=True)
        (skin / 'addon.xml').write_text('<addon id="skin.arctic.fuse.3"><extension point="xbmc.gui.skin">'
                                        '<res aspect="16:9" default="true" folder="1080i" width="1920" height="1080" /></extension></addon>')
        for name, data in {'Font.xml': '<fonts><fontset id="Default" /></fonts>', 'Includes.xml': '<includes />',
                           'Settings.xml': '<window id="10004"><onload>RunScript(script.skinvariables)</onload><controls /></window>',
                           'SettingsCategory.xml': '<window><controls /></window>',
                           'DialogAddonSettings.xml': '<window><controls /></window>'}.items():
            (skin / '1080i' / name).write_text(data)
        profile = Path(cls.tmp.name) / 'profile'
        profile.mkdir()
        portrait.build(skin, profile)
        cls.skin = skin

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def xml(self, name):
        return (self.skin / 'portrait' / name).read_text()

    def root(self, name):
        return ET.fromstring(self.xml(name))

    def test_both_pages_are_well_formed_with_unique_control_ids(self):
        for name in ('IOSProfiles.xml', 'IOSFavourites.xml'):
            ids = [c.get('id') for c in self.root(name).iter('control') if c.get('id')]
            self.assertEqual(len(ids), len(set(ids)), name)

    def test_conditions_use_kodi_brackets(self):
        for name in ('IOSProfiles.xml', 'IOSFavourites.xml'):
            self.assertNotIn('!(', self.xml(name), name)

    def test_profile_buttons_match_the_script(self):
        ids = {c.get('id') for c in self.root('IOSProfiles.xml').iter('control')}
        expected = {str(pr_base) for pr_base in range(9601, 9601 + pr.MAX)} | {'9609', '9001', '9300'}
        self.assertTrue(expected <= ids, expected - ids)
        self.assertIn('ROW_BASE = 9600', profiles_script)
        self.assertIn('ADD = 9609', profiles_script)

    def test_favourite_buttons_match_the_script(self):
        ids = {c.get('id') for c in self.root('IOSFavourites.xml').iter('control')}
        cells = {str(n) for n in range(9701, 9701 + fr.MAX)}
        self.assertTrue(cells | {'9010', '9011', '9001', '9300'} <= ids)
        self.assertIn('CELL_BASE = 9700', favourites_script)
        self.assertIn('EDIT = 9010', favourites_script)
        self.assertIn('DONE = 9011', favourites_script)

    def test_every_window_property_the_xml_reads_is_one_the_script_sets(self):
        # Activity.* properties belong to the activity pill that portrait.build adds to every full page, not to these pages.
        fixed = {'rows', 'editing', 'count'}
        profile_keys = set(pr.properties([]).keys())
        fav_keys = set(fr.properties([]).keys())
        for name, own in (('IOSProfiles.xml', profile_keys), ('IOSFavourites.xml', fav_keys)):
            keys = {k for k in re.findall(r'Property\(([^)]+)\)', self.xml(name)) if k.startswith(('profile.', 'fav.')) or k in fixed}
            self.assertTrue(keys, name)
            for key in keys:
                self.assertTrue(key in fixed or key in own, (name, key))

    def test_profiles_page_has_no_startup_group_and_says_add_profile(self):
        xml = self.xml('IOSProfiles.xml')
        self.assertNotIn("Ask Who", xml)          # not exposed through JSON-RPC (see profiles_rows.py)
        self.assertIn('Add Profile', xml)
        self.assertIn('Profiles', ''.join(t.text or '' for t in self.root('IOSProfiles.xml').iter('label')))

    def test_profiles_footer_and_row_colours_use_the_tokens(self):
        xml = self.xml('IOSProfiles.xml')
        self.assertIn(pr.FOOT, xml)
        self.assertIn(portrait.ACCENT, xml)     # blue text and tick (policy 4.3: text blue is 4FA8FF)
        self.assertNotIn('FF0A84FF', xml)       # the fill blue is not used for text or glyphs here

    def test_favourites_page_has_empty_text_footer_and_edit_only_when_there_are_favourites(self):
        xml = self.xml('IOSFavourites.xml')
        self.assertIn(fr.EMPTY, xml)
        self.assertIn(fr.FOOT, xml)
        root = self.root('IOSFavourites.xml')
        edit = [c for c in root.iter('control') if c.get('id') == '9010'][0]
        self.assertIn('fav.1.title', edit.findtext('visible'))
        done = [c for c in root.iter('control') if c.get('id') == '9011'][0]
        self.assertIn('editing', done.findtext('visible'))
        self.assertEqual(edit.findtext('label'), 'Edit')

    def test_favourite_grid_is_three_across_with_the_poster_mask(self):
        xml = self.xml('IOSFavourites.xml')
        self.assertIn('poster_mask.png', xml)
        self.assertIn('avatar_s.png', xml)      # the remove badge disc

    def test_settings_home_routes_both_rows_to_their_scripts(self):
        settings = self.skin / 'portrait/Settings.xml'
        root = ET.fromstring(settings.read_text())
        clicks = {c.get('id'): [o.text for o in c.findall('onclick')] for c in root.iter('control') if c.get('id')}
        self.assertEqual(clicks['9133'], ['RunScript(service.kodi.ios.bootstrap,profiles_page)'])
        self.assertEqual(clicks['9172'], ['RunScript(service.kodi.ios.bootstrap,favourites_page)'])

    def test_the_pages_are_registered_and_their_scripts_exist(self):
        dispatch = load('default_pf', BOOT / 'default.py')
        for page in ('profiles_page', 'favourites_page'):
            self.assertIn(page, dispatch.PAGES)
            script, argv = dispatch.target(['service.kodi.ios.bootstrap', page])
            self.assertEqual(Path(script), BOOT / (page + '.py'))
            self.assertTrue(Path(script).is_file())

    def test_scripts_read_kodi_through_the_documented_json_rpc_calls(self):
        self.assertIn("'Profiles.GetProfiles'", profiles_script)
        self.assertIn("'Profiles.LoadProfile'", profiles_script)
        self.assertIn("'profile': name, 'prompt': True", profiles_script)
        self.assertIn("System.ProfileName", profiles_script)
        self.assertIn("'Favourites.GetFavourites'", favourites_script)
        self.assertIn("'Favourites.AddFavourite'", favourites_script)
        self.assertIn('fr.READ', favourites_script)
        self.assertIn('ActivateWindow(profiles)', profiles_script)

    def test_portrait_fingerprint_covers_the_rows_modules(self):
        source = (LIB / 'portrait.py').read_text()
        self.assertIn("'profiles_rows.py','favourites_rows.py'", source)


if __name__ == '__main__':
    unittest.main()
