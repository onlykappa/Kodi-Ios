"""Continue is never a dead end (owner, build 634 log 4b37fc5b: the remembered Umbrella link sat 30 s and "could not open file", and nothing else was tried)."""
import importlib.util,json,sys,types,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import continue_guard as g
WATCH=ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'
sys.path.insert(0,str(WATCH))
import ios_continue as c

PARAMS={'tmdb_type':'tv','tmdb_id':'73223','season':'2','episode':'8','ios_continue':'1'}
class Home:
    def __init__(self):self.p={}
    def getProperty(self,k):return self.p.get(k,'')
    def setProperty(self,k,v):self.p[k]=v
    def clearProperty(self,k):self.p.pop(k,None)

class OpenedAndCircle(unittest.TestCase):
    """Build 663 log 63e92ff2: the open was cut 3 s after Kodi had its streams, and nothing showed that the video was opening."""
    def test_an_open_whose_streams_are_there_is_not_cut_at_the_short_limit(self):
        mark=g.note(PARAMS,lambda:1000.0)
        self.assertEqual(g.decide(mark,1000+g.LIMIT,False,False,opened=True),'wait')
        self.assertEqual(g.decide(mark,1000+g.LIMIT_OPENED,False,False,opened=True),'fallback')
        self.assertEqual(g.decide(mark,1000+g.LIMIT,False,False,opened=False),'fallback')
        self.assertEqual(g.decide(mark,1000+g.LIMIT,False,True,opened=True),'fallback')   # a failure box still ends it
    def test_the_fallback_keeps_the_circle_flag(self):
        home=Home();home.p[g.MARK]=g.note(PARAMS,lambda:1000.0);played=[]
        g.step(home,lambda:False,lambda:False,lambda:None,lambda:None,played.append,lambda t:None,now=lambda:1000+g.LIMIT,opened=lambda:False)
        self.assertEqual(home.getProperty(g.OPENING),'1');self.assertEqual(len(played),1)
    def circle(self,playing=False,box=False,visible=False,clock=None):
        self.home=Home();self.calls=[];self.t=[1000.0]
        return g.Circle(self.home,lambda:playing,lambda:box,lambda:visible,lambda:self.calls.append('raise'),lambda:self.calls.append('close'),
                        lambda t:self.calls.append('log'),lambda:self.t[0])
    def test_nothing_is_raised_without_the_flag(self):
        c=self.circle();self.assertEqual(c.tick(),'idle');self.assertEqual(self.calls,[])
    def test_the_circle_is_raised_again_when_kodi_has_closed_its_own(self):
        c=self.circle();self.home.p[g.OPENING]='1'
        self.assertEqual(c.tick(),'keep');self.assertEqual(self.calls,['raise'])
        c.visible=lambda:True;self.calls.clear();self.assertEqual(c.tick(),'keep');self.assertEqual(self.calls,[])
    def test_a_picture_or_a_failure_box_closes_it_and_clears_the_flag(self):
        for kw,word in (({'playing':True},'playing'),({'box':True},'failed')):
            c=self.circle(**kw);self.home.p[g.OPENING]='1'
            self.assertEqual(c.tick(),word);self.assertEqual(self.calls,['close']);self.assertEqual(self.home.getProperty(g.OPENING),'')
    def test_it_is_never_kept_longer_than_the_cap(self):
        c=self.circle();self.home.p[g.OPENING]='1';c.tick();self.t[0]+=g.CIRCLE_CAP
        self.assertEqual(c.tick(),'gave up');self.assertIn('close',self.calls);self.assertEqual(self.home.getProperty(g.OPENING),'')

