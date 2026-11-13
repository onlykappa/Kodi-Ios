"""Settings › Library › Library status (owner-approved mockup, build 158): prepare_downloads.library_view and its
requests, library_rows (what the page lists and the details sheet says), library_page (the skin XML) and the wiring."""
import importlib.util,json,os,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
sys.path.insert(0,str(LIB))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
import prepare_downloads as prep
import library_rows as rows
portrait=load('portrait_libstatus',LIB/'portrait.py')
library_page=load('library_page_t',LIB/'library_page.py')
GB=1024**3

def item(n,name,state='todo',size=4*GB):return {'id':n,'name':name,'folder':'Movies','size':size,'state':state}
def job(n,name,**extra):return dict({'source':{'id':n,'name':name,'size':4*GB},'status':'waiting'},**extra)

def library_state():
 items=[item('r1','Heat.1995.2160p.HDR.mkv','ready'),item('r2','Dune.2021.1080p.mkv','ready'),
        item('w1','Fall.2022.1080p.mkv'),item('w2','Alien.1979.2160p.mkv'),item('s1','Big.2020.2160p.mkv',size=60*GB),
        item('p1','Lanterns.S01E01.2160p.mkv'),item('f1','Broken.2019.1080p.mkv'),item('k1','Odd.2018.2160p.mkv'),
        item('k2','Mine.2017.1080p.mkv'),item('u1','Gone.2016.mkv','unreadable')]
 jobs={'a':job('w1','Fall.2022.1080p.mkv'),'b':job('w2','Alien.1979.2160p.mkv',priority=50),
       'c':job('s1','Big.2020.2160p.mkv',space=70*GB),'d':job('p1','Lanterns.S01E01.2160p.mkv'),
       'e':job('f1','Broken.2019.1080p.mkv',status='failed',error='HTTP Error 503',retry_after=1600),
       'f':job('k1','Odd.2018.2160p.mkv',blocked=True,error='picture subtitles: tracks MP4 cannot preserve'),
       'g':job('k2','Mine.2017.1080p.mkv',kept=True)}
 return {'library':{'items':items,'checked':880},'jobs':jobs,
         'current':{'running':True,'title':'Lanterns.S01E01.2160p.mkv','progress':39,'stage':'Step 3 of 3 · Writing MP4'}}

class View(unittest.TestCase):
 def setUp(self):
  self.view=prep.library_view(library_state(),[{'id':'t','title':'New One','progress':12,'line':'12%  ·  1 GB of 8 GB','speed':'2 MB/s'}],
                              [],free=40*GB,working=2*GB,now=lambda:1000)
 def test_counts_and_ring(self):
  v=self.view
  self.assertEqual((v['ready'],v['todo'],v['downloading'],v['kept'],v['total']),(2,6,1,2,10))
  self.assertEqual(v['pct'],20);self.assertEqual(v['checked'],'checked 2 min ago')
 def test_sections(self):
  r=self.view['rows']
  self.assertEqual([x['id'] for x in r['preparing']],['p1']);self.assertEqual(r['preparing'][0]['pct'],39)
  self.assertEqual(r['preparing'][0]['sub'],'Writing MP4 · 39%')
  self.assertEqual([x['id'] for x in r['waiting'][:2]],['w2','w1'])
  self.assertTrue(r['waiting'][0]['sub'].startswith('Next · 2160p'));self.assertTrue(r['waiting'][1]['sub'].startswith('2nd in line'))
  states={x['id']:x['state'] for x in r['waiting']}
  self.assertEqual((states['s1'],states['f1'],states['u1']),('space','problem','problem'))
  self.assertEqual({x['id']:x['owner'] for x in r['kept']},{'k1':False,'k2':True})
  self.assertIn('picture subtitles',[x for x in r['kept'] if x['id']=='k1'][0]['sub'])
  self.assertEqual(r['downloading'][0]['state'],'downloading')
 def test_problem_reason_in_plain_words(self):
  f1=[x for x in self.view['rows']['waiting'] if x['id']=='f1'][0]
  self.assertEqual(f1['reason'],'Google Drive did not answer');self.assertIn('in 10 min',f1['sub'])
 def test_empty_library(self):
  v=prep.library_view({});self.assertEqual((v['total'],v['pct'],v['checked']),(0,0,'not checked yet'))
  self.assertEqual(rows.page_properties(v)['headline'],'Not checked yet')
  self.assertEqual(rows.list_items(v),[])

