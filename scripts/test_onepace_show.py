"""One Pace inside the app (owner, 2026-11-28): saved copy, rows, downloads, the hourly new-episode check, search entry, menus and the plugin routes."""
import json, sys, tempfile, types, unittest
from pathlib import Path
from unittest import mock
ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
BOOT = ROOT / 'migration/bundled-bootstrap'
OVERLAY = ROOT / 'migration/import-overlays/plugin.video.kodi.ios.watch'
for p in (str(LIB), str(OVERLAY / 'resources/lib'), str(BOOT)):
    sys.path.insert(0, p)
import onepace, onepace_show as show

PAGE = json.loads((ROOT / 'scripts/fixtures/onepace_watch.json').read_text(encoding='utf-8'))['html']


class Net:
    def __init__(self, page=PAGE):
        self.page, self.calls, self.down = page, 0, False
    def __call__(self, url, timeout=25):
        self.calls += 1
        if self.down:
            raise OSError('unreachable')
        return self.page


class Saved(unittest.TestCase):
    def test_read_once_an_hour_and_the_saved_copy_covers_an_outage(self):
        with tempfile.TemporaryDirectory() as tmp:
            net, now = Net(), [1000.0]
            first, error = show.seasons(tmp, net, lambda: now[0])
            self.assertEqual((len(first), error, net.calls), (3, '', 1))
            show.seasons(tmp, net, lambda: now[0] + 60); self.assertEqual(net.calls, 1)                 # fresh: not read again
            net.down = True
            again, error = show.seasons(tmp, net, lambda: now[0] + show.FRESH + 5)
            self.assertEqual((len(again), net.calls), (3, 2)); self.assertIn('OSError', error)         # stale and unreachable: the saved copy
    def test_first_run_with_the_site_down_is_empty_with_a_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            net = Net(); net.down = True
            self.assertEqual(show.seasons(tmp, net)[0], []); self.assertTrue(show.seasons(tmp, net)[1])
    def test_a_page_with_no_arcs_is_an_error_not_a_blank_show(self):
        with tempfile.TemporaryDirectory() as tmp:
            found, error = show.seasons(tmp, Net('<html>changed</html>'))
            self.assertEqual(found, []); self.assertIn('no arcs', error)


class Rows(unittest.TestCase):
    def setUp(self):
        self.found = onepace.seasons(onepace.parse_watch(PAGE))
    def test_arcs_are_seasons_and_say_how_many_have_a_dub(self):
        rows = show.season_rows(self.found)
        self.assertEqual([(r['season'], r['label'], r['episodes']) for r in rows], [(1, 'Romance Dawn', 4), (2, 'Whisky Peak', 2), (3, 'Thriller Bark', 2)])
        self.assertIn('Manga chapters', rows[0]['plot']); self.assertIn('0 of 2 episodes have an English dub', rows[1]['plot'])
    def test_episodes_say_when_they_are_japanese_only(self):
        dubbed = show.episode_rows(show.find(self.found, 1)); jp = show.episode_rows(show.find(self.found, 2))
        self.assertFalse(any(r['japanese_only'] for r in dubbed)); self.assertTrue(all(r['japanese_only'] for r in jp))
        self.assertEqual(dubbed[0]['audio'], 'English dub'); self.assertEqual(jp[0]['audio'], 'Japanese')
    def test_play_targets(self):
        dub = show.play_target(self.found, 1, 1); self.assertEqual((dub['audio'], dub['japanese_only'], dub['arc']), ('English dub', False, 'Romance Dawn'))
        ja = show.play_target(self.found, 1, 1, 'japanese'); self.assertEqual((ja['audio'], ja['japanese_only']), ('Japanese', False))
        self.assertTrue(show.play_target(self.found, 2, 1)['japanese_only'])
        self.assertIsNone(show.play_target(self.found, 9, 1)); self.assertIsNone(show.play_target(self.found, 1, 99))


