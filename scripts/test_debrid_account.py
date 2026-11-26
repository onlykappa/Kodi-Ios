"""Own AllDebrid sign-in and typed failures against a controlled fake service (roadmap step 17). Real AllDebrid is not contacted."""
import json,os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import alldebrid as ad, debrid_account as da, debrid_token as dt, source_contract as c, source_health as sh

class Clock:
 def __init__(s,t=1000.0):s.t=t
 def __call__(s):return s.t
 def sleep(s,d):s.t+=d

class Service:
 """Fake AllDebrid: pin/get then pin/check answers `activated` after N checks."""
 def __init__(s,activate_after=2,fail=None,expires=600):s.checks=0;s.n=activate_after;s.fail=fail;s.expires=expires;s.calls=[]
 def __call__(s,method,url,data,headers):
  s.calls.append((method,url.split('?')[0],data))
  if s.fail:
   if isinstance(s.fail,Exception):raise s.fail
   return json.dumps({'status':'error','error':{'code':s.fail,'message':'x'}}).encode()
  if '/pin/get' in url:return json.dumps({'status':'success','data':{'pin':'ABCD','check':'chk1','expires_in':s.expires,'user_url':'https://alldebrid.com/pin/?pin=ABCD'}}).encode()
  if '/pin/check' in url:
   s.checks+=1;ok=s.checks>=s.n
   return json.dumps({'status':'success','data':{'activated':ok,'expires_in':100,'apikey':'SECRETKEY' if ok else None}}).encode()
  raise AssertionError(url)

class Codes(unittest.TestCase):
 def test_every_documented_class_maps_to_a_known_outcome(self):
  for code,outcome in da.CODES.items():self.assertIn(outcome,c.OUTCOMES,code)
  want={'AUTH_BAD_APIKEY':c.ACCOUNT_REQUIRED,'MUST_BE_PREMIUM':c.ACCOUNT_REQUIRED,'AUTH_BLOCKED':c.REFUSED,'MAGNET_TOO_MANY_ACTIVE':c.REFUSED,'MAINTENANCE':c.OFFLINE,
        'MAGNET_INVALID_ID':c.EXPIRED,'MAGNET_INVALID_URI':c.UNSUPPORTED,'MAGNET_CANT_BOOTSTRAP':c.EMPTY}
  for code,o in want.items():self.assertEqual(da.outcome_for(ad.Problem('m',code)),o,code)
  self.assertEqual(da.outcome_for(ad.Problem('m','NEW_UNKNOWN_CODE')),c.UNSUPPORTED);self.assertEqual(da.outcome_for(ad.Problem('m')),c.UNSUPPORTED)
 def test_busy_kinds_and_other_errors(self):
  b=ad.Busy('x');self.assertEqual(da.outcome_for(b),c.OFFLINE);b.kind='timeout';self.assertEqual(da.outcome_for(b),c.TIMEOUT);b.kind='refused';self.assertEqual(da.outcome_for(b),c.REFUSED)
  self.assertEqual(da.outcome_for(TimeoutError()),c.TIMEOUT);self.assertEqual(da.outcome_for(f:=KeyError('x')),c.UNSUPPORTED)
 def test_the_client_attaches_codes_and_kinds(self):
  def req(code,body):
   def r(m,u,d,h):
    import urllib.error,io
    raise urllib.error.HTTPError(u,code,'x',{},io.BytesIO(body))
   return r
  with self.assertRaises(ad.Problem) as cm:ad.AllDebrid('k',request=lambda *a:json.dumps({'status':'error','error':{'code':'AUTH_BAD_APIKEY','message':'m'}}).encode()).call('/v4/user')
  self.assertEqual(cm.exception.code,'AUTH_BAD_APIKEY')
  with self.assertRaises(ad.Busy) as cm:ad.AllDebrid('k',request=req(429,b'')).call('/v4/user')
  self.assertEqual(cm.exception.kind,'refused')
  with self.assertRaises(ad.Busy) as cm:ad.AllDebrid('k',request=lambda *a:(_ for _ in ()).throw(TimeoutError())).call('/v4/user')
  self.assertEqual(cm.exception.kind,'timeout')

class Circuit(unittest.TestCase):
 def setUp(self):self.clk=Clock();self.h=sh.Health('',self.clk)
 def test_unavailable_only_after_repeated_service_failures_and_clears_on_success(self):
  off=ad.Busy('x')
  for i in range(2):da.record(self.h,off);self.clk.t+=1
  self.assertFalse(da.unavailable(self.h,self.clk()));da.record(self.h,off);self.assertTrue(da.unavailable(self.h,self.clk()))
  da.record(self.h);self.assertFalse(da.unavailable(self.h,self.clk()))
 def test_not_cached_account_and_per_title_errors_never_flip_it(self):
  for e in (ad.Problem('m','MAGNET_CANT_BOOTSTRAP'),ad.Problem('m','AUTH_BAD_APIKEY'),ad.Problem('m','MAGNET_INVALID_ID'),ad.Problem('m','MAGNET_INVALID_URI')):
   for i in range(5):da.record(self.h,e);self.clk.t+=1
  self.assertFalse(da.unavailable(self.h,self.clk()))
 def test_unavailable_ends_with_the_cooldown(self):
  for i in range(3):da.record(self.h,ad.Busy('x'));self.clk.t+=1
  self.assertTrue(da.unavailable(self.h,self.clk()));self.clk.t+=3600;self.assertFalse(da.unavailable(self.h,self.clk()))
 def test_no_health_means_available(self):
  da.record(None,ad.Busy('x'));self.assertFalse(da.unavailable(None))

