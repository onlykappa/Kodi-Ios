"""Build 192 (owner, build 191): a converted Interstellar "takes forever" to open; Library › Movies "takes a few
seconds" with Kodi's "Kodi iOS ..." box over the page; a clean loading circle. Older conversions are re-packed into
r32's layout after everything else; the Library page shows the saved Drive list at once and the service refreshes it."""
import json,os,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True;sys.path[:0]=[str(LIB)]
import prepare_downloads as prep,drivelibrary,driveupload

def item(profile,md5='abc'):return {'id':'f','name':'Interstellar (2014).mp4','md5Checksum':md5,'size':'9','version':'1','appProperties':{prep.PROPERTY:profile,prep.CHECKSUM_PROPERTY:md5}}

class Repack(unittest.TestCase):
 def test_old_layout_still_plays_but_is_repacked(self):
  old=item('source-resolution-mp4-v1');new=item(prep.PROFILE)
  self.assertTrue(prep.ready(old));self.assertTrue(prep.repack_due(old))
  self.assertTrue(prep.ready(new));self.assertFalse(prep.repack_due(new))
  self.assertFalse(prep.repack_due(item('something-else')))
 def test_repacks_go_after_everything_else(self):
  jobs={'r':{'repack':True},'a':{'source':{'name':'Fall.2.2026.mkv'}},'n':{'priority':5,'repack':True}}
  self.assertEqual([k for k,_ in sorted(jobs.items(),key=lambda p:prep.order_key(*p))],['n','a','r'])   # Start now still wins
 def test_wiring(self):
  cloud=(LIB/'prepare_cloud.py').read_text();scan=(LIB/'prepare_downloads.py').read_text()
  self.assertIn("if prep.ready(current):",cloud)
  self.assertIn("doing='Making it start faster' if job.get('repack') else 'Converting'",cloud)
  self.assertNotIn("'repack':True",scan)

class Lists(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.dir=self.tmp.name
 def tearDown(self):self.tmp.cleanup()
 def save(self,cache):Path(self.dir,'drive-library.json').write_text(json.dumps(cache))
 def test_the_page_shows_the_saved_list_whatever_its_age(self):
  self.save({'movie:':{'time':0,'entries':[{'title':'Fall'}],'driveid':'d'}})
  self.assertEqual(drivelibrary.listing('movie',self.dir,stale_ok=True,now=lambda:10**9),([{'title':'Fall'}],'d'))
 def test_an_upload_marks_lists_stale_and_keeps_them(self):
  self.save({'movie:':{'time':123,'entries':[1],'driveid':'d'},'tv:x':{'time':5,'entries':[],'driveid':'d'}})
  driveupload.invalidate_library(self.dir)
  cache=json.loads(Path(self.dir,'drive-library.json').read_text())
  self.assertEqual((cache['movie:']['time'],cache['movie:']['entries'],cache['tv:x']['time']),(0,[1],0))
 def test_the_service_lists_stale_and_missing_lists_again(self):
  self.save({'movie:':{'time':1000,'entries':[],'driveid':'d'},'tv:x':{'time':0,'entries':[],'driveid':'d'}})
  calls=[];old=drivelibrary.listing
  drivelibrary.listing=lambda kind,state_dir,folder=None,**kw:calls.append((kind,folder,kw.get('fresh')))
  try:done=drivelibrary.refresh_stale(self.dir,now=lambda:1100)
  finally:drivelibrary.listing=old
  self.assertEqual(done,['tv:','tv:x']);self.assertEqual(calls,[('tv',None,True),('tv','x',True)])   # movie: is 100 s old
 def test_wiring(self):
  page=(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_library.py').read_text()
  self.assertEqual(page.count('stale_ok=True)'),3);self.assertIn("'Kodi iOS Library: %s page in %.2f s'",page)
  self.assertIn('done=drivelibrary.refresh_stale(state_dir)',(BOOT/'service.py').read_text())

if __name__=='__main__':unittest.main()
