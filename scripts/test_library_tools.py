"""Library tools (owner-approved mockup, docs/design/library-tools-spec.md): Queue (Edit order), Phone space, History and
AirPlay check. The logic (library_tools), the queue requests (prepare_downloads up / down), the page XML (44 pt, every
property set) and the real controllers driven through a fake Kodi from the pages that open them."""
import importlib.util,json,os,sys,tempfile,time,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path[:0]=[str(LIB),str(Path(__file__).resolve().parent)]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
import prepare_downloads as prep
import library_tools as lt
import transfer_history as th
import test_library_status as ls
portrait=load('portrait_tools',LIB/'portrait.py')
ltp=load('library_tools_page_t',LIB/'library_tools_page.py')
library_page=load('library_page_tools',LIB/'library_page.py')
GB=1024**3;MB=1024**2

def queue_state():
 """Four plain waiting videos (a, b, c, d in that order once they have priorities), one converting, one for space."""
 items=[ls.item(i,'%s.2020.1080p.mkv'%n) for i,n in (('w1','Alpha'),('w2','Bravo'),('w3','Charlie'),('w4','Delta'),('p1','Inception'),('s1','Huge'))]
 jobs={'a':ls.job('w1','Alpha.2020.1080p.mkv',priority=40),'b':ls.job('w2','Bravo.2020.1080p.mkv',priority=30),
       'c':ls.job('w3','Charlie.2020.1080p.mkv',priority=20),'d':ls.job('w4','Delta.2020.1080p.mkv'),
       'e':ls.job('p1','Inception.2020.1080p.mkv'),'f':ls.job('s1','Huge.2020.1080p.mkv',space=90*GB)}
 return {'library':{'items':items,'checked':900},'jobs':jobs,
         'current':{'running':True,'title':'Inception.2020.1080p.mkv','progress':4,'stage':'Step 3 of 3 · Converting'}}

class QueueOrder(unittest.TestCase):
 def test_order_and_ties_follow_the_queue(self):
  s=queue_state();self.assertEqual(prep.queue_order(s,1000),['w1','w2','w3','w4'])
  for j in s['jobs'].values():j.pop('priority',None)
  # No priorities yet: prepare_cloud takes them by job key, and the page now says the same.
  self.assertEqual(prep.queue_order(s,1000),['w1','w2','w3','w4'])
 def test_up_and_down_move_one_place_and_keep_the_order(self):
  s=queue_state()
  prep.apply_to(s,[{'action':'down','id':'w1'}],5000);self.assertEqual(prep.queue_order(s,5000),['w2','w1','w3','w4'])
  prep.apply_to(s,[{'action':'up','id':'w4'},{'action':'up','id':'w4'}],5001);self.assertEqual(prep.queue_order(s,5001),['w2','w4','w1','w3'])
  prep.apply_to(s,[{'action':'up','id':'w2'},{'action':'down','id':'w3'},{'action':'up','id':'nope'}],5002)
  self.assertEqual(prep.queue_order(s,5002),['w2','w4','w1','w3'])   # nothing above the top or below the bottom
  self.assertEqual(s['jobs']['b']['priority'],5001-1)   # a move that cannot happen changes nothing
 def test_prepare_next_still_wins(self):
  s=queue_state();prep.apply_to(s,[{'action':'up','id':'w3'},{'action':'next','id':'w4'}],6000)
  self.assertEqual(prep.queue_order(s,6000)[0],'w4')
 def test_repeated_taps_are_kept_and_never_stop_the_conversion(self):
  with tempfile.TemporaryDirectory() as p:
   for a,i in (('up','w4'),('up','w4'),('down','w1'),('keep','w3'),('next','w3')):prep.request(p,a,i)
   self.assertEqual([(r['action'],r['id']) for r in prep.pending_requests(p)],[('up','w4'),('up','w4'),('down','w1'),('next','w3')])
   self.assertTrue(prep.interrupts(p))   # 'next' still does
  with tempfile.TemporaryDirectory() as p:
   for a,i in (('up','w4'),('down','w1')):prep.request(p,a,i)
   self.assertFalse(prep.interrupts(p))
 def test_the_service_applies_them_once(self):
  with tempfile.TemporaryDirectory() as p:
   q=prep.Queue.__new__(prep.Queue);q.profile=p;q.clock=lambda:7000;q.state=queue_state();q.commit=lambda:None
   prep.request(p,'up','w3');prep.request(p,'up','w3')
   self.assertTrue(q.apply_requests());self.assertEqual(prep.queue_order(q.state,7000),['w3','w1','w2','w4'])
   self.assertFalse(q.apply_requests())

