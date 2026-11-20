"""Subtitles drawer (owner, 2026-11-16; docs/design/subtitles-manage-mockups.html): hold a track to find another or remove it.

Rows and wording come from track_menu; the flows run the real tracks.py controller against a fake Kodi."""
import json
import os
import sys
import tempfile
import time
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
LIB = BOOT / 'resources/lib'
sys.dont_write_bytecode = True
sys.path[:0] = [str(BOOT), str(LIB)]
import pages  # noqa: E402
import track_menu as tm  # noqa: E402
import tracks  # noqa: E402


def streams(extra=()):
    return [{'index': 0, 'language': 'eng', 'name': 'English'}, {'index': 1, 'language': 'spa', 'name': 'Spanish'}, *extra]


class Rows(unittest.TestCase):
    def rows(self, subs=None, removable=()):
        subs = [dict(s, removable=s['index'] in removable) for s in subs or streams()]
        return tm.subtitle_rows(subs, 0, True)

    def test_off_has_no_menu_a_file_track_only_finds_another_and_an_added_one_can_be_removed(self):
        rows = self.rows(removable=(0,))
        self.assertIsNone(tm.hold_options(rows[0]))
        self.assertEqual(tm.hold_options(rows[1]), ('Find another English', 'Remove from this video'))
        self.assertEqual(tm.hold_options(rows[2]), ('Find another Spanish', ''))

    def test_release_names_are_shortened_to_words_that_fit_two_lines(self):
        self.assertEqual(tm.release_label('Title.of.the.Film.2019.1080p.BluRay.x264-GROUP'), 'Title of the Film 2019 1080p')
        self.assertEqual(tm.release_label('Title of the Film (2019) 720p'), 'Title of the Film (2019) 720p')
        self.assertLessEqual(len(tm.release_label('The.Extremely.Long.Documentary.Title.Part.Two.2021.2160p.UHD.BluRay.REMUX')), 34)
        self.assertEqual(tm.release_label(''), '')
        xml = pages.track_menu()
        self.assertGreaterEqual(xml.count('<wrapmultiline>true</wrapmultiline>'), 4)   # every track label may take a second line

    def test_a_track_the_file_holds_no_subtitles_for_is_refused_unless_forced(self):
        import subtitle_match as sm
        ranked = sm.rank([{'index': 0, 'language': 'eng', 'name': '', 'sample_count': 0}, {'index': 1, 'language': 'eng', 'name': '', 'sample_count': 900},
                          {'index': 2, 'language': 'eng', 'name': '', 'sample_count': 1, 'isforced': True}], {'duration': 3000})
        by = {t['index']: t for t in ranked}
        self.assertTrue(by[0]['match_rejected']);self.assertEqual(by[0]['match_reason'], 'Empty subtitle track')
        self.assertFalse(by[1]['match_rejected']);self.assertFalse(by[2]['match_rejected'])

    def test_remove_is_red(self):
        self.assertTrue(tm.more_rows(0, False, '', 'English', True)[2]['danger'])
        self.assertIn('FFFF453A', pages.track_menu())

    def test_the_question_names_the_track(self):
        title, text = tm.sure_text(self.rows()[1])
        self.assertEqual(title, 'Remove this subtitle?')
        self.assertIn('English will be removed from this video', text)

    def test_more_offers_remove_only_for_a_removable_current_track(self):
        plain = [r['index'] for r in tm.more_rows(0, False, '', 'English', False)]
        removable = tm.more_rows(2, False, '', 'English', True)
        self.assertEqual(plain, ['choose', 'file', 'always', 'keys'])
        self.assertEqual([r['index'] for r in removable], ['choose', 'file', 'remove', 'always', 'keys'])
        self.assertEqual((removable[0]['label'], removable[2]['label']), ('Find another English', 'Remove English from this video'))

    def test_drawer_controls_are_unique_and_shared_with_the_controller(self):
        root = ET.fromstring(pages.track_menu().split('\n', 2)[2])
        ids = [c.get('id') for c in root.iter('control') if c.get('id')]
        self.assertEqual(len(ids), len(set(ids)))
        for name in ('SUBS_LIST', 'T_MINUS_S', 'T_PLUS_S', 'HOLD_FIND', 'HOLD_REMOVE', 'HOLD_SCRIM', 'SURE_SCRIM', 'SURE_CANCEL', 'SURE_REMOVE'):
            self.assertEqual(getattr(tracks, name), getattr(pages, name), name)
            self.assertIn(str(getattr(pages, name)), ids)
        self.assertEqual(tracks.SUBS_ROWS, pages.SUBS_ROWS)

    def test_the_drawer_is_full_height_at_the_right_edge_with_no_cut_text(self):
        xml = pages.track_menu()
        self.assertIn('end="40,-172" time="0" condition="String.IsEqual(Window().Property(mode),subtitles)"', xml)
        self.assertIn('Timing and more', xml)
        self.assertIn('<wrapmultiline>true</wrapmultiline>', xml)   # the removal question wraps