class Download(unittest.TestCase):
    def setUp(self):
        self.found = onepace.seasons(onepace.parse_watch(PAGE))
    def test_an_arc_queues_every_episode_with_a_library_name(self):
        req = show.download_requests(self.found, season=1)
        self.assertEqual(len(req), 4)
        url, candidate, request = req[0]
        self.assertTrue(url.startswith('https://pixeldrain.net/api/file/'))
        self.assertTrue(candidate['name'].startswith('One Pace - S01E01 - ROMANCE DAWN') and candidate['name'].endswith('.mp4'))
        self.assertEqual((request['show_title'], request['season'], request['episode'], request['media_type']), ('One Pace', '1', '1', 'episode'))
        self.assertEqual(len(show.download_requests(self.found, season=1, episode=2)), 1); self.assertEqual(len(show.download_requests(self.found)), 8)
    def test_counts_and_a_failure_does_not_stop_the_rest(self):
        calls = []
        def queue(profile, url, candidate, request):
            calls.append(request['season'] + 'x' + request['episode'])
            if request['episode'] == '2':
                raise ValueError('no')
        queued, failed, japanese = show.download('p', self.found, queue, season=2)
        self.assertEqual((queued, failed, japanese), (1, 1, 1)); self.assertEqual(len(calls), 2)       # arc 2 has two Japanese-only episodes
        self.assertEqual(show.download('p', self.found, lambda *a: None, season=1)[2], 0)
    def test_names_are_safe(self):
        self.assertNotIn('/', show.file_name(1, 1, 'A/B: C?', '1080p'))


class Tracking(unittest.TestCase):
    def test_first_look_records_and_says_nothing_then_news_is_noticed_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            notes, logs, now = [], [], [5000.0]
            net = Net()
            self.assertEqual(show.check(tmp, net, lambda t, x: notes.append((t, x)), logs.append, lambda: now[0]), []); self.assertEqual(notes, [])
            state = json.loads((Path(tmp) / show.FOLDER / show.STATE).read_text())
            self.assertEqual((state['arcs'], state['episodes'], state['last_error']), (3, 8, ''))
            state['signature']['romance-dawn'] = [3, 3]; del state['signature']['thriller-bark']
            (Path(tmp) / show.FOLDER / show.STATE).write_text(json.dumps(state))
            changes = show.check(tmp, net, lambda t, x: notes.append((t, x)), logs.append, lambda: now[0] + 10)
            self.assertEqual(sorted(c['kind'] for c in changes), ['arc', 'dub', 'episode'])
            self.assertEqual(len(notes), 3); self.assertIn('New One Pace arc: Thriller Bark', [n[0] for n in notes])
            self.assertEqual(show.check(tmp, net, lambda t, x: notes.append((t, x)), logs.append, lambda: now[0] + 20), []); self.assertEqual(len(notes), 3)   # once
    def test_a_down_site_is_a_quiet_log_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            net, notes, logs = Net(), [], []
            show.check(tmp, net, lambda t, x: notes.append(t), logs.append)
            net.down = True
            self.assertEqual(show.check(tmp, net, lambda t, x: notes.append(t), logs.append), []); self.assertEqual(notes, [])
            self.assertTrue(any('could not be read' in l for l in logs))
            self.assertIn('OSError', json.loads((Path(tmp) / show.FOLDER / show.STATE).read_text())['last_error'])
    def test_a_failing_notice_does_not_stop_the_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            net = Net(); show.check(tmp, net)
            path = Path(tmp) / show.FOLDER / show.STATE; state = json.loads(path.read_text()); state['signature']['romance-dawn'] = [1, 1]; path.write_text(json.dumps(state))
            def boom(t, x): raise RuntimeError('x')
            self.assertTrue(show.check(tmp, net, boom, lambda text: None)); self.assertEqual(json.loads(path.read_text())['signature']['romance-dawn'], [4, 4])
    def test_the_service_loop_waits_checks_and_stops(self):
        class Monitor:
            def __init__(self): self.n = 0
            def waitForAbort(self, s): self.n += 1; return self.n > 4
            def abortRequested(self): return self.n > 4
        with tempfile.TemporaryDirectory() as tmp:
            seen = []
            show.run(Monitor(), tmp, lambda: True, lambda: True, lambda t, x: None, seen.append, Net())
            self.assertTrue(any('checked 3 arcs' in l for l in seen))
            seen.clear(); show.run(Monitor(), tmp, lambda: True, lambda: False, lambda t, x: None, seen.append, Net()); self.assertEqual(seen, [])   # not in front: no look


