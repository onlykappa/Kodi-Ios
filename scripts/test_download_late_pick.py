"""Man of Steel (owner log 6bcfc38d): the engine answers a download request only after the owner has picked a version. A fake engine on a real socket
stands in for it: the pick comes late, the redirect is followed, and the download request reaches the engine."""
import sys,threading,time,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import elementum_download as ed
class Engine(ThreadingHTTPServer):
    def __init__(self,delay):
        self.delay,self.seen=delay,[]
        class H(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_GET(h):
                self.seen.append(h.path)
                if h.path.startswith('/movie/49521/forcelinks'):
                    time.sleep(self.delay)   # the owner is still choosing a version
                    h.send_response(302);h.send_header('Location','plugin://plugin.video.elementum/play?uri=magnet%3A%3Fxt%3Dabc&type=movie&background=true');h.send_header('Content-Length','0');h.end_headers()
                else:
                    h.send_response(200);h.send_header('Content-Length','2');h.end_headers();h.wfile.write(b'ok')
        super().__init__(('127.0.0.1',0),H)
class LatePick(unittest.TestCase):
    def run_follow(self,delay,timeout):
        engine=Engine(delay);threading.Thread(target=engine.serve_forever,daemon=True).start()
        old=ed.ENGINE;ed.ENGINE='http://127.0.0.1:%d'%engine.server_address[1]
        try:
            result=ed.follow('plugin://plugin.video.elementum/movie/49521/forcelinks?doresume=false',route=lambda u:False,gate=lambda:None,engine=lambda:None,timeout=timeout)
            return result,engine.seen
        finally:
            ed.ENGINE=old;engine.shutdown();engine.server_close()
    def test_a_late_pick_still_queues_the_download(self):
        result,seen=self.run_follow(1.5,30)
        self.assertTrue(result.endswith('/play?uri=magnet%3A%3Fxt%3Dabc&type=movie&background=true'),result)
        self.assertEqual([p.split('?')[0] for p in seen],['/movie/49521/forcelinks','/play'])
    def test_a_request_that_waits_longer_than_its_limit_is_reported_not_silently_dropped(self):
        with self.assertRaises(Exception):self.run_follow(3,1)
class PatchedNavigation(unittest.TestCase):
    def test_the_plugin_request_has_an_explicit_long_wait(self):
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        import build_customized_ipa as b
        news=[new for name,old,new in b.ELEMENTUM_PATCHES if name.endswith('navigation.py') and b'urlopen' in new]
        self.assertTrue(any(b'urlopen(url, timeout=3600)' in n for n in news))
if __name__=='__main__':unittest.main()
