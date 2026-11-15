"""Runs the Favourites import flow, the Favourites page and the bell sheet end to end against fake Kodi modules (no rig here).
Covers what the pure tests cannot: the screens' sequence, what each tap does, and that nothing raises."""
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path[:0] = [str(BOOT / 'resources/lib'), str(BOOT), str(ROOT / 'scripts')]
import favourites_import as fi
import favourites_match as fm

LIST = """✅=Complete
1. Naruto\U0001f3a5//shippuden✅
2. bleach (2) ✅ ‼️
3. aot (3)✅  RYANNE
4. one peice
5. darling in the franxx
6. darling in the franxx
7. zzzz
"""

TABLE = {
    'naruto': [{'media_type': 'tv', 'id': 1, 'name': 'Naruto', 'first_air_date': '2002-10-03', 'popularity': 90}],
    'naruto shippuden': [{'media_type': 'tv', 'id': 2, 'name': 'Naruto Shippuden', 'first_air_date': '2007-02-15', 'popularity': 95}],
    'bleach': [{'media_type': 'tv', 'id': 3, 'name': 'Bleach', 'first_air_date': '2004-10-05', 'popularity': 80}],
    'aot': [{'media_type': 'tv', 'id': 4, 'name': 'Attack on Titan', 'first_air_date': '2013-04-07', 'popularity': 200}],
    'one peice': [{'media_type': 'tv', 'id': 5, 'name': 'One Piece', 'first_air_date': '1999-10-20', 'popularity': 300},
                  {'media_type': 'movie', 'id': 6, 'title': 'One Piece Film: Red', 'release_date': '2022-08-06', 'popularity': 50}],
    'darling in the franxx': [{'media_type': 'tv', 'id': 7, 'name': 'Darling in the Franxx', 'first_air_date': '2018-01-13', 'popularity': 60}],
}


class Dialog:
    def __init__(self):
        self.shown, self.text = [], []
        self.typed = LIST

    def input(self, *a, **k):
        return self.typed

    def ok(self, *a):
        self.shown.append(('ok',) + a)

    def textviewer(self, title, text):
        self.text.append((title, text))

    def notification(self, title, text, *a):
        self.shown.append(('notification', title, text))

    def yesno(self, *a, **k):
        return True


class Progress:
    def create(self, *a): pass
    def update(self, *a): pass
    def close(self): pass
    def iscanceled(self): return False


def fake_modules(sheet):
    """xbmc / xbmcgui / xbmcvfs stand-ins; `sheet(spec)` answers every choice sheet."""
    dialog = Dialog()
    xbmc = types.SimpleNamespace(LOGINFO=1, LOGWARNING=2, log=lambda *a: None, executed=[],
                                 executebuiltin=lambda cmd: xbmc.executed.append(cmd))
    gui = types.SimpleNamespace(Dialog=lambda: dialog, DialogProgress=Progress, INPUT_ALPHANUM=0, NOTIFICATION_INFO='info',
                                ListItem=lambda label='', label2='': (label, label2))
    return xbmc, gui, dialog


