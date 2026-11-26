"""The AllDebrid sign-in screens, the stream wording and the peers line (UI wiring, host tests; the rig shows how they look)."""
import sys,threading,time,types,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import accounts,debrid_signin_ui as ui,debrid_token as dt,torrent_prompt as tp,choice_sheet as cs,source_contract as c,backup_playback as bp,p2p_rules as p2p
from test_debrid_account import Service,Clock
import tempfile

class Accounts(unittest.TestCase):
 def test_alldebrid_row_follows_the_own_sign_in(self):
  s=[x for x in accounts.SERVICES if x['key']=='alldebrid'][0]
  off=accounts.status(s,True,lambda k:'',own=lambda k:False);on=accounts.status(s,True,lambda k:'',own=lambda k:True)
  self.assertEqual((off['signed'],off['text'],off['button']),(False,'Not signed in','Sign In'));self.assertEqual((on['signed'],on['text'],on['button']),(True,'Signed in',''))
  self.assertIn('debrid_signin_page',off['action']);self.assertTrue(on['action'].endswith(',manage)'))
 def test_the_row_sits_in_streaming_and_sources_and_ids_stay_inside_the_service_range(self):
  keys=[x['key'] for x in accounts.SERVICES];self.assertEqual(accounts.SERVICES[keys.index('alldebrid')]['section'],0);self.assertLess(len(accounts.SERVICES),10,'service buttons are 9601..9609; links start at 9611')
  props=accounts.properties([{'signed':False,'text':'x','button':'','action':''}]*len(accounts.SERVICES),'Me');self.assertEqual(props['acct.%d.name'%(keys.index('alldebrid')+1)],'AllDebrid')

class Sheets(unittest.TestCase):
 def test_wording_is_plain_and_fits_the_sheet(self):
  spec=ui.pin_spec('ABCD');self.assertEqual(spec['rows'][0]['label'],'A B C D')
  for s in (spec,ui.signed_in_spec()):
   props=cs.properties(s);texts=[s['heading'],s['sub']]+[r['label'] for r in s['rows']]+[r['detail'] for r in s['rows']]
   for t in texts:self.assertNotIn('…',t);self.assertNotIn('...',t)
   for r in s['rows']:t,d=cs.shape(r);self.assertLessEqual((t,d),(3,2))
 def test_failure_texts_name_one_recovery_step_and_never_a_code_or_link(self):
  for kind,(title,text) in ui.OUTCOME_TEXT.items():
   self.assertTrue(text.endswith('.'));self.assertNotIn('http',title+text);self.assertNotIn('…',title+text)

class Flow(unittest.TestCase):
 def setUp(self):self.dir=tempfile.TemporaryDirectory();self.addCleanup(self.dir.cleanup);self.notes=[];self.closed=[]
 def notify(self,*a):self.notes.append(a)
 def run_it(self,svc,choose,**k):
  clk=Clock();return ui.run(choose,lambda:self.closed.append(1),self.notify,svc,profile=self.dir.name,sleep=lambda d:(time.sleep(.01),setattr(clk,'t',clk.t+d)),clock=lambda:clk.t,**k)
 def test_success_closes_the_sheet_by_itself_and_says_so_once(self):
  svc=Service(2);gate=threading.Event()
  def choose(spec):
   self.assertEqual(spec['rows'][0]['label'],'A B C D');gate.set();time.sleep(.5);return -1
  self.assertEqual(self.run_it(svc,choose),'signed-in');self.assertTrue(self.closed);self.assertEqual(self.notes,[('info','AllDebrid is signed in','Downloads and streams can use it now.')]);self.assertTrue(dt.own(self.dir.name))
 def test_cancel_leaves_nothing_behind(self):
  svc=Service(10**6);self.assertEqual(self.run_it(svc,lambda spec:-1),'canceled');self.assertEqual(self.notes,[]);self.assertFalse(dt.own(self.dir.name))
 def test_failure_is_one_problem_notice_with_one_step(self):
  self.assertEqual(self.run_it(Service(fail='MAINTENANCE'),lambda spec:-1),c.OFFLINE);self.assertEqual(self.notes[0][:2],('problem','AllDebrid could not be reached'))
 def test_sign_out_asks_first_then_removes_only_the_app_key(self):
  dt.save_own('KEY',self.dir.name)
  self.assertEqual(self.run_it(Service(),lambda spec:-1),'canceled');self.assertTrue(dt.own(self.dir.name))
  self.assertEqual(self.run_it(Service(),lambda spec:0),'signed-out');self.assertFalse(dt.own(self.dir.name));self.assertEqual(self.notes[-1][1],'AllDebrid signed out')

class Wording(unittest.TestCase):
 def test_the_stream_prompt_says_stream_and_the_download_prompt_is_unchanged(self):
  found={'state':'direct','route':'en0','tunnels':[]};text,yes=tp.message(found,stream=True);self.assertIn('stream',text.lower());self.assertEqual(yes,'Stream anyway');self.assertNotIn('download',text.lower())
  self.assertEqual(tp.message(found)[1],'Download anyway')
  for state in ('direct','unknown','tunnel'):
   body=tp.message({'state':state},stream=True)[0].split('\n\n')[0];self.assertLessEqual(len(body),90,'Kodi\'s question box shows about three lines of body; longer text is clipped (seen on the rig)')
  d=MagicMock();d.yesno.return_value=True;self.assertTrue(tp.ask(found,d,stream=True));self.assertEqual(d.yesno.call_args.args[0],tp.STREAM_HEADING);self.assertEqual(d.yesno.call_args.kwargs['nolabel'],'Cancel')
  d.yesno.return_value=False;self.assertFalse(tp.ask({'state':'tunnel','route':'utun3','tunnels':['utun3']},d,stream=True))
 def test_peers_line_counts_down_each_second_of_the_wait(self):
  class P:
   def __init__(s):s.t=0;s.running=False
   def play(s,u,h,r=0):s.running=True
   def time(s):return 0.0
   def stop(s):s.running=False
  clk=[0.0];ticks=[];pb=bp.Playback(P(),clock=lambda:clk[0],sleep=lambda d:clk.__setitem__(0,clk[0]+d))
  with self.assertRaises(c.Outcome):pb.start_resolved(('k',),lambda:__import__('fresh_resolve').Resolved('http://127.0.0.1:1/x',{},0),wait=3,tick=ticks.append)
  self.assertGreaterEqual(len(ticks),8);self.assertEqual(ticks,sorted(ticks));self.assertEqual(p2p.status_text(ticks[0],90).split(' · ')[0],'Waiting for peers')

if __name__=='__main__':unittest.main()
