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
  self.assertEqual([i['kind'] for i in rows.list_items(v)],['foot'])

class Rows(unittest.TestCase):
 def setUp(self):
  state=library_state()
  for n in range(8):state['library']['items'].append(item('x%d'%n,'Film%d.2000.1080p.mkv'%n,'ready'))
  self.view=prep.library_view(state,free=40*GB,working=2*GB,now=lambda:1000)
 def test_all_shows_what_happens_now_and_folders(self):
  """Owner (build 160): "it needs to be in like a folder so ready will show 7 then if i tap it it shows the movies"."""
  items=rows.list_items(self.view)
  self.assertEqual([(i['kind'],i['props'].get('folder') or i['props'].get('id')) for i in items],
                   [('row','p1'),('folder','waiting'),('folder','ready'),('folder','kept'),('foot',None)])
  folders={i['props']['folder']:i for i in items if i['kind']=='folder'}
  self.assertEqual({k:f['props']['count'] for k,f in folders.items()},{'waiting':'5','ready':'10','kept':'2'})
  self.assertEqual(folders['ready']['label'],'Ready for Kodi and AirPlay')
  self.assertEqual(folders['waiting']['label2'],'Alien (1979) · next and 4 more')
  self.assertTrue(folders['ready']['label2'].endswith('and 8 more'))
  self.assertEqual([f['props']['pos'] for f in folders.values()],['first','mid','last'])
  self.assertEqual((folders['ready']['props']['icon'],folders['ready']['props']['tint']),('circle-check.png','FF30D158'))
  self.assertEqual(len([i for i in rows.list_items(self.view,'ready') if i['kind']=='row']),10)
 def test_every_item_is_one_height_in_one_layout(self):
  self.assertNotIn('condition=',library_page.page(portrait).split('<control type="list"')[1].split('</control>')[0][:400])
  self.assertEqual(rows.TITLES['ready'],'Ready')
 def test_positions_round_the_group(self):
  waiting=[i['props']['pos'] for i in rows.list_items(self.view,'waiting')]
  self.assertEqual((waiting[0],waiting[-1]),('first','last'));self.assertTrue(all(p=='mid' for p in waiting[1:-1]))
 def test_filters(self):
  todo={i['props']['state'] for i in rows.list_items(self.view,'todo') if i['kind']=='row'}
  self.assertNotIn('ready',todo);self.assertIn('preparing',todo)
  self.assertEqual(rows.list_items(self.view,'downloading')[0]['kind'],'foot')
  self.assertIn('Nothing is downloading',rows.list_items(self.view,'downloading')[0]['label'])
 def test_ring_texture(self):
  self.assertEqual((rows.ring_name(0),rows.ring_name(39),rows.ring_name(100),rows.ring_name(None)),('ring_00.png','ring_08.png','ring_20.png','ring_00.png'))
 def test_page_top(self):
  props=rows.page_properties(self.view)
  self.assertEqual(props['headline'],'10 of 18 ready');self.assertNotIn('space',props)   # owner, build 173: no phone space card
  self.assertIn('checking now',rows.page_properties(self.view,True)['sub'])
 def test_details_actions(self):
  by={r['id']:r for k in self.view['rows'].values() for r in k}
  actions=lambda n:[a for _,a in rows.details(by[n],self.view)['actions']]
  self.assertEqual(actions('w1'),['next','keep']);self.assertEqual(actions('s1'),['next','keep'])
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
  for k in rows.page_properties(prep.library_view({})):
   self.assertIn('Window().Property(%s)'%k,self.page,k)
  for k in ('title','status','tone','quality','poster','fact3.value','action2.label'):self.assertIn('Window().Property(%s)'%k,self.sheet,k)
  for k in ('kind','pos','state','ring','pct','warn'):self.assertIn('ListItem.Property(%s)'%k,self.page,k)
 def test_status_sheet_closes_with_a_cross(self):
  self.assertIn('close_cross.png',self.sheet);self.assertNotIn('>Done<',self.sheet)
 def test_pill_stays_off_this_page(self):
  skin=(LIB/'activity_skin.py').read_text()
  self.assertIn('IOSLibraryStatus.xml',skin);self.assertIn('IOSLibraryItem.xml',skin)
 def test_registered_in_the_skin(self):
  files=library_page.files(portrait)
  self.assertEqual(sorted(Path(k).name for k in files),['IOSLibraryItem.xml','IOSLibraryStatus.xml'])
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

