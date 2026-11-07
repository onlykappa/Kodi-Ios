"""Owner (build 190): "If i press refresh in the library status it doesnt do anything", and Fall 2 "seems to be frozen".
A library check asked for while a movie converts runs beside it (it used to wait hours for the movie to finish); it
never touches the converting card, the converting movie's job or its source file. Lining up after a restart reports
"Finding where it left off"."""
import sys,tempfile,threading,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True;sys.path[:0]=[str(LIB)]
import prepare_downloads as prep

def item(i,name):return {'id':i,'name':name,'size':'10','md5Checksum':'m'+i,'version':'1','parents':['movies'],'appProperties':{}}

class Beside(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.q=prep.Queue(self.tmp.name,None,None)
  fall=item('fall','Fall.2.Deadpoint.2026.2160p.mkv');self.fall=prep.key(fall)
  self.q.state['jobs']={self.fall:{'source':fall,'status':'waiting'}}
  self.q.state['current']={'title':fall['name'],'stage':'Step 3 of 3 · Converting','running':True,'progress':67}
  self.listed=[dict(item('new','Inception.2010.2160p.mkv'),folderName='Movies')]   # Fall 2's source is not listed
 def tearDown(self):self.tmp.cleanup()
 def run_scan(self,beside):
  meta={'new':item('new','Inception.2010.2160p.mkv')}
  with mock.patch.object(prep.library_scan,'remote_files',return_value=self.listed),mock.patch.object(prep,'metadata',side_effect=lambda d,i:meta[i]):
   self.q.scan(force=True,beside=beside)
 def test_a_check_beside_a_conversion(self):
  self.run_scan(True)
  self.assertEqual(self.q.state['current']['stage'],'Step 3 of 3 · Converting')   # the converting card stays
  self.assertIn(self.fall,self.q.state['jobs'])                                 # the converting movie keeps its job
  self.assertEqual(len(self.q.state['jobs']),2);self.assertIn('checked',self.q.state['library'])
  self.assertNotIn('checking',self.q.state)
 def test_one_check_at_a_time(self):
  self.q.scanning.acquire()
  try:self.run_scan(True)   # returns at once: the main loop is checking
  finally:self.q.scanning.release()
  self.assertNotIn('library',self.q.state)
 def test_commit_writes_again_if_a_job_changed_meanwhile(self):
  calls=[]
  def save(profile,state):
   calls.append(1)
   if len(calls)==1:raise RuntimeError('dictionary changed size during iteration')
  with mock.patch.object(prep,'save',side_effect=save):self.q.commit()
  self.assertEqual(len(calls),2)

class Wiring(unittest.TestCase):
 def test_service_and_queue(self):
  svc=(BOOT/'service.py').read_text();cloud=(LIB/'prepare_cloud.py').read_text()
  self.assertIn("if q.busy and prepare_downloads.check_requested(profile):",svc)
  self.assertIn("q.scan(lambda:not monitor.abortRequested(),force=True,beside=True)",svc)
  self.assertIn("preparation.busy=True",svc);self.assertIn("finally:preparation.busy=False",svc)
  self.assertIn("with q.lock:   # build 191",cloud)
  self.assertIn("progress('Finding where it left off',converted[0]);return",cloud)
  self.assertIn('tick(cb,ctx,4,',(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text())

if __name__=='__main__':unittest.main()
