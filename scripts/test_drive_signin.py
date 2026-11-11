"""Owner (build 192): "Google Drive upload paused · Drive sign-in refresh: HTTP 429", details full of raw JSON.
The log: the sign-in server's refresh answered 400 from Kodi's start (Google refused the saved sign-in), and two
threads asked again every 5-10 s until the server answered 429. Now a refused sign-in is never asked again until
the owner signs in (a new refresh token), a busy answer holds every refresh for HOLD_S, the message says to sign in
again, and diagnostic lines read as sentences."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import driveupload as du,notices

class Clock:
 def __init__(self):self.t=100000.0
 def __call__(self):return self.t

class Refresh(unittest.TestCase):
 def setUp(self):
  du.REFUSED.clear();du.HOLD['until']=0.0;self.clock=Clock();self.calls=[];self.answer=[]
  self.account={'a':{'access_tokens':{'access_token':'old','refresh_token':'R1','date':0,'expires_in':3600}}}
  def refresh(token):
   self.calls.append(token);a=self.answer.pop(0)
   if isinstance(a,int):raise du.refresh_error(a)
   return a
  self.token=du.token_source(lambda:self.account,lambda acc:None,refresh,now=self.clock)
 def test_refused_sign_in_is_not_asked_again(self):
  self.answer=[400]
  with self.assertRaises(du.SignedOut) as ctx:self.token()
  self.assertIn('Sign in to Google Drive again',str(ctx.exception))
  for _ in range(5):
   self.clock.t+=5
   with self.assertRaises(du.SignedOut):self.token()
  self.assertEqual(self.calls,['R1'])
  # Signed in again: a new refresh token works at once.
  self.account['a']['access_tokens']['refresh_token']='R2';self.answer=[{'access_token':'new','expires_in':3600}]
  self.assertEqual(self.token(),'new');self.assertEqual(self.calls,['R1','R2'])
 def test_busy_holds_every_refresh(self):
  self.answer=[429,{'access_token':'new','expires_in':3600}]
  with self.assertRaises(du.RefreshBusy):self.token()
  self.clock.t+=du.HOLD_S-1
  with self.assertRaises(du.RefreshBusy):self.token()
  self.assertEqual(len(self.calls),1)
  self.clock.t+=2;self.assertEqual(self.token(),'new');self.assertEqual(len(self.calls),2)
 def test_status_mapping(self):
  self.assertIsInstance(du.refresh_error(401),du.SignedOut);self.assertIsInstance(du.refresh_error(503),du.RefreshBusy)
 def test_both_refreshers_use_it(self):
  for f in (BOOT/'service.py',LIB/'drivelibrary.py'):
   self.assertIn('raise driveupload.refresh_error(status)',f.read_text())
  service=(BOOT/'service.py').read_text()
  self.assertIn("except driveupload.SignedOut as error:",service);self.assertIn("'Sign in to Google Drive again'",service)
  self.assertIn("except (driveupload.SignedOut,driveupload.RefreshBusy):monitor.waitForAbort(60)",service)

class Details(unittest.TestCase):
 def test_diagnostic_lines_read_as_sentences(self):
  err='Kodi iOS diagnostic {"component":"drive_upload","errors":[{"frames":[{"file":"service.py","line":405},{"file":"service.py","line":266}],"message":"Drive sign-in refresh: HTTP 400","type":"RuntimeError"}],"event":"failure"}'
  http='Kodi iOS diagnostic {"component":"drive_http","event":"http_error","host":"kodi-signin.example.dev","status":429}'
  self.assertEqual(notices.plain_record({'text':err}),'drive upload: Drive sign-in refresh: HTTP 400 (service.py, line 266)')
  self.assertEqual(notices.plain_record({'text':http}),'drive http: HTTP 429 from kodi-signin.example.dev')
  self.assertEqual(notices.plain_record({'text':'Kodi iOS diagnostic {broken'}),'Kodi iOS diagnostic {broken')

if __name__=='__main__':unittest.main()
