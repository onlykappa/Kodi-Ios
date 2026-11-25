"""Umbrella sources that open fast come first (owner, 2026-11-20: a stream took 20 s because the chosen debrid source was slow to start)."""
import json,os,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path[:0]=[str(LIB),str(ROOT/'migration/bundled-bootstrap')]
import source_speed as S

def item(debrid,provider,source='CACHED'):return {'debrid':debrid,'provider':provider,'source':source,'name':'x'}

class SpeedTests(unittest.TestCase):
 def make(self):
  self.now=[100000.0];return S.Speed(None,lambda:self.now[0])
 def test_the_key_is_labels_only(self):
  self.assertEqual(S.key(item('AllDebrid','Torrentio')),'alldebrid|torrentio');self.assertEqual(S.key({}),'')
 def test_a_fast_source_ranks_above_a_slow_one_and_unknown_sits_between(self):
  s=self.make();s.ok('a|fast',2);s.ok('b|slow',25)
  order=[S.key(i) for _,i in s.order([(0,item('b','slow')),(1,item('c','new')),(2,item('a','fast'))])]
  self.assertEqual(order,['a|fast','c|new','b|slow'])
 def test_a_recent_failure_goes_last_and_fades(self):
  s=self.make();s.ok('a|x',2);self.now[0]+=10;s.fail('a|x')
  self.assertLess(s.score('a|x'),s.score('z|unknown'))
  self.now[0]+=S.FRESH+1;self.assertGreater(s.score('a|x'),s.score('z|unknown'))   # forgiven after six hours, its good history still counts
 def test_a_later_success_clears_the_failure(self):
  s=self.make();s.fail('a|x');self.now[0]+=10;s.ok('a|x',3);self.assertGreater(s.score('a|x'),0)
 def test_equal_scores_keep_umbrellas_order_and_cached_beats_unchecked(self):
  s=self.make();pairs=[(0,item('a','p1','UNCHECKED')),(1,item('b','p2','CACHED')),(2,item('c','p3','CACHED'))]
  out=[n for n,_ in s.order(pairs,lambda i:'CACHED' in i['source'])];self.assertEqual(out,[1,2,0])
 def test_it_persists_only_labels_and_numbers(self):
  with tempfile.TemporaryDirectory() as d:
   path=os.path.join(d,'x','speed.json');s=S.Speed(path);s.ok('alldebrid|torrentio',4.2);s.fail('b|c')
   text=Path(path).read_text();self.assertNotIn('http',text);again=S.Speed(path);self.assertEqual(again.data['alldebrid|torrentio']['lat'],[4.2])
 def test_only_the_last_five_openings_count(self):
  s=self.make()
  for v in (30,30,30,2,2,2,2,2):s.ok('a|x',v)
  self.assertEqual(len(s.data['a|x']['lat']),S.SAMPLES);self.assertGreater(s.score('a|x'),1)
 def test_a_corrupt_file_starts_empty(self):
  with tempfile.TemporaryDirectory() as d:
   p=os.path.join(d,'s.json');Path(p).write_text('{no');self.assertEqual(S.Speed(p).data,{})

class Settle(unittest.TestCase):
 def window(self):
  props={};return NS(setProperty=lambda k,v:props.__setitem__(k,v),getProperty=lambda k:props.get(k,''),clearProperty=lambda k:props.pop(k,None)),props
 def test_the_open_is_credited_to_the_source_chosen_before_it(self):
  w,props=self.window();s=S.Speed(None,lambda:1000.0)
  S.picked(w,item('AllDebrid','Torrentio'),now=100.0);self.assertIn(S.PICK,props)
  self.assertEqual(S.settle(w,s,True,now=113.0),('alldebrid|torrentio',13.0));self.assertEqual(s.data['alldebrid|torrentio']['lat'],[13.0]);self.assertNotIn(S.PICK,props)
 def test_a_failed_open_is_a_failure_and_a_stale_pick_is_ignored(self):
  w,_=self.window();s=S.Speed(None,lambda:1000.0)
  S.picked(w,item('a','b'),now=100.0);self.assertEqual(S.settle(w,s,False,now=110.0),('a|b',None));self.assertIn('fail_at',s.data['a|b'])
  S.picked(w,item('c','d'),now=100.0);self.assertIsNone(S.settle(w,s,True,now=100+S.FRESH));self.assertNotIn('c|d',s.data)
 def test_nothing_picked_nothing_credited(self):
  w,_=self.window();self.assertIsNone(S.settle(w,S.Speed(),True))

