"""Activity pill: activity.py (reading and rewriting Kodi's background progress box), activity_skin.py (the pill,
the hidden box, the sheet, the tap areas) and activity_page.py. Also checked in desktop Kodi 21.2; the tests below
pin what that found."""
import importlib.util,json,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
sys.path.insert(0,str(LIB))
activity=load('activity_t',LIB/'activity.py')
portrait=load('portrait_act',LIB/'portrait.py')
navigation=load('navigation_act',LIB/'navigation.py')
page=load('activity_page_t',BOOT/'activity_page.py')
activity_skin=load('activity_skin_t',LIB/'activity_skin.py')
C=activity.classify

class Wording(unittest.TestCase):
 def test_elementum_download_line(self):
  j=C('Elementum','INCEPTION.2010.PROPER.BLURAY.1080p.x264 - 446 kB/s - 0 B/s',10)
  self.assertEqual((j['app'],j['title'],j['sub'],j['pct']),('elementum','Inception (2010)','1080p · 446 KB/s',10))
  self.assertTrue(j['download'])
 def test_elementum_total_is_dropped_and_steps_are_plain(self):
  self.assertTrue(C('Elementum','Total - D/L: 1.2 MB/s - U/L: 80 kB/s',10)['drop'])
  self.assertEqual(C('Elementum','Resolving magnet link',-1)['title'],'Getting the torrent ready')
  self.assertEqual(C('Elementum','Scraping trackers...',-1)['title'],'Finding peers')
 def test_burst_search_and_errors(self):
  j=C('Elementum [COLOR FFFF6B00]Burst[/COLOR]','4 providers left',43)
  self.assertEqual((j['app'],j['title'],j['sub']),('burst','Searching torrent sites','4 sites left'))
  e=C('Elementum [COLOR FFFF6B00]Burst[/COLOR] errors','1337x | TorrentGalaxy',-1)
  self.assertTrue(e['drop']);self.assertEqual(e['problem'],'1337x | TorrentGalaxy')
 def test_umbrella_sources(self):
  j=C('[COLOR FFFFFF00]Dune: Part Two (2024)[/COLOR]','[COLOR x]4K:[/COLOR]  3  |  [COLOR x]1080p:[/COLOR]  5  |  720p:  2  |  SD:  0',58)
  self.assertEqual((j['app'],j['title'],j['sub']),('umbrella','Finding sources · Dune: Part Two (2024)','4K 3 · 1080p 5 · 720p 2'))
 def test_kodi_jobs(self):
  self.assertEqual((C('Checking for add-on updates','',-1)['group'],C('Checking for add-on updates','',-1)['pct']),('quiet',None))
  i=C('Installing Umbrella...','Downloading add-on...',42);self.assertEqual((i['app'],i['title'],i['sub']),('addon','Installing Umbrella','Downloading 42%'))
  s=C('Scanning movies using The Movie Database','Inception',-1);self.assertEqual((s['app'],s['title'],s['sub']),('library','Updating library','Inception'))
  self.assertEqual(C('Copy','Inception.mkv',34)['title'],'Copying')
  self.assertEqual(C('Skin Variables','Constructing Viewtypes...',-1)['group'],'quiet')
  self.assertEqual(C('TMDbHelper Library','Severance',47)['title'],'Adding to your library')
 def test_unknown_is_kept_without_tags(self):
  j=C('[B]Some Add-on[/B]','[COLOR red]Doing things[/COLOR]',20)
  self.assertEqual((j['app'],j['title'],j['sub']),('other','Some Add-on','Doing things'))
 def test_release_names(self):
  self.assertEqual(activity.release('The.Bear.S03E01.1080p.WEB.h264'),('The Bear · S3 E1','1080p'))
  self.assertEqual(activity.release('Dune.Part.Two.2024.2160p.UHD'),('Dune Part Two (2024)','4K'))
  self.assertEqual(activity.speed_text('0.4 MB/s  ·  5h 49m'),'410 KB/s · 5h 49m left')

