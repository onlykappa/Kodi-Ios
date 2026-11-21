"""Next Episode must not wait on the playing Drive video's stuck reads (owner, build 623 log 8c570737: the old video took 40 s to close)."""
import http.server,importlib.util,sys,threading,time,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
sys.dont_write_bytecode=True;sys.path[:0]=[str(BOOT/'resources/lib'),str(BOOT)]
import drive_proxy as dp

class Sock:
    def __init__(self):self.cut=False
    def shutdown(self,how):self.cut=True
class Conn:
    def __init__(self):self.sock=Sock();self.closed=False
    def close(self):self.closed=True

class Abort(unittest.TestCase):
    def upstream(self):
        made=[];up=dp.Upstream(lambda force=False:'tok',connect=lambda:(made.append(Conn()),made[-1])[1]);up.made=made;return up
    def test_every_connection_is_cut_and_new_requests_are_refused_for_a_moment(self):
        up=self.upstream();a=up._conn();up.local.conn=None;b=up._conn(fresh=False)
        self.assertEqual(up.abort_all(hold=0.15),2);self.assertTrue(a.sock.cut and b.sock.cut and a.closed)
        with self.assertRaises(ConnectionAbortedError):up.request('/x',attempts=1)
        time.sleep(.2);up.connect=lambda:self.fail('not asked: only the hold is over')   # after the hold requests go on (this one fails on the fake token path, not the refusal)
        try:up.request('/x',attempts=1)
        except ConnectionAbortedError:self.fail('still refused after the hold')
        except Exception:pass
    def test_release_lets_the_next_videos_requests_in_at_once(self):   # build 639 log 9f7b4ab2: the next episode's first reads, 0.4 s after the close, got 502
        up=self.upstream();up.abort_all(hold=30)
        with self.assertRaises(ConnectionAbortedError):up.request('/x',attempts=1)
        up.release()
        try:up.request('/x',attempts=1)
        except ConnectionAbortedError:self.fail('still refused after release')
        except Exception:pass
    def test_next_episode_releases_the_proxy_once_the_old_video_is_closed(self):
        text=(BOOT/'next_episode.py').read_text();self.assertIn('release_drive_reads(xbmc, xbmcgui.Window(10000))',text)
        self.assertIn("'?release=1'",(BOOT/'resources/lib/drive_proxy.py').read_text());self.assertIn("'release=1' in self.path",(BOOT/'resources/lib/drive_proxy.py').read_text())
    def test_nothing_to_cut_is_fine(self):
        self.assertEqual(self.upstream().abort_all(),0)
    def test_the_proxy_answers_abort_and_ask_abort_reaches_it(self):
        seen=[]
        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_GET(self):
                seen.append(self.path);self.send_response(200);self.send_header('Content-Length','0');self.end_headers()
        server=http.server.HTTPServer(('127.0.0.1',0),H);threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.shutdown)
        self.assertTrue(dp.ask_abort(server.server_address[1]));self.assertEqual(seen,['/abort']);self.assertFalse(dp.ask_abort(1,timeout=.2))
        text=(BOOT/'resources/lib/drive_proxy.py').read_text()
        self.assertIn("if self.path.startswith('/abort'):",text);self.assertIn('self.upstream.abort_all()',text)

class NextEpisode(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location('next_ep_abort',BOOT/'next_episode.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_a_drive_copy_has_its_reads_cut_before_the_stop_and_other_videos_are_left_alone(self):
        m=self.load();asked=[]
        real=dp.ask_abort;dp.ask_abort=lambda port,timeout=1.0,release=False:(asked.append(port),True)[1];self.addCleanup(setattr,dp,'ask_abort',real)
        home=types.SimpleNamespace(getProperty=lambda k:'53037' if k=='KodiIOS.DriveProxy' else '')
        xbmc=lambda f:types.SimpleNamespace(Player=lambda:types.SimpleNamespace(getPlayingFile=lambda:f))
        self.assertTrue(m.cut_drive_reads(xbmc('http://127.0.0.1:53037/drive/abc/Show.mp4'),home));self.assertEqual(asked,[53037])
        self.assertFalse(m.cut_drive_reads(xbmc('https://dl.example.invalid/f.mkv'),home));self.assertEqual(asked,[53037])
        self.assertFalse(m.cut_drive_reads(xbmc('http://127.0.0.1:53037/x'),types.SimpleNamespace(getProperty=lambda k:'')))
    def fake(self,playing_after=3):
        calls=[];state={'t':0}
        class Monitor:
            def waitForAbort(inner,step):state['t']+=1;return False
        class Player:
            def getTime(inner):return 1.0 if state['t']>=playing_after else 0.0
        xbmc=types.SimpleNamespace(executebuiltin=lambda c:calls.append(c),Monitor=Monitor,Player=Player,
                                   getCondVisibility=lambda c:{'Player.HasVideo':state['t']>=playing_after,'Player.Caching':False}.get(c,False))
        return xbmc,calls
    def test_next_episode_shows_the_circle_closes_stray_pages_and_removes_the_circle_when_the_video_plays(self):   # build 634 log 4c4cf619
        m=self.load();xbmc,calls=self.fake()
        m.spinner(xbmc,True);m.tidy(xbmc);m.finish(xbmc)
        self.assertEqual(calls[0],'ActivateWindow(busydialognocancel)')
        for name in ('movieinformation','contextmenu','selectdialog','okdialog','yesnodialog'):self.assertIn('Dialog.Close(%s,true)'%name,calls)
        self.assertEqual(calls[-1],'Dialog.Close(busydialognocancel,true)');self.assertNotIn('Dialog.Close(all,true)',calls)   # never closes the circle by accident, nor everything
    def test_the_circle_is_removed_even_when_the_video_never_plays(self):
        m=self.load();xbmc,calls=self.fake(playing_after=10**6);m.finish(xbmc,limit=1.0,step=0.3)
        self.assertEqual(calls[-1],'Dialog.Close(busydialognocancel,true)')
    def test_both_routes_show_the_circle_tidy_up_and_wait_for_the_picture(self):
        text=(BOOT/'next_episode.py').read_text()
        self.assertEqual(text.count('spinner(xbmc, True)'),2);self.assertEqual(text.count('finish(xbmc)'),2);self.assertEqual(text.count('        tidy(xbmc)\n        xbmc.executebuiltin'),1)
        self.assertIn("                tidy(xbmc)\n                xbmc.executebuiltin('PlayMedia(%s)' % found[1])",text)
    def test_a_library_play_right_after_launch_waits_for_the_apps_drive_proxy(self):
        lib=(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_library.py').read_text()
        self.assertIn("window.getProperty('KodiIOS.ServiceStart')",lib);self.assertIn('time.time()-began<40',lib)
        self.assertIn("window.setProperty('KodiIOS.ServiceStart',str(time.time()))",(BOOT/'service.py').read_text())
    def test_the_stop_is_preceded_by_the_cut_and_logs_how_long_it_took(self):
        text=(BOOT/'next_episode.py').read_text()
        self.assertLess(text.index('cut_drive_reads(xbmc, xbmcgui.Window(10000))'),text.index('stopped = _wait_stopped(xbmc, limit, step)'))
        self.assertIn("'Kodi iOS Next Episode: old video %s after %.1f s'",text)
if __name__=='__main__':unittest.main()