class Search(unittest.TestCase):
    def test_only_a_query_about_one_pace_adds_the_entry(self):
        for q in ('one pace', 'One Pace', 'onepace', 'pace', 'one pace wano'):
            self.assertEqual(show.search_rows(q)[0]['file'], 'plugin://plugin.video.kodi.ios.watch/?action=onepace', q)
        for q in ('', None, 'dragon ball', 'one piece', 'space'):
            self.assertEqual(show.search_rows(q), [], q)
    def test_the_search_list_puts_it_first_in_tv_shows(self):
        import ios_search
        text = (OVERLAY / 'resources/lib/ios_search.py').read_text()
        self.assertIn("found['tv'] = onepace_show.search_rows(query) + (found.get('tv') or [])", text)


class Menus(unittest.TestCase):
    def test_actions(self):
        import onepace_menu as m
        self.assertEqual(m.action('download', 'season', 3, ''), 'RunPlugin(plugin://plugin.video.kodi.ios.watch/?action=onepace_download&season=3)')
        self.assertIn('episode=2', m.action('download', 'episode', 3, 2))
        self.assertIn('prefer=japanese', m.action('japanese', 'episode', 3, 2)); self.assertTrue(m.action('japanese', 'episode', 3, 2).startswith('PlayMedia('))
        for bad in (m.action('download', 'movie', 1, 1), m.action('download', 'episode', '', 1), m.action('japanese', 'season', 1, ''), m.action('x', 'episode', 1, 1)):
            self.assertEqual(bad, '')
    def test_addon_xml_wires_both_items_and_keeps_other_downloads_off_one_pace(self):
        text = (BOOT / 'addon.xml').read_text()
        self.assertIn('library="onepace_download_menu.py"', text); self.assertIn('library="onepace_japanese_menu.py"', text)
        first = text[text.index('library="download.py"'):text.index('library="choose_source.py"')]
        self.assertIn('!String.Contains(ListItem.FolderPath,plugin.video.kodi.ios.watch/?action=onepace)', first)   # the Elementum Download item steps aside
        self.assertTrue((BOOT / 'onepace_download_menu.py').is_file() and (BOOT / 'onepace_japanese_menu.py').is_file())


class FakeKodi:
    """Just enough of xbmc / xbmcgui / xbmcplugin / xbmcvfs for the plugin routes."""
    def __init__(self, yes=True):
        self.yes, self.items, self.resolved, self.notes, self.content, self.ended, self.questions = yes, [], [], [], None, None, []
        k = self
        class Tag:
            def __init__(s): s.v = {}
            def __getattr__(s, n):
                if n.startswith('set'): return lambda *a: s.v.__setitem__(n[3:], a[0] if a else None)
                raise AttributeError(n)
        class ListItem:
            def __init__(s, label='', path=''): s.label, s.path, s.props, s.tag = label, path, {}, Tag()
            def getVideoInfoTag(s): return s.tag
            def setProperty(s, a, b): s.props[a] = b
            def setLabel2(s, t): s.label2 = t
        class Dialog:
            def notification(s, *a): k.notes.append(a[1])
            def yesno(s, title, text, **kw): k.questions.append((title, text, kw)); return k.yes
        self.mods = {'xbmc': types.SimpleNamespace(log=lambda *a: None, LOGINFO=1, LOGWARNING=2),
                     'xbmcgui': types.SimpleNamespace(ListItem=ListItem, Dialog=Dialog, NOTIFICATION_INFO=1),
                     'xbmcvfs': types.SimpleNamespace(translatePath=lambda p: TMP[0] if 'profile' in p else str(BOOT)),
                     'xbmcplugin': types.SimpleNamespace(addDirectoryItems=lambda h, rows: k.items.extend(rows), setContent=lambda h, c: setattr(k, 'content', c),
                                                         endOfDirectory=lambda h, succeeded=True, cacheToDisc=True: setattr(k, 'ended', succeeded),
                                                         setResolvedUrl=lambda h, ok, li: k.resolved.append((ok, li)))}
