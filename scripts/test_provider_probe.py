"""Real local HTTP checks: a resolved link must be reachable before playback is dispatched."""
import http.server,sys,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import provider_fallback as f
class Server(http.server.ThreadingHTTPServer):daemon_threads=True
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_HEAD(self):
  self.server.seen.append((self.command,self.headers.get('Cookie')))
  if self.path=='/get-only':self.send_error(405);return
  if self.path=='/missing':self.send_error(404);return
  if self.path=='/slow':time.sleep(.5)
  self.send_response(200);self.send_header('Content-Type','text/html' if self.path=='/html' else 'video/mp4');self.end_headers()
 def do_GET(self):
  self.server.seen.append((self.command,self.headers.get('Cookie')))
  self.send_response(206);self.send_header('Content-Type','video/mp4');self.send_header('Content-Range','bytes 0-0/100');self.end_headers()
class Probe(unittest.TestCase):
 def setUp(self):
  self.server=Server(('127.0.0.1',0),Handler);self.server.seen=[]
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
  self.transport=f.KodiTransport.__new__(f.KodiTransport);self.transport.clock=time.monotonic
  self.url='http://127.0.0.1:%d'%self.server.server_port
 def tearDown(self):self.server.shutdown();self.server.server_close()
 def test_live_head_preserves_headers_without_getting_movie(self):
  self.transport.probe(self.url+'/video|Cookie=fixture',time.monotonic()+1,None)
  self.assertEqual(self.server.seen,[('HEAD','fixture')])
 def test_head_not_supported_uses_tiny_range_get(self):
  self.transport.probe(self.url+'/get-only',time.monotonic()+1,None)
  self.assertEqual([x[0] for x in self.server.seen],['HEAD','GET'])
 def test_missing_and_html_fail_before_playback(self):
  for path in ['/missing','/html']:
   with self.subTest(path=path),self.assertRaises(ConnectionError):self.transport.probe(self.url+path,time.monotonic()+1,None)
 def test_shared_deadline_returns_promptly(self):
  began=time.monotonic()
  with self.assertRaises(TimeoutError):self.transport.probe(self.url+'/slow',began+.1,None)
  self.assertLess(time.monotonic()-began,.3)
 def test_cancellation_stops_probe(self):
  began=time.monotonic()
  with self.assertRaises(f.Canceled):self.transport.probe(self.url+'/slow',began+1,lambda:time.monotonic()-began>.05)
  self.assertLess(time.monotonic()-began,.3)
if __name__=='__main__':unittest.main()