class Flow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.profile = self.tmp.name + '/'
        spec = importlib.util.spec_from_file_location('favourites_import_page', BOOT / 'favourites_import_page.py')
        self.page = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.page)
        self.sheets = []
        self.answers = []
        self.page.pick = lambda gui, spec: (self.sheets.append(spec), self.answers.pop(0) if self.answers else -1)[1]
        self.page.tmdb_search = lambda key: (lambda q: TABLE.get(fm.norm(q), []))
        key = types.SimpleNamespace(tmdb_key=lambda: 'key')
        patcher = patch.dict(sys.modules, {'source_match': key})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_import(self):
        xbmc, gui, dialog = fake_modules(None)
        self.dialog = dialog
        return self.page.run_import(xbmc, gui, self.profile)

    def test_paste_match_save_and_report(self):
        """Owner (2026-11-15): the report never opens by itself: a notice, and the report is saved for Last import."""
        self.answers = [0]                           # source: Paste a list
        added = self.run_import()
        items = fi.load(self.profile)['items']
        self.assertEqual(added, len(items))
        names = [i['title'] for i in items]
        self.assertEqual(names[:3], ['Naruto', 'Naruto Shippuden', 'Bleach'])          # list order is rank
        self.assertEqual([i['rank'] for i in items][:3], [1, 2, 3])
        self.assertIn('Attack on Titan', names)
        self.assertEqual({i['title']: i['watched'] for i in items}['Bleach'], 2)
        self.assertEqual({i['title']: i['watched'] for i in items}['Attack on Titan'], 3)
        self.assertNotIn('RYANNE', ' '.join(names))
        self.assertEqual(len(self.sheets), 1)                                          # no report sheet popped up
        import notices                                                                   # mockup N: a Notifications message
        message = notices.load(self.profile)[0]
        self.assertEqual((message['title'], message['action'], message['kind']), ('Import finished', 'import_report', 'general'))
        self.assertEqual(message['text'], '%d added to Favourites from %s \u00b7 2 need a look' % (added, fi.load_report(self.profile)['list']))
        self.assertFalse([x for x in self.dialog.shown if x[0] == 'notification'])     # no pop-up
        report = fi.load_report(self.profile)
        self.assertEqual([d['lines'] for d in report['duplicates']], [[5, 6]])
        self.assertEqual([q['entry']['title'] for q in report['questions']], ['one peice'])   # the show or the film: asked
        self.assertEqual([m['title'] for m in report['missing']], ['zzzz'])
        props = fi.report_properties(report)
        self.assertEqual((props['dup.title'], props['ask.title'], props['miss.title']),
                         ('Duplicates \u00b7 1', 'Needs your answer \u00b7 1', 'Not found \u00b7 1'))
        self.assertEqual((props['dup.pos'], props['ask.pos'], props['miss.pos']), ('first', 'mid', 'last'))
        self.assertIn('darling in the franxx (lines 5 and 6)', props['dup.text'])   # the list's own spelling

    def test_last_import_opens_the_report_page_and_its_groups_act(self):
        self.answers = [0]
        self.run_import()
        self.sheets.clear()
        # The Import sheet now has a third row, Last import; choosing it opens the report page (a window).
        clicks = []
        page = self.page
        import favourites_report_page as rp

        class Window:
            def __init__(self, *a):
                self.props = {}
            def setProperty(self, k, v):
                self.props[k] = v
            def close(self):
                clicks.append('closed')
            def doModal(self):
                self.onInit()
                for control in (rp.DUP, rp.ASK, rp.MISS, rp.DONE):
                    self.onClick(control)
                clicks.append(dict(self.props))
        xbmc, gui, dialog = fake_modules(None)
        gui.WindowXMLDialog = Window
        self.answers = [2, 0]                       # Import sheet: Last import; the question: One Piece
        dialog.typed = 'zzzz'                        # Not found: searched again as written, still nothing
        page.run_import(xbmc, gui, self.profile)
        first = self.sheets[0]
        self.assertEqual(first['rows'][2]['label'], 'Last import')
        self.assertEqual(first['rows'][2]['tag'], '2 to check')
        self.assertIn('One Piece', [i['title'] for i in fi.load(self.profile)['items']])
        self.assertEqual([t for t, _ in dialog.text], ['Duplicates'])
        self.assertIn('Nothing was found', ' '.join(str(x) for x in dialog.shown))
        report = fi.load_report(self.profile)
        self.assertEqual(report['questions'], [])                                       # answered: it leaves the report
        self.assertEqual([m['title'] for m in report['missing']], ['zzzz'])            # still there for later
        final = [c for c in clicks if isinstance(c, dict)][-1]
        self.assertEqual(final['ask.title'], '')
        self.assertEqual(final['miss.pos'], 'last')

    def test_no_import_yet_shows_no_last_import_row(self):
        self.answers = [-1]
        self.run_import()
        self.assertEqual([r['label'] for r in self.sheets[0]['rows']], ['Paste a list', 'Choose a text file'])
        self.assertEqual(fi.report_properties(None)['empty'], 'No list imported yet')

    def test_long_groups_end_with_and_n_more_never_a_cut_name(self):
        names = ['Title number %d' % n for n in range(40)]
        text = fi.listed(names)
        self.assertTrue(text.endswith(' more'))
        self.assertLessEqual(len(text), fi.REPORT_CHARS + 12)
        for part in text.rsplit(' and ', 1)[0].split(', '):
            self.assertIn(part, names)

    def test_cancel_at_the_first_sheet_changes_nothing(self):
        self.answers = [-1]
        self.assertEqual(self.run_import(), 0)
        self.assertEqual(fi.load(self.profile)['items'], [])

    def test_no_tmdb_helper_is_said_plainly(self):
        with patch.dict(sys.modules, {'source_match': types.SimpleNamespace(tmdb_key=lambda: '')}):
            self.assertEqual(self.run_import(), 0)
        self.assertIn('TMDb Helper is needed', self.dialog.shown[0][2])

    def test_an_empty_paste_adds_nothing(self):
        self.answers = [0]
        xbmc, gui, dialog = fake_modules(None)
        dialog.typed = ''
        self.assertEqual(self.page.run_import(xbmc, gui, self.profile), 0)

    def test_opening_a_started_movie_asks_continue_and_a_show_opens_its_page(self):
        import favourites_rows as fr
        xbmc, gui, dialog = fake_modules(None)
        store = Path(self.tmp.name) / 'continue.json'
        store.write_text(json.dumps({'items': {'movie:6::': {'position': 4360, 'total': 8880}}}))
        vfs = types.SimpleNamespace(translatePath=lambda p: str(store))
        movie = fr.imported_entry({'kind': 'movie', 'tmdb': '6', 'title': 'Inception'})
        self.answers = [0]
        self.page.open_item(xbmc, gui, vfs, movie)
        self.assertEqual(self.sheets[-1]['sub'], 'Stopped at 1:12:40 of 2:28:00')
        self.assertIn('ios_continue=1', xbmc.executed[-1])
        self.answers = [1]
        self.page.open_item(xbmc, gui, vfs, movie)
        self.assertNotIn('ios_continue', xbmc.executed[-1])
        self.answers = [-1]
        before = len(xbmc.executed)
        self.page.open_item(xbmc, gui, vfs, movie)
        self.assertEqual(len(xbmc.executed), before)                   # Cancel plays nothing
        show = fr.imported_entry({'kind': 'tv', 'tmdb': '1', 'title': 'Naruto'})
        self.page.open_item(xbmc, gui, vfs, show)
        self.assertIn('info=seasons', xbmc.executed[-1])
        fresh = fr.imported_entry({'kind': 'movie', 'tmdb': '99', 'title': 'New'})
        self.page.open_item(xbmc, gui, vfs, fresh)
        self.assertIn('info=play&tmdb_type=movie&tmdb_id=99', xbmc.executed[-1])
        self.assertEqual(len(self.sheets), 3)                          # a movie that was not started goes straight to the chooser

    def test_a_finished_movie_is_not_offered_continue(self):
        store = Path(self.tmp.name) / 'continue.json'
        store.write_text(json.dumps({'items': {'movie:6::': {'position': 8700, 'total': 8880}}}))
        vfs = types.SimpleNamespace(translatePath=lambda p: str(store))
        self.assertIsNone(self.page.movie_progress(vfs, '6'))
        self.assertIsNone(self.page.movie_progress(types.SimpleNamespace(translatePath=lambda p: '/nope'), '6'))