TMP = ['']


class Plugin(unittest.TestCase):
    def run_route(self, params, yes=True, net=None):
        import ios_onepace
        kodi = FakeKodi(yes)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(sys.modules, kodi.mods), mock.patch.object(show, 'fetch', net or Net()):
            TMP[0] = tmp
            if params.get('action') == 'onepace_play': ios_onepace.play(1, params)
            elif params.get('action') == 'onepace_download': ios_onepace.download(params)
            else: ios_onepace.directory(1, params)
        return kodi
    def test_the_season_row_lists_arcs_and_an_arc_lists_playable_episodes(self):
        k = self.run_route({'action': 'onepace'})
        self.assertEqual((k.content, len(k.items)), ('seasons', 3)); self.assertTrue(all(folder for _, _, folder in k.items)); self.assertIn('season=1', k.items[0][0])
        e = self.run_route({'action': 'onepace', 'season': '2'})
        self.assertEqual((e.content, len(e.items)), ('episodes', 2))
        path, li, folder = e.items[0]; self.assertFalse(folder); self.assertIn('action=onepace_play', path); self.assertEqual(li.props['IsPlayable'], 'true'); self.assertEqual(li.props['onepace_japanese_only'], 'true')
        self.assertEqual(li.tag.v['TvShowTitle'], 'One Pace'); self.assertIn('Japanese only', li.label2)
    def test_an_unreachable_site_with_no_saved_copy_says_so(self):
        net = Net(); net.down = True
        k = self.run_route({'action': 'onepace'}, net=net)
        self.assertEqual(k.ended, False); self.assertIn('Cannot reach One Pace', k.notes[0])
    def test_a_dubbed_episode_plays_without_a_question(self):
        k = self.run_route({'action': 'onepace_play', 'season': '1', 'episode': '1'})
        self.assertEqual(k.questions, []); ok, li = k.resolved[0]; self.assertTrue(ok); self.assertTrue(li.path.startswith('https://pixeldrain.net/api/file/'))
    def test_a_japanese_only_episode_asks_and_cancel_plays_nothing(self):
        k = self.run_route({'action': 'onepace_play', 'season': '2', 'episode': '1'}, yes=False)
        self.assertEqual(k.questions[0][0], 'This episode is Japanese only'); self.assertEqual(k.questions[0][2], {'nolabel': 'Cancel', 'yeslabel': 'Continue'})
        self.assertEqual(k.resolved[0][0], False)
        k = self.run_route({'action': 'onepace_play', 'season': '2', 'episode': '1'}, yes=True)
        self.assertTrue(k.resolved[0][0]); self.assertTrue(k.resolved[0][1].path.startswith('https://pixeldrain.net/api/file/'))
    def test_play_in_japanese_picks_the_japanese_file_without_asking(self):
        k = self.run_route({'action': 'onepace_play', 'season': '1', 'episode': '1', 'prefer': 'japanese'})
        self.assertEqual(k.questions, []); dub = self.run_route({'action': 'onepace_play', 'season': '1', 'episode': '1'})
        self.assertNotEqual(k.resolved[0][1].path, dub.resolved[0][1].path)
    def test_a_missing_episode_resolves_nothing(self):
        k = self.run_route({'action': 'onepace_play', 'season': '1', 'episode': '99'})
        self.assertEqual(k.resolved[0][0], False); self.assertIn('not available', k.notes[0])
    def test_the_routes_are_in_the_plugin(self):
        text = (OVERLAY / 'default.py').read_text()
        for needle in ("action')=='onepace'", "action')=='onepace_play'", "action')=='onepace_download'"): self.assertIn(needle, text)


if __name__ == '__main__':
    unittest.main()