class Tracking(unittest.TestCase):
 def test_shared_bar_value_is_not_given_to_the_next_job(self):
  # Kodi never resets its bar between jobs: the update check would otherwise show Elementum's 10%.
  t=activity.Tracker();t.see('Elementum','A.2010.1080p - 1 kB/s - 0 B/s',10.0,0)
  self.assertIsNone(t.see('Checking for add-on updates','',10.0,2)['pct'])
  self.assertEqual(t.see('Installing X...','Downloading add-on...',42.0,4)['pct'],42)
 def test_jobs_expire_and_installs_flash_done(self):
  t=activity.Tracker();t.see('Installing X...','Downloading add-on...',90,0)
  t.prune(20);self.assertEqual([j.get('state') for j in t.current([],[],20)],['done'])
  t.prune(20+activity.DONE_FOR+1);self.assertEqual(t.current([],[],30),[])
 def test_engine_downloads_replace_elementum_lines_and_flash_when_done(self):
  t=activity.Tracker();t.see('Elementum','Inception.2010.1080p - 446 kB/s - 0 B/s',10,0)
  d=[{'id':'a','title':'Inception.2010.1080p','progress':97,'speed':'2.0 MB/s  ·  1 min','paused':False}]
  jobs=t.current(d,[],1);self.assertEqual([j['key'] for j in jobs],['dl|a'])
  done=t.current([],[],2);self.assertEqual((done[0]['state'],done[0]['pct']),('done',100))
 def test_quiet_jobs_hidden_by_default_and_during_video(self):
  q=C('Checking for add-on updates','',-1);s=lambda k,d:d
  self.assertFalse(activity.allowed(q,s));self.assertTrue(activity.allowed(q,lambda k,d:True))
  self.assertFalse(activity.allowed(q,lambda k,d:True,playing=True))
  self.assertFalse(activity.allowed(C('Installing X...','',-1),lambda k,d:False if k=='activity_show' else d))
 def test_properties(self):
  one=activity.properties([dict(C('Installing X...','Downloading add-on...',42),pct=42)])
  self.assertEqual((one['Activity.Show'],one['Activity.Title'],one['Activity.State'],one['Activity.Ring']),('true','Installing X','progress','ring_08.png'))
  many=activity.properties([dict(C('Installing X...','',42),pct=42),C('Checking for add-on updates','',-1)])
  self.assertEqual((many['Activity.Title'],many['Activity.Stack'],many['Activity.S2.Icon']),('2 running','true','arrows-rotate.png'))
  none=activity.properties([],2);self.assertEqual((none['Activity.Show'],none['Activity.Running']),('','2'))
 def test_watch_publishes_changes_only(self):
  seq=iter([('Installing X...','Downloading add-on...',40.0)]*3);out=[];ticks=[0]
  def wait(_):ticks[0]+=1;return ticks[0]>3
  activity.watch(lambda:next(seq,None),lambda:[],lambda:[],lambda k,d:d,lambda:False,out.append,lambda t:None,wait,clock=lambda:ticks[0])
  self.assertEqual(out[0]['Activity.Title'],'Installing X');self.assertTrue(all('Activity.Title' not in o for o in out[1:]))

