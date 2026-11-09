"""Execute the service's real scheduling loop against isolated queue/control files."""
import ast,io,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0,str(LIB))
import prepare_downloads as prep,preparation_runtime as runtime,transfer_control as control,driveupload,diagnostics,work_state

class Scheduling(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.profile=Path(self.tmp.name)
  self.state={'jobs':{'one':{'source':{'id':'one','name':'Sample.mkv'},'status':'waiting','retry_after':0}}}
  prep.save(self.profile,self.state)
 def queue(self):
  q=prep.Queue(self.profile,object(),object());q.scan=lambda *a,**k:None
  return q
 def service_pass(self,q,uploads=False):
  tree=ast.parse((ROOT/'migration/bundled-bootstrap/service.py').read_text())
  fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='drive_uploads')
  loop=next(n for n in fn.body if isinstance(n,ast.While))
  calls=[];waits=[];logs=[]
  def wait(delay):waits.append(delay);return len(waits)>1
  def process(keep):self.assertTrue(keep());calls.append('started');return False
  q.process_one=process
  addon=types.SimpleNamespace(getSetting=lambda key:'',getSettingBool=lambda key:True)
  mods={'xbmcaddon':types.SimpleNamespace(Addon=lambda *a:addon)}
  env=dict(profile=self.profile,root=str(self.profile/'phone'),state=str(self.profile/'uploads.json'),
           delay=5,last_schedule=None,preparation=q,monitor=types.SimpleNamespace(waitForAbort=wait,abortRequested=lambda:False),
           accounts=types.SimpleNamespace(get_accounts=lambda:{'test':{}}),idle=lambda:True,log=logs.append,drive=object(),
           xbmcaddon=mods['xbmcaddon'],xbmcvfs=types.SimpleNamespace(translatePath=lambda p:''),
           urllib=__import__('urllib'),json=json,driveupload=driveupload,prepare_downloads=prep,transfer_control=control,
           diagnostics=diagnostics,work_state=work_state,drive_uploads=types.SimpleNamespace(told_signed_out=False),notices=types.SimpleNamespace(add=lambda *a:None))
  def upload(*args,**kwargs):
   self.assertTrue(args[4]());calls.append('uploaded');return 1
  pending=[{'path':'synthetic'}] if uploads else []
  with patch.dict(sys.modules,mods),patch('urllib.request.urlopen',return_value=io.BytesIO(b'[]')),\
       patch.object(driveupload,'pending',return_value=pending),patch.object(driveupload,'run_once',side_effect=upload):
   exec(compile(ast.Module(body=[loop],type_ignores=[]),'service-scheduling','exec'),env)
  return calls,waits,logs
 def test_idle_eligible_conversion_starts_automatically(self):
  calls,waits,logs=self.service_pass(self.queue());self.assertEqual(calls,['started']);self.assertEqual(waits,[5,20])
  self.assertTrue(any('"reason":"ready"' in line for line in logs))
 def test_idle_upload_runs_then_the_existing_conversion_starts(self):
  calls,_,_=self.service_pass(self.queue(),uploads=True)
  self.assertEqual(calls,['uploaded','started'])
 def test_saved_pause_without_an_explicit_start_is_respected_and_logged(self):
  control.set_paused(self.profile,'conv',True)
  calls,_,logs=self.service_pass(self.queue());self.assertEqual(calls,[])
  self.assertTrue(any('"reason":"owner_paused"' in line for line in logs))
 def test_old_pending_start_is_read_before_the_pause_skip(self):
  control.set_paused(self.profile,'conv',True)
  path=prep.location(self.profile).parent/prep.REQUESTS
  path.write_text(json.dumps([{'id':'one','action':'now'}]))
  q=self.queue();calls,waits,_=self.service_pass(q)
  self.assertEqual(calls,['started']);self.assertFalse(control.paused(self.profile,'conv'))
  self.assertEqual(prep.pending_requests(self.profile),[]);self.assertGreater(q.state['jobs']['one']['priority'],0)
 def test_new_start_resumes_immediately_without_unpausing_uploads(self):
  control.set_paused(self.profile,'conv',True);control.set_paused(self.profile,'up',True)
  prep.request(self.profile,'now','one')
  self.assertFalse(control.paused(self.profile,'conv'));self.assertTrue(control.paused(self.profile,'up'))
 def test_reorder_or_missing_or_blocked_start_does_not_clear_owner_pause(self):
  for action,ident in [('next','one'),('now','missing'),('up','one')]:
   control.set_paused(self.profile,'conv',True);prep.request(self.profile,action,ident)
   self.assertTrue(control.paused(self.profile,'conv'))
  self.state['jobs']['one']['blocked']=True;prep.save(self.profile,self.state)
  prep.request(self.profile,'now','one');self.assertTrue(control.paused(self.profile,'conv'))
 def test_schedule_distinguishes_retry_and_completed_work(self):
  self.state['jobs']['one']['retry_after']=200
  self.assertEqual(runtime.schedule(self.state,now=100)['reason'],'retry_wait')
  self.state['jobs']['one']['status']='done'
  self.assertEqual(runtime.schedule(self.state,now=100)['reason'],'no_jobs')
 def test_diagnostics_include_only_control_flags_and_request_count(self):
  control.set_paused(self.profile,'conv',True)
  path=prep.location(self.profile).parent/prep.REQUESTS;path.write_text(json.dumps([{'id':'private-file-id','action':'now'}]))
  result=diagnostics.snapshot(self.profile)
  self.assertTrue(result['controls']['conversion_paused']);self.assertEqual(result['controls']['preparation_requests'],1)
  self.assertNotIn('private-file-id',json.dumps(result))
if __name__=='__main__':unittest.main()
