"""DEC-047 boards B, C and D (docs/design/library-show-mockups.html): the show page as a dialog with its own ••• menu, rows with
stills and titles, Repair that shows at once, and Select with a toolbar (Better Version replaces the old file once the new
one is saved). Host checks of the generated XML and the pure helpers; the desktop Kodi rig and the iPhone are separate."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
LIB = BOOT / 'resources/lib'
sys.dont_write_bytecode = True
sys.path.insert(0, str(LIB))
import portrait  # noqa: E402
import status_ui  # noqa: E402
import library_show_page as show_page  # noqa: E402
import library_select_page as select_page  # noqa: E402
import library_repair  # noqa: E402
import better_version  # noqa: E402
import debrid_drive  # noqa: E402


def manager():
    spec = importlib.util.spec_from_file_location('library_manager_dec047', BOOT / 'library_manager.py')
    lm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lm)
    return lm


class Home:
    def __init__(self):
        self.props = {}

    def getProperty(self, k):
        return self.props.get(k, '')

    def setProperty(self, k, v):
        self.props[k] = v


class ShowPageXml(unittest.TestCase):
    def setUp(self):
        self.xml = show_page.page(portrait)
        self.root = ET.fromstring(self.xml.split('\n', 2)[2])
        self.ids = {c.get('id') for c in self.root.iter('control') if c.get('id')}

    def test_a_dialog_with_its_own_menu(self):
        self.assertEqual(self.root.get('type'), 'dialog')            # nothing behind it is drawn or tapped (board C)
        for n in [show_page.MENU_DIM] + [show_page.MENU + i for i in range(show_page.MENU_ITEMS)]:
            self.assertIn(str(n), self.ids)
        self.assertIn('!String.IsEmpty(Window().Property(menu))', self.xml)
        for ident in (show_page.BACK, show_page.MORE, show_page.SELECT):
            c = next(c for c in self.root.iter('control') if c.get('id') == str(ident))
            self.assertGreaterEqual(int(c.findtext('height')), 118)   # 44 pt touch areas

    def test_rows_have_a_still_a_wrapping_title_and_a_round_repair(self):
        self.assertIn('Window().Property(ep.0.thumb)', self.xml)
        self.assertIn('Window().Property(ep.0.num)', self.xml)
        self.assertIn('<control type="textbox">', self.xml)          # two lines, never "…" (DEC-046/047)
        self.assertIn('arrow-rotate-right.png', self.xml)
        self.assertIn('Window().Property(ep.0.searching)', self.xml)
        self.assertNotIn('<label>Repair</label>', self.xml)          # the big red capsule is gone
        self.assertIn('thumb16.png', status_ui.textures(portrait))


class Rows(unittest.TestCase):
    def test_titles_stills_and_searching(self):
        lm = manager()
        self.assertEqual(lm.searching_keys('31910:1:5;31910:1:6;bad'), {('31910', 1, 5), ('31910', 1, 6)})
        art = {'season:31910:1': {'5': {'title': 'The Kazekage Stands Tall', 'thumb': 'k.jpg'}}}
        self.assertEqual(lm.episode_meta(art, '31910', [1]), {(1, 5): {'title': 'The Kazekage Stands Tall', 'thumb': 'k.jpg'}})
        self.assertEqual(lm.episode_meta(art, '', [1]), {})

    def test_the_menu_entries(self):
        src = (BOOT / 'library_manager.py').read_text()
        for words in ("'Find Missing Episodes'", "'Select Episodes'", "'Delete %s\\u2026'", "'Pick Better Versions'",
                      "'Repair %d Episode%s'"):
            self.assertIn(words, src)
        self.assertIn("if not xbmcgui.Dialog().yesno('Delete %s?' % label", src)   # C2: Delete asks first
        self.assertIn("delete_items(items, ask=False)", src)


class RepairState(unittest.TestCase):
    def test_searching_and_cancel(self):
        home = Home()
        library_repair.mark_searching(home, ['1:1:5', '1:1:6'])
        self.assertEqual(home.getProperty(library_repair.SEARCHING), '1:1:5;1:1:6')
        library_repair.mark_searching(home, ['1:1:5'], add=False)
        self.assertEqual(home.getProperty(library_repair.SEARCHING), '1:1:6')
        home.setProperty(library_repair.CANCEL, '1:1:6')
        self.assertTrue(library_repair.cancelled(home, '1:1:6'))
        library_repair.clear_cancel(home, ['1:1:6'])
        self.assertFalse(library_repair.cancelled(home, '1:1:6'))
        page = (BOOT / 'library_repair_page.py').read_text()
        self.assertIn('library_repair.mark_searching(home, keys(pending), add=True)', page)
        self.assertIn('cancel=lambda: library_repair.cancelled(home, key)', page)


class SelectToolbar(unittest.TestCase):
    def test_toolbar_and_rows(self):
        xml = select_page.page(portrait)
        for ident in (select_page.BETTER, select_page.PREPARE, select_page.TOOL_DELETE, select_page.DELETE, select_page.SEASON):
            self.assertIn('id="%d"' % ident, xml)
        self.assertIn('Window().Property(it.0.thumb)', xml)
        self.assertIn('Window().Property(count)', xml)
        src = (BOOT / 'library_manager.py').read_text()
        self.assertIn('better_version.remember(profile,', src)
        self.assertIn("prepare_downloads.request(profile, 'retry', item['id'])", src)


class BetterVersion(unittest.TestCase):
    def test_the_old_file_goes_once_the_new_one_is_saved(self):
        with tempfile.TemporaryDirectory() as profile:
            better_version.remember(profile, [('31910', 1, 3, 'old3', 'E3.mkv')])
            job = {'show_tmdb': '31910', 'season': 1, 'episode': 3, 'files': [{'drive_id': 'new3'}]}
            self.assertTrue(better_version.replacing(profile, job))
            self.assertFalse(better_version.replacing(profile, dict(job, episode=4)))
            trashed, forgotten = [], []
            self.assertEqual(better_version.finished(profile, job, trashed.append, forgotten.extend), ['old3'])
            self.assertEqual((trashed, forgotten), (['old3'], ['old3']))
            self.assertFalse(better_version.replacing(profile, job))

    def test_lifecycle(self):
        import time
        with tempfile.TemporaryDirectory() as profile:
            better_version.remember(profile, [('9', 1, 2, 'old', 'x')])
            job = {'show_tmdb': '9', 'season': 1, 'episode': 2, 'files': [{'drive_id': 'old'}]}
            self.assertEqual(better_version.finished(profile, job, lambda i: None), [])      # the same file: nothing goes
            trashed = []
            job['files'] = [{'drive_id': 'new'}]
            self.assertEqual(better_version.finished(profile, job, trashed.append), ['old'])
            self.assertEqual((trashed, better_version.load(profile)), (['old'], {}))
            better_version.remember(profile, [('9', 1, 2, 'old', 'x')], now=time.time() - 8 * 86400)
            self.assertEqual(better_version.load(profile), {})                               # forgotten after a week

    def test_the_copier_keeps_a_replacement_waiting(self):
        job = {'kind': 'episode', 'status': 'waiting', 'title': 'Naruto Shippuuden', 'season': 1, 'episode': 3, 'files': [], 'hash': 'h3'}
        state = {'jobs': [job]}
        on_drive = {(debrid_drive.show_match('Naruto Shippuuden'), 1, 3)}
        self.assertEqual(len(debrid_drive.drop_on_drive({'jobs': [dict(job)]}, on_drive)), 1)   # build 325's rule stands
        self.assertEqual(debrid_drive.drop_on_drive(state, on_drive, keep=lambda j: True), [])
        self.assertEqual(state['jobs'], [job])
        service = (BOOT / 'service.py').read_text()
        self.assertIn('better_version.finished(profile,job,', service)


class VersionPickerFocus(unittest.TestCase):
    def test_the_picker_opens_on_back_and_focuses_its_list_once_filled(self):
        # ISSUE-248: "Control 32503 in window 13002 has been asked to focus, but it can't" in every log.
        src = (LIB / 'portrait.py').read_text()
        self.assertIn('<defaultcontrol always="true">32500</defaultcontrol>', src)
        self.assertNotIn('<defaultcontrol always="true">32503</defaultcontrol>', src)
        self.assertIn('self.setFocusId(self.list_id())', (ROOT / 'migration/deck-picker/deck_picker.py').read_text())


if __name__ == '__main__':
    unittest.main()
