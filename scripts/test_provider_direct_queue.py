"""Resolved backup HTTP videos use the existing resumable Drive copier, never the torrent API."""
import io,os,sys,tempfile,threading,time,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import debrid_drive as dd
from test_debrid_drive import FakeDrive
class Reply(io.BytesIO):
 def __init__(self,data=b'x',code=206,span='bytes 0-0/3'):super().__init__(data);self.headers={'Content-Range':span};self.code=code
 def getcode(self):return self.code
class NoTorrent:
 def __getattr__(self,key):raise AssertionError('Torrent API called: '+key)
class Direct(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.profile=self.tmp.name
  self.request={'media_type':'movie','title':'Fall','year':2022,'tmdb':'1','quality':'1080p'}
  self.candidate={'provider':'jacktook','name':'Fall.2022.1080p.mkv','_id':'release'}
  self.url='https://fixture.invalid/video.mkv|Authorization=Bearer%20synthetic&User-Agent=Fixture'
 def queue(self,**kw):return dd.queue_direct(self.profile,self.url,self.candidate,self.request,open_url=kw.pop('open_url',lambda *a,**k:Reply()),**kw)
 def test_standalone_probe_returns_exact_size_without_queue_side_effects(self):
  calls=[]
  def opened(req,timeout):calls.append(req);return Reply()
  self.assertEqual(dd.probe_direct(self.url,open_url=opened),3)
  self.assertFalse(dd.location(self.profile).exists());self.assertEqual(len(calls),1)
  self.assertEqual(calls[0].get_header('Range'),'bytes=0-0')
 def test_missing_and_expired_probe_is_rejected_without_queue(self):
  for code in (401,403,404,410,500):
   def fail(*args,**kwargs):raise urllib.error.HTTPError('https://fixture.invalid',code,'unavailable',{},None)
   with self.assertRaises(urllib.error.HTTPError):dd.probe_direct(self.url,open_url=fail)
   with self.assertRaises(urllib.error.HTTPError):self.queue(open_url=fail)
  self.assertFalse(dd.load(self.profile)['jobs'])
 def test_direct_bytes_copy_without_any_torrent_api(self):
  job=self.queue();self.assertEqual(job['status'],'copying');self.assertTrue(job['files'][0]['direct'])
  drive=FakeDrive();seen=[]
  def read(url,offset):seen.append((url,offset));return io.BytesIO(b'abc'[offset:])
  dd.step(self.profile,NoTorrent(),drive,open_url=read)
  self.assertEqual(drive.data,b'abc');self.assertEqual(dd.load(self.profile)['jobs'][0]['status'],'done')
  self.assertEqual(seen,[(self.url,0)])
 def test_native_copy_keeps_source_headers_out_of_url(self):
  self.queue();seen=[]
  class Native(FakeDrive):
   def copy_piece(inner,source,source_headers,target,headers,offset,count,total,timeout):
    seen.append((source,source_headers,offset))
    return inner.call('PUT',target,b'abc'[offset:offset+count],{'Content-Range':'bytes %d-%d/%d'%(offset,offset+count-1,total)})
  drive=Native()
  dd.step(self.profile,NoTorrent(),drive,open_url=lambda *a:(_ for _ in ()).throw(AssertionError('Python media read')))
  self.assertEqual(drive.data,b'abc');self.assertEqual(seen,[('https://fixture.invalid/video.mkv',{'Authorization':'Bearer synthetic','User-Agent':'Fixture'},0)])
 def test_canceled_download_never_contacts_source_or_torrent(self):
  job=self.queue();drive=FakeDrive()
  dd.step(self.profile,NoTorrent(),drive,cancelled=lambda:{job['hash']},open_url=lambda *a:(_ for _ in ()).throw(AssertionError('read after cancel')))
  self.assertEqual(dd.load(self.profile)['jobs'][0]['status'],'failed');self.assertEqual(drive.data,b'')
 def test_invalid_direct_companion_never_hits_torrent_api(self):
  self.assertEqual(dd.companions({},[{'hash':'a'*40,'status':'new','direct_source':True,'files':[]}],NoTorrent(),lambda:0),[])
 def test_probe_requires_verified_exact_range_and_never_reads_movie(self):
  for response in (Reply(code=200),Reply(span='bytes 0-1/3'),Reply(data=b'xx'),Reply(span='bytes 0-0/0')):
   with self.assertRaises(ValueError):self.queue(open_url=lambda *a,**k:response)
  self.assertFalse(dd.load(self.profile)['jobs'])
 def test_probe_headers_and_pending_dedup_and_private_file(self):
  calls=[]
  def opening(req,timeout):calls.append((req,timeout));return Reply()
  first=self.queue(open_url=opening);second=self.queue()
  self.assertEqual(first['hash'],second['hash']);self.assertEqual(len(dd.load(self.profile)['jobs']),1)
  req,timeout=calls[0];self.assertEqual(req.get_header('Authorization'),'Bearer synthetic');self.assertEqual(req.get_header('Range'),'bytes=0-0')
  self.assertLessEqual(timeout,10);self.assertEqual(os.stat(dd.location(self.profile)).st_mode&0o777,0o600)
 def test_episode_identity_deduplicates_across_provider_versions(self):
  self.request.update(media_type='episode',show_title='Show',season=1,episode=2)
  self.candidate.update(name='Show.S01E02.1080p.mkv');first=self.queue()
  self.candidate.update(provider='pov',_id='other');second=self.queue()
  self.assertEqual(first['hash'],second['hash']);self.assertEqual(len(dd.load(self.profile)['jobs']),1)
 def test_pending_movie_deduplicates_across_backup_providers(self):
  first=self.queue();self.candidate.update(provider='pov',_id='other')
  second=self.queue();self.assertEqual(first['hash'],second['hash']);self.assertEqual(len(dd.load(self.profile)['jobs']),1)
 def test_broken_direct_state_never_becomes_a_torrent_request(self):
  for status in ('new','copying'):
   self.queue();state=dd.load(self.profile);state['jobs'][-1].update(status=status,files=[]);dd.save(self.profile,state)
   dd.step(self.profile,NoTorrent(),FakeDrive())
   self.assertEqual(dd.load(self.profile)['jobs'][-1]['status'],'failed')
 def test_cancellation_never_queues(self):
  from provider_fallback import Canceled
  with self.assertRaises(Canceled):self.queue(cancel=lambda:True)
  self.assertFalse(dd.load(self.profile)['jobs'])
 def test_owner_replaced_during_probe_cannot_enqueue(self):
  from provider_fallback import Canceled
  active=[True]
  class Replaced(Reply):
   def read(inner,size=-1):active[0]=False;return super().read(size)
  with self.assertRaises(Canceled):self.queue(open_url=lambda *a,**k:Replaced(),cancel=lambda:not active[0])
  self.assertFalse(dd.load(self.profile)['jobs'])
 def test_cancel_interrupts_stalled_probe_before_its_network_timeout(self):
  from provider_fallback import Canceled
  entered=threading.Event();release=threading.Event();canceled=threading.Event()
  class Stalled(Reply):
   def read(inner,size=-1):entered.set();release.wait(2);return b'x'
   def close(inner):release.set();super().close()
  def stop():entered.wait(1);canceled.set()
  thread=threading.Thread(target=stop);thread.start();started=time.monotonic()
  with self.assertRaises(Canceled):self.queue(open_url=lambda *a,**k:Stalled(),cancel=canceled.is_set)
  self.assertLess(time.monotonic()-started,.5);self.assertFalse(dd.load(self.profile)['jobs']);thread.join(1)
 def test_direct_open_preserves_headers_and_offset(self):
  with patch.object(dd.urllib.request,'urlopen',return_value=Reply()) as opener:
   dd.default_open(self.url,42)
  req=opener.call_args.args[0];self.assertEqual(req.full_url,'https://fixture.invalid/video.mkv');self.assertEqual(req.get_header('Range'),'bytes=42-');self.assertEqual(req.get_header('Authorization'),'Bearer synthetic')
 def test_expired_source_stops_without_unlocking_another_file(self):
  self.queue()
  def gone(*args):raise urllib.error.HTTPError('https://fixture.invalid',403,'expired',{},None)
  dd.step(self.profile,NoTorrent(),FakeDrive(),open_url=gone)
  job=dd.load(self.profile)['jobs'][0];self.assertEqual(job['status'],'failed');self.assertTrue(job['terminal'])
 def test_source_headers_cannot_inject_range_or_newline(self):
  self.assertEqual(dd.direct_parts('https://fixture.invalid/x|Range=bytes%3D1-2&Host=evil')[1],{})
  with self.assertRaises(ValueError):dd.direct_parts('https://fixture.invalid/x|Cookie=a%0D%0Ab')
if __name__=='__main__':unittest.main()