class Wiring(unittest.TestCase):
 def test_open_timing_tells_listeners_when_an_open_finishes(self):
  import open_timing as ot
  told=[];ot.LISTENERS[:]=[lambda ok,via:told.append((ok,via))]
  props={ot.PROPERTY:json.dumps({'t':100.0,'via':'umbrella'})}
  home=NS(getProperty=lambda k:props.get(k,''),setProperty=lambda k,v:props.__setitem__(k,v),clearProperty=lambda k:props.pop(k,None))
  ot.check(home,lambda:True,lambda t:None,now=120.0);self.assertEqual(told,[(True,'umbrella')])
  props[ot.PROPERTY]=json.dumps({'t':100.0,'via':'umbrella'});told.clear()
  ot.check(home,lambda:False,lambda t:None,now=100.0+ot.GIVE_UP+1);self.assertEqual(told,[(False,'umbrella')]);ot.LISTENERS[:]=[]
 def test_the_version_page_and_the_service_use_it(self):
  picker=(LIB/'umbrella_picker.py').read_text();service=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn('source_speed.open_store().order(playable_items',picker);self.assertIn('source_speed.picked(',picker)
  self.assertIn('open_timing.LISTENERS.append(_credit)',service)
 def test_the_picker_lists_a_fast_source_first(self):
  import umbrella_picker as up
  with tempfile.TemporaryDirectory() as d:
   store=S.Speed(os.path.join(d,'s.json'));store.ok('fastdebrid|fastprov',2);store.fail('slowdebrid|slowprov')
   seen={}
   class Deck:
    def run(self,title,labels,**kw):seen['labels']=labels;return -1
   results=[dict(item('slowdebrid','slowprov'),name='Slow.release',quality='1080p'),dict(item('fastdebrid','fastprov'),name='Fast.release',quality='1080p')]
   orig=S.open_store;S.open_store=lambda *a,**k:store
   up.share=lambda meta,window=None:{}
   try:
    up.run(results,{'title':'T'},deck=Deck(),sm=NS(from_meta=lambda m:None))
   finally:S.open_store=orig
   self.assertIn('Fast.release',seen['labels'][0]);self.assertIn('Slow.release',seen['labels'][1])

class LateVerdict(unittest.TestCase):
    """Owner 2026-11-25 (build 698 log f12dfcdd): a source that was "ready" in 12.8 s but stalled for minutes kept ranking first: only the time to streams-ready counted."""
    def store(self,clock=None):
        self.now=[1000.0];return S.Speed(None,lambda:self.now[0])
    def test_a_file_that_never_put_a_picture_up_goes_last_and_the_fingerprint_is_not_the_name(self):
        slow={'debrid':'alldebrid','provider':'torrentio','source':'CACHED','name':'Phony.S01E07.2160p.HEVC-GRP'};other={'debrid':'alldebrid','provider':'torrentio','source':'CACHED','name':'Phony.S01E07.1080p.x265-OTH'}
        fp=S.fingerprint(slow);self.assertEqual(len(fp),10);self.assertNotIn('phony',fp.lower());self.assertEqual(fp,S.fingerprint(dict(slow,name='PHONY.s01e07.2160p.hevc-grp ')))
        st=self.store();order=lambda:[p[0] for p in st.order([(0,slow),(1,other)],lambda it:True)]
        self.assertEqual(order(),[0,1]);st.bad(fp);self.assertEqual(order(),[1,0])
        self.now[0]+=S.BAD_FOR+1;self.assertEqual(order(),[0,1])          # six hours later it gets another chance
    def test_the_bad_marks_survive_trimming_and_the_file(self):
        with tempfile.TemporaryDirectory() as t:
            path=os.path.join(t,'s.json');st=S.Speed(path,lambda:1000.0);st.bad('abc');
            for n in range(S.KEEP+5):st.ok('k%d'%n,2.0)
            again=S.Speed(path,lambda:1000.0);self.assertTrue(again.is_bad('abc'));self.assertFalse(again.is_bad('zzz'));self.assertFalse(again.is_bad(''))
    def test_settle_leaves_the_file_fingerprint_for_the_late_verdict(self):
        home=NS(p={},getProperty=lambda k:home.p.get(k,''),setProperty=lambda k,v:home.p.__setitem__(k,v),clearProperty=lambda k:home.p.pop(k,None))
        it={'debrid':'alldebrid','provider':'torrentio','source':'CACHED','name':'A.B.C'};S.picked(home,it,now=1000.0);S.settle(home,S.Speed(None,lambda:1010.0),True,now=1010.0)
        self.assertEqual(home.getProperty(S.PICK_FILE),S.fingerprint(it))
    def test_the_service_judges_by_the_first_picture(self):
        svc=(ROOT/'migration/bundled-bootstrap/service.py').read_text() if 'ROOT' in globals() else ''
        self.assertIn('open_timing.LATE.append(_late)',svc);self.assertIn('_speed.bad(fp)',svc);self.assertIn('source_speed.LATE_SLOW',svc)

if __name__=='__main__':unittest.main()