class Rules(unittest.TestCase):
    def test_the_retry_address_is_the_same_title_without_the_remembered_link(self):
        url=g.retry_url(PARAMS);self.assertTrue(url.startswith('plugin://plugin.video.themoviedb.helper/?'))
        for part in ('info=play','tmdb_type=tv','tmdb_id=73223','season=2','episode=8','ios_continue=1','ios_fast=0'):self.assertIn(part,url)
        movie=g.retry_url({'tmdb_type':'movie','tmdb_id':'5','ios_continue':'1'});self.assertNotIn('season',movie);self.assertIn('ios_fast=0',movie)
    def test_what_each_moment_means(self):
        mark=g.note(PARAMS,lambda:1000.0)
        self.assertEqual(g.decide('',1001,False,False),'none')
        self.assertEqual(g.decide(mark,1005,False,False),'wait')
        self.assertEqual(g.decide(mark,1005,True,False),'ok')                 # a picture is up: done
        self.assertEqual(g.decide(mark,1005,False,True),'fallback')           # Kodi's failure box
        self.assertEqual(g.decide(mark,1000+g.LIMIT,False,False),'fallback')  # no picture in time
        self.assertEqual(g.decide(mark,1000+g.LIMIT+9,True,False),'ok')       # a slow open that did start is left alone
        self.assertEqual(g.decide('junk',1,False,False),'ok');self.assertEqual(g.decide(json.dumps({'at':1,'retry':'http://x'}),99,False,False),'ok')   # never run an address that is not a plugin's
    def test_a_fallback_stops_closes_and_plays_once(self):
        home=Home();home.setProperty(g.MARK,g.note(PARAMS,lambda:1000.0));did=[];logs=[]
        v=g.step(home,lambda:False,lambda:True,lambda:did.append('stop'),lambda:did.append('close'),lambda u:did.append(('play',u)),logs.append,lambda:1012.0)
        self.assertEqual(v,'fallback');self.assertEqual(did[:2],['stop','close']);self.assertEqual(did[2],('play',g.retry_url(PARAMS)));self.assertEqual(home.getProperty(g.MARK),'')
        self.assertIn('12 s, failure box up',logs[0]);self.assertNotIn('http',logs[0])
        self.assertEqual(g.step(home,lambda:False,lambda:True,lambda:1,lambda:1,lambda u:self.fail('twice'),logs.append,lambda:1013.0),'none')   # the note is gone: nothing runs again
    def test_a_picture_clears_the_note(self):
        home=Home();home.setProperty(g.MARK,g.note(PARAMS,lambda:1000.0))
        self.assertEqual(g.step(home,lambda:True,lambda:False,lambda:self.fail('stop'),lambda:1,lambda u:self.fail('play'),lambda t:1,lambda:1003.0),'ok');self.assertEqual(home.getProperty(g.MARK),'')
    def test_the_loop_survives_errors_and_ends_when_kodi_closes(self):
        home=Home();home.setProperty(g.MARK,'x');ticks=iter([False,False,True]);logs=[]
        def bad(*a):raise RuntimeError('x')
        g.watch(home,bad,bad,bad,bad,bad,logs.append,lambda s:next(ticks))
        self.assertTrue(any('RuntimeError' in l for l in logs))

