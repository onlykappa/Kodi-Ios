"""Real HTTP reproducer: valid source headers do not make an unread 4 MiB opening block ready for Kodi.

Fixture URLs and credentials are invented. These host checks do not establish the owner's iPhone outcome.
"""
import http.server
import json
import select
import socket
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import drive_stream
import native_http
import remote_media as remote

DATA=bytes(range(256))*(9*1024*1024//256+1)


class FixtureServer(drive_stream._Server):
 request_queue_size=32


class SourceHTTP:
 """Actual socket responses: 206 headers immediately, followed by either real bytes or a stalled body."""
 def __init__(self):
  self.release=threading.Event();self.headers_sent=threading.Event();self.lock=threading.Lock()
  self.requests=[];self.live=0;self.peak=0
  fixture=self
  class Handler(http.server.BaseHTTPRequestHandler):
   protocol_version='HTTP/1.1'
   def log_message(self,*args):pass
   def do_GET(self):
    with fixture.lock:
     fixture.requests.append((self.path,dict(self.headers)));fixture.live+=1;fixture.peak=max(fixture.peak,fixture.live)
    try:
     payload=DATA[:256*1024] if '/small.' in self.path else DATA
     start,end=map(int,self.headers['Range'][6:].split('-'));end=min(end,len(payload)-1)
     if start>=len(payload):
      self.send_response(416);self.send_header('Content-Length','0');self.end_headers();return
     wrong='/wrong-range.' in self.path
     self.send_response(206)
     self.send_header('Content-Range','bytes %d-%d/%d'%(start+1 if wrong else start,end,len(payload)))
     self.send_header('Content-Length',str(end-start+1));self.end_headers();self.wfile.flush()
     fixture.headers_sent.set()
     if '/delayed-tail-stall.' in self.path and start<remote.BLOCK:
      time.sleep(.18)
     if ('/stall.' in self.path or ('/tail-stall.' in self.path and start>=remote.BLOCK)
         or ('/delayed-tail-stall.' in self.path and start>=remote.BLOCK)
         or ('/buffered-piece-stall.' in self.path and start>=remote.BLOCK//remote.SPLIT)):
      while not fixture.release.wait(.02):
       # Detect cancellation of the upstream socket rather than retaining fixture threads until teardown.
       readable,_,_=select.select([self.connection],[],[],0)
       if readable and not self.connection.recv(1,socket.MSG_PEEK):return
     self.wfile.write(payload[start:end+1]);self.wfile.flush()
    except (OSError,ValueError):pass
    finally:
     with fixture.lock:fixture.live-=1
  self.server=FixtureServer(('127.0.0.1',0),Handler)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def open(self,request,timeout):
  from urllib.parse import urlsplit
  source=urlsplit(request.full_url)
  target='http://127.0.0.1:%d%s%s'%(self.server.server_address[1],source.path,'?'+source.query if source.query else '')
  return urllib.request.urlopen(urllib.request.Request(target,headers=dict(request.header_items())),timeout=timeout)
 def close(self):
  self.release.set();self.server.shutdown();self.server.server_close();self.thread.join(2)


class OpeningFallback(unittest.TestCase):
 SRC='https://fixture.invalid/stall.mkv?token=synthetic-source-token|User-Agent=Fixture%20Player&Authorization=Bearer%20synthetic-auth&Cookie=test%3Dsynthetic-cookie'
 FAST='https://fixture.invalid/fast.mkv?token=synthetic-fast-token|User-Agent=Fixture%20Player&Authorization=Bearer%20synthetic-auth'
 def setUp(self):
  self.fixture=SourceHTTP();self.sources=[];self.buffered=False;self.native_timeouts=[];self.native_calls=[]
  def buffered_open(request,timeout):
   # native_http.opener/kodi_http_send returns a BytesIO response only after the entire range body arrives.
   self.native_timeouts.append(timeout)
   self.native_calls.append((time.monotonic(),timeout))
   with self.fixture.open(request,timeout) as response:
    return native_http.Response(response.status,dict(response.headers),response.read())
  def factory(source):
   current=remote.Foreground(source,open_url=buffered_open if self.buffered else self.fixture.open)
   self.sources.append(current);return current
  self.broker=remote.Broker(source_factory=factory)
  self.home=SimpleNamespace(getProperty=lambda key:self.broker.url)
  self.enabled=mock.patch.object(remote,'KODI_PLAYBACK',True);self.enabled.start()
  self.budget=mock.patch.object(remote,'FIRST_ANSWER',.3);self.budget.start()
  self.selected=mock.patch.object(remote.umbrella_recovery,'selected',return_value=None);self.selected.start()
 def tearDown(self):
  self.fixture.release.set()
  self.broker.close();self.fixture.close()
  self.selected.stop();self.budget.stop();self.enabled.stop()
 def wait_until(self,predicate,limit=1):
  deadline=time.monotonic()+limit
  while not predicate() and time.monotonic()<deadline:time.sleep(.01)
  self.assertTrue(predicate())
 def test_headers_only_do_not_qualify_as_a_ready_cache(self):
  answer=remote._call(self.broker.url,{'action':'open','source':self.SRC,'player':'kodi'})
  self.assertTrue(self.fixture.headers_sent.wait(1))
  self.wait_until(lambda:self.sources[0].answered_size==len(DATA))
  self.assertNotIn(('media',0),self.sources[0].blocks.data)
  self.assertFalse(remote.answered(self.broker.url,answer['id'],limit=.1))
 def test_stalled_body_falls_back_within_budget_and_releases_the_cache(self):
  began=time.monotonic();actual=remote.for_kodi(self.SRC,self.home);elapsed=time.monotonic()-began
  self.assertEqual(actual,self.SRC)
  self.assertLess(elapsed,1.5)
  self.assertIsNone(self.broker.current);self.assertFalse(self.broker.kodi)
  # A background request from the abandoned cache must not compete with the direct player.
  self.wait_until(lambda:self.fixture.live==0)
 def test_an_unready_proxy_head_still_waits_for_the_opening_block(self):
  answer=remote._call(self.broker.url,{'action':'open','source':self.SRC,'player':'kodi'})
  self.assertTrue(self.fixture.headers_sent.wait(1))
  began=time.monotonic()
  with self.assertRaises((TimeoutError,urllib.error.URLError)):
   urllib.request.urlopen(urllib.request.Request(answer['url'],method='HEAD'),timeout=.1)
  self.assertLess(time.monotonic()-began,.5)
  self.assertNotIn(('media',0),self.sources[0].blocks.data)
 def test_a_fast_first_block_cannot_hide_a_stalled_later_opening_block(self):
  source='https://fixture.invalid/tail-stall.mkv?token=synthetic-source-token'
  answer=remote._call(self.broker.url,{'action':'open','source':source,'player':'kodi'})
  current=self.broker.current
  self.wait_until(lambda:('media',0) in current.blocks.data)
  self.assertEqual(current.blocks.data[('media',0)],DATA[:remote.BLOCK])
  self.assertFalse(remote.answered(self.broker.url,answer['id'],limit=.1))
  began=time.monotonic();self.assertEqual(remote.for_kodi(source,self.home),source)
  self.assertLess(time.monotonic()-began,1.5);self.assertIsNone(self.broker.current)
  self.wait_until(lambda:self.fixture.live==0)
 def test_a_file_smaller_than_one_block_does_not_require_nonexistent_probe_blocks(self):
  source='https://fixture.invalid/small.mkv'
  target=remote.for_kodi(source,self.home)
  self.assertNotEqual(target,source)
  with urllib.request.urlopen(urllib.request.Request(target,method='HEAD'),timeout=1) as response:
   self.assertEqual(int(response.headers['Content-Length']),256*1024)
  with urllib.request.urlopen(urllib.request.Request(target,headers={'Range':'bytes=10-109'}),timeout=1) as response:
   self.assertEqual(response.read(),DATA[10:110])
 def test_native_buffered_one_piece_answer_is_not_a_completed_opening_block(self):
  self.buffered=True
  source='https://fixture.invalid/buffered-piece-stall.mkv?token=synthetic-source-token'
  began=time.monotonic();target=remote.for_kodi(source,self.home);elapsed=time.monotonic()-began
  self.assertEqual(target,source);self.assertLess(elapsed,1.5)
  self.assertNotIn(('media',0),self.sources[0].blocks.data)
  self.assertIsNone(self.broker.current)
  # Buffering system/native networking cannot expose a response to close until it returns: bound its own call.
  self.assertTrue(self.native_timeouts);self.assertLessEqual(max(self.native_timeouts),remote.FIRST_ANSWER+.1)
  self.wait_until(lambda:self.fixture.live==0,limit=1.5)
 def test_later_native_probe_calls_share_the_original_opening_deadline(self):
  self.buffered=True
  source='https://fixture.invalid/delayed-tail-stall.mkv'
  began=time.monotonic();self.assertEqual(remote.for_kodi(source,self.home),source)
  self.assertGreater(len(self.native_calls),remote.SPLIT)  # block0 completed before later probes were launched
  self.assertLessEqual(max(started+timeout for started,timeout in self.native_calls),began+remote.FIRST_ANSWER+.06)
  self.wait_until(lambda:self.fixture.live==0)
 def test_fast_source_uses_actual_cached_bytes_for_head_and_resume_range(self):
  began=time.monotonic();target=remote.for_kodi(self.FAST,self.home)
  self.assertNotEqual(target,self.FAST);self.assertTrue(target.startswith('http://127.0.0.1:'))
  self.assertLess(time.monotonic()-began,1.5)
  with urllib.request.urlopen(urllib.request.Request(target,method='HEAD'),timeout=1) as response:
   self.assertEqual(int(response.headers['Content-Length']),len(DATA))
  start=remote.BLOCK+37;end=start+1234
  with urllib.request.urlopen(urllib.request.Request(target,headers={'Range':'bytes=%d-%d'%(start,end)}),timeout=2) as response:
   self.assertEqual(response.status,206);self.assertEqual(response.read(),DATA[start:end+1])
  self.assertEqual(remote.original(target,self.home),self.FAST)
  self.assertLessEqual(self.fixture.peak,remote.PIECES)
 def test_fallback_preserves_original_signed_query_and_provider_headers(self):
  self.assertEqual(remote.for_kodi(self.SRC,self.home),self.SRC)
  self.assertTrue(self.fixture.requests)
  for path,headers in self.fixture.requests:
   self.assertEqual(path,'/stall.mkv?token=synthetic-source-token')
   self.assertEqual(headers['User-Agent'],'Fixture Player')
   self.assertEqual(headers['Authorization'],'Bearer synthetic-auth');self.assertEqual(headers['Cookie'],'test=synthetic-cookie')
   self.assertTrue(headers['Range'].startswith('bytes='))
 def test_source_diagnostics_never_expose_url_or_provider_secrets(self):
  remote._call(self.broker.url,{'action':'open','source':self.SRC,'player':'kodi'})
  self.assertTrue(self.fixture.headers_sent.wait(1))
  ident=self.broker.ident;secret=self.broker.secret;logged=[]
  diagnostics=json.dumps(remote.stats(self.home))
  xbmc=SimpleNamespace(log=lambda message,level:logged.append(message),LOGINFO=1)
  with mock.patch.dict(sys.modules,{'xbmc':xbmc}):self.assertEqual(remote.for_kodi(self.SRC,self.home),self.SRC)
  opening=[line for line in logged if 'stream opening' in line]   # ISSUE-317: the read/block trace lines are checked below too
  self.assertEqual(len(opening),1);self.assertIn('route=direct',opening[0]);self.assertIn('blocks=',opening[0])
  diagnostics+='\n'.join(logged)
  for private in ('fixture.invalid','synthetic-source-token','synthetic-auth','synthetic-cookie',ident,secret,self.SRC):
   self.assertNotIn(private,diagnostics)
 def test_failed_opening_does_not_poison_the_next_fast_source(self):
  self.assertEqual(remote.for_kodi(self.SRC,self.home),self.SRC)
  abandoned=self.sources[0]
  target=remote.for_kodi(self.FAST,self.home)
  self.assertNotEqual(target,self.FAST);self.assertIsNot(self.broker.current,abandoned)
  with urllib.request.urlopen(urllib.request.Request(target,headers={'Range':'bytes=0-99'}),timeout=2) as response:
   self.assertEqual(response.read(),DATA[:100])
  self.wait_until(lambda:not abandoned.blocks.pending)
 def test_wrong_range_headers_do_not_qualify_as_ready_or_change_the_original_link(self):
  source='https://fixture.invalid/wrong-range.mkv?token=synthetic-source-token|Authorization=Bearer%20synthetic-auth'
  self.assertEqual(remote.for_kodi(source,self.home),source)
  self.assertIsNone(self.broker.current)


if __name__=='__main__':unittest.main()
