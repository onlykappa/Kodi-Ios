"""Transfers page (owner-approved mockups, builds 171 and 172): one job at a time, its painted graph, the page XML, and that only a
tap on a transfer card in Notifications opens it ("I only want the graph to show in notifications if i tap on it")."""
import importlib.util,os,struct,sys,tempfile,time,unittest,zlib,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path[:0]=[str(LIB),str(BOOT),str(Path(__file__).resolve().parent)]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
import transfer_history as th
portrait=load('portrait_transfers',LIB/'portrait.py')
tp=load('transfers_page_t',LIB/'transfers_page.py')
MB=1048576.0;GB=1024*MB

def decode(png):
 w,h=struct.unpack('>II',png[16:24]);i=33;data=b''
 while i<len(png):
  n=struct.unpack('>I',png[i:i+4])[0];tag=png[i+4:i+8]
  if tag==b'IDAT':data+=png[i+8:i+8+n]
  i+=12+n
 raw=zlib.decompress(data);stride=w*4+1
 return w,h,[raw[y*stride+1:(y+1)*stride] for y in range(h)]

GREEN=(48,209,88)

def feed(d,t0,seconds,**active):
 for i in range(0,seconds,2):th.track(d,t0+i,{k:dict(v) for k,v in active.items()})
 return d

class History(unittest.TestCase):
 def test_one_record_per_job_with_peak_and_average(self):
  d=feed({},1000,120,up={'title':'Fall 2','rate':8*MB,'done':5*GB,'total':16*GB})
  job=d['jobs']['up'];self.assertEqual(job['title'],'Fall 2');self.assertAlmostEqual(job['peak'],8*MB);self.assertEqual(job['start'],1000)
  self.assertEqual(th.pick(d,'up',1120),'up');self.assertEqual(th.running(d,1120),['up'])
 def test_finished_when_it_stops_or_changes(self):
  d=feed({},1000,60,up={'title':'Fall 2','rate':8*MB,'done':16*GB,'total':16*GB},conv={'title':'Inception','rate':4*MB,'done':1*GB,'total':0})
  th.track(d,1100,{'conv':{'title':'Inception','rate':4*MB}})   # the copy stopped more than 30 s ago
  self.assertNotIn('up',d['jobs']);self.assertEqual(d['finished'][0]['title'],'Fall 2');self.assertEqual(d['finished'][0]['size'],16*GB)
  th.track(d,1102,{'conv':{'title':'Interstellar','rate':3*MB}})   # the next video
  self.assertEqual(d['finished'][0]['title'],'Inception');self.assertEqual(d['jobs']['conv']['title'],'Interstellar')
 def test_moves_on_to_what_still_runs(self):
  d=feed({},1000,60,down={'title':'Batman','rate':20*MB},conv={'title':'Inception','rate':4*MB})
  self.assertEqual(th.pick(d,'down',1058),'down')
  th.track(d,1100,{'conv':{'title':'Inception','rate':4*MB}})
  self.assertEqual(th.pick(d,'down',1100),'conv');self.assertIsNone(th.pick({},'down',1100))
 def test_points_stay_few_and_cover_the_whole_job(self):
  d=feed({},0,6*3600,conv={'title':'Long','rate':MB})
  pts=d['jobs']['conv']['points'];self.assertLessEqual(len(pts),th.MAX_POINTS);self.assertLess(pts[0][0],60);self.assertGreater(pts[-1][0],6*3600-600)
 def test_activity(self):
  a=th.activity([{'status':'downloading','download_rate':1024,'name':'Batman.2022.mkv','size_bytes':GB,'progress':50},
                 {'status':'paused','download_rate':9999,'name':'x'}],
                {'stage':'copying','rate':8*MB,'name':'Fall 2','sent':GB,'total':2*GB},
                {'running':True,'rate':.5*MB,'title':'Inception.mkv','read':GB,'progress':12,'updated':time.time()})
  self.assertEqual(a['down']['rate'],MB);self.assertEqual(a['down']['done'],GB/2);self.assertEqual(a['up']['rate'],8*MB);self.assertEqual(a['conv']['pct'],12)
  self.assertEqual(th.activity(None,{'stage':'fetching','rate':5},{'running':True,'title':'x','updated':0}),{})   # old conversion state is not running
 def test_conversion_extra_reaches_the_job(self):
  a=th.activity([],{},{'running':True,'title':'Inception.mkv','rate':7*MB,'progress':24,'updated':time.time(),
                      'film_done':2780,'film_total':8880,'pace':3.8,'eta':'about 27 min left','detail':'x'})
  self.assertEqual(a['conv']['extra'],{'film_done':2780,'film_total':8880,'pace':3.8,'eta':'about 27 min left'})
  d=th.track({},1000,a);self.assertEqual(d['jobs']['conv']['extra']['pace'],3.8)
 def test_graph_is_smoothed(self):
  pts=[[i,(8 if i%2 else 0)*MB,1] for i in range(40)]
  sm=th.smoothed(pts);self.assertLess(max(p[1] for p in sm[5:-5])-min(p[1] for p in sm[5:-5]),2*MB)
 def test_saved_and_loaded(self):
  with tempfile.TemporaryDirectory() as p:
   th.save(p,feed({},1000,4,up={'title':'A','rate':MB}));self.assertEqual(th.load(p)['jobs']['up']['title'],'A')
   self.assertEqual(th.load(p+'/nope'),{})
 def test_words(self):
  self.assertEqual(th.mb(.5*MB),'512 KB/s');self.assertEqual(th.mb(7.2*MB),'7.2 MB/s');self.assertEqual(th.ago(38*60),'38 min ago')
  self.assertEqual(th.took(41*60),'41 min');self.assertEqual(th.size(16.9*GB),'16.9 GB')