class QueueView(unittest.TestCase):
 def setUp(self):
  view=prep.library_view(queue_state(),now=lambda:1000)
  debrid=lt.debrid_jobs({'jobs':[{'title':'Fall 2','status':'copying'},{'name':'The.Batman','status':'copying'},{'title':'Old','status':'done'}],
                         'current':{'stage':'copying','sent':93,'total':100,'rate':8.4*MB,'eta_s':120}})
  self.q=lt.queue_view(view,debrid)
 def test_sections(self):
  q=self.q
  self.assertEqual(q['now']['id'],'p1');self.assertEqual([r['id'] for r in q['line']],['w1','w2','w3','w4'])
  self.assertEqual(q['line'][0]['title'],'1. Alpha (2020)');self.assertEqual((q['line'][0]['up'],q['line'][0]['down']),('','true'))
  self.assertEqual((q['line'][-1]['up'],q['line'][-1]['down']),('true',''));self.assertEqual([r['id'] for r in q['held']],['s1'])
  self.assertEqual([d['title'] for d in q['drive']],['Fall 2','The.Batman']);self.assertTrue(q['drive'][0]['sub'].startswith('93% · 8.4 MB/s'))
  self.assertEqual(q['drive'][1]['sub'],'Waiting · AllDebrid has it ready')
 def test_properties_fill_every_slot(self):
  props=lt.queue_properties(self.q)
  self.assertEqual(props['line.count'],'4 videos');self.assertEqual(props['line.5.title'],'');self.assertEqual(props['empty'],'')
  xml=ltp.queue_page(portrait)
  for k in props:self.assertIn('Window().Property(%s)'%k,xml,k)
  self.assertEqual(lt.queue_properties(lt.queue_view({'rows':{}}))['empty'],'Nothing is waiting to be converted.')
 def test_more_than_fit(self):
  line=[{'id':str(n),'title':'T%d'%n,'state':'waiting','sub':'x · y'} for n in range(13)]
  props=lt.queue_properties(lt.queue_view({'rows':{'waiting':line}}))
  self.assertEqual(props['line.more'],'and 3 more below: move one up to see it')

