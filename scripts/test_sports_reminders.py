"""Sports reminders: asked first, one notification per reason, Play replaces Remind me when a source exists."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import sports_reminders as sr  # noqa: E402

NOW = 1_700_000_000
GAME = {'id': 'g1', 'league': 'NFL', 'start': NOW + 2 * 3600, 'joiner': 'at', 'away': {'name': 'Indianapolis Colts'},
        'home': {'name': 'Houston Texans'}, 'sources': []}


class Reminders(unittest.TestCase):
    def test_saved_and_read_back(self):
        with tempfile.TemporaryDirectory() as profile:
            self.assertIsNone(sr.get(profile, 'g1'))
            record = sr.set_reminder(profile, GAME)
            self.assertEqual((record['title'], record['on_source'], record['before']), ('Indianapolis Colts at Houston Texans', True, True))
            self.assertEqual(sr.get(profile, 'g1'), record)
            self.assertIsNone(sr.set_reminder(profile, GAME, on_source=False, before=False))   # both off removes it
            self.assertEqual(sr.load(profile), {})

    def test_a_source_gives_one_notification(self):
        with tempfile.TemporaryDirectory() as profile:
            sr.set_reminder(profile, GAME, before=False)
            games = {'g1': dict(GAME, sources=[{'addon': 'The Loop'}])}
            first = sr.due(sr.load(profile), games, NOW)
            self.assertEqual([(g, k, t, x) for g, k, t, x in first],
                             [('g1', 'source', 'Indianapolis Colts at Houston Texans', 'A source is ready. Tap to play.')])
            sr.sent(profile, 'g1', 'source')
            self.assertEqual(sr.due(sr.load(profile), games, NOW), [])          # never twice
            self.assertEqual(sr.due(sr.load(profile), {'g1': GAME}, NOW), [])   # no source: nothing to say

    def test_fifteen_minutes_before(self):
        with tempfile.TemporaryDirectory() as profile:
            sr.set_reminder(profile, GAME, on_source=False)
            self.assertEqual(sr.due(sr.load(profile), {'g1': GAME}, GAME['start'] - 16 * 60), [])
            got = sr.due(sr.load(profile), {'g1': GAME}, GAME['start'] - 14 * 60)
            self.assertEqual((got[0][1], got[0][3]), ('before', 'Starts in 14 minutes.'))
            self.assertEqual(sr.due(sr.load(profile), {'g1': GAME}, GAME['start'] + 60), [])   # already started

    def test_old_reminders_go_and_search_runs_only_while_waiting(self):
        with tempfile.TemporaryDirectory() as profile:
            sr.set_reminder(profile, GAME)
            self.assertEqual(sr.pending(sr.load(profile)), ['g1'])
            sr.sent(profile, 'g1', 'source')
            self.assertEqual(sr.pending(sr.load(profile)), [])
            self.assertEqual(sr.prune(profile, GAME['start'] + sr.KEEP_AFTER + 1), {})

    def test_the_note_under_reminder_on(self):
        self.assertEqual(sr.summary({'on_source': True, 'before': True}), "We'll notify you when a source is ready, and 15 minutes before it starts.")
        self.assertEqual(sr.summary({'on_source': False, 'before': True}), "We'll notify you 15 minutes before it starts.")
        self.assertEqual(sr.summary({'on_source': True, 'before': False}), "We'll notify you when a source is ready.")
        self.assertEqual(sr.summary(None), '')

class Sheet(unittest.TestCase):
    """The reminder sheet (sports_remind.ask) on the app's choice sheet."""
    def setUp(self):
        sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap'))
        import sports_remind
        self.remind = sports_remind

    def ask(self, profile, answer, flips=()):
        seen = []
        def choose(spec, toggle=None):
            seen.append(spec)
            for index in flips:
                toggle(index)
            return answer
        return self.remind.ask(GAME, profile, choose=choose, now=NOW), seen

    def test_a_new_reminder_is_saved_only_by_turning_it_on(self):
        with tempfile.TemporaryDirectory() as profile:
            got, seen = self.ask(profile, 2, flips=[1])          # the link row after switching "15 minutes before" off
            self.assertEqual((got['on_source'], got['before']), (True, False))
            self.assertEqual(seen[0]['link'], 'Turn on reminder')
            self.assertEqual([r['switch'] for r in seen[0]['rows']], [True, True])      # both start on
            self.assertEqual(sr.get(profile, 'g1')['before'], False)

    def test_cancel_saves_nothing(self):
        with tempfile.TemporaryDirectory() as profile:
            self.assertFalse(self.ask(profile, -1, flips=[0])[0])
            self.assertIsNone(sr.get(profile, 'g1'))

    def test_an_existing_reminder_saves_each_flip_and_can_be_turned_off(self):
        with tempfile.TemporaryDirectory() as profile:
            sr.set_reminder(profile, GAME)
            got, seen = self.ask(profile, -1, flips=[0])         # Done after flipping the first switch off
            self.assertEqual(got['on_source'], False)
            self.assertEqual((seen[0]['link'], seen[0]['button']), ('Turn reminder off', 'Done'))
            self.assertIsNone(self.ask(profile, 2)[0])
            self.assertIsNone(sr.get(profile, 'g1'))

    def test_the_sheet_accepts_the_spec(self):
        import choice_sheet
        props = choice_sheet.properties(self.remind.spec(GAME, None, True, True, 0))
        self.assertEqual((props['switches'], props['row.1.switch'], props['row.2.switch']), ('true', 'on', 'on'))