class Wiring(unittest.TestCase):
    def load(self):
        spec=importlib.util.spec_from_file_location('watch_guard',WATCH/'ios_watch_dialog.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def seeded(self):
        box={'t':'{}'};read=lambda l:box['t'];write=lambda l,t:box.__setitem__('t',t)
        pl=types.SimpleNamespace(tmdb_type='tv',tmdb_id='73223',season='2',episode='8',details=types.SimpleNamespace(infolabels={'title':'t','tvshowtitle':'s'},art={}))
        c.record(pl,read,write,choice='umbrella');c.update(read,write,600,1400,now=lambda:1000.0,stream='https://dl.example.invalid/f.mkv');return read
    def test_the_second_try_never_uses_the_remembered_link(self):
        m=self.load();read=self.seeded()
        never=lambda *a:self.fail('played the remembered link')
        self.assertFalse(m.fast_stream(7,dict(PARAMS,ios_fast='0'),read,alive=lambda u:True,play=never,now=lambda:1500.0))
        played=[];self.assertTrue(m.fast_stream(7,PARAMS,read,alive=lambda u:True,play=lambda *a:played.append(a),now=lambda:1500.0));self.assertEqual(len(played),1)
    def test_the_service_runs_the_guard_and_the_plugin_leaves_the_note(self):
        svc=(ROOT/'migration/bundled-bootstrap/service.py').read_text();self.assertIn('continue_guard.watch(home,',svc);self.assertIn("Window.IsActive(yesnodialog) | Window.IsActive(okdialog)",svc)
        self.assertIn('continue_guard.note(params,now,remembered,item_key)',(WATCH/'ios_watch_dialog.py').read_text())
    def test_the_source_search_waits_three_seconds_for_a_page_that_is_opening(self):
        svc=(ROOT/'migration/bundled-bootstrap/service.py').read_text();self.assertIn('if opened<3:return False',svc)
class ForgetsTheSavedVersion(unittest.TestCase):
    """Owner 2026-11-25 (build 698 log f12dfcdd): the guard's second try replayed the same saved version through Umbrella at once, no list, the same slow server; and the loading circle sat over the list."""
    def run_fallback(self,key='episode:73223:2:8',forget=None):
        home=Home();home.p[g.MARK]=g.note(PARAMS,lambda:1000.0,'https://x/y.mkv',key);played=[];logs=[];calls=[]
        g.step(home,lambda:False,lambda:False,lambda:calls.append('stop'),lambda:calls.append('close'),lambda url:(calls.append('play'),played.append(url)),logs.append,
               now=lambda:1000+g.LIMIT,opened=lambda:False,forget=forget);return home,played,logs,calls
    def test_the_note_carries_the_title_key(self):
        self.assertEqual(json.loads(g.note(PARAMS,lambda:1.0,'u','k1'))['key'],'k1');self.assertEqual(json.loads(g.note(PARAMS,lambda:1.0))['key'],'')
    def test_a_dead_link_makes_the_guard_forget_the_saved_version_before_the_second_try(self):
        forgotten=[];home,played,logs,calls=self.run_fallback(forget=forgotten.append)
        self.assertEqual(forgotten,['episode:73223:2:8']);self.assertEqual(len(played),1);self.assertIn('ios_fast=0',played[0])
        self.assertLess(calls.index('stop'),calls.index('play'));self.assertTrue(any('saved version is forgotten' in l for l in logs))
    def test_nothing_is_forgotten_without_a_key_and_a_failure_never_blocks_the_second_try(self):
        forgotten=[];self.run_fallback(key='',forget=forgotten.append);self.assertEqual(forgotten,[])
        def broken(key):raise OSError('disk')
        home,played,logs,calls=self.run_fallback(forget=broken);self.assertEqual(len(played),1);self.assertTrue(any('could not forget' in l for l in logs))
    def test_the_overlay_passes_the_key_and_the_service_wires_forget_and_the_picker_closes_the_circle(self):
        overlay=(WATCH/'ios_watch_dialog.py').read_text();service=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
        picker=(ROOT/'migration/bundled-bootstrap/resources/lib/umbrella_picker.py').read_text()
        self.assertIn('continue_guard.note(params,now,remembered,item_key)',overlay);self.assertIn('forget=forget',service);self.assertIn('ios_continue.forget_choice(read,write,item_key)',service)
        self.assertLess(picker.index(' share(meta)\n close_circle()'),picker.index('choice=deck.run('))   # closed before the list opens
        self.assertIn("clearProperty('KodiIOS.ContinueOpening')",picker)

class SmarterLimits(unittest.TestCase):
    """The guard needs to work (owner 2026-11-25): 30 s of nothing is too long, a slow open that has begun still gets its time."""
    def test_a_continue_whose_open_never_began_is_given_up_after_ten_seconds(self):
        mark=g.note(PARAMS,lambda:1000.0)
        self.assertEqual(g.decide(mark,1000+g.NOTHING-1,False,False,opened=False,has_media=False),'wait')
        self.assertEqual(g.decide(mark,1000+g.NOTHING,False,False,opened=False,has_media=False),'fallback')
        self.assertEqual(g.decide(mark,1000+g.NOTHING,False,False,opened=False,has_media=True),'wait')    # Kodi is opening: the longer limit
        self.assertEqual(g.decide(mark,1000+g.NOTHING,False,False,opened=True,has_media=False),'wait')
    def test_the_plain_limit_is_twenty_seconds_and_an_open_with_streams_keeps_its_longer_one(self):
        mark=g.note(PARAMS,lambda:1000.0)
        self.assertEqual((g.LIMIT,g.NOTHING,g.LIMIT_OPENED),(20.0,10.0,45.0))
        self.assertEqual(g.decide(mark,1000+g.LIMIT,False,False,opened=False,has_media=True),'fallback')
        self.assertEqual(g.decide(mark,1000+g.LIMIT,False,False,opened=True,has_media=True),'wait')
    def test_step_asks_kodi_whether_it_has_media(self):
        home=Home();home.p[g.MARK]=g.note(PARAMS,lambda:1000.0);played=[]
        verdict=g.step(home,lambda:False,lambda:False,lambda:None,lambda:None,played.append,lambda t:None,now=lambda:1000+g.NOTHING,opened=lambda:False,has_media=lambda:False)
        self.assertEqual(verdict,'fallback');self.assertEqual(len(played),1)

if __name__=='__main__':unittest.main()