class Pages(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.files=ltp.files(portrait)
  cls.trees={k:ET.fromstring(v.decode().split('\n',2)[2]) for k,v in cls.files.items() if k.endswith('.xml')}
 def test_every_button_is_44_pt(self):
  for name,tree in self.trees.items():
   least=100 if name.startswith('1080i/') else ltp.HIT
   for c in tree.iter('control'):
    if c.get('type')=='button' and c.get('id')!='9099':self.assertGreaterEqual(float(c.findtext('height') or 0),least,(name,c.get('id')))
 def test_ids(self):
  ids=lambda name:{c.get('id') for c in self.trees[name].iter('control')}
  q=ids('portrait/IOSQueue.xml')
  for n in range(1,ltp.QUEUE_SLOTS+1):self.assertIn(str(ltp.UP+n),q);self.assertIn(str(ltp.DOWN+n),q)
  s=ids('portrait/IOSPhoneSpace.xml')
  for n in range(1,ltp.SPACE_ROWS+1):self.assertIn(str(ltp.BAR+n),s);self.assertIn(str(ltp.CLEAR+n),s)
  self.assertTrue({str(ltp.DAY+n) for n in (1,2,3)}<=ids('portrait/IOSHistory.xml'))
  self.assertIn(str(ltp.CLOSE),ids('1080i/IOSAirPlayCheck.xml'));self.assertIn(str(ltp.BACK),ids('portrait/IOSAirPlayCheck.xml'))
  self.assertEqual(ltp.DAYS,lt.DAYS)
 def test_arrows_and_registration(self):
  self.assertTrue(self.files['extras/portrait/arrow_up.png'].startswith(b'\x89PNG'))
  text=(LIB/'portrait.py').read_text()
  self.assertIn('library_tools_page.files(ns)',text);self.assertIn("'IOSAirPlayCheck.xml'",text.split('OWN_1080I=')[1].split('\n')[0])
  self.assertIn('Path(library_tools_page.__file__)',text)
  skip=(LIB/'activity_skin.py').read_text()
  for name in (ltp.QUEUE,ltp.SPACE,ltp.HISTORY,ltp.AIRPLAY):self.assertIn("'%s'"%name,skip)
 def test_back_is_the_nav_button(self):
  for name in ('portrait/IOSQueue.xml','portrait/IOSPhoneSpace.xml','portrait/IOSHistory.xml','portrait/IOSAirPlayCheck.xml'):
   self.assertIn('chevron-left.png',self.files[name].decode())

class PhoneSpaceTools(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.profile=self.root/'userdata';self.home=self.root/'home';self.el=self.root/'Elementum Downloads'
  (self.profile/'Thumbnails/a').mkdir(parents=True);(self.profile/'Thumbnails/a/x.jpg').write_bytes(b'1'*3000)
  (self.profile/'Thumbnails/a/Textures.db').write_bytes(b'd'*10)
  (self.home/'temp').mkdir(parents=True);(self.home/'temp/kodi.log').write_bytes(b'l'*500)
  (self.home/'temp/old.tmp').write_bytes(b't'*700);(self.home/'temp/new.tmp').write_bytes(b'n'*100)
  os.utime(self.home/'temp/old.tmp',(time.time()-3600,)*2)
  (self.el/'Running Movie').mkdir(parents=True);(self.el/'Running Movie/a.mkv').write_bytes(b'r'*4000)
  (self.el/'Old Movie.2019').mkdir();(self.el/'Old Movie.2019/b.mkv').write_bytes(b'o'*5000)
  (self.profile/'addon_data/x').mkdir(parents=True);(self.profile/'addon_data/x/settings.xml').write_bytes(b's'*200)
  self.places=lt.space_places(str(self.profile),str(self.home),[str(self.el),str(self.el)],'')
 def tearDown(self):self.tmp.cleanup()
 def test_measure_and_what_is_safe(self):
  m=lt.measure(self.places,[{'name':'Running Movie','progress':40}],time.time())
  self.assertEqual(m['artwork']['bytes'],3010);self.assertEqual([Path(p).name for p in m['artwork']['clear']],['x.jpg'])
  self.assertEqual([Path(p).name for p in m['elementum']['clear']],['Old Movie.2019']);self.assertEqual(m['elementum']['bytes'],5000)
  self.assertEqual([Path(p).name for p in m['temp']['clear']],['old.tmp'])   # not the log, not a file changed just now
  self.assertEqual((m['data']['bytes'],m['data']['clear']),(200,None))
 def test_elementum_not_answering_clears_nothing(self):
  m=lt.measure(self.places,None,time.time());self.assertIsNone(m['elementum']['clear'])
  props,_=lt.space_properties(m,40*GB);self.assertEqual(props['space.2.clear'],'');self.assertIn("isn't answering",props['space.2.line'])
 def test_clear_frees_and_keeps_the_rest(self):
  m=lt.measure(self.places,[{'name':'Running Movie'}],time.time())
  self.assertEqual(lt.clear(m['elementum']['clear']),5000)
  self.assertTrue((self.el/'Running Movie/a.mkv').exists());self.assertFalse((self.el/'Old Movie.2019').exists())
  self.assertEqual(lt.clear(m['temp']['clear']),700);self.assertTrue((self.home/'temp/kodi.log').exists())
 def test_properties_and_the_split_bar(self):
  m={'artwork':{'bytes':GB,'clear':['x']},'elementum':{'bytes':GB,'clear':['y']},'temp':{'bytes':0,'clear':[]},
     'data':{'bytes':GB,'clear':None},'app':{'bytes':GB,'clear':None}}
  props,bar=lt.space_properties(m,48*GB)
  self.assertEqual(props['total'],'4.0 GB');self.assertEqual(props['free'],'48 GB free on this iPhone');self.assertEqual(bar,[25,50,50,75,100])
  self.assertEqual((props['space.1.clear'],props['space.3.clear'],props['space.4.clear']),('true','',''))
  xml=ltp.space_page(portrait)
  for k in props:self.assertIn('Window().Property(%s)'%k,xml,k)
  self.assertEqual(lt.space_properties(None,None)[0]['total'],'Measuring…')

class History(unittest.TestCase):
 def test_failures_are_kept_30_days(self):
  with tempfile.TemporaryDirectory() as p:
   now=time.time()
   th.failed(p,'conv','Inception.2010.mkv','DVD picture subtitles',now-40*86400);th.failed(p,'up','Fall 2','AllDebrid could not fetch it',now)
   self.assertEqual([(f['kind'],f['title']) for f in th.failures(p,now)],[('up','Fall 2')])
   th.failed(p+'/missing/'+'x'*5000,'up','x','y')   # never raises
 def test_finished_keeps_30_days(self):
  d={'finished':[{'kind':'up','title':'old','start':0,'end':1000}]}
  th._finish(d,{'kind':'down','title':'new','start':40*86400,'last':40*86400+60,'sum':0,'n':1})
  self.assertEqual([f['title'] for f in d['finished']],['new']);self.assertGreaterEqual(th.FINISHED,200)
 def test_days_totals_and_a_stopped_conversion(self):
  now=time.mktime((2026,11,6,15,0,0,0,0,-1));today=lt.midnight(now)
  finished=[{'kind':'up','title':'Fall 2','start':today+3600,'end':today+3600+37*60,'avg':7.8*MB,'size':16.9*GB},
            {'kind':'conv','title':'Inception (2010)','start':today+7200,'end':today+7200+1800,'avg':MB,'size':0},
            {'kind':'down','title':'Scarface','start':today-80000,'end':today-79000,'avg':20*MB,'size':4*GB},
            {'kind':'down','title':'Ancient','start':today-20*86400,'end':today-20*86400+60,'size':GB}]
  failures=[{'kind':'conv','title':'Inception (2010)','reason':'a damaged subtitle','time':today+7200+1830},
            {'kind':'up','title':'The Batman','reason':'AllDebrid could not fetch it','time':today-3*86400}]
  h=lt.history_view(finished,failures,now,'today')
  self.assertEqual([(r['title'],r['tone']) for r in h['rows']],[('Inception (2010)','bad'),('Fall 2','ok')])
  self.assertEqual(h['rows'][0]['line'],'after 30 min');self.assertEqual(h['rows'][1]['line'],'16.9 GB · 37 min · 7.8 MB/s')
  self.assertEqual(h['rows'][1]['result'],'On Google Drive');self.assertEqual((h['count'],h['failed'],h['total']),(2,2,'20.9 GB'))
  self.assertEqual(h['busiest'],'Busiest: today · 16.9 GB')
  self.assertEqual([r['title'] for r in lt.history_view(finished,failures,now,'yesterday')['rows']],['Scarface'])
  self.assertEqual(len(lt.history_view(finished,failures,now,'week')['rows']),4)
  props=lt.history_properties(h,'today');xml=ltp.history_page(portrait)
  for k in props:
   if k!='day':self.assertIn('Window().Property(%s)'%k,xml,k)
  self.assertIn("Window().Property(day)",xml)
  self.assertEqual(lt.history_properties(lt.history_view([],[],now,'yesterday'),'yesterday')['empty'],'Nothing finished yesterday.')
 def test_failures_are_noted_where_jobs_fail(self):
  self.assertIn("transfer_history.failed(q.profile,'conv'",(LIB/'prepare_cloud.py').read_text())
  self.assertIn("transfer_history.failed(self.profile,'conv'",(LIB/'prepare_downloads.py').read_text())
  self.assertEqual((LIB/'debrid_drive.py').read_text().count("transfer_history.failed(profile, 'up'"),2)

THIRD=['start: http://127.0.0.1:5000/download/x/Inception.mkv',
       'master: #EXT-X-STREAM-INF:BANDWIDTH=9000000,CODECS="hvc1.2.4.L150,mp4a.40.2",RESOLUTION=3840x2160,VIDEO-RANGE=PQ',
       'compat: third-party AirPlay receivers (MFi_AirPlay_Device) get the picture as H.264, others the hvc1 copy',
       'client: AppleCoreMedia/1.0.0.24A446 (iPhone; U; CPU OS 27_0_1 like Mac OS X; en_us)',
       'client: AirPlay/2.0 MFi_AirPlay_Device (MFiModelGroup/TCL-Roku)',
       'compat: AirPlay/2.0 MFi_AirPlay_Device gets the picture as H.264: CODECS="avc1.640028"',
       'GET /master.m3u8 200 512 B 2 ms','GET /cvideo/seg0.m4s 200 1834567 B 412 ms','GET /cvideo/seg1.m4s 200 1834567 B 380 ms',
       'compat: segment 1 converted in 900 ms (40% of realtime) via vt, source I/O 20 ms, 0 subtitle events, 0 frames drawn, subtitle preroll through 0.000 s',
       'player: ready','player: external playback ended','player: closed at 1312.0 s']

class AirPlayCheck(unittest.TestCase):
 def test_a_third_party_tv_that_played(self):
  with tempfile.TemporaryDirectory() as p:
   lt.begin_airplay(p,'Inception',1000);lt.note_airplay(p,THIRD[:7],1001);lt.note_airplay(p,THIRD[7:],1002)
   s=lt.load_airplay(p);self.assertEqual((s['title'],s['video'],s['requests']),('Inception',2,3))
   self.assertFalse(any(x.startswith(('GET','compat: segment')) for x in s['lines']))
   check=lt.airplay_steps(s)
   self.assertEqual(check['tone'],'ok');self.assertEqual(check['try'],'')
   self.assertEqual([x[1] for x in check['steps']],['A TV with AirPlay built in (TCL-Roku)',
                    'Converted to H.264 from HEVC 4K HDR (this TV needs it)','The TV asked for the video (2 parts sent)',
                    'AirPlay ended on the TV after 21 min'])
 def test_a_tv_that_never_asked(self):
  import cast
  s={'title':'Nightmare','started':1,'lines':['start: http://127.0.0.1/x.mp4','prepared: source-resolution MP4 byte ranges; no live conversion, subtitle burn or prefetch queue',
     'master: CODECS="avc1.640028",RESOLUTION=1920x1080',
     'player: could not open the stream: Error Domain=NSURLErrorDomain Code=-1004 "Could not connect to the server."'],'video':0,'requests':0}
  check=lt.airplay_steps(s,cast.player_problem)
  self.assertEqual(check['tone'],'bad');self.assertEqual(check['steps'][0],('The TV','No TV connected','bad'))
  self.assertEqual(check['steps'][1][1],'Sent as it is (H.264 1080p): this video is already prepared')
  self.assertEqual(check['steps'][3][1],'It stopped: the TV could not connect to the phone');self.assertIn('same Wi-Fi',check['try'])
  props=lt.airplay_properties(check,61);self.assertEqual(props['headline'],"It didn't work");self.assertEqual(props['when'],'1 min ago')
  for xml in (ltp.airplay_page(portrait),ltp.airplay_sheet()):
   for k in props:
    if k!='tone':self.assertIn('Window().Property(%s)'%k,xml,k)
 def test_apple_tv_and_no_session(self):
  s={'lines':['client: AppleCoreMedia/1.0 (Apple TV; U; CPU OS 18)','master: CODECS="hvc1"','player: ready'],'video':5}
  self.assertEqual(lt.airplay_steps(s)['steps'][0][1],'An Apple TV');self.assertIsNone(lt.airplay_steps({}))
  self.assertEqual(lt.airplay_properties(None,0)['empty'],'No Play on TV yet. After one, this shows how it went.')
 def test_a_new_start_begins_a_new_session(self):
  with tempfile.TemporaryDirectory() as p:
   lt.note_airplay(p,THIRD,1);lt.note_airplay(p,['start: http://127.0.0.1/y.mp4','player: ready'],2)
   self.assertEqual(lt.load_airplay(p)['lines'],['start: http://127.0.0.1/y.mp4','player: ready'])
 def test_relay_hands_the_lines_on(self):
  import airplay
  seen=[];written=[]
  class Lib:
   calls=0
   def kodi_airplay_log(self,buffer,size):
    Lib.calls+=1
    if Lib.calls>1:return 0
    data=b'player: ready\nclient: x';buffer.value=data;return len(data)
  airplay.relay(Lib(),written.append,lambda s:True,keep=seen.extend)
  self.assertEqual(seen,['player: ready','client: x']);self.assertEqual(len(written),2)
 def test_wired_into_play_on_tv_and_the_service(self):
  cast_src=(BOOT/'cast.py').read_text();self.assertIn('library_tools.begin_airplay(profile,title)',cast_src)
  self.assertLess(cast_src.index('library_tools.begin_airplay'),cast_src.index("lib.kodi_airplay_play(source"))
  self.assertIn('library_tools.note_airplay(profile,',cast_src);self.assertIn("'keep':lambda lines:library_tools.note_airplay(profile,lines)",(BOOT/'service.py').read_text())
  sheet=load('pages_tools',LIB/'pages.py').play_on_tv();self.assertIn('id="9501"',sheet);self.assertIn('Last time',sheet)
  self.assertTrue(lt.airplay_notice({'title':"AirPlay didn't start"}));self.assertFalse(lt.airplay_notice({'title':'Saved to Google Drive'}))

class Wiring(unittest.TestCase):
 def test_entry_points(self):
  self.assertIn("'tool_pages'",(BOOT/'default.py').read_text());self.assertTrue((BOOT/'tool_pages.py').exists())
  self.assertIn('id="%d"'%library_page.EDIT,library_page.page(portrait));self.assertIn('id="%d"'%library_page.SPACE_TAP,library_page.page(portrait))
  tp=load('transfers_page_tools',LIB/'transfers_page.py');self.assertIn('id="%d"'%tp.HISTORY,tp.page(portrait))
  self.assertIn('tool_windows.open_history(profile)',(BOOT/'transfers.py').read_text())
  self.assertIn('tool_windows.open_airplay(profile)',(BOOT/'notifications.py').read_text())
  for page in ('tool_pages.py',):self.assertNotRegex((BOOT/page).read_text(),r'xbmcaddon\.Addon\(\)')

class TapEveryButton(unittest.TestCase):
 """The real controllers through a fake Kodi, opened from the pages the owner taps."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.profile=self.tmp.name;prep.save(self.profile,queue_state())
 def tearDown(self):self.tmp.cleanup()
 def run_status(self,script):
  kodi=ls.FakeKodi(self.profile,script)
  import notices
  with patch.dict(sys.modules,kodi.modules),patch.object(notices,'downloads',lambda get=None:[]),patch.object(notices,'torrent_list',lambda *a,**k:[]):
   load('library_status_tools',BOOT/'library_status.py').run([])
  return kodi
 def test_edit_order_moves_a_video_down_and_up(self):
  seen=[]
  snap=lambda w:seen.append([w.getProperty('line.%d.title'%n) for n in range(1,5)])
  open_waiting=lambda w:w.set_filter('waiting')
  kodi=self.run_status([(library_page.WINDOW,open_waiting),(library_page.WINDOW,ls.tap(library_page.EDIT)),
                        (ltp.QUEUE,snap),(ltp.QUEUE,ls.tap(ltp.DOWN+1)),(ltp.QUEUE,snap),(ltp.QUEUE,ls.tap(ltp.UP+2)),(ltp.QUEUE,ls.tap(ltp.UP+1)),
                        (ltp.QUEUE,ls.tap(ltp.UP+4)),(ltp.QUEUE,snap),(ltp.QUEUE,lambda w:seen.append(w.getProperty('now.title'))),
                        (ltp.QUEUE,ls.tap(ltp.BACK)),(library_page.WINDOW,lambda w:seen.append(ls.TapEveryButton.page_rows(None,w))),
                        (library_page.WINDOW,ls.tap(library_page.BACK)),(library_page.WINDOW,ls.tap(library_page.BACK))])
  self.assertEqual(seen[0],['1. Alpha (2020)','2. Bravo (2020)','3. Charlie (2020)','4. Delta (2020)'])
  self.assertEqual(seen[1][:2],['1. Bravo (2020)','2. Alpha (2020)'])
  self.assertEqual(seen[2],['1. Alpha (2020)','2. Bravo (2020)','3. Delta (2020)','4. Charlie (2020)'])   # ▲ on the top one: nothing
  self.assertEqual(seen[3],'Inception (2020)')
  waiting=[r[0] for r in seen[4] if r[1]=='waiting'];self.assertEqual(waiting,['w1','w2','w4','w3'])   # Library status agrees
  self.assertEqual([(r['action'],r['id']) for r in prep.pending_requests(self.profile)],[('down','w1'),('up','w1'),('up','w4')])
  self.assertFalse(prep.interrupts(self.profile));self.assertTrue(all(w.closed for w in kodi.windows))
 def test_phone_space_card_opens_and_clears(self):
  art=Path(self.profile)/'Thumbnails';art.mkdir();(art/'a.jpg').write_bytes(b'x'*(2*MB))
  seen={}
  def wait(w):
   for _ in range(200):
    if w.getProperty('space.1.clear'):break
    time.sleep(0.02)
   seen['before']=(w.getProperty('space.1.size'),w.getProperty('space.1.clear'),w.getControl(ltp.BAR+1).percent)
  def after(w):
   for _ in range(200):
    if w.getProperty('space.1.size')=='0 MB':break
    time.sleep(0.02)
   seen['after']=w.getProperty('space.1.size')
  kodi=self.run_status([(library_page.WINDOW,ls.tap(library_page.SPACE_TAP)),(ltp.SPACE,wait),(ltp.SPACE,ls.tap(ltp.CLEAR+1)),(ltp.SPACE,after),
                        (ltp.SPACE,ls.tap(ltp.BACK)),(library_page.WINDOW,ls.tap(library_page.BACK))])
  self.assertEqual(seen['before'][:2],('2 MB','true'));self.assertIsNotNone(seen['before'][2])
  self.assertEqual(seen['after'],'0 MB');self.assertFalse((art/'a.jpg').exists())
  self.assertIn(('yesno','Clear 2 MB of artwork cache?'),kodi.notes);self.assertIn(('note','Cleared 2 MB of artwork cache'),kodi.notes)
 def test_history_from_transfers(self):
  now=time.time()
  th.save(self.profile,{'finished':[{'kind':'up','title':'Fall 2','start':now-600,'end':now-60,'avg':MB,'size':GB,'peak':MB}]})
  th.failed(self.profile,'conv','Inception.2010.mkv','a damaged subtitle',now-30)
  seen=[]
  import transfers_page as tp
  kodi=ls.FakeKodi(self.profile,[(tp.WINDOW,ls.tap(tp.HISTORY)),(ltp.HISTORY,lambda w:seen.append((w.getProperty('h.1.title'),w.getProperty('h.2.result')))),
                                 (ltp.HISTORY,ls.tap(ltp.DAY+2)),(ltp.HISTORY,lambda w:seen.append((w.getProperty('day'),w.getProperty('empty')))),
                                 (ltp.HISTORY,ls.tap(ltp.BACK)),(tp.WINDOW,ls.tap(tp.BACK))])
  kodi.modules['xbmcvfs'].listdir=lambda p:([],[])
  with patch.dict(sys.modules,kodi.modules):load('transfers_tools',BOOT/'transfers.py').run(['up'])
  self.assertEqual(seen[0],('Inception (2010)','On Google Drive'));self.assertEqual(seen[1],('yesterday','Nothing finished yesterday.'))
  self.assertTrue(all(w.closed for w in kodi.windows))
 def test_airplay_check_from_a_notification(self):
  import notices
  lt.note_airplay(self.profile,THIRD)
  notices.add(self.profile,'info','Playing with AirPlay','Inception')
  seen={}
  kodi=ls.FakeKodi(self.profile,[('IOSNotifications.xml',ls.tap(9501)),(ltp.AIRPLAY,lambda w:seen.update(dict(w.props))),(ltp.AIRPLAY,ls.tap(ltp.BACK)),
                                 ('IOSNotifications.xml',ls.tap(9001))])
  class Window:
   def __init__(self,n):pass
   def setProperty(self,*a):pass
  kodi.modules['xbmcgui'].Window=Window;kodi.modules['xbmc'].executebuiltin=lambda a:None
  with patch.dict(sys.modules,kodi.modules),patch.object(notices,'downloads',lambda get=None:[]),patch.object(notices,'uploads',lambda p:[]):
   load('notifications_tools',BOOT/'notifications.py').run()
  self.assertEqual(seen['headline'],'It worked');self.assertEqual(seen['step.1.detail'],'A TV with AirPlay built in (TCL-Roku)')
  self.assertFalse(any(w.xml=='IOSNoticeDetail.xml' for w in kodi.windows));self.assertTrue(all(w.closed for w in kodi.windows))
 def test_last_time_from_the_play_on_tv_sheet(self):
  lt.note_airplay(self.profile,THIRD)
  seen={}
  kodi=ls.FakeKodi(self.profile,[('IOSPlayOnTV.xml',lambda w:seen.update(last=w.getProperty('last'))),('IOSPlayOnTV.xml',ls.tap(9501)),
                                 (ltp.AIRPLAY,lambda w:seen.update(title=w.getProperty('title'))),(ltp.AIRPLAY,ls.tap(ltp.CLOSE)),
                                 ('IOSPlayOnTV.xml',ls.tap(9500))])
  import threading
  done=threading.Event();done.set()
  with patch.dict(sys.modules,kodi.modules):
   cast_page=load('cast_tools',BOOT/'cast.py')
   chosen=cast_page.pick_sheet(kodi.modules['xbmc'],kodi.modules['xbmcgui'],str(BOOT),'Inception','',[],{},done,'')
  self.assertIsNone(chosen);self.assertEqual(seen,{'last':'true','title':'Last Play on TV'})

if __name__=='__main__':unittest.main()