class Fake:
    """A Kodi that has one video with two subtitle tracks and a search that finds two other subtitles."""

    def __init__(self, folder):
        self.folder, self.props, self.calls, self.notes = folder, {}, [], []
        self.subs = streams()
        self.current, self.enabled = 0, True
        self.item = {'title': 'Film', 'year': 2019, 'file': 'Film.2019.1080p.mkv', 'uniqueid': {}}

    def rpc(self, text):
        request = json.loads(text)
        method, params = request['method'], request.get('params') or {}
        self.calls.append((method, params))
        result = None
        if method == 'Player.GetActivePlayers':
            result = [{'playerid': 1, 'type': 'video'}]
        elif method == 'Player.GetProperties':
            result = {'subtitles': list(self.subs), 'currentsubtitle': {'index': self.current}, 'subtitleenabled': self.enabled,
                      'audiostreams': [], 'currentaudiostream': {}}
        elif method == 'Player.GetItem':
            result = {'item': dict(self.item)}
        elif method == 'Player.SetSubtitle':
            self.enabled = params.get('subtitle') != 'off'
            self.current = params['subtitle'] if self.enabled else None
            if self.enabled:
                self.current = params['subtitle']
        elif method == 'Settings.GetSettingValue':
            result = {'value': 'default' if 'locale' in params.get('setting', '') else ['English']}
        return json.dumps({'jsonrpc': '2.0', 'id': 1, 'result': result})


HOME_PROPS = {}
FIND_CALLS = []


def drive(scenario, fake, found=2):
    """Run tracks.run('subtitles') against the fake; `scenario(menu)` is the user's touches. Returns the notifications."""
    windows = []

    class Window:
        def __init__(self, *args):
            self.props, self.focus, self.items, self.controls = {}, None, [], {}
            windows.append(self)

        def setProperty(self, key, value):
            self.props[key] = value

        def getProperty(self, key):
            return self.props.get(key, '')

        def setFocusId(self, ident):
            self.focus = ident

        def getFocusId(self):
            return self.focus

        def getControl(self, ident):
            return self.controls.setdefault(ident, Lst(self))

        def close(self):
            self.closed = True

        def doModal(self):
            self.onInit()
            scenario(self)

    class Lst:
        def __init__(self, window):
            self.window, self.items, self.pos = window, [], 0

        def reset(self):
            self.items = []

        def addItems(self, items):
            self.items = list(items)

        def selectItem(self, n):
            self.pos = n

        def getSelectedPosition(self):
            return self.pos

    class Item:
        def __init__(self, label):
            self.label, self.p = label, {}

        def setProperty(self, k, v):
            self.p[k] = v

    notes = []
    xbmc = types.SimpleNamespace(
        log=lambda *a: None, LOGINFO=1, ISO_639_1=1, executeJSONRPC=fake.rpc, executebuiltin=lambda *a: None, sleep=lambda ms: None,
        getInfoLabel=lambda key: '', convertLanguage=lambda name, kind: {'spa': 'es', 'eng': 'en', 'English': 'en'}.get(name, ''),
        Player=lambda: types.SimpleNamespace(getTotalTime=lambda: 7200, setSubtitles=lambda path: None))
    gui = types.SimpleNamespace(
        WindowXMLDialog=Window, ListItem=Item, NOTIFICATION_INFO=1,
        Window=lambda ident: types.SimpleNamespace(setProperty=lambda *a: None, clearProperty=lambda *a: None, getProperty=lambda k: HOME_PROPS.get(k, '')),
        Dialog=lambda: types.SimpleNamespace(notification=lambda title, *a: notes.append(title)))
    vfs = types.SimpleNamespace(translatePath=lambda path: fake.folder + os.sep)
    results = [{'id': str(n), 'releases': ['Film.2019.rel%d' % n], 'impaired': False, 'match_reason': '', 'match_rejected': False} for n in range(found)]
    with patch.dict(sys.modules, xbmc=xbmc, xbmcgui=gui, xbmcvfs=vfs), \
            patch.object(tracks, 'player_id', return_value=1), \
            patch.object(tracks, 'subtitle_language', return_value=('en', 'English')), \
            patch.object(tracks, 'keys_tag', return_value='SET'), \
            patch('subtitle_sources.find', side_effect=lambda *a, **k: (FIND_CALLS.append(a), list(results) if found else [])[1]), \
            patch('subtitle_sources.load_keys', return_value={}), \
            patch('subtitle_sources.sources', return_value=['subdl']):
        tracks.run('subtitles')
    return notes, windows[0]