class Bell(unittest.TestCase):
    def test_the_sheet_flips_a_switch_per_tap_and_stops_on_cancel(self):
        import anticipated as bell
        import episode_watch
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        info = {'season': 5, 'episode': 1, 'date': '2026-11-21'}
        state = bell.flip(tmp.name, '99', 'Show', 'alert', info)
        self.assertTrue(state['alert'])
        self.assertEqual([r['switch'] for r in bell.rows(state)], [True, False])      # G3: real switches, not On/Off tags
        state = bell.flip(tmp.name, '99', 'Show', 'auto', info, preference={'quality': '1080p'})
        self.assertEqual([r['switch'] for r in bell.rows(state)], [True, True])
        self.assertTrue(episode_watch.option(tmp.name, '99', 'auto'))

    def test_the_service_sets_and_clears_the_bell_properties(self):
        import anticipated as bell
        props, labels = {}, {'Container(50).ListItem.Property(tvshow.tmdb_id)': '99', 'Container.Content': 'seasons'}
        window = types.SimpleNamespace(setProperty=lambda k, v: props.update({k: v}), clearProperty=lambda k: props.pop(k, None))
        turns = iter([False, False, False, True])

        def wait(_):
            n = next(turns)
            if n is False and len(props) and labels['Container.Content'] == 'seasons' and 'later' not in labels:
                labels['later'] = True
                labels['Container.Content'] = 'episodes'      # the person left the seasons view
            return n
        monitor = types.SimpleNamespace(waitForAbort=wait)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        future = {'next_episode_to_air': {'season_number': 5, 'episode_number': 1, 'air_date': '2999-01-01'}}
        with patch.object(bell.Lookup, '_fetch', lambda self, tmdb: future):
            bell.bell_service(monitor, tmp.name, window, lambda k: labels.get(k, ''), lambda: 'key')
        self.assertNotIn(bell.PROP_TMDB, props)                  # left the page: bell hidden again
        self.assertEqual(props, {})

    def test_a_lookup_failure_only_hides_the_bell(self):
        import anticipated as bell
        props = {}
        window = types.SimpleNamespace(setProperty=lambda k, v: props.update({k: v}), clearProperty=lambda k: props.pop(k, None))
        _turns = iter([False, True])
        monitor = types.SimpleNamespace(waitForAbort=lambda _: next(_turns))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)

        def broken(self, tmdb):
            raise OSError('offline')
        with patch.object(bell.Lookup, '_fetch', broken):
            bell.bell_service(monitor, tmp.name, window, lambda k: {'Container(50).ListItem.Property(tvshow.tmdb_id)': '99', 'Container.Content': 'seasons'}.get(k, ''), lambda: 'key')
        self.assertEqual(props, {})



class ImportNotice(unittest.TestCase):
    """Mockup N (owner-approved 2026-11-15): the message shows a star and Review, and opens the report page."""

    def test_the_message_has_a_star_review_and_opens_the_report(self):
        import time
        sys.modules.setdefault('xbmc', types.SimpleNamespace())
        import notifications
        item = {'id': '1', 'time': time.time(), 'kind': 'general', 'title': 'Import finished',
                'text': '48 added to Favourites from Notes list \u00b7 5 need a look', 'action': 'import_report'}
        props, shown = notifications.message_properties([item], 'all')
        self.assertEqual((props['msg.1.icon'], props['msg.1.fix']), ('star.png', 'Review'))
        quiet = dict(item, text='48 added to Favourites from Notes list')
        props, _ = notifications.message_properties([quiet], 'all')
        self.assertEqual(props['msg.1.fix'], '')                                     # nothing to check: no Review
        source = (BOOT / 'notifications.py').read_text()
        self.assertIn("RunScript(service.kodi.ios.bootstrap,favourites_import_page,report)", source)
        self.assertIn("'report' in sys.argv[1:]", (BOOT / 'favourites_import_page.py').read_text())


if __name__ == '__main__':
    unittest.main()
