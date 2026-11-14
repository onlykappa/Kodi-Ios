"""Reject wrong subtitle episodes/timing before installation; rank usable tracks without claiming unseen speech."""
import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / 'migration/bundled-bootstrap'
sys.path.insert(0, str(BOOT / 'resources/lib'))
import subtitle_match as sm
import track_menu as tm

VIDEO = {'duration': 1400, 'language': 'en', 'season': 1, 'episode': 5}
CUES = [(10 + n * 50, 13 + n * 50) for n in range(27)]


def srt(cues):
    def stamp(value):
        return '%02d:%02d:%02d,000' % (value // 3600, value // 60 % 60, value % 60)
    return '\n\n'.join('%d\n%s --> %s\nA subtitle line' % (n, stamp(a), stamp(b))
                       for n, (a, b) in enumerate(cues, 1)).encode()


class Match(unittest.TestCase):
    def test_text_formats_and_dvd_index_times(self):
        self.assertEqual(sm.cue_times(srt([(10, 12), (130, 132)])), [(10, 12), (130, 132)])
        self.assertEqual(sm.cue_times('WEBVTT\n\n00:01.200 --> 00:03.400\nHi'), [(1.2, 3.4)])
        self.assertEqual(sm.cue_times('Dialogue: 0,0:00:05.20,0:00:07.30,Default,,0,0,0,,Hello'), [(5.2, 7.3)])
        self.assertEqual(sm.cue_times('{1}{1}25\n{250}{300}Hello'), [(10, 12)])
        self.assertEqual(sm.cue_times('timestamp: 00:01:02:500, filepos: 00000001', 'English.idx'), [(62.5, 62.6)])
        self.assertEqual(sm.cue_times('1\n00:00:02,000 --> 00:00:01,000\nbackwards'), [])
        self.assertEqual(sm.cue_times('1\n00:00:01,000 --> 00:00:02,000\nHi'.encode('utf-16')), [(1, 2)])

    def match(self, **fields):
        return sm.assess(dict(filename='Naruto.S01E05.en.srt', cues=CUES, **fields), VIDEO)

    def test_matching_track_has_a_reason_and_timing_evidence(self):
        answer = self.match()
        self.assertEqual((answer['rejected'], answer['reason'], answer['timing_checked']),
                         (False, 'Matches this episode', True))
        self.assertGreaterEqual(answer['score'], 85)

    def test_cues_beyond_the_video_are_rejected(self):
        answer = sm.assess({'cues': [(n * 100, n * 100 + 4) for n in range(25)]}, VIDEO)
        self.assertTrue(answer['rejected'])
        self.assertEqual(answer['reason'], 'Timing does not fit this video')

    def test_cues_far_from_both_ends_are_rejected(self):
        answer = sm.assess({'cues': [(500 + n * 10, 502 + n * 10) for n in range(20)]}, VIDEO)
        self.assertTrue(answer['rejected'])

    def test_credits_alone_reduce_rank_but_do_not_reject(self):
        answer = sm.assess({'cues': [(10 + n * 30, 12 + n * 30) for n in range(20)]}, VIDEO)
        self.assertFalse(answer['rejected'])
        self.assertLess(answer['score'], self.match()['score'])

    def test_episode_and_language_mismatches(self):
        for name in ('Naruto.S01E06.en.srt', 'Naruto.1x06.en.srt', 'Naruto - 006.en.srt', 'Naruto Episode 006.en.srt'):
            answer = sm.assess({'filename': name, 'cues': CUES}, VIDEO)
            self.assertEqual((answer['rejected'], answer['reason']), (True, 'Different episode'), name)
        answer = sm.assess({'filename': 'Naruto.S01E05.spa.srt', 'cues': CUES}, VIDEO)
        self.assertEqual(answer['reason'], 'Different language')
        answer = sm.assess({'filename': 'Naruto.S01E05.spa.srt', 'language': 'eng', 'cues': CUES}, VIDEO)
        self.assertEqual(answer['reason'], 'Language tag does not match')
        # Absolute episode numbers cannot be compared to season-relative numbers without an offset.
        self.assertFalse(sm.assess({'filename': 'Naruto - 057.en.srt', 'cues': CUES}, dict(VIDEO, season=2))['rejected'])
        self.assertTrue(sm.assess({'filename': 'Naruto - 057.en.srt', 'cues': CUES}, dict(VIDEO, season=2, absolute_episode=58))['rejected'])

    def test_empty_short_and_forced_tracks(self):
        self.assertTrue(sm.assess({'filename': 'English.srt', 'data': b''}, VIDEO)['rejected'])
        self.assertTrue(sm.assess({'filename': 'English.srt', 'data': b'no cue times'}, VIDEO)['rejected'])
        self.assertTrue(sm.assess({'cues': [(5, 7)]}, VIDEO)['rejected'])
        self.assertFalse(sm.assess({'cues': [(5, 7)], 'isforced': True}, VIDEO)['rejected'])
        # Embedded DVD and external binary VobSub are not decoded by this Python backend.
        for track in ({'name': 'DVD English', 'language': 'eng'}, {'filename': 'English.sub', 'data': b'\x00\x00\x01\xba'}):
            answer = sm.assess(track, VIDEO)
            self.assertFalse(answer['rejected'])
            self.assertFalse(answer['timing_checked'])
            self.assertEqual(answer['reason'], 'Timing not checked')

    def test_measured_speech_can_establish_large_offset(self):
        speech = [(10, 12), (45, 47), (92, 94), (170, 172), (224, 226), (333, 335),
                  (470, 472), (632, 634), (811, 813), (1070, 1072), (1300, 1302)]
        shifted = [(a + 20, b + 20) for a, b in speech]
        offset, confidence = sm.estimate_offset(shifted, speech)
        self.assertAlmostEqual(offset, -20, delta=1)
        self.assertGreaterEqual(confidence, .75)
        answer = sm.assess({'cues': shifted}, dict(VIDEO, speech=speech))
        self.assertEqual((answer['rejected'], answer['reason']), (True, 'Subtitles are out of sync'))
        self.assertIsNone(sm.estimate_offset(speech, speech)[0])
        self.assertIsNone(sm.estimate_offset(speech[:2], speech[:2])[0])

    def test_best_match_automatic_and_off_respected(self):
        streams = [{'index': 0, 'language': 'es'}, {'index': 1, 'language': 'en'},
                   {'index': 2, 'filename': 'Naruto.S01E05.en.srt', 'cues': CUES}]
        self.assertEqual(sm.preferred(streams, 0, True, VIDEO), 2)
        self.assertIsNone(sm.preferred(streams, 0, False, VIDEO))
        self.assertEqual(sm.preferred([{'index': 0}, {'index': 1}], 1, True, VIDEO), 1)
        self.assertIsNone(sm.preferred([streams[0]], 0, True, VIDEO))
        rows = tm.subtitle_rows(streams, 2, True, VIDEO)
        self.assertEqual(rows[1]['index'], 2)
        self.assertEqual(rows[1]['match_reason'], 'Matches this episode')
        self.assertTrue(rows[-1]['match_rejected'])

    def test_single_wrong_episode_in_zip_is_rejected(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('Naruto.S01E06.en.srt', srt(CUES))
        self.assertIsNone(tm.subtitle_from_zip(buffer.getvalue(), 1, 5))

    def test_automatic_download_skips_mismatch_and_network_failure(self):
        results = [{'id': str(n), 'releases': [], 'impaired': False, 'language': 'en'} for n in range(3)]
        asked = []

        def fetch(result):
            asked.append(result['id'])
            if result['id'] == '0':
                return 'Naruto.S01E05.en.srt', srt([(n * 200, n * 200 + 4) for n in range(20)])
            if result['id'] == '1':
                raise OSError('site did not answer')
            return 'Naruto.S01E05.en.srt', srt(CUES)
        chosen, name, data = sm.choose_download(results, fetch, VIDEO)
        self.assertEqual(asked, ['0', '1', '2'])
        self.assertEqual(chosen['id'], '2')
        self.assertEqual(data, srt(CUES))
        self.assertTrue(results[0]['match_rejected'])
        self.assertEqual(tm.result_rows(results)[2]['match_reason'], 'Matches this episode')


class Controller(unittest.TestCase):
    """Execute the real controller against fake Kodi: rejected files never reach setSubtitles."""
    def test_download_validates_before_install_and_exposes_the_reason(self):
        spec = importlib.util.spec_from_file_location('subtitle_match_tracks', BOOT / 'tracks.py')
        tracks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tracks)
        selected, windows = [], []
        current = {'index': 0}

        class Window:
            def __init__(self, *args):
                self.properties = {}
                self.controls = {}
                windows.append(self)

            def setProperty(self, key, value):
                self.properties[key] = value

            def getProperty(self, key):
                return self.properties.get(key, '')

            def doModal(self):
                self.onInit()

            def setFocusId(self, *args):
                pass

            def getControl(self, key):
                self.controls.setdefault(key, types.SimpleNamespace(reset=lambda: None, addItems=lambda items: None, selectItem=lambda n: None))
                return self.controls[key]

        class Item:
            def __init__(self, *args):
                self.properties = {}

            def setProperty(self, key, value):
                self.properties[key] = value

        class Player:
            def getTotalTime(self):
                return 1400

            def setSubtitles(self, path):
                selected.append(Path(path).read_bytes())
                current['index'] = 1

        def rpc(xbmc, method, params=None):
            if method == 'Player.GetActivePlayers':
                return [{'type': 'video', 'playerid': 1}]
            if method == 'Settings.GetSettingValue':
                return {'value': ['English']}
            if method == 'Player.GetItem':
                return {'item': dict(title='Naruto', showtitle='Naruto', season=1, episode=5, file='Naruto.S01E05.mkv')}
            if method == 'Player.GetProperties':
                return {'subtitles': [{'index': n, 'language': 'en'} for n in range(current['index'] + 1)],
                        'currentsubtitle': current, 'subtitleenabled': True}
            return {}
        xbmc = types.SimpleNamespace(Player=Player, log=lambda *args: None, LOGINFO=1, ISO_639_1=1,
                                     convertLanguage=lambda *args: 'en', getInfoLabel=lambda *args: '', sleep=lambda *args: None)
        gui = types.SimpleNamespace(WindowXMLDialog=Window, Window=lambda *args: types.SimpleNamespace(setProperty=lambda *args: None, getProperty=lambda *args: ''),
                                    ListItem=Item, Dialog=lambda: types.SimpleNamespace(notification=lambda *args: None), NOTIFICATION_INFO=1)
        with tempfile.TemporaryDirectory() as folder, patch.dict(sys.modules, xbmc=xbmc, xbmcgui=gui,
                                                                 xbmcvfs=types.SimpleNamespace(translatePath=lambda path: folder)), patch.object(tracks, 'rpc', rpc):
            tracks.run('subtitles')
            menu = windows[-1]
            menu.results = [{'id': 'bad', 'releases': [], 'impaired': False, 'language': 'en'},
                            {'id': 'good', 'releases': [], 'impaired': False, 'language': 'en'}]
            menu.search = lambda: menu.results
            menu.fetch_result = lambda result: ('Naruto.S01E05.en.srt', srt([(2000, 2010)]) if result['id'] == 'bad' else srt(CUES))
            menu.download_and_apply()
            self.assertEqual(selected, [srt(CUES)])
            self.assertTrue(menu.results[0]['match_rejected'])
            self.assertEqual(menu.rows[1]['match_reason'], 'Matches this episode')
            self.assertEqual(menu.rows[1]['index'], 1)

    def test_playback_hook_selects_once_and_never_undoes_off(self):
        matcher = sm.PlaybackMatcher()
        changes, published = [], []
        state = {'streams': [{'index': 0, 'name': 'Naruto.S01E06', 'language': 'en'},
                             {'index': 1, 'name': 'Naruto.S01E05', 'language': 'en'}],
                 'current': 0, 'enabled': True, 'video': VIDEO}
        matcher.step('private-playing-url', lambda: state, changes.append, published.append)
        self.assertEqual(changes, [1])
        self.assertNotIn('private-playing-url', published[-1])
        rows = json.loads(published[-1])
        self.assertEqual(rows[0]['index'], 1)
        self.assertEqual(rows[0]['match_reason'], 'Timing not checked')
        self.assertTrue(rows[1]['match_rejected'])
        matcher.step('private-playing-url', lambda: state, changes.append)
        self.assertEqual(changes, [1])  # Do not override a manual choice later in this playback.
        matcher.step('', lambda: state, changes.append)
        state['enabled'] = False
        matcher.step('private-playing-url', lambda: state, changes.append)
        self.assertEqual(changes, [1])
        service = (BOOT / 'service.py').read_text()
        self.assertIn('target=subtitle_match.run', service)

    def test_playback_hook_waits_for_streams(self):
        matcher = sm.PlaybackMatcher()
        changes = []
        matcher.step('video', lambda: {'streams': []}, changes.append)
        self.assertFalse(matcher.done)
        matcher.step('video', lambda: {'streams': [{'index': 0, 'language': 'es'}, {'index': 1, 'language': 'en'}],
                                     'current': 0, 'enabled': True, 'video': VIDEO}, changes.append)
        self.assertEqual(changes, [1])

    def test_service_adapter_reads_explicit_preference_and_changes_the_player(self):
        calls, properties = [], {}

        def execute(request):
            q = json.loads(request)
            method = q['method']
            if method == 'Player.GetActivePlayers':
                result = [{'type': 'video', 'playerid': 3}]
            elif method == 'Player.GetProperties':
                result = {'subtitles': [{'index': 0, 'language': 'spa'}, {'index': 1, 'language': 'eng'}],
                          'currentsubtitle': {'index': 0}, 'subtitleenabled': True}
            elif method == 'Player.GetItem':
                result = {'item': {'file': 'private://video', 'title': 'Naruto', 'season': 1, 'episode': 5}}
            elif method == 'Settings.GetSettingValue':
                result = {'value': 'English'}
            else:
                calls.append(q)
                result = 'OK'
            return json.dumps({'result': result})
        player = types.SimpleNamespace(getPlayingFile=lambda: 'private://video', isPlayingVideo=lambda: True, getTotalTime=lambda: 1400)
        xbmc = types.SimpleNamespace(Player=lambda: player, executeJSONRPC=execute, log=lambda *args: None, LOGWARNING=1)
        gui = types.SimpleNamespace(Window=lambda *args: types.SimpleNamespace(setProperty=properties.__setitem__))
        waits = iter([False, True])
        sm.run(xbmc, gui, types.SimpleNamespace(waitForAbort=lambda seconds: next(waits)))
        self.assertEqual(calls[0]['method'], 'Player.SetSubtitle')
        self.assertEqual(calls[0]['params'], {'playerid': 3, 'subtitle': 1, 'enable': True})
        self.assertEqual(json.loads(properties['KodiIOS.SubtitleMatches'])[0]['index'], 1)


class ConservativeNames(unittest.TestCase):
    def test_movie_title_is_not_a_language_suffix(self):
        result = sm.assess({'filename': 'It.2017.srt', 'language': 'eng'}, {'language': 'en'})
        self.assertFalse(result['rejected'])
        self.assertTrue(sm.assess({'filename': 'Film.it.srt'}, {'language': 'en'})['rejected'])


if __name__ == '__main__':
    unittest.main()
