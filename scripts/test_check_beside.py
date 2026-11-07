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

class ShowsWhatItDoes(unittest.TestCase):
 """Build 192 (owner: "stuck on starting / 67% or its not showing me what its doing")."""
 def test_card_names_the_step_while_nothing_moves(self):
  import library_rows
  props,points=library_rows.card({},'conv','Fall 2',100,'Finding where it left off')
  self.assertEqual((props['card.now'],points),('Finding where it left off',[]))
  self.assertEqual(library_rows.card({},'conv','Fall 2',100)[0]['card.now'],'starting')
 def test_a_resumed_movie_starts_at_its_place(self):
  import resume_store
  self.assertEqual(resume_store.mark_seconds('kr-resume 1\nin 0 0 1 1 2 4980.5\nin 1 0 0 0 9 4981.0\nin 2 1 0 0 0 0.0\n'),4981.0)
  self.assertEqual(resume_store.mark_seconds(''),0.0)
  cloud=(LIB/'prepare_cloud.py').read_text()
  self.assertIn("converted=[min(80,80*resume_store.mark_seconds(checkpoint['mark'])/duration) if checkpoint and duration else 0]",cloud)
  self.assertIn("progress('Converting',converted[0])",cloud);self.assertNotIn("progress('Converting and saving to Drive'",cloud)
  self.assertIn("library_rows.card(transfer_history.load(profile),s['card'],s['title'],time.time(),s.get('step',''))",(BOOT/'library_status.py').read_text())
 def test_drive_reads_are_logged_while_converting(self):
  svc=(BOOT/'service.py').read_text()
  self.assertIn("log('preparation: Drive reads: %.1f MB in %.0f s (%.2f MB/s), last read %s ago%s'",svc)
 def test_the_unit_a_resume_waits_for_is_finding(self):
  c=(ROOT/'migration/airplay-ios/remux/src/kr_prepare.c').read_text()
  self.assertIn('g->resuming?4:g->is_video?0:1',c);self.assertIn('for(int i=0;i<TRACKS;i++)gens[i].resuming=0;',c)

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
