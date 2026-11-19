"""ISSUE-325: Settings › Favourites as the Favourites manager (owner-approved boards K1-K8). Kodi picks one layout for a
whole list (CGUIListItemLayout::CheckCondition has no item), so the page is a column of slots filled from window
properties; every kind the model makes has a drawing; slots never keep a previous page's values; nothing is cut off."""
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path[:0] = [str(BOOT / 'resources/lib'), str(BOOT)]
import favourites_manager_model as model  # noqa: E402
import favourites_manager_page as page  # noqa: E402
import portrait  # noqa: E402

REPORT = {'time': 0, 'list': 'Notes list', 'lines': 56, 'added': 48,
          'duplicates': [{'title': 'darling in the franxx', 'lines': [46, 50]}], 'already': ['Bleach'],
          'questions': [{'entry': {'title': 'one peice', 'line': 64, 'rank': 64},
                         'choices': [{'kind': 'tv', 'tmdb': '37854', 'title': 'One Piece', 'year': '1999', 'popularity': 300},
                                     {'kind': 'movie', 'tmdb': '900667', 'title': 'One Piece Film: Red', 'year': '2022'}]}],
          'missing': [{'title': 'Gurrun lagann', 'line': 13, 'rank': 13}]}
ITEMS = [{'kind': 'tv', 'tmdb': '1', 'title': 'Naruto', 'year': '2002', 'rank': 1, 'list': 'Notes list', 'watched': 0, 'poster': ''}]


class Window(unittest.TestCase):
    def setUp(self):
        self.xml = page.manage(portrait)
        self.root = ET.fromstring(self.xml.split('\n', 1)[1])

    def test_no_per_row_list_layouts(self):
        self.assertNotIn('<itemlayout', self.xml)                     # Kodi would draw every row with the first one
        self.assertNotIn('!(', self.xml)
        self.assertNotIn('…', self.xml)

    def test_every_slot_has_every_kind_and_its_tap(self):
        kinds = [k for k, _, _ in page._parts(portrait)]
        for n in (0, page.SLOTS - 1):
            for kind in kinds:
                self.assertIn('String.IsEqual(Window().Property(r.%d.kind),%s)' % (n, kind), self.xml)
            self.assertIn('id="%d"' % (page.ROW_TAP + n), self.xml)

    def test_every_kind_the_model_makes_is_drawn(self):
        kinds = {k for k, _, _ in page._parts(portrait)}
        pages = [model.landing(ITEMS, ITEMS, REPORT, 1, 'List order'), model.questions_page(REPORT),
                 model.missing_page(REPORT, False), model.duplicates_page(REPORT), model.list_page('Notes list', ITEMS, REPORT)]
        for spec in pages:
            for r in spec['rows']:
                self.assertIn(r['kind'], kinds, (spec.get('title'), r))
            self.assertLessEqual(len(spec['rows']), page.SLOTS)


class Slots(unittest.TestCase):
    def test_a_page_never_keeps_the_last_pages_values(self):
        import favourites_manager as fm
        first = fm.slot_properties([{'kind': 'row', 'label': 'A', 'count': '3', 'action': 'ask'}])
        self.assertEqual((first['r.0.kind'], first['r.0.count']), ('row', '3'))
        before = [k for k, v in first.items() if v]
        second = fm.slot_properties([{'kind': 'header', 'label': 'B'}], before)
        self.assertEqual((second['r.0.kind'], second['r.0.label'], second['r.0.count']), ('header', 'B', ''))
        empty = fm.slot_properties([], before)
        self.assertEqual(empty['r.0.kind'], '')                       # an unused slot hides

    def test_settings_opens_the_manager(self):
        self.assertIn("RunScript(service.kodi.ios.bootstrap,favourites_manager)", (BOOT / 'resources/lib/settings_page.py').read_text())
        self.assertIn("'favourites_manager'", (BOOT / 'default.py').read_text())


class Picker(unittest.TestCase):
    """ISSUE-338 (owner log a42d17d7): Kodi drops buttons inside list cells ("Trying to add unsupported control type 7"),
    and the search closed the picker for the keyboard and rebuilt it."""
    def test_no_button_inside_a_grid_cell(self):
        root = ET.fromstring(page.pick(portrait).split('\n', 1)[1])
        for layout in root.iter():
            if layout.tag in ('itemlayout', 'focusedlayout'):
                self.assertEqual([c.get('type') for c in layout.iter('control') if c.get('type') in ('button', 'edit', 'radiobutton', 'togglebutton')], [])
        best = [c for c in root.iter('control') if c.get('type') == 'label' and 'Property(best)' in (c.findtext('label') or '')]
        self.assertTrue(best and all(int(c.findtext('width')) >= page.BADGE_W for c in best))
    def test_search_stays_on_the_page(self):
        src = (BOOT / 'favourites_manager.py').read_text()
        self.assertIn("elif control == page.SEARCH and self.refresh:", src)
        self.assertIn("self.spec, self.extra = self.refresh(query)", src)
        self.assertIn("answer, choices = show_pick(spec, refresh=build, extra=choices)", src)


class ContinueRow(unittest.TestCase):
    def test_an_entry_without_a_show_title_does_not_stop_the_row(self):
        src = (ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_continue.py').read_text()
        self.assertIn("entry.setdefault('tvshowtitle',entry['title'])", src)
        self.assertIn("episode=entry.get('kind')=='episode'", src)


if __name__ == '__main__':
    unittest.main()
