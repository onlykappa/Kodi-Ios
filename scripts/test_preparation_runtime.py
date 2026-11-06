"""Worker liveness, suspension policy and safe connection diagnostics."""
import json,sys,tempfile,time,unittest,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import background,preparation_runtime as runtime
class Runtime(unittest.TestCase):
 def test_heartbeat_survives_a_slow_probe_then_expires_after_exit(self):
  with tempfile.TemporaryDirectory() as profile:
   with runtime.Lease(profile,stats=lambda:dict(bytes_read=4096),every=.01) as lease:
    lease.phase('Inspecting video',title='Film')
    time.sleep(.04)
    self.assertTrue(runtime.active())
    item=runtime.read(profile);self.assertEqual(item['phase'],'Inspecting video')
    self.assertFalse(item['known']);self.assertEqual(item['bytes_read'],4096)
   self.assertFalse(runtime.active());self.assertEqual(runtime.read(profile),{})
   path=runtime.location(profile);path.write_text(json.dumps(dict(updated=10)))
   self.assertEqual(runtime.read(profile,clock=lambda:26),{})
 def test_only_actionable_jobs_keep_background_service_armed(self):
  for state in ({},{'jobs':{'x':{'status':'done'}}},{'jobs':{'x':{'status':'waiting','blocked':True}}},{'jobs':{'x':{'kept':True}}}):
   self.assertFalse(runtime.pending(state))
  for state in ({'staging_cleanup':{'x':1}},{'jobs':{'x':{'status':'retry','retry_at':99999999}}}):self.assertTrue(runtime.pending(state))
 def test_errors_include_reason_without_signed_urls(self):
  self.assertIn('timed out',runtime.problem(urllib.error.URLError(TimeoutError())))
  self.assertIn('refused',runtime.problem(urllib.error.URLError(ConnectionRefusedError())))
  self.assertIn('certificate',runtime.problem(urllib.error.URLError('CERTIFICATE_VERIFY_FAILED')))
  self.assertNotIn('secret',runtime.problem(RuntimeError('read https://drive.example/movie?token=secret failed')))
 def test_keeper_rechecks_toggle_and_stops_after_work_completes(self):
  reasons=iter(['queued preparation','queued preparation','',''])
  calls=[];ticks=[0];logs=[]
  def wait(seconds):ticks[0]+=1;return ticks[0]>=4
  background.watch(calls.append,lambda:next(reasons),wait,logs.append,status=lambda:-2)
  self.assertEqual(calls,[1,1,0]);self.assertTrue(any('interrupted' in line for line in logs))
if __name__=='__main__':unittest.main()