class SheetWindow(unittest.TestCase):
    """The reminder sheet's own window (owner mockup page 7): properties, which tap answers what, and the XML."""
    def setUp(self):
        sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap'))
        import sports_remind
        import sports_remind_page
        self.remind, self.page = sports_remind, sports_remind_page

    def test_new_reminder_properties_and_wording(self):
        spec = self.remind.spec(GAME, None, True, False, 0, NOW)
        props = self.remind.window_props(spec)
        self.assertEqual((props['mode'], props['row.1.on'], props['row.2.on']), ('new', 'on', 'off'))
        self.assertEqual(props['heading'], 'Remind me about Indianapolis Colts at Houston Texans')
        self.assertEqual(props['row.1.detail'], 'Then Play appears here')
        self.assertRegex(props['row.2.detail'], r'^(Today|Tomorrow|\w{3}, \w{3} \d+) at \d+:\d\d [AP]M$')   # "Today at 5:00 PM"

    def test_the_white_capsule_and_the_text_button_answer_as_before(self):
        page = self.page
        new = self.remind.spec(GAME, None, True, True, 0, NOW)
        self.assertEqual(new['primary'], 'link')
        self.assertEqual((self.remind.answer_for(page.PRIMARY, new), self.remind.answer_for(page.SECONDARY, new)), (2, -1))   # Turn on reminder / Cancel
        old = self.remind.spec(GAME, {'on_source': True, 'before': True}, True, True, 0, NOW)
        self.assertEqual((old['primary'], self.remind.window_props(old)['mode']), ('button', 'existing'))
        self.assertEqual((self.remind.answer_for(page.DONE, old), self.remind.answer_for(page.SECONDARY_OFF, old)), (-1, 2))   # Done / Turn reminder off

    def test_the_xml_is_well_formed_with_unique_ids_and_real_hit_areas(self):
        import re
        import xml.dom.minidom
        sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
        import portrait
        text = self.page.page(portrait)
        xml.dom.minidom.parseString(text.encode())
        ids = re.findall(r'<control type="\w+" id="(\d+)"', text)
        self.assertEqual(len(ids), len(set(ids)))
        for ident in (self.page.ROW1, self.page.ROW2, self.page.PRIMARY, self.page.DONE, self.page.SECONDARY, self.page.SECONDARY_OFF):
            self.assertIn(str(ident), ids)
        for word in ('Turn on reminder', 'Cancel', 'Done', 'Turn reminder off', 'Window().Property(heading)'):
            self.assertIn(word, text)
        self.assertNotIn('!(', text)


class Watcher(unittest.TestCase):
    """The background check: one notification per reason, searches asked sparingly, a tap opens the game."""
    class Provider:
        def __init__(self, games): self.games, self.asked = games, []
        def game(self, gid): return self.games.get(gid)
        def request_game(self, gid): self.asked.append(gid)

    def test_a_source_notifies_once_and_the_tap_opens_the_game(self):
        with tempfile.TemporaryDirectory() as profile:
            sr.set_reminder(profile, GAME, before=False)
            sent = []
            provider = self.Provider({'g1': dict(GAME, sources=[{'addon': 'The Loop'}])})
            self.assertEqual(sr.check(profile, provider, lambda *a: sent.append(a), NOW), 1)
            self.assertEqual(sent, [('Indianapolis Colts at Houston Texans', 'A source is ready. Tap to play.',
                                     'RunScript(service.kodi.ios.bootstrap,sports_game,g1)')])
            self.assertEqual(sr.check(profile, provider, lambda *a: sent.append(a), NOW + 60), 0)   # never twice

    def test_the_source_search_is_asked_at_most_every_ten_minutes(self):
        with tempfile.TemporaryDirectory() as profile:
            sr.set_reminder(profile, GAME, before=False)
            provider, state = self.Provider({'g1': GAME}), {}
            for step in (0, 60, 599, 600, 700):
                sr.check(profile, provider, lambda *a: None, NOW + step, state=state)
            self.assertEqual(provider.asked, ['g1', 'g1'])

    def test_a_failing_provider_or_notification_never_raises(self):
        with tempfile.TemporaryDirectory() as profile:
            sr.set_reminder(profile, GAME, before=False)
            class Broken:
                def game(self, gid): raise OSError('x')
            self.assertEqual(sr.check(profile, Broken(), lambda *a: None, NOW), 0)
            def boom(*a): raise RuntimeError('x')
            self.assertEqual(sr.check(profile, self.Provider({'g1': dict(GAME, sources=[{'addon': 'x'}])}), boom, NOW), 0)
            self.assertFalse(sr.get(profile, 'g1')['told_source'])     # it will try again

    def test_the_service_runs_it_and_the_page_can_be_opened_by_id(self):
        service = (ROOT / 'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('sports_reminders.watch(', service)
        default = (ROOT / 'migration/bundled-bootstrap/default.py').read_text()
        self.assertIn("'sports_game'", default)
        self.assertIn("def main(args):", (ROOT / 'migration/bundled-bootstrap/sports_game.py').read_text())


if __name__ == '__main__':
    unittest.main()