class Rows(unittest.TestCase):
 def setUp(self):
  state=library_state()
  for n in range(8):state['library']['items'].append(item('x%d'%n,'Film%d.2000.1080p.mkv'%n,'ready'))
  self.view=prep.library_view(state,free=40*GB,working=2*GB,now=lambda:1000)
 def test_all_shows_what_happens_now_and_folders(self):
  items=rows.list_items(self.view)
  self.assertTrue(all(i['kind']=='row' for i in items))
  self.assertEqual([i['props']['section'] for i in items if i['props']['section']],['UP NEXT','READY FOR KODI AND AIRPLAY','KEPT AS IT IS'])
  self.assertEqual(sum(i['props']['state']=='ready' for i in items),10)
  self.assertEqual(items[0]['props']['number'],'1')
 def test_every_item_is_one_height_in_one_layout(self):
  xml=library_page.page(portrait)
  self.assertIn('<control type="grouplist" id="9300">',xml)
  # Build 194 (boards 1 and 2): one pool of rows per section, each section one grouped card.
  for key in ('down','next','kept','ready'):self.assertIn('Window().Property(%s.0.title)'%key,xml)
  self.assertIn('Window().Property(next.0.number)',xml)
 def test_positions_round_the_group(self):
  waiting=[i['props']['pos'] for i in rows.list_items(self.view,'waiting')]
  self.assertEqual((waiting[0],waiting[-1]),('first','last'));self.assertTrue(all(p=='mid' for p in waiting[1:-1]))
 def test_filters(self):
  todo={i['props']['state'] for i in rows.list_items(self.view,'todo')}
  self.assertNotIn('ready',todo);self.assertIn('preparing',todo)
  self.assertEqual(rows.list_items(self.view,'downloading'),[])
 def test_ring_texture(self):
  self.assertEqual((rows.ring_name(0),rows.ring_name(39),rows.ring_name(100),rows.ring_name(None)),('ring_00.png','ring_08.png','ring_20.png','ring_00.png'))
 def test_page_top(self):
  props=rows.page_properties(self.view)
  self.assertEqual(props['headline'],'10 of 18 ready');self.assertNotIn('space',props)   # owner, build 173: no phone space card
  self.assertIn('checking now',rows.page_properties(self.view,True)['sub'])
 def test_details_actions(self):
  by={r['id']:r for k in self.view['rows'].values() for r in k}
  actions=lambda n:[a for _,a in rows.details(by[n],self.view)['actions']]
  self.assertEqual(actions('w1'),['now','next','keep']);self.assertEqual(actions('s1'),['next','keep'])
  self.assertEqual(actions('f1'),['retry','keep']);self.assertEqual(actions('k2'),['prepare']);self.assertEqual(actions('k1'),[])
  # Build 177 (approved): a ready movie can be played from its sheet.
  self.assertEqual(actions('r1'),['play','tv']);self.assertEqual(rows.details(by['r1'],self.view)['tone'],'ok')
  space=rows.details(by['s1'],self.view);self.assertEqual(space['tone'],'warn')
  self.assertIn(('Free now','40 GB'),space['facts']);self.assertTrue(all(len(rows.details(r,self.view)['facts'])<=rows.FACTS for r in by.values()))

class Requests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.queue=prep.Queue.__new__(prep.Queue);self.queue.profile=self.tmp.name;self.queue.clock=lambda:5000
  self.queue.state=library_state();self.queue.commit=lambda:None
 def tearDown(self):self.tmp.cleanup()
 def test_requests_are_applied_once(self):
  for action,n in (('next','w1'),('retry','f1'),('keep','w2'),('prepare','k2'),('next','w1')):prep.request(self.tmp.name,action,n)
  pending=json.loads((prep.location(self.tmp.name).parent/prep.REQUESTS).read_text())
  self.assertEqual(len(pending),4)   # the repeated request replaces the first
  self.assertTrue(self.queue.apply_requests());jobs=self.queue.state['jobs']
  self.assertEqual(jobs['a']['priority'],5000);self.assertTrue(jobs['b']['kept']);self.assertNotIn('kept',jobs['g'])
  self.assertEqual((jobs['e']['status'],jobs['e']['retry_after']),('waiting',0));self.assertNotIn('error',jobs['e'])
  self.assertFalse(self.queue.apply_requests())
 def test_next_moves_it_to_the_front(self):
  self.queue.state['jobs']['a']['priority']=9000
  v=prep.library_view(self.queue.state,now=lambda:1000);self.assertEqual(v['rows']['waiting'][0]['id'],'w1')
 def test_kept_videos_are_not_prepared(self):
  source=(LIB/'prepare_downloads.py').read_text()
  self.assertIn("not job.get('kept')",source.split('def process_one')[1].split('candidates=')[1][:300])