class FakeKodi:
 """Just enough of xbmc, xbmcgui, xbmcaddon and xbmcvfs to run library_status.run() and tap every button."""
 def __init__(self,profile,script,settings=None,answer=True):
  import types
  self.script=list(script);self.settings=dict(settings or {'prepare_downloads':True});self.answer=answer
  self.notes=[];self.windows=[];kodi=self
  xbmc=types.ModuleType('xbmc');xbmc.LOGWARNING=2;xbmc.LOGINFO=1;xbmc.log=lambda *a:None
  class Monitor:
   def waitForAbort(self,t=0):return True    # the refresh loop ends at once; the test refreshes by tapping
  xbmc.Monitor=Monitor
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
   def __init__(self,xml,*rest):self.xml=xml;self.props={};self.controls={};self.closed=False;self.focus=None;kodi.windows.append(self)
   def setProperty(self,k,v):self.props[k]=v
   def getProperty(self,k):return self.props.get(k,'')
   def getControl(self,n):return self.controls.setdefault(n,Control())
   def setFocusId(self,n):self.focus=n
   def close(self):self.closed=True
   def doModal(self):
    self.onInit()
    while not self.closed and kodi.script:
     step=kodi.script.pop(0)
     if step[0]!=self.xml:kodi.script.insert(0,step);break
     step[1](self)
  class Dialog:
   def yesno(self,*a,**k):kodi.notes.append(('yesno',a[1]));return kodi.answer
   def notification(self,title,text,*a):kodi.notes.append(('note',text))
  gui.ListItem,gui.WindowXMLDialog,gui.Dialog=ListItem,Window,Dialog
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
def tap_row(ident):
 """Tap a video's row, opening the folder it is in first when it is not on the page (All shows folders)."""
 def go(w):
  listing=w.getControl(library_page.LIST)
  ids=lambda:[r.getProperty('id') for r in listing.items]
  if ident not in ids():
   if w.getProperty('filter')!='all':w.onClick(library_page.BACK)
   for folder in [r.getProperty('folder') for r in listing.items if r.getProperty('kind')=='folder']:
    listing.selectItem([r.getProperty('folder') for r in listing.items].index(folder));w.onClick(library_page.LIST)
    if ident in ids():break
    w.onClick(library_page.BACK)
  listing.selectItem(ids().index(ident));w.onClick(library_page.LIST)
 return go