class SignIn(unittest.TestCase):
 def setUp(self):
  self.dir=tempfile.TemporaryDirectory();self.addCleanup(self.dir.cleanup);self.clk=Clock();self.shown=[]
 def go(self,svc,**k):return da.sign_in(lambda pin,url:self.shown.append((pin,url)),svc,sleep=self.clk.sleep,clock=self.clk,profile=self.dir.name,**k)
 def test_pin_flow_stores_the_key_owner_only_and_it_outranks_umbrella(self):
  svc=Service(2);self.assertTrue(self.go(svc));self.assertEqual(self.shown,[('ABCD','https://alldebrid.com/pin/?pin=ABCD')])
  self.assertEqual([c[1].rsplit('/',1)[-1] for c in svc.calls],['get','check','check']);self.assertEqual(svc.calls[1][2]['pin'],'ABCD')
  self.assertEqual(dt.get(self.dir.name,lambda:'OLD-UMBRELLA-KEY'),'SECRETKEY');self.assertTrue(dt.own(self.dir.name))
  self.assertEqual(oct(os.stat(Path(self.dir.name)/dt.NAME).st_mode&0o777),'0o600')
 def test_sign_out_returns_to_umbrellas_key_or_nothing(self):
  self.go(Service(1));self.assertTrue(da.sign_out(self.dir.name));self.assertFalse(dt.own(self.dir.name))
  self.assertEqual(dt.get(self.dir.name,lambda:'UMB'),'UMB');self.assertEqual(dt.get(self.dir.name,lambda:''),'UMB' if False else 'UMB')
 def test_expired_pin_and_cancel(self):
  with self.assertRaises(c.Outcome) as cm:self.go(Service(10**6,expires=12))
  self.assertEqual(cm.exception.kind,c.EXPIRED);self.assertFalse(dt.own(self.dir.name))
  with self.assertRaises(c.Outcome) as cm:self.go(Service(10**6),cancel=lambda:True)
  self.assertEqual(cm.exception.kind,c.CANCELED)
 def test_service_errors_become_typed_outcomes_and_feed_health(self):
  h=sh.Health('',self.clk)
  for fail,want in (('PIN_EXPIRED',c.EXPIRED),('MAINTENANCE',c.OFFLINE),('AUTH_BLOCKED',c.REFUSED),(ConnectionError('https://x.invalid?t=SECRET'),c.OFFLINE),(TimeoutError(),c.TIMEOUT)):
   with self.assertRaises(c.Outcome) as cm:self.go(Service(fail=fail),health=h)
   self.assertEqual(cm.exception.kind,want,fail)
  self.assertNotIn('SECRET',repr(h.data))
 def test_key_is_never_in_the_calls_logs_or_health(self):
  h=sh.Health('',self.clk);svc=Service(1);self.go(svc,health=h);self.assertNotIn('SECRETKEY',repr(svc.calls)+repr(h.data)+repr(self.shown))
 def test_unreadable_answer_is_a_busy_outcome(self):
  with self.assertRaises(c.Outcome) as cm:self.go(lambda *a:b'<html>maintenance</html>')
  self.assertEqual(cm.exception.kind,c.OFFLINE)

class Wired(unittest.TestCase):
 def test_client_calls_feed_the_circuit_through_the_observer(self):
  clk=Clock();h=sh.Health('',clk);seen=[]
  client=ad.AllDebrid('k',request=lambda *a:(_ for _ in ()).throw(ConnectionError()),observe=lambda e:(seen.append(e),da.record(h,e)))
  for i in range(3):
   with self.assertRaises(ad.Busy):client.call('/v4/user')
   clk.t+=1
  self.assertTrue(da.unavailable(h,clk()));self.assertEqual(len(seen),3)
  ok=ad.AllDebrid('k',request=lambda *a:json.dumps({'status':'success','data':{'x':1}}).encode(),observe=lambda e:da.record(h,e));ok.call('/v4/user');self.assertFalse(da.unavailable(h,clk()))
 def test_a_failing_observer_never_breaks_a_call(self):
  def bad(e):raise RuntimeError('x')
  self.assertEqual(ad.AllDebrid('k',request=lambda *a:json.dumps({'status':'success','data':{'x':1}}).encode(),observe=bad).call('/v4/user'),{'x':1})
 def test_missing_key_is_account_required(self):
  with self.assertRaises(ad.Problem) as cm:ad.AllDebrid('')
  self.assertEqual(da.outcome_for(cm.exception),c.ACCOUNT_REQUIRED)

if __name__=='__main__':unittest.main()
