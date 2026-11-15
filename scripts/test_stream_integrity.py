"""Foreground stream integrity and cancellation: fake upstream only, no provider/account state."""
import io,sys,threading,time,types,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import remote_media as remote

DATA=bytes(range(256))*(5*1024*1024//256)
SOURCE='https://fixture.invalid/episode.mkv'

def bounds(request):return tuple(map(int,request.get_header('Range')[6:].split('-')))

class Reply(io.BytesIO):
 def __init__(self,start,end,total=None,data=DATA):
  total=len(data) if total is None else total
  super().__init__(data[start:min(end,len(data)-1)+1]);self.status=206
  self.headers={'Content-Range':'bytes %d-%d/%d'%(start,min(end,len(data)-1),total)}

class Integrity(unittest.TestCase):
 def source(self,opener):
  source=remote.Foreground(SOURCE,open_url=opener);self.addCleanup(source.close);return source
 def test_mixed_parallel_content_range_totals_cannot_publish_a_cache_block(self):
  def open(request,timeout):
   start,end=bounds(request);return Reply(start,end,len(DATA)+(17 if start else 0))
  source=self.source(open)
  with self.assertRaises(ConnectionError):source.blocks.get('media',0)
  self.assertNotIn(('media',0),source.blocks.data)
  self.assertNotIn('media',source.blocks.sizes)
  self.assertFalse(source.blocks.pending)
 def test_in_range_416_piece_is_not_treated_as_a_shorter_successful_block(self):
  second=remote.BLOCK//remote.SPLIT
  def open(request,timeout):
   start,end=bounds(request)
   if start==second:raise urllib.error.HTTPError(SOURCE,416,'Fixture missing in-range piece',{},None)
   return Reply(start,end)
  source=self.source(open)
  with self.assertRaisesRegex(ConnectionError,'complete range'):source.blocks.get('media',0)
  self.assertNotIn(('media',0),source.blocks.data);self.assertFalse(source.blocks.pending)
 def test_genuine_end_of_file_inside_the_first_split_block_is_valid(self):
  data=DATA[:512*1024]
  def open(request,timeout):
   start,end=bounds(request)
   if start>=len(data):raise urllib.error.HTTPError(SOURCE,416,'Fixture EOF',{},None)
   return Reply(start,end,data=data)
  source=self.source(open)
  self.assertEqual(source.blocks.get('media',0),data)
  self.assertEqual(source.blocks.sizes['media'],len(data))
 def test_wrong_piece_end_never_publishes_partial_data(self):
  def open(request,timeout):
   start,end=bounds(request);reply=Reply(start,end)
   reply.headers['Content-Range']='bytes %d-%d/%d'%(start,max(start,end-1),len(DATA))
   return reply
  source=self.source(open)
  with self.assertRaises(ConnectionError):source.blocks.get('media',0)
  self.assertNotIn(('media',0),source.blocks.data)
 def test_renewal_finishing_after_cancellation_cannot_open_the_fresh_link(self):
  calls=[]
  def open(request,timeout):
   calls.append(request.full_url);raise urllib.error.HTTPError(SOURCE,403,'Fixture expiry',{},None)
  source=self.source(open)
  def renew(attempted):source.remote_url='https://fixture.invalid/fresh.mkv';source.cancelled.set();return True
  with patch.object(source,'_renew',side_effect=renew):
   with self.assertRaises(remote._SourceClosed):source._fetch('media',0,99)
  self.assertEqual(calls,[SOURCE])
 def test_renewal_finishing_after_opening_deadline_cannot_open_the_fresh_link(self):
  calls=[]
  def open(request,timeout):
   calls.append(request.full_url);raise urllib.error.HTTPError(SOURCE,403,'Fixture expiry',{},None)
  source=self.source(open);source.opening_deadline=time.monotonic()+10
  def renew(attempted):source.remote_url='https://fixture.invalid/fresh.mkv';source.opening_deadline=time.monotonic()-1;return True
  with patch.object(source,'_renew',side_effect=renew):
   with self.assertRaises(remote._SourceClosed):source._fetch('media',0,99)
  self.assertEqual(calls,[SOURCE])
 def test_fresh_link_receives_only_the_budget_remaining_after_renewal(self):
  calls=[]
  def open(request,timeout):
   calls.append(timeout)
   if len(calls)==1:raise urllib.error.HTTPError(SOURCE,403,'Fixture expiry',{},None)
   return Reply(*bounds(request))
  source=self.source(open);source.opening_deadline=time.monotonic()+10
  def renew(attempted):source.remote_url='https://fixture.invalid/fresh.mkv';source.opening_deadline=time.monotonic()+.1;return True
  with patch.object(source,'_renew',side_effect=renew):self.assertEqual(source._fetch('media',0,99)[0],DATA[:100])
  self.assertEqual(len(calls),2);self.assertGreater(calls[0],1);self.assertLessEqual(calls[1],.1)

class BlockingUpstream:
 """Socket shutdown releases a blocked body read; a shared counter observes the actual response lifetime."""
 def __init__(self,target):
  self.target=target;self.lock=threading.Lock();self.opened=0;self.active=0;self.peak=0;self.shutdowns=0
  self.entered=threading.Event();self.release=threading.Event();self.responses=[]
 def open(self,request,timeout):
  start,end=bounds(request);outer=self
  with self.lock:
   self.opened+=1;self.active+=1;self.peak=max(self.peak,self.active)
  class Socket:
   def shutdown(self,how):
    with outer.lock:outer.shutdowns+=1
    outer.release.set()
  class Response:
   status=206
   def __init__(self):
    self.headers={'Content-Range':'bytes %d-%d/%d'%(start,end,len(DATA))};self.closed=False;self.at=0
    self.fp=types.SimpleNamespace(raw=types.SimpleNamespace(_sock=Socket()))
   def read(self,size):
    with outer.lock:
     if len(outer.responses)>=outer.target:outer.entered.set()
    if not outer.release.wait(3):raise TimeoutError('Fixture body did not release')
    body=DATA[start+self.at:min(end+1,start+self.at+size)];self.at+=len(body);return body
   def close(self):
    with outer.lock:
     if not self.closed:self.closed=True;outer.active-=1
  response=Response()
  with self.lock:self.responses.append(response)
  return response

class Cancellation(unittest.TestCase):
 def setUp(self):self.threads=[];self.errors=[];self.fixture=None;self.source=None
 def tearDown(self):
  if self.fixture:self.fixture.release.set()
  if self.source:self.source.close()
  for thread in self.threads:thread.join(3)
 def start(self,action):
  def run():
   try:action()
   except BaseException as error:self.errors.append(error)
  thread=threading.Thread(target=run,daemon=True);self.threads.append(thread);thread.start()
 def assert_settled(self):
  for thread in self.threads:thread.join(2);self.assertFalse(thread.is_alive())
  self.assertTrue(self.errors)
  self.assertTrue(all(isinstance(error,remote._SourceClosed) for error in self.errors),[type(error).__name__ for error in self.errors])
 def test_close_interrupts_four_split_reads_without_retries_or_cache_publication(self):
  self.fixture=BlockingUpstream(remote.SPLIT);self.source=remote.Foreground(SOURCE,open_url=self.fixture.open)
  self.start(lambda:self.source.blocks.get('media',0));self.assertTrue(self.fixture.entered.wait(2))
  began=time.monotonic();self.source.close();self.assertLess(time.monotonic()-began,1.5)
  self.assert_settled()
  self.assertEqual(self.fixture.opened,remote.SPLIT)
  self.assertGreaterEqual(self.fixture.shutdowns,1);self.assertEqual(self.fixture.active,0)
  self.assertNotIn(('media',0),self.source.blocks.data);self.assertFalse(self.source.blocks.pending)
 def test_connection_cap_includes_unsplit_requests_and_queued_reads_never_open_after_close(self):
  self.fixture=BlockingUpstream(remote.PIECES);self.source=remote.Foreground(SOURCE,open_url=self.fixture.open)
  for _ in range(remote.PIECES+4):self.start(lambda:self.source._fetch('media',0,99))
  self.assertTrue(self.fixture.entered.wait(2));self.assertEqual(self.fixture.opened,remote.PIECES)
  self.source.close();self.assert_settled()
  self.assertEqual(self.fixture.opened,remote.PIECES);self.assertEqual(self.fixture.peak,remote.PIECES)
  self.assertEqual(self.fixture.active,0)
 def test_the_unsplit_connection_cap_is_released_after_successful_bodies(self):
  self.fixture=BlockingUpstream(remote.PIECES);self.source=remote.Foreground(SOURCE,open_url=self.fixture.open)
  for _ in range(remote.PIECES+4):self.start(lambda:self.assertEqual(self.source._fetch('media',0,99)[0],DATA[:100]))
  self.assertTrue(self.fixture.entered.wait(2));self.assertEqual(self.fixture.opened,remote.PIECES)
  self.fixture.release.set()
  for thread in self.threads:thread.join(2);self.assertFalse(thread.is_alive())
  self.assertFalse(self.errors,[type(error).__name__ for error in self.errors])
  self.assertEqual(self.fixture.opened,remote.PIECES+4);self.assertLessEqual(self.fixture.peak,remote.PIECES)
  self.assertEqual(self.fixture.active,0)

if __name__=='__main__':unittest.main()