class Graph(unittest.TestCase):
 def test_png_is_one_job_in_its_colour(self):
  d=feed({},1000,300,up={'title':'Fall 2','rate':8*MB})
  job=d['jobs']['up'];w,h,rows=decode(th.render(job['points'],th.TINTS['up'],start=job['start'],now=1300))
  self.assertEqual((w,h),(th.W,th.H))
  colours={bytes(r[x*4:x*4+3]) for r in rows for x in range(w) if r[x*4+3]==255}
  # Only the job's line is solid (no other jobs, no limit line), plus board 3/4's white "now" dot.
  self.assertEqual(colours,{bytes(GREEN),b'\xff\xff\xff'})
  self.assertTrue(any(r[3] for r in rows))
 def test_empty_and_single_point(self):
  decode(th.render([],th.TINTS['down']));decode(th.render([[5,MB,1]],th.TINTS['down']))
 def test_cycling_names(self):
  with tempfile.TemporaryDirectory() as f:
   names=[th.write_graph(f,n,b'x') for n in range(12)]
   self.assertEqual(len(set(names)),th.GRAPH_FILES);self.assertEqual(names[0],names[10])
   self.assertEqual(sorted(os.listdir(f)),sorted(set(names)))

class Page(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.xml=tp.page(portrait);cls.tree=ET.fromstring(cls.xml.split('\n',2)[2])
 def test_buttons_44pt_and_ids(self):
  ids={c.get('id') for c in self.tree.iter('control')}
  for n in (tp.BACK,tp.LIST,tp.BAR,tp.OTHER+1,tp.OTHER+2):self.assertIn(str(n),ids)
  for c in self.tree.iter('control'):
   if c.get('type')=='button':self.assertGreaterEqual(float(c.findtext('height') or 0),tp.HIT,c.get('id'))
  self.assertNotIn('upload limit',self.xml);self.assertNotIn('9701',self.xml)   # no range switch, no limit line
 def test_every_property_is_set(self):
  import transfers
  now=time.time()
  d=feed({},now-600,600,up={'title':'Fall 2','rate':7.2*MB,'done':15.8*GB,'total':16.9*GB},conv={'title':'Inception','rate':4.6*MB,'done':2.1*GB,'pct':24})
  d['finished']=[{'kind':'conv','title':'Inception','start':now-400,'end':now-300,'peak':3*MB,'avg':2*MB,'size':0,'pct':4.0},   # stopped: not listed
                  {'kind':'down','title':'Batman','start':now-3000,'end':now-500,'peak':30*MB,'avg':20*MB,'size':12*GB,'done':12*GB,'total':12*GB}]
  props,pct,kind,others=transfers.page_state(d,now,'up',[('Interstellar','convert · 8.4 GB')])
  self.assertEqual(kind,'up');self.assertEqual(others,['up','conv']);self.assertEqual(props['now'],'7.2 MB/s');self.assertEqual(props['kind'],'SAVING TO GOOGLE DRIVE')
  self.assertEqual(props['tint'],th.TINTS['up']);self.assertAlmostEqual(pct,100*15.8/16.9,1);self.assertIn('15.8 GB of 16.9 GB',props['line'])
  self.assertIn('left',props['line']);self.assertEqual(props['other.1.label'],'Downloading');self.assertRegex(props['started'],r'^\d{1,2}:\d\d [AP]M$')   # board 4: "Started 1:13 PM"
  self.assertEqual(props['done.1.title'],'Batman');self.assertIn('peak 30.0 MB/s',props['done.1.line']);self.assertEqual(props['next.1.title'],'Interstellar')
  props2,pct2,kind2,_=transfers.page_state(d,now,'conv',[])
  self.assertEqual(kind2,'conv');self.assertEqual(pct2,24);self.assertEqual(props2['line'],'24%')
  d['jobs']['conv']['extra']={'film_done':46*60+20,'film_total':148*60,'pace':3.8,'eta':'about 27 min left'}
  props3,_,_,_=transfers.page_state(d,now,'conv',[])
  self.assertEqual(props3['line'],"24% · 46 of 148 min of film · 3.8× the film's speed · about 27 min left")
  for k in props:
   # Board 4: the time left rides with the unit ("MB/s · 6 min left"); 'line' stays for the notification card.
   if k in ('title','step','number','units','peak','avg','started','axis0','axis1','axis2','from','headline') or k.startswith(('other.', 'next.')) and k.endswith(('label','title','line')):self.assertIn('Window().Property(%s)'%k,self.xml,k)
  self.assertIn('Window().Property(graph)',self.xml)
  empty,_,none,_=transfers.page_state({},now,'down',[]);self.assertIsNone(none);self.assertEqual(empty['title'],'')
 def test_registered_and_pill_hidden(self):
  self.assertIn('transfers_page.files(ns)',(LIB/'portrait.py').read_text());self.assertIn('IOSTransfers.xml',(LIB/'activity_skin.py').read_text())

class NewPageFound(unittest.TestCase):
 """Build 173: "XML File for Window is missing" for a page written while Kodi ran (Kodi's directory cache)."""
 def test_portrait_folder_is_read_again_after_writing(self):
  import types
  from unittest.mock import patch
  seen=[];fake=types.SimpleNamespace(listdir=lambda path:seen.append(path) or ([],[]))
  with patch.dict(sys.modules,{'xbmcvfs':fake}):portrait.refresh_listing('/skin')
  self.assertEqual(seen,['/skin/portrait/'])
  self.assertIn("{c.split('/')[0] for c in changed if '/' in c}",(LIB/'portrait.py').read_text())
 def test_every_written_folder_is_read_again(self):
  # Build 200: IOSAirPlayFlow.xml is in 1080i; only portrait was re-listed, so the Play on TV card was "missing".
  import types
  from unittest.mock import patch
  seen=[];fake=types.SimpleNamespace(listdir=lambda path:seen.append(path) or ([],[]))
  with patch.dict(sys.modules,{'xbmcvfs':fake}):portrait.refresh_listing('/skin','1080i')
  self.assertEqual(seen,['/skin/1080i/'])
  text=(LIB/'portrait.py').read_text();self.assertIn('refresh_listing(skin,folder)',text)
 def test_play_on_tv_card_retries_once_after_refreshing(self):
  text=(BOOT/'cast.py').read_text()
  self.assertIn("Flow=airplay_flow.make(xbmc,xbmcgui)",text)
  self.assertIn("xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'),'1080i')+'/')",text)
 def test_transfers_retries_once_after_refreshing(self):
  text=(BOOT/'transfers.py').read_text()
  self.assertIn("except RuntimeError:",text);self.assertIn("xbmcvfs.listdir(os.path.join(skin,'portrait')+'/')",text)

class OnlyFromNotifications(unittest.TestCase):
 def test_cards_have_tap_targets_under_pause(self):
  xml=portrait.notices_page()
  for n in (9432,9433,9436,9437,9438,9439):self.assertIn('id="%d"'%n,xml)
  # Board 5 drops the "•••" buttons: Pause/Cancel stay on a long press of the card (notifications.long_press).
  self.assertNotIn('id="9462"',xml);self.assertIn('if self.long_press(*card)',(BOOT/'notifications.py').read_text())
  for page in ('library_status.py','activity_page.py'):self.assertNotIn('transfers',(BOOT/page).read_text())
 def test_tapping_the_upload_card_opens_transfers(self):
  import notices,test_library_status as lib
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as profile:
   th.save(profile,feed({},time.time()-20,20,up={'title':'Fall 2','rate':8*MB,'done':GB,'total':2*GB},conv={'title':'Inception','rate':4*MB}))
   import work_state
   work_state.save(profile,work_state.build({'phone':[{'title':'Fall 2','rate':8*MB,'progress':50}], 'prep':{'current':{'running':True,'title':'Inception','rate':4*MB,'updated':time.time()}}},time.time()))
   seen={}
   def look(w):seen.update(dict(w.props))
   kodi=lib.FakeKodi(profile,[('IOSNotifications.xml',lambda w:w.onClick(9432)),(tp.WINDOW,look),(tp.WINDOW,lambda w:w.onClick(tp.OTHER+1)),
                              (tp.WINDOW,lambda w:seen.update(after=w.getProperty('title'))),(tp.WINDOW,lambda w:w.onClick(tp.BACK)),
                              ('IOSNotifications.xml',lambda w:w.onClick(9001))])
   kodi.modules['xbmcvfs'].translatePath=lambda path:profile
   class Window:
    def __init__(self,n):pass
    def setProperty(self,*a):pass
   kodi.modules['xbmcgui'].Window=Window;kodi.modules['xbmc'].executebuiltin=lambda a:None
   with patch.dict(sys.modules,kodi.modules),patch.object(notices,'downloads',lambda get=None:[]),patch.object(notices,'uploads',lambda p:[]):
    load('notifications_run_t',BOOT/'notifications.py').run()
   self.assertEqual(seen['title'],'Fall 2');self.assertEqual(seen['now'],'8.0 MB/s');self.assertTrue(seen['graph'].startswith('special://skin/extras/portrait/graph/transfers-') and Path(seen['graph']).name.startswith('graph_'))
   self.assertEqual(seen['after'],'Inception');self.assertTrue(all(w.closed for w in kodi.windows))
   self.assertTrue(os.path.exists(os.path.join(profile,'extras','portrait','graph')))

class NeverNothingWhileConverting(unittest.TestCase):
 """Owner (build 181 screenshot): Transfers said "Nothing is moving right now" at random while a movie converted."""
 def test_a_conversion_quiet_during_an_upload_still_runs(self):
  now=time.time()
  a=th.activity([],{},{'running':True,'title':'Inception.mkv','updated':now-40,'progress':30,'rate':MB})
  self.assertIn('conv',a)   # a 32 MB piece can take 6-17 s to upload on a busy line, and progress waits for it
  self.assertNotIn('conv',th.activity([],{},{'running':True,'title':'Inception.mkv','updated':now-120}))
 def test_the_page_reads_a_saved_record_as_running(self):
  d=feed({},1000,20,conv={'title':'Inception','rate':MB,'pct':10})
  self.assertEqual(th.running(d,1018+20),['conv'])   # saved up to 5 s before, read 20 s after the last look
  self.assertEqual(th.pick(d,'conv',1040),'conv')
  import inspect
  self.assertEqual(inspect.signature(th.watch).parameters['save_every'].default,5)
 def test_library_cards_too(self):
  import prepare_downloads as prep
  self.assertIn("now()-current.get('updated',0)<60",(LIB/'prepare_downloads.py').read_text())

class SeasonEpisodeSpeeds(unittest.TestCase):
 """Build 207 (owner, build-206 Transfers screenshot: "Lanterns · S01E02 ... 46%", Peak and Average 0.0 MB/s, no
 graph): the history titled the copy by its show, the page by its episode, so the page dropped the speeds."""
 def test_history_and_page_name_the_same_episode(self):
  import work_state,transfers
  now=time.time();d={}
  for i in range(0,60,2):
   cur={'name':'Lanterns','stage':'copying','sent':(1400+i)*MB,'total':3000*MB,'rate':1.6*MB,'updated':now-60+i,
        'file':'Lanterns.S01E02.2160p.WEB.mkv','index':2,'count':8}
   th.track(d,now-60+i,th.activity([],cur,{}))
  debrid={'current':cur,'jobs':[{'title':'Lanterns','status':'copying','hash':'01226f96'}]}
  model=work_state.build({'debrid':debrid},now)
  props,pct,kind,_=transfers.page_state(d,now,'up',[],model,{})
  self.assertEqual(props['title'],'Lanterns · S01E02')
  self.assertEqual(props['peak'],'1.6 MB/s');self.assertEqual(props['avg'],'1.6 MB/s')
  self.assertEqual(props['wait'],'')                     # the graph shows
  self.assertEqual(int(pct),48)

if __name__=='__main__':unittest.main()