class Skin(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.page=library_page.page(portrait);cls.sheet=library_page.item_sheet(portrait)
  cls.pagex=ET.fromstring(cls.page.split('\n',2)[2]);cls.sheetx=ET.fromstring(cls.sheet.split('\n',2)[2])
 def test_every_button_is_at_least_44_pt(self):
  for tree in (self.pagex,self.sheetx):
   for c in tree.iter('control'):
    if c.get('type')=='button':
     self.assertGreaterEqual(float(c.findtext('height') or 0),library_page.HIT,c.get('id'))
 def test_ids_the_controller_uses(self):
  ids={c.get('id') for c in self.pagex.iter('control')}
  for n in (library_page.LIST,library_page.BACK,library_page.CHECK,library_page.EDIT,9101,9102,9103,9104):self.assertIn(str(n),ids)
  ids={c.get('id') for c in self.sheetx.iter('control')}
  for n in (9200,9201,9202,9099):self.assertIn(str(n),ids)
 def test_properties_the_controller_sets(self):
  for k in ('sub','headline','count.ready','count.working','count.next','count.kept'):
   self.assertIn('Window().Property(%s)'%k,self.page,k)
  for k in ('title','quality','poster','fact3.value','action2.label','step2.label','card.num','card.unit','card.left','card.wait'):
   self.assertIn('Window().Property(%s)'%k,self.sheet,k)
  for k in ('title','sub','number','pos'):
   self.assertIn('Window().Property(next.0.%s)'%k,self.page,k)
 def test_status_sheet_closes_with_a_cross(self):
  self.assertIn('close_cross.png',self.sheet);self.assertTrue(all(c.findtext('label')!='Done' for c in self.sheetx.iter('control') if c.get('type')=='button'))
 def test_pill_stays_off_this_page(self):
  skin=(LIB/'activity_skin.py').read_text()
  self.assertIn('IOSLibraryStatus.xml',skin);self.assertIn('IOSLibraryItem.xml',skin)
 def test_registered_in_the_skin(self):
  files=library_page.files(portrait)
  self.assertEqual(sorted(Path(k).name for k in files if k.endswith('.xml')),['IOSLibraryItem.xml','IOSLibraryStatus.xml'])
  # Build 194: the rounded shapes the approved boards use (status_ui.textures), drawn by the generator.
  self.assertTrue({'r27.png','pill16.png','poster27.png'}<=set(Path(k).name for k in files))
  self.assertIn('library_page.files(ns)',(LIB/'portrait.py').read_text())

class Wiring(unittest.TestCase):
 def test_settings_row_opens_the_page(self):
  setting=ET.parse(BOOT/'resources/settings.xml').find(".//setting[@id='library_status']")
  self.assertEqual(setting.findtext('data'),'RunScript(service.kodi.ios.bootstrap,library_status)')
  self.assertIn("'library_status'",(BOOT/'default.py').read_text())
  self.assertIn("R(9457,'Library status',LIBRARY_STATUS",(LIB/'settings_page.py').read_text())
  self.assertTrue((BOOT/'library_status.py').exists())
 def test_controller_compiles_without_kodi(self):
  sys.modules.pop('library_status_t',None)
  module=load('library_status_t',BOOT/'library_status.py')
  self.assertTrue(callable(module.run));self.assertEqual(module.FILTER_BASE,9101)

def model_for(profile):
 import work_state,time
 now=time.time()
 state=prep.apply_to(prep.load(profile),prep.pending_requests(profile),now)
 if state.get('current'):state['current']['updated']=now
 return work_state.build({'prep':state},now)

class FakeKodi:
 """Just enough of xbmc, xbmcgui, xbmcaddon and xbmcvfs to run library_status.run() and tap every button."""
 def __init__(self,profile,script,settings=None,answer=True):
  import types
  self.script=list(script);self.settings=dict(settings or {'prepare_downloads':True});self.answer=answer
  self.notes=[];self.windows=[];self.menus=[];self.picks=[];kodi=self
  xbmc=types.ModuleType('xbmc');xbmc.LOGWARNING=2;xbmc.LOGINFO=1;xbmc.log=lambda *a:None
  class Monitor:
   def waitForAbort(self,t=0):return True    # the refresh loop ends at once; the test refreshes by tapping
  xbmc.Monitor=Monitor
  def visible(condition):
   # Window.IsActive(N): window N (its index here) is open; live_window.Guard asks before touching controls.
   import re
   m=re.match(r'Window\.IsActive\((\d+)\)$',condition)
   return bool(m) and int(m.group(1))<len(kodi.windows) and not kodi.windows[int(m.group(1))].closed
  xbmc.getCondVisibility=visible
  gui=types.ModuleType('xbmcgui');gui.NOTIFICATION_INFO='info';gui.NOTIFICATION_WARNING='warn'
  class ListItem:
   def __init__(self,label='',label2=''):self.label,self.label2,self.props,self.art=label,label2,{},{}
   def setProperty(self,k,v):self.props[k]=v
   def getProperty(self,k):return self.props.get(k,'')
   def setLabel2(self,v):self.label2=v
   def setArt(self,a):self.art.update(a)
   def getArt(self,k):return self.art.get(k,'')
  class Control:
   def __init__(self):self.items=[];self.selected=0;self.percent=None
   def reset(self):self.items=[];self.selected=0
   def addItems(self,items):self.items.extend(items)
   def getSelectedPosition(self):return self.selected if self.items else -1
   def selectItem(self,n):self.selected=n
   def getListItem(self,n):return self.items[n]
   def setPercent(self,v):self.percent=v
  class Window:
   def __init__(self,xml,*rest):
    self.xml=xml;self.props={};self.controls={};self.closed=False;self.focus=None;self._kodi=kodi;kodi.windows.append(self)
   def setProperty(self,k,v):self.props[k]=v
   def getProperty(self,k):return self.props.get(k,'')
   def getId(self):return kodi.windows.index(self)
   def getControl(self,n):
    # Kodi frees a closed window's controls; using one then crashes Kodi (ISSUE-123), so the fake refuses loudly.
    assert not self.closed,'control %d used after its window closed'%n
    return self.controls.setdefault(n,Control())
   def setFocusId(self,n):self.focus=n
   def getFocusId(self):return self.focus
   def close(self):self.closed=True
   def doModal(self):
    self.onInit()
    while not self.closed and kodi.script:
     step=kodi.script.pop(0)
     if step[0]!=self.xml:kodi.script.insert(0,step);break
     step[1](self)
  class Dialog:
   def yesno(self,*a,**k):kodi.notes.append(('yesno',a[1]));return kodi.answer
   def contextmenu(self,labels):kodi.menus.append(list(labels));return kodi.picks.pop(0) if kodi.picks else -1
   def notification(self,title,text,*a):kodi.notes.append(('note',text))
  gui.ListItem,gui.WindowXMLDialog,gui.Dialog=ListItem,Window,Dialog
  def existing(ident):
   # xbmcgui.Window(id): a wrapper on a window Kodi already has (one of this run's windows, or Home's properties)
   if 0<=ident<len(kodi.windows):return kodi.windows[ident]
   home=Window.__new__(Window);home.props,home.controls,home.closed=kodi.props_home if hasattr(kodi,'props_home') else {},{},False
   return home
  gui.Window=existing
  addon=types.ModuleType('xbmcaddon')
  class Addon:
   def __init__(self,name=None):
    # Real Kodi (build 159 log): a script run through default.py's runpy has no add-on of its own.
    if name is None:raise RuntimeError('No valid addon id could be obtained. None was passed and the script wasn\'t executed in a normal Kodi manner.')
    self.name=name
   def getSettingBool(self,k):return kodi.settings.get(k,False)
   def setSettingBool(self,k,v):kodi.settings[k]=v
   def getAddonInfo(self,k):raise RuntimeError('TMDb Helper not installed')
  addon.Addon=Addon
  vfs=types.ModuleType('xbmcvfs');vfs.translatePath=lambda path:os.path.join(profile,'home') if path=='special://home/' else profile
  self.modules={'xbmc':xbmc,'xbmcgui':gui,'xbmcaddon':addon,'xbmcvfs':vfs}

def tap(control):return lambda w:w.onClick(control)
def tap_first(w):w.onClick(w.control_for(w.items[0]))
def tap_row(ident):
 def go(w):
  if w.filter!='all':w.set_filter('all')
  ids=[i['props'].get('id') for i in w.items]
  index=ids.index(ident)
  w.onClick(w.control_for(w.items[index]))
 return go
def tap_kind(kind):
 def go(w):
  index=next(n for n,i in enumerate(w.items) if i['kind']==kind)
  w.onClick(w.control_for(w.items[index]))
 return go

class TapEveryButton(unittest.TestCase):
 """Owner (build 158): "the buttons i press better work". Runs the real controller against a fake Kodi."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.profile=self.tmp.name
  state=library_state()
  for n in range(8):state['library']['items'].append(item('x%d'%n,'Film%d.2000.1080p.mkv'%n,'ready'))
  prep.save(self.profile,state)
 def tearDown(self):self.tmp.cleanup()
 def run_page(self,script,**kw):
  from unittest.mock import patch
  kodi=FakeKodi(self.profile,script,**kw)
  import work_state
  import notices
  with patch.dict(sys.modules,kodi.modules),patch.object(notices,'downloads',lambda get=None:[]),patch.object(work_state,'load',side_effect=lambda *a:model_for(self.profile)):
   module=load('library_status_run',BOOT/'library_status.py');module.run([])
  return kodi
 def page_rows(self, w):
  return [(i['props'].get('id'),i['props'].get('state'),i.get('label2','')) for i in w.items if i['kind']=='row']
 def test_page_opens_filled(self):
  seen={}
  kodi=self.run_page([(library_page.WINDOW,lambda w:seen.update(props=dict(w.props),rows=self.page_rows(w))),(library_page.WINDOW,tap(library_page.BACK))])
  self.assertTrue(kodi.windows[0].closed)
  self.assertEqual(seen['props']['headline'],'10 of 18 ready')
  self.assertEqual(seen['props']['work.title'],'Lanterns · S1 E1')
  self.assertEqual({r[1] for r in seen['rows']},{'waiting','space','problem','ready','kept'})
 def test_filters(self):
  seen=[]
  snap=lambda w:seen.append((w.filter,{r[1] for r in self.page_rows(w)}))
  self.run_page([(library_page.WINDOW,tap(9101)),(library_page.WINDOW,snap),(library_page.WINDOW,tap(9102)),(library_page.WINDOW,snap),(library_page.WINDOW,tap(9103)),(library_page.WINDOW,snap),(library_page.WINDOW,tap(9104)),(library_page.WINDOW,snap),(library_page.WINDOW,tap(library_page.BACK)),(library_page.WINDOW,tap(library_page.BACK))])
  self.assertEqual([x[0] for x in seen],['ready','working','waiting','kept'])
  self.assertEqual(seen[0][1],{'ready'});self.assertEqual(seen[1][1],{'preparing'});self.assertEqual(seen[3][1],{'kept'})
 def folders(self,w):return [(r.getProperty('folder'),r.getProperty('count')) for r in w.getControl(library_page.LIST).items if r.getProperty('kind')=='folder']
 def test_a_folder_opens_and_back_returns_to_all(self):
  seen=[]
  kodi=self.run_page([(library_page.WINDOW,tap(9103)),(library_page.WINDOW,lambda w:seen.append(w.filter)),(library_page.WINDOW,tap(library_page.BACK)),(library_page.WINDOW,lambda w:seen.append(w.filter)),(library_page.WINDOW,tap(library_page.BACK))])
  self.assertEqual(seen,['waiting','all']);self.assertTrue(kodi.windows[0].closed)
 def test_back_closes_only_from_all_in_the_skin_too(self):
  xml=library_page.page(portrait)
  self.assertIn('<onclick condition="String.IsEqual(Window().Property(filter),all)">Close</onclick>',xml)
 def test_check_now(self):
  seen=[]
  self.run_page([(library_page.WINDOW,tap(library_page.CHECK)),(library_page.WINDOW,lambda w:seen.append(w.getProperty('sub'))),
                 (library_page.WINDOW,tap(library_page.BACK))])
  self.assertTrue(prep.check_requested(self.profile));self.assertIn('checking now',seen[0])
 def test_check_now_with_preparation_off_asks_first(self):
  kodi=self.run_page([(library_page.WINDOW,tap(library_page.CHECK)),(library_page.WINDOW,tap(library_page.BACK))],
                     settings={'prepare_downloads':False},answer=False)
  self.assertFalse(prep.check_requested(self.profile));self.assertEqual(kodi.notes[0][0],'yesno')
 def test_prepare_next_shows_at_once_and_the_service_applies_it(self):
  seen=[]
  sheet={}
  kodi=self.run_page([(library_page.WINDOW,tap_row('w1')),
                      (library_page.ITEM,lambda w:sheet.update(dict(w.props))),(library_page.ITEM,tap(9202)),
                      (library_page.WINDOW,lambda w:seen.append(self.page_rows(w))),(library_page.WINDOW,tap(library_page.BACK))])
  self.assertEqual((sheet['action1.label'],sheet['action2.label'],sheet['action3.label']),('Start converting now','Prepare next','Keep as it is'))
  self.assertEqual((sheet['action2.colour'],sheet['action3.colour']),('FFFFFFFF','FFFF453A'))
  self.assertEqual(prep.pending_requests(self.profile),[{'action':'next','id':'w1'}])
  waiting=[r for r in seen[0] if r[1]=='waiting'];self.assertEqual(waiting[0][0],'w1');self.assertTrue(waiting[0][2].startswith('convert'))
  self.assertIn(('note','Prepare next: Fall (2022)'),kodi.notes)
  queue=prep.Queue.__new__(prep.Queue);queue.profile=self.profile;queue.clock=lambda:7000;queue.state=prep.load(self.profile);queue.commit=lambda:None
  self.assertTrue(queue.apply_requests());self.assertEqual(queue.state['jobs']['a']['priority'],7000);self.assertEqual(prep.pending_requests(self.profile),[])
 def test_keep_moves_it_to_kept_and_prepare_after_all_brings_it_back(self):
  seen=[]
  snap=lambda w:seen.append({i:s for i,s,_ in self.page_rows(w)})
  self.run_page([(library_page.WINDOW,tap(9103)),(library_page.WINDOW,tap_row('w2')),(library_page.ITEM,tap(9203)),(library_page.WINDOW,snap),
                 (library_page.WINDOW,tap_row('w2')),(library_page.ITEM,tap(9201)),(library_page.WINDOW,snap),
                 (library_page.WINDOW,tap(library_page.BACK))])
  self.assertEqual(seen[0]['w2'],'kept');self.assertEqual(seen[1]['w2'],'waiting')
 def test_try_again(self):
  self.run_page([(library_page.WINDOW,tap_row('f1')),(library_page.ITEM,tap(9201)),(library_page.WINDOW,tap(library_page.BACK))])
  self.assertEqual(prep.pending_requests(self.profile),[{'action':'retry','id':'f1'}])
 def test_close_buttons_and_no_action_sheets(self):
  kodi=self.run_page([(library_page.WINDOW,tap_row('r1')),(library_page.ITEM,tap(9200)),
                      (library_page.WINDOW,tap_row('k1')),(library_page.ITEM,tap(9099)),
                      (library_page.WINDOW,lambda w:w.onAction(type('A',(),{'getId':lambda self:92})())),
                      (library_page.WINDOW,lambda w:w.onAction(type('A',(),{'getId':lambda self:92})())) ])
  sheets=[w for w in kodi.windows if w.xml==library_page.ITEM]
  self.assertTrue(all(w.closed for w in sheets));self.assertTrue(kodi.windows[0].closed)
  self.assertEqual((sheets[0].props['action1.label'],sheets[0].props['action2.label']),('Play','Play on TV'))
  self.assertEqual(sheets[0].props['action2.colour'],'FFFFFFFF')
  self.assertEqual(prep.pending_requests(self.profile),[])
 def test_action_with_preparation_off_asks_to_turn_it_on(self):
  kodi=self.run_page([(library_page.WINDOW,tap_row('w1')),(library_page.ITEM,tap(9202)),(library_page.WINDOW,tap(library_page.BACK))],
                     settings={'prepare_downloads':False},answer=True)
  self.assertTrue(kodi.settings['prepare_downloads']);self.assertEqual(prep.pending_requests(self.profile),[{'action':'next','id':'w1'}])
 def test_service_wakes_for_a_choice(self):
  self.assertIn('if prepare_downloads.check_requested(profile) or prepare_downloads.pending_requests(profile):delay=5',(BOOT/'service.py').read_text())

class PhoneSpace(unittest.TestCase):
 """Owner (build 159): "Kodi is eating 10 GB"."""
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def queue(self,jobs):
  q=prep.Queue.__new__(prep.Queue);q.state={'jobs':jobs};q.work=self.root/'work';q.work.mkdir(exist_ok=True)
  for slot in list(jobs)+['orphan']:(q.work/slot).mkdir();(q.work/slot/'prepared.mp4').write_bytes(b'x'*1000)
  return q
 def test_only_work_that_carries_on_keeps_its_files(self):
  q=self.queue({'wait':job('a','A.mkv'),'paused':job('b','B.mkv',status='paused'),'saving':job('c','C.mkv',status='committing'),
                'failed':job('d','D.mkv',status='failed'),'kept':job('e','E.mkv',kept=True),'blocked':job('f','F.mkv',blocked=True),
                'done':job('g','G.mkv',status='done')})
  self.assertEqual(q.tidy(),5000)
  self.assertEqual(sorted(d.name for d in q.work.iterdir()),['paused','saving','wait'])
 def test_tidy_runs_before_every_video(self):
  self.assertIn('self.apply_requests();self.tidy()',(LIB/'prepare_downloads.py').read_text())
class EveryScriptNamesItsAddon(unittest.TestCase):
 def test_no_bare_addon_in_runscript_pages(self):
  import re
  pages=re.search(r"PAGES=\(([^)]*)\)",(BOOT/'default.py').read_text()).group(1)
  for page in re.findall(r"'([a-z_]+)'",pages):
   path=BOOT/(page+'.py')
   if path.exists():self.assertNotRegex(path.read_text(),r'xbmcaddon\.Addon\(\)',page)

class SpaceAsTheIPhoneCountsIt(unittest.TestCase):
 """Owner (build 160): "It says my phone has 30gb free but it has 50" and Inception waited on a figure the page did not show."""
 def test_free_is_never_less_than_statvfs_and_falls_back_off_ios(self):
  import phone_space,shutil
  from unittest.mock import patch
  self.assertIsNone(phone_space.important_usage('/'))     # no Objective-C runtime here
  self.assertEqual(phone_space.free('/'),shutil.disk_usage('/').free)
  with patch.object(phone_space,'important_usage',return_value=49*GB),patch.object(phone_space.shutil,'disk_usage',return_value=type('U',(),{'free':29*GB})()):
   self.assertEqual(phone_space.free('/'),49*GB)
  with patch.object(phone_space,'important_usage',return_value=None),patch.object(phone_space.shutil,'disk_usage',return_value=type('U',(),{'free':29*GB})()):
   self.assertEqual(phone_space.free('/'),29*GB)
 def test_reads_the_key_the_settings_app_uses(self):
  import phone_space
  self.assertEqual(phone_space.KEY,'NSURLVolumeAvailableCapacityForImportantUsageKey')
  src=(LIB/'phone_space.py').read_text()
  for s in ("'resourceValuesForKeys:error:'","'longLongValue'","objc_autoreleasePoolPush"):self.assertIn(s,src)
 def test_one_estimate_for_the_queue_the_step_and_the_page(self):
  item={'size':9*GB}
  self.assertEqual(prep.space_needed(item,True),9*GB+prep.RESERVE+prep.KEEP_FREE)
  copy={'copy_video':True,'audio_work_bytes':400*1024**2}
  self.assertEqual(prep.space_needed(item,True,copy),9*GB+800*1024**2+16*1024**2+prep.RESERVE+prep.KEEP_FREE)
  av1={'copy_video':False,'audio_work_bytes':0,'duration':8880,'width':3840,'height':2160,'codec':'av1','bit_depth':10}
  self.assertGreater(prep.space_needed(item,True,av1),60*GB)
  self.assertEqual(prep.space_reason(av1),'its picture (AV1 10-bit) cannot go into MP4 as it is, so it is re-encoded')
  self.assertEqual(prep.space_reason(copy),'');self.assertEqual(prep.space_reason(None),'')
  src=(LIB/'prepare_downloads.py').read_text()
  self.assertIn("needed=work_bytes(item,before)",src);self.assertIn("job['probe']=",src)
  self.assertEqual(src.count("space_needed(job['source'],bool(self.stream),job.get('probe'))"),2)
  self.assertNotIn('shutil.disk_usage',src)
 def test_the_page_says_why(self):
  state={'library':{'items':[item('i1','Inception.2010.2160p.mkv',size=9*GB)],'checked':1},
         'jobs':{'a':job('i1','Inception.2010.2160p.mkv',space=72*GB,probe={'copy_video':False,'codec':'av1','bit_depth':10})}}
  view=prep.library_view(state,free=49*GB,now=lambda:1)
  row=view['rows']['waiting'][0];self.assertEqual(row['state'],'space')
  facts=dict(rows.details(row,view)['facts'])
  self.assertEqual(facts['Free now'],'49 GB');self.assertTrue(facts['Why'].startswith('Its picture (AV1 10-bit)'))


class RoundPosterInTheRing(unittest.TestCase):
 """Owner (build 170): the square poster did not fit in the preparing ring."""
 def test_poster_is_a_circle_inside_the_ring(self):
  import status_ui
  xml=status_ui.working(portrait,'work.',9005)
  self.assertIn('poster_mask.png',xml);self.assertIn('Window().Property(work.ring)',xml)
  self.assertIn('Window().Property(work.percent)',xml)
  self.assertIn('Window().Property(work.poster)',xml)

class WorkingCardIsABar(unittest.TestCase):
 """DEC-036: the 'Working on now' card shows a bar the script fills, not a ring (the only ring is the Home bell's)."""
 def test_bar_not_ring(self):
  import library_page
  src=(Path(library_page.__file__)).read_text()
  start=src.index('def _work(');end=src.index('def _needs(')
  self.assertNotIn('work.ring',src[start:end]);self.assertNotIn('ring_20.png',src[start:end])
  self.assertIn('WORK_BAR',src[start:end])
  script=(Path(library_page.__file__).parents[2]/'library_status.py').read_text()
  self.assertIn('library_page.WORK_BAR+n',script)

class FindAVersionWithoutConverting(unittest.TestCase):
 def test_sheet_offers_it_for_reencodes_only(self):
  base={'id':'a','title':'Inception (2010)','name':'Inception.2010.2160p.AV1.mkv','size':9*GB,'state':'waiting','sub':'Next · 2160p'}
  sheet=rows.details(dict(base,reencode=True),{'free':0})
  self.assertEqual(sheet['actions'][0],('Find a version without converting','quicker'));self.assertNotIn('next',[a[1] for a in sheet['actions']])
  self.assertLessEqual(len(sheet['actions']),3)
  self.assertNotIn('quicker',[a[1] for a in rows.details(dict(base,reencode=False),{'free':0})['actions']])
 def test_reencode_from_probe_or_name(self):
  self.assertTrue(prep.needs_reencode({'probe':{'copy_video':False}},'x.mkv'));self.assertFalse(prep.needs_reencode({'probe':{'copy_video':True}},'x.AV1.mkv'))
  self.assertTrue(prep.needs_reencode(None,'Inception.2010.2160p.WEB-DL.AV1.mkv'));self.assertFalse(prep.needs_reencode(None,'Movie.2010.2160p.x265.mkv'))
 def test_the_copy_without_conversion_is_kept(self):
  src=(LIB/'prepare_downloads.py').read_text()
  self.assertIn("rank=lambda item:(ready(item),not needs_reencode(None,item.get('name','')),started.get(item['id'],0),",src)
 def test_wiring(self):
  st=(BOOT/'library_status.py').read_text()
  self.assertIn("xbmcgui.Window(10000).setProperty('KodiIOS.AvoidAV1'",st);self.assertIn("RunScript(service.kodi.ios.bootstrap,download,%s)",st)
  self.assertIn("if args.get('replace')=='1':return None",(BOOT/'download.py').read_text())
  status=load('library_status_q',BOOT/'library_status.py')
  self.assertEqual([status.quality_key(h) for h in (2160,1080,720,0)],['4k','1080p','720p',''])

class ReplacementStopsTheConversion(unittest.TestCase):
 """Owner (build 185): the button worked but Inception kept converting; "it needs to end the conversion and begin
 the downloading automatically"."""
 def test_replace_stops_now_and_says_so(self):
  with tempfile.TemporaryDirectory() as p:
   state=library_state();prep.save(p,state)
   prep.request(p,'replace','p1')                 # p1 is converting in library_state()
   self.assertTrue(prep.interrupts(p))
   s=prep.apply_to(prep.load(p),prep.pending_requests(p),1000)
   job=[j for j in s['jobs'].values() if j['source']['id']=='p1'][0]
   self.assertTrue(job['kept']);self.assertEqual(job['replacing'],1000)
   s.pop('current',None)
   view=prep.library_view(s,now=lambda:1000)
   row=[r for r in view['rows']['kept'] if r['id']=='p1'][0]
   self.assertEqual(row['sub'],'Being replaced · a version without conversion is downloading')
 def test_the_pick_hands_over_once(self):
  import elementum_cloud
  class W:
   def __init__(s,v):s.v=v
   def getProperty(s,k):return s.v
   def clearProperty(s,k):s.v=''
  w=W('abc|1000');self.assertEqual(elementum_cloud.replacing(w,now=1100),'abc');self.assertEqual(w.v,'')
  self.assertEqual(elementum_cloud.replacing(W('abc|1000'),now=1000+16*60),'')
  src=(LIB/'elementum_cloud.py').read_text()
  self.assertIn("prepare_downloads.request(profile, 'replace', replaced)",src)
  self.assertIn("setProperty('KodiIOS.Replacing'",(BOOT/'library_status.py').read_text())

def kodi_of(w):return w._kodi
def press(code):return lambda w:w.onAction(type('A',(),{'getId':lambda self:code})())
def focus(n):return lambda w:w.setFocusId(n)

class LongPressCancel(unittest.TestCase):
 """Owner (build 328): "holding down on the show that is converting should show a cancel button"; build 347: "holding
 down anything on the library status sends me out of the page ... ensure if i hold down on a download or transfer it
 also works like this". The phone delivers one long press as action 10 (which also means Back) and 117."""
 setUp,tearDown,run_page=TapEveryButton.setUp,TapEveryButton.tearDown,TapEveryButton.run_page
 def test_holding_the_working_card_keeps_the_page_open(self):
  kodi=self.run_page([(library_page.WINDOW,focus(library_page.WORK)),(library_page.WINDOW,press(10)),(library_page.WINDOW,press(117)),
                      (library_page.WINDOW,lambda w:self.assertFalse(w.closed)),(library_page.WINDOW,focus(library_page.BACK)),
                      (library_page.WINDOW,press(10))])
  self.assertEqual(kodi.menus,[['Pause converting','Cancel conversion']])   # one menu for one press
  self.assertTrue(kodi.windows[0].closed)                                   # 10 away from a card is still Back
 def test_cancel_conversion(self):
  self.run_page([(library_page.WINDOW,lambda w:setattr(kodi_of(w),'picks',[1])),(library_page.WINDOW,focus(library_page.WORK+100)),
                 (library_page.WINDOW,press(117)),(library_page.WINDOW,tap(library_page.BACK))])
  self.assertIn('keep',[r['action'] for r in prep.pending_requests(self.profile)])
 def held(self,row,picks):
  def setup(w):
   w.pools={'down':[{'row':row,'props':{}}]};kodi_of(w).picks=list(picks);w.setFocusId(library_page.POOLS[0][1])
  return self.run_page([(library_page.WINDOW,setup),(library_page.WINDOW,press(10)),(library_page.WINDOW,press(117)),
                        (library_page.WINDOW,lambda w:self.assertFalse(w.closed)),(library_page.WINDOW,tap(library_page.BACK))])
 def test_holding_a_drive_copy_cancels_it(self):
  import transfer_control
  kodi=self.held({'kind':'copy','hash':'ABC123','title':'Naruto · S1 E3'},[1])
  self.assertEqual(kodi.menus,[['Pause uploads','Cancel this download']])
  self.assertEqual(transfer_control.cancelled_copies(self.profile),{'abc123'})
 def test_holding_a_drive_copy_pauses_uploads(self):
  import transfer_control
  self.held({'kind':'copy','hash':'abc','title':'Naruto · S1 E3'},[0])
  self.assertTrue(transfer_control.paused(self.profile,'up'))
 def test_holding_an_elementum_download(self):
  import notices
  from unittest.mock import patch
  with patch.object(notices,'engine_action',return_value=True) as engine:
   kodi=self.held({'kind':'down','id':'e7','title':'Arrival (2016)','held':True},[0])
  self.assertEqual(kodi.menus,[['Resume download','Cancel download']]);engine.assert_called_once_with('resume','e7')
 def test_a_queued_copy_in_up_next_and_rows_that_are_not_transfers(self):
  import transfer_control
  self.assertEqual(transfer_control.row_menu({'queued_transfer':True,'hash':'h','title':'T'},queued=3)[2],
                   [('Pause uploads','toggle'),('Cancel this download','cancel'),('Cancel all downloads to Drive (3)','cancel_all')])
  self.assertEqual(transfer_control.row_menu({'kind':'upload','title':'Clip'})[2],[('Pause uploads','toggle')])
  self.assertIsNone(transfer_control.row_menu({'state':'waiting','id':'w1'}))
 def test_source(self):
  src=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/library_status.py').read_text()
  self.assertIn("prepare_downloads.request(profile,'keep',row['id'])",src)
  self.assertIn("if code in LONG or code==10:",src)
  import sys;sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
  import transfer_control
  self.assertIn(('Cancel conversion','cancel'),transfer_control.menu('conv',{'id':'d1'}))

if __name__=='__main__':unittest.main()