class Flows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fake = Fake(self.tmp.name)

    def action(self, code):
        return types.SimpleNamespace(getId=lambda: code)

    def hold(self, menu, n):
        menu.focus = tracks.SUBS_LIST
        menu.getControl(tracks.SUBS_LIST).pos = n
        menu.onAction(self.action(117))
        menu.menu_done = 0   # the next press is a new one

    def test_holding_a_track_opens_its_menu_and_never_closes_the_drawer(self):
        seen = {}

        def scenario(menu):
            self.assertEqual(menu.props['rows'], '3')   # Off and two tracks
            menu.focus = tracks.SUBS_LIST
            menu.getControl(tracks.SUBS_LIST).pos = 2
            menu.onAction(self.action(10))     # iOS sends a long press as Back first ...
            menu.onAction(self.action(117))    # ... then as the context menu
            seen.update(menu.props)
            self.assertFalse(getattr(menu, 'closed', False))
        drive(scenario, self.fake)
        self.assertEqual((seen['ctx'], seen['ctx.find'], seen['ctx.remove'], seen['ctx.row']), ('1', 'Find another Spanish', '', '2'))

    def test_off_has_no_menu(self):
        def scenario(menu):
            self.hold(menu, 0)
            self.assertEqual(menu.props.get('ctx', ''), '')
        drive(scenario, self.fake)

    def test_a_downloaded_track_is_removed_after_asking_and_its_file_is_deleted(self):
        path = os.path.join(self.tmp.name, '123.en.srt')
        Path(path).write_text('1\n')

        def scenario(menu):
            menu.added.add(0)
            menu.paths[0] = path
            menu.fill()
            self.hold(menu, 1)
            self.assertEqual(menu.props['ctx.remove'], 'Remove from this video')
            menu.onClick(tracks.HOLD_REMOVE)
            self.assertEqual((menu.props['ctx'], menu.props['sure.title']), ('sure', 'Remove this subtitle?'))
            menu.onClick(tracks.SURE_REMOVE)
            self.assertEqual(menu.props['ctx'], '')
            self.assertEqual([r['label'] for r in menu.rows], ['Off', 'Spanish'])
        notes, _ = drive(scenario, self.fake)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(notes, ['English removed'])
        self.assertIn(('Player.SetSubtitle', {'playerid': 1, 'subtitle': 'off'}), self.fake.calls)   # it was on

    def test_a_downloaded_subtitle_survives_closing_and_reopening_the_menu(self):
        # Build 617 log: the downloaded track ("<crc> (External)") was forgotten on the next open, the embedded CC outranked it and the menu
        # switched Kodi to the CC (turning the download off). A fresh menu must keep it on and offer it for English.
        self.fake.subs = [{'index': 0, 'language': 'eng', 'name': ''}, {'index': 1, 'language': 'eng', 'name': '', 'isimpaired': True},
                          {'index': 3, 'language': 'eng', 'name': '4168484231 (External)'}]
        self.fake.current = 3

        def scenario(menu):
            english = [r for r in menu.rows if r['label'].startswith('English')]
            self.assertEqual([r['index'] for r in english], [3])
            self.assertTrue(english[0]['on'])
        drive(scenario, self.fake)
        self.assertEqual([c for c in self.fake.calls if c[0] == 'Player.SetSubtitle'], [])   # opening the menu changed nothing
        self.assertEqual(self.fake.current, 3)

    def test_turning_it_off_and_on_again_selects_the_download_not_the_embedded_cc(self):
        self.fake.subs = [{'index': 0, 'language': 'eng', 'name': ''}, {'index': 1, 'language': 'eng', 'name': '', 'isimpaired': True},
                          {'index': 3, 'language': 'eng', 'name': '4168484231 (External)'}]
        self.fake.current = 3

        def scenario(menu):
            menu.pick(0)            # Off
            self.assertFalse(self.fake.enabled)
            menu.fill()
            menu.pick(next(n for n, r in enumerate(menu.rows) if r['label'].startswith('English')))
        drive(scenario, self.fake)
        self.assertTrue(self.fake.enabled)
        self.assertEqual(self.fake.current, 3)

    def test_an_embedded_track_with_no_subtitles_in_it_is_not_offered(self):
        self.fake.subs = [{'index': 0, 'language': 'eng', 'name': ''}, {'index': 1, 'language': 'spa', 'name': ''}]
        self.fake.current = 1

        def scenario(menu):
            menu.file_tracks = [{'samples': 0}, {'samples': 800}]
            menu.fill()
            self.assertEqual([r['label'] for r in menu.rows], ['Off', 'Spanish'])
        drive(scenario, self.fake)

    def test_the_search_uses_what_the_playing_add_on_knew_when_kodis_item_lacks_it(self):
        # Build 618 log: a Drive episode searched as 'Trust Fall' with season and episode None, SubDL found 0.
        import json as _json
        self.fake.item = {'title': 'Trust Fall', 'file': 'http://127.0.0.1:50465/x', 'uniqueid': {}}
        HOME_PROPS['KodiIOS.Playing'] = _json.dumps({'t': time.time(), 'kind': 'episode', 'title': 'Trust Fall', 'show': 'Some Show', 'season': 1, 'episode': 2, 'year': 2021, 'tmdb': '95350'})
        FIND_CALLS.clear()
        self.addCleanup(HOME_PROPS.clear)

        def scenario(menu):
            menu.search()
        drive(scenario, self.fake)
        title, year, season, episode, tmdb = FIND_CALLS[0][3], FIND_CALLS[0][4], FIND_CALLS[0][5], FIND_CALLS[0][6], FIND_CALLS[0][8]
        self.assertEqual((title, season, episode, tmdb), ('Some Show', 1, 2, '95350'))

    def test_a_stale_or_different_video_is_not_used(self):
        import json as _json
        self.fake.item = {'title': 'Another Film', 'year': 2019, 'file': 'Another.Film.2019.mkv', 'uniqueid': {}}
        HOME_PROPS['KodiIOS.Playing'] = _json.dumps({'t': time.time(), 'kind': 'episode', 'title': 'Trust Fall', 'show': 'Some Show', 'season': 1, 'episode': 2, 'tmdb': '95350'})
        FIND_CALLS.clear()
        self.addCleanup(HOME_PROPS.clear)
        drive(lambda menu: menu.search(), self.fake)
        self.assertEqual((FIND_CALLS[0][3], FIND_CALLS[0][5], FIND_CALLS[0][8]), ('Another Film', None, None))

    def test_cancel_removes_nothing(self):
        def scenario(menu):
            menu.added.add(0)
            menu.fill()
            self.hold(menu, 1)
            menu.onClick(tracks.HOLD_REMOVE)
            menu.onClick(tracks.SURE_CANCEL)
            self.assertEqual(menu.props['ctx'], '')
            self.assertEqual(len(menu.rows), 3)
        notes, _ = drive(scenario, self.fake)
        self.assertEqual(notes, [])

    def test_a_track_inside_the_video_file_cannot_be_removed(self):
        def scenario(menu):
            self.hold(menu, 1)
            self.assertEqual(menu.props['ctx.remove'], '')
            menu.onClick(tracks.HOLD_REMOVE)   # a stale tap does not ask
            self.assertNotEqual(menu.props['ctx'], 'sure')
        drive(scenario, self.fake)

    def test_find_another_searches_that_tracks_language_and_keeps_the_current_one(self):
        searched = []

        def scenario(menu):
            self.hold(menu, 2)
            with patch('subtitle_sources.find', side_effect=lambda get, keys, language, *a, **k: searched.append(language) or [
                    {'id': '9', 'releases': ['Film.2019.spanish'], 'impaired': False, 'match_reason': '', 'match_rejected': False}]):
                menu.onClick(tracks.HOLD_FIND)
                for _ in range(100):
                    if menu.props.get('page') == 'choose':
                        break
                    time.sleep(0.02)
            self.assertEqual(menu.props['page'], 'choose')
            self.assertEqual(menu.props['back'], '‹ Subtitles')
            self.assertEqual([r['label'] for r in menu.rows], ['Film 2019 spanish'])
            self.assertEqual(self.fake.current, 0)   # still the English one
            menu.onClick(tracks.BACK_LINK)           # straight back to the tracks, language restored
            self.assertEqual((menu.props['page'], menu.lang, menu.lang_name), ('', 'en', 'English'))
        drive(scenario, self.fake)
        self.assertEqual(searched, ['es'])

    def test_nothing_found_says_so_and_restores_the_language(self):
        def scenario(menu):
            self.hold(menu, 2)
            with patch('subtitle_sources.find', return_value=[]):
                menu.onClick(tracks.HOLD_FIND)
                for _ in range(100):
                    if menu.props.get('cta_state') == 'none':
                        break
                    time.sleep(0.02)
            self.assertEqual(menu.props['cta_state'], 'none')
            self.assertEqual((menu.lang, menu.lang_name), ('en', 'English'))
        drive(scenario, self.fake)

    def test_the_words_check_runs_after_the_subtitle_is_on_and_only_then_swaps_or_shifts(self):
        # Build 616 log: Download and apply took 58 s listening to the video before anything was applied, and the check made no claim (9 words).
        import speech_check
        def scenario(menu):
            applied=[];shown=[]
            menu.apply=lambda result,got=None:applied.append((result['id'],got[1] if got else None))
            menu.fetch_result=lambda r:('%s.en.srt'%r['id'],b'1\n00:00:01,000 --> 00:00:02,000\nhello\n')
            first={'id':'a','source':'x'};second={'id':'b','source':'x'}
            data=b'orig'
            heard=[(1.0,'hello')]
            # too few words: nothing happens
            menu.checked_video=lambda:{'heard':[]}
            menu.check_by_speech(first,'a.en.srt',data,[first,second],'English');self.assertEqual(applied,[])
            # a shift: the corrected file is applied again
            menu.checked_video=lambda:{'heard':heard}
            with patch.object(speech_check,'apply',return_value=(b'shifted',None)):
                menu.check_by_speech(first,'a.en.srt',data,[first,second],'English')
            self.assertEqual(applied,[('a',b'shifted')])
            # a clear mismatch: the next candidate replaces it
            applied.clear()
            with patch.object(speech_check,'apply',side_effect=[(data,'Words do not match the speech'),(b'ok',None)]), \
                 patch('subtitle_match.choose_download',return_value=(second,'b.en.srt',b'second')):
                menu.check_by_speech(first,'a.en.srt',data,[first,second],'English')
            self.assertEqual([a[0] for a in applied],['b'])
        drive(scenario, self.fake)

    def test_a_tap_outside_ends_the_menu(self):
        def scenario(menu):
            self.hold(menu, 2)
            menu.onClick(tracks.HOLD_SCRIM)
            self.assertEqual(menu.props['ctx'], '')
        drive(scenario, self.fake)


if __name__ == '__main__':
    unittest.main()