class Skin(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();skin=Path(cls.tmp.name)/'skin.arctic.fuse.3';(skin/'1080i').mkdir(parents=True)
  (skin/'addon.xml').write_text('<addon id="skin.arctic.fuse.3"><extension point="xbmc.gui.skin"><res aspect="16:9" default="true" folder="1080i" width="1920" height="1080" /></extension></addon>')
  plain='<window><controls><control type="label" id="1"><label>x</label></control></controls></window>'
  for name in ('Font.xml','Includes.xml','Home.xml','Settings.xml','VideoOSD.xml','DialogSeekBar.xml','DialogExtendedProgressBar.xml','MyPics.xml','DialogNumeric.xml'):
   (skin/'1080i'/name).write_text('<fonts><fontset id="Default" /></fonts>' if name=='Font.xml' else '<includes />' if name=='Includes.xml' else plain)
  cls.profile=Path(cls.tmp.name)/'profile';cls.profile.mkdir()
  navigation.patch_skin(skin);portrait.build(skin,cls.profile);cls.skin=skin
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def root(self,rel):return ET.parse(self.skin/rel).getroot()
 def test_old_box_is_never_drawn(self):
  for rel in ('portrait/DialogExtendedProgressBar.xml','1080i/DialogExtendedProgressBar.xml'):
   r=self.root(rel);group=r.find('controls/control')
   self.assertEqual(group.findtext('visible'),'false',rel)
   self.assertEqual([c.get('type') for c in r.iter('control') if c.get('id')],['button','button','progress'])
   self.assertEqual(len([c for c in r.iter('control') if c.get('type')=='image']),0)
   self.assertIsNone(r.find('animation'))
 def test_box_controls_python_can_read(self):
  # Found in Kodi: a label or textbox reads empty from Python; a button's label comes from Kodi.
  ids={c.get('id'):c.get('type') for c in self.root('portrait/DialogExtendedProgressBar.xml').iter('control') if c.get('id')}
  self.assertEqual(ids,{'30':'button','31':'button','32':'progress'})
 def test_landscape_files_left_alone_by_navigation_and_refresh(self):
  self.assertEqual(navigation.patch_skin(self.skin),[]);self.assertEqual(portrait.refresh(self.skin,self.profile),[])
  self.assertFalse((self.skin/'portrait/Custom_1187_Activity.xml').read_text().count('landscape window'))
 def test_pill_dialog_opens_itself_and_has_no_buttons(self):
  r=self.root('portrait/Custom_1187_Activity.xml')
  self.assertEqual((r.get('type'),r.get('id')),('dialog','1187'));self.assertIn('Activity.Show',r.findtext('visible'))
  # Modeless dialogs get no taps or keys (Kodi), so the pill only draws; the pages catch the taps.
  self.assertEqual([c for c in r.iter('control') if c.get('type')=='button'],[])
  self.assertIn('Custom_1187_Activity.xml',portrait.LOADED_AT_START)
  l=self.root('1080i/Custom_1187_Activity.xml');self.assertIn('Window.IsVisible(videoosd)',l.findtext('visible'))
 def test_every_page_gets_the_tap_area(self):
  for name in ('Home.xml','Settings.xml','MyPics.xml','DeckSourceSelect.xml','source_progress.xml'):
   xml=(self.skin/'portrait'/name).read_text();self.assertEqual(xml.count('activity pill tap'),1,name)
   self.assertIn('RunScript(service.kodi.ios.bootstrap,activity_page)',xml)
  home=(self.skin/'portrait/Home.xml').read_text();self.assertIn('<bottom>196</bottom>',home.split('activity pill tap')[1])
  for name in ('DialogNumeric.xml','Custom_1187_Activity.xml','IOSActivity.xml','DialogExtendedProgressBar.xml'):
   self.assertNotIn('activity pill tap',(self.skin/'portrait'/name).read_text(),name)
 def test_sheet_matches_the_script(self):
  r=self.root('portrait/IOSActivity.xml');ids={c.get('id') for c in r.iter('control')}
  for n in range(1,activity.ROWS+1):self.assertIn(str(page.PAUSE_BASE+n),ids)
  self.assertTrue({'9600','9099'}<=ids)
 def test_textures_and_fonts(self):
  for k in (0,10,20):self.assertTrue((self.skin/('extras/portrait/ring_%02d.png'%k)).read_bytes().startswith(b'\x89PNG'))
  for name in ('pill_glass_170.png','pill_glass_124.png','pill_glass_72.png','tile108.png','sheet_bg.png','row_only.png','row_first.png','row_last.png'):
   self.assertTrue((self.skin/'extras/portrait'/name).is_file(),name)
  self.assertIn('p_pill',(self.skin/'portrait/Font.xml').read_text())
 def test_conditions_use_kodi_brackets(self):
  for rel in ('portrait/Custom_1187_Activity.xml','1080i/Custom_1187_Activity.xml','portrait/IOSActivity.xml'):
   self.assertNotIn('!(',(self.skin/rel).read_text(),rel)

def label_boxes(group):
 out=[]
 for c in group.findall('control'):
  if c.get('type')!='label':continue
  num=lambda tag:float(c.findtext(tag) or 0)
  out.append((num('left'),num('top'),num('left')+num('width'),num('top')+num('height'),c.findtext('label'),c.findtext('visible') or ''))
 return out

class ApprovedDesign(unittest.TestCase):
 """Round-4 mockup approved by the owner (DEC-027; docs/design/APPLE-UI-POLICY.md section 4.7)."""
 @classmethod
 def setUpClass(cls):
  cls.pill=ET.fromstring(activity_skin.pill_window(portrait).split('\n',2)[2])
  cls.sheet=ET.fromstring(activity_skin.sheet(portrait).split('\n',2)[2])
 def test_every_sheet_control_is_at_least_44_pt(self):
  for c in self.sheet.iter('control'):
   if c.get('type')=='button' and c.get('id')!='9099':
    self.assertGreaterEqual(min(int(c.findtext('width')),int(c.findtext('height'))),118,c.get('id'))
 def test_pill_pause_tap_area_is_44_pt(self):
  taps=activity_skin.tap_controls(portrait,'Home.xml');self.assertIn('<width>118</width><height>118</height>',taps.split('id="9792"')[1])
 def test_close_not_done(self):
  xml=activity_skin.sheet(portrait);self.assertNotIn('>Done<',xml);self.assertIn('xmark.png',xml.split('id="9600"')[0][-900:]+xml.split('id="9600"')[1][:200])
 def test_ring_around_the_tile_in_pill_and_sheet(self):
  for root in (self.pill,self.sheet):
   textures=[t.text for t in root.iter('texture')]
   self.assertTrue(any(t and 'ring_20.png' in t for t in textures));self.assertTrue(any(t and 'tile108.png' in t for t in textures))
  self.assertNotIn('<control type="progress"',activity_skin.sheet(portrait))
 def test_no_two_labels_overlap_unless_never_shown_together(self):
  for root in (self.pill,self.sheet):
   for group in root.iter('control'):
    boxes=label_boxes(group)
    for i,a in enumerate(boxes):
     for b in boxes[i+1:]:
      if a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]:self.fail('labels overlap: %r and %r'%(a[4],b[4]))
 def test_every_layout_has_a_background(self):
  xml=activity_skin.sheet(portrait)
  for k in range(1,activity.ROWS+1):
   for g in range(1,min(k,activity_skin.MAX_HEADS)+1):
    if (k,g)!=(1,1):self.assertIn('Activity.Layout),%d_%d)'%(k,g),xml)
  self.assertGreaterEqual(activity_skin.MAX_HEADS,len(activity.KINDS))