def tap_kind(kind):
 def go(w):
  rows=w.getControl(library_page.LIST).items
  w.getControl(library_page.LIST).selectItem([r.getProperty('kind') for r in rows].index(kind));w.onClick(library_page.LIST)
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
  import notices
  with patch.dict(sys.modules,kodi.modules),patch.object(notices,'downloads',lambda get=None:[]):
   module=load('library_status_run',BOOT/'library_status.py');module.run([])
  return kodi
 def page_rows(self,w):return [(r.getProperty('id'),r.getProperty('state'),r.label2) for r in w.getControl(library_page.LIST).items if r.getProperty('kind')=='row']
 def test_page_opens_filled(self):
  seen={}
  kodi=self.run_page([(library_page.WINDOW,lambda w:seen.update(props=dict(w.props),rows=self.page_rows(w))),(library_page.WINDOW,tap(library_page.BACK))])
  page=kodi.windows[0]
  self.assertTrue(page.closed);self.assertEqual(seen['props']['headline'],'10 of 18 ready');self.assertEqual(seen['props']['filter'],'all')
  self.assertEqual(seen['props']['title'],'Library status')
  self.assertEqual([r[:2] for r in seen['rows']],[('p1','preparing')])
  self.assertEqual(self.folders(kodi.windows[0]),[('waiting','5'),('ready','10'),('kept','2')])
 def test_filters(self):
  seen=[]
  snap=lambda w:seen.append((w.getProperty('filter'),{s for _,s,_ in self.page_rows(w)}))
  self.run_page([(library_page.WINDOW,tap(9102)),(library_page.WINDOW,snap),(library_page.WINDOW,tap(9103)),(library_page.WINDOW,snap),
                 (library_page.WINDOW,tap(9104)),(library_page.WINDOW,snap),(library_page.WINDOW,tap(9101)),(library_page.WINDOW,snap),
                 (library_page.WINDOW,tap(library_page.BACK))])
  self.assertEqual([f for f,_ in seen],['ready','todo','downloading','all'])
  self.assertEqual(seen[0][1],{'ready'});self.assertNotIn('ready',seen[1][1]);self.assertEqual(seen[2][1],set())
  self.assertEqual(seen[3][1],{'preparing'})   # All: what happens now; the rest is in folders
 def folders(self,w):return [(r.getProperty('folder'),r.getProperty('count')) for r in w.getControl(library_page.LIST).items if r.getProperty('kind')=='folder']
 def test_a_folder_opens_and_back_returns_to_all(self):
  seen=[]
  snap=lambda w:seen.append((w.getProperty('filter'),w.getProperty('title'),len(self.page_rows(w)),self.folders(w),w.closed))
  kodi=self.run_page([(library_page.WINDOW,snap),(library_page.WINDOW,tap_kind('folder')),(library_page.WINDOW,snap),
                      (library_page.WINDOW,tap(library_page.BACK)),(library_page.WINDOW,snap),
                      (library_page.WINDOW,tap_kind('folder')),(library_page.WINDOW,lambda w:w.onAction(type('A',(),{'getId':lambda s:92})())),(library_page.WINDOW,snap),
                      (library_page.WINDOW,tap(library_page.BACK))])
  self.assertEqual(seen[0][:2],('all','Library status'));self.assertEqual(seen[0][3],[('waiting','5'),('ready','10'),('kept','2')])
  self.assertEqual(seen[1][:3],('waiting','Waiting',5));self.assertFalse(seen[1][4])
  self.assertEqual(seen[2][:2],('all','Library status'));self.assertFalse(seen[2][4])
  self.assertEqual(seen[3][:2],('all','Library status'))   # the back gesture in a folder returns to All
  self.assertTrue(kodi.windows[0].closed)
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
                      (library_page.ITEM,lambda w:sheet.update(dict(w.props))),(library_page.ITEM,tap(9201)),
                      (library_page.WINDOW,lambda w:seen.append(self.page_rows(w))),(library_page.WINDOW,tap(library_page.BACK))])
  self.assertEqual((sheet['action1.label'],sheet['action2.label']),('Prepare next','Keep as it is'))
  self.assertEqual(prep.pending_requests(self.profile),[{'action':'next','id':'w1'}])
  waiting=[r for r in seen[0] if r[1]=='waiting'];self.assertEqual(waiting[0][0],'w1');self.assertTrue(waiting[0][2].startswith('Next'))
  self.assertIn(('note','Prepare next: Fall (2022)'),kodi.notes)
  queue=prep.Queue.__new__(prep.Queue);queue.profile=self.profile;queue.clock=lambda:7000;queue.state=prep.load(self.profile);queue.commit=lambda:None
  self.assertTrue(queue.apply_requests());self.assertEqual(queue.state['jobs']['a']['priority'],7000);self.assertEqual(prep.pending_requests(self.profile),[])
 def test_keep_moves_it_to_kept_and_prepare_after_all_brings_it_back(self):
  seen=[]
  snap=lambda w:seen.append({i:s for i,s,_ in self.page_rows(w)})
  self.run_page([(library_page.WINDOW,tap(9103)),(library_page.WINDOW,tap_row('w2')),(library_page.ITEM,tap(9202)),(library_page.WINDOW,snap),
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
  kodi=self.run_page([(library_page.WINDOW,tap_row('w1')),(library_page.ITEM,tap(9201)),(library_page.WINDOW,tap(library_page.BACK))],
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
  src=(LIB/'library_page.py').read_text()
  ring=src[src.index("ring = ("):src.index("text_w = w - 160 - 130")]
  self.assertNotIn('tile108.png',ring);self.assertEqual(ring.count("M + 'knob.png'"),2)

if __name__=='__main__':unittest.main()