class Grouping(unittest.TestCase):
 JOBS=[{'app':'drive','title':'Scary Movie (2000)','sub':'Movies · then off the phone','pct':71},
       {'app':'elementum','title':'Interstellar (2014)','sub':'4K · 20.9 MB/s · 5 min left','pct':42,'id':'x'},
       {'app':'elementum','title':'Fall (2022)','sub':'1.2 of 9.8 GB','pct':12,'paused':True,'id':'y'}]
 def test_rows_grouped_by_kind_with_one_header_each(self):
  pr=activity.properties(self.JOBS);row=lambda n,k:pr['%s%d.%s'%(activity.PREFIX,n,k)]
  self.assertEqual([row(n,'Title') for n in (1,2,3)],['Interstellar (2014)','Fall (2022)','Scary Movie (2000)'])
  self.assertEqual([row(n,'Head') for n in (1,2,3)],['Downloading','','Uploading to Google Drive'])
  self.assertEqual(row(1,'HeadCount'),'2 running');self.assertEqual(row(3,'HeadCount'),'')
  self.assertEqual([row(n,'Pos') for n in (1,2,3)],['first','last','only'])
  self.assertEqual(pr[activity.PREFIX+'Layout'],'3_2')
 def test_pill_line_starts_with_the_percentage(self):
  pr=activity.properties(self.JOBS[1:2]);self.assertEqual(pr[activity.PREFIX+'Sub'],'42% · 4K · 20.9 MB/s · 5 min left')
  pr=activity.properties(self.JOBS[2:3]);self.assertEqual(pr[activity.PREFIX+'Sub'],'Paused · 12% · 1.2 of 9.8 GB')
  self.assertEqual(activity.status_line({'pct':5,'sub':'5% · 1 of 20 GB'},'progress'),'5% · 1 of 20 GB')
 def test_done_shows_a_green_check(self):
  pr=activity.properties([dict(self.JOBS[1],state='done')])
  self.assertEqual((pr[activity.PREFIX+'Icon'],pr[activity.PREFIX+'Tint'],pr[activity.PREFIX+'Ring']),('check.png','FF30D158','ring_20.png'))

class Toggle(unittest.TestCase):
 def test_pause_and_resume(self):
  class W(dict):
   def getProperty(self,k):return self.get(k,'')
   def setProperty(self,k,v):self[k]=v
  w=W({'Activity.PauseId':'abc','Activity.Pause':'pause','Activity.2.Id':'def','Activity.2.Pause':'resume'})
  calls=[];page.notices.engine_action=lambda c,t:calls.append((c,t)) or True
  self.assertTrue(page.toggle(w,'Activity.'));self.assertTrue(page.toggle(w,'Activity.2.'))
  self.assertEqual(calls,[('pause','abc'),('resume','def')]);self.assertEqual((w['Activity.Pause'],w['Activity.2.Pause']),('resume','pause'))
  self.assertFalse(page.toggle(W(),'Activity.'))

class Settings(unittest.TestCase):
 def test_switches_exist_with_defaults(self):
  xml=ET.parse(BOOT/'resources/settings.xml').getroot();ids={s.get('id'):s.findtext('default') for s in xml.iter('setting')}
  for key,group in activity.GROUPS.items():
   if group:self.assertIn(group,ids,key)
  self.assertEqual((ids['activity_show'],ids['activity_video'],ids['activity_quiet']),('true','true','false'))

if __name__=='__main__':unittest.main()
