"""Round 2 portrait pages (pages.py), Umbrella's getting-ready parser (umbrella_ready.py) and the Play on TV sheet
(cast.py). The pages were also checked in desktop Kodi 21.2; these tests pin what that found."""
import importlib.util,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
sys.dont_write_bytecode=True
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
sys.path.insert(0,str(LIB))
ready=load('umbrella_ready_t',LIB/'umbrella_ready.py')
portrait=load('portrait_pages',LIB/'portrait.py')
navigation=load('navigation_pages',LIB/'navigation.py')
castui=load('cast_page',BOOT/'cast.py')

UMBRELLA=('[COLOR FF00FFFF]Twenty-six years after outrunning a masked killer.[/COLOR][CR][CR]'
          '[COLOR FFFFFF00]ALLDEBRID[CR]TORRENTIO[CR]4K[CR]47.02 GB  DOLBY-VISION  HDR  HEVC  REMUX  BLURAY  MULTI-LANG[CR]'
          '02 - Scary.Movie.2026.2160p.Theatri[/COLOR]')

class UmbrellaText(unittest.TestCase):
 def test_resolve_text_becomes_card_fields(self):
  out=ready.parse(UMBRELLA)
  self.assertEqual((out['Provider'],out['Via'],out['Quality'],out['Size'],out['File'],out['Index'],out['Ready']),
                   ('AllDebrid','Torrentio','4K','47.02 GB','Scary.Movie.2026.2160p.Theatri','02','true'))
  self.assertEqual(out['Badges'].split('   '),['DOLBY VISION','HDR','HEVC','REMUX','BLU-RAY','MULTI-LANG'])
  self.assertEqual(out['Text'],'')
 def test_other_layout_without_quality(self):
  out=ready.parse('[COLOR x]REALDEBRID[CR]03 - Movie.2024.1080p.WEB.mkv[CR]4.37 GB[/COLOR]')
  self.assertEqual((out['Provider'],out['File'],out['Size'],out['Quality'],out['Ready']),('Real-Debrid','Movie.2024.1080p.WEB.mkv','4.37 GB','','true'))
 def test_unknown_text_is_kept_as_text(self):
  for text in ('[COLOR x]Resolving...[/COLOR]Some.File.mkv','[COLOR x]4K:[/COLOR]  3  |  1080p:  5[CR]Remaining: 2',''):
   out=ready.parse(text);self.assertEqual(out['Ready'],'');self.assertNotIn('[COLOR',out['Text'])
 def test_watch_publishes_then_clears(self):
  frames=iter([(True,UMBRELLA),(True,UMBRELLA),(False,''),(False,'')]);state={'v':False,'t':''};props={};ticks=[0]
  def wait(_):
   ticks[0]+=1
   try:state['v'],state['t']=next(frames)
   except StopIteration:return True
   return False
  ready.watch(lambda:state['v'],lambda:state['t'],props.__setitem__,lambda k:props.pop(k,None),wait)
  self.assertEqual(props,{},'properties stay behind after the window closed')
  props.clear();frames=iter([(True,UMBRELLA)]);ready.watch(lambda:state['v'],lambda:state['t'],props.__setitem__,lambda k:props.pop(k,None),wait)
  self.assertEqual(props.get('IOSReady.Provider'),'AllDebrid')

class PlayOnTV(unittest.TestCase):
 TVS=[{'kind':'roku','host':'1.2.3.4','name':'Bedroom TV'},{'kind':'dlna','host':'1.2.3.5','name':'Samsung'},
      {'kind':'airplay','host':'','name':'Apple TV / AirPlay TV'}]
 def test_last_tv_first_and_iphone_on_top(self):
  tvs=castui.ordered(self.TVS,'dlna|1.2.3.5');self.assertEqual(tvs[0]['name'],'Samsung')
  rows=castui.rows(tvs);self.assertEqual(rows[0]['name'],'This iPhone');self.assertEqual(rows[0]['on'],'true')
  self.assertEqual([r['kind'] for r in rows[1:]],['Smart TV','Roku','AirPlay'])
 def test_sheet_height_follows_rows(self):
  self.assertEqual(castui.properties([],True,'t','n')['count'],'2')          # iPhone + searching
  self.assertEqual(castui.properties(self.TVS,False,'t','n')['count'],'4')   # iPhone + 3 TVs
  none=castui.properties([],False,'t','n');self.assertEqual(none['count'],'2');self.assertTrue(none['searching'].startswith('No other TV'))
  many=castui.properties(self.TVS*4,True,'t','n');self.assertEqual(many['count'],str(castui.ROWS+1))
 def test_rows_match_the_sheet(self):
  pages=portrait.pages;self.assertEqual(castui.ROWS,pages.TV_ROWS)
  root=ET.fromstring(pages.play_on_tv());ids={c.get('id') for c in root.iter('control')}
  self.assertTrue({str(castui.ROW_BASE+n) for n in range(1,castui.ROWS+1)}|{'9500','9099'}<=ids)
  backs=[v.text for v in root.iter('visible') if v.text and 'Property(count)' in v.text]
  self.assertEqual(len(backs),castui.ROWS+1)

# Fuse 3.4.8's DialogBusy: its Kodi logo in a white circle with a spinning arc, bottom right of a 1920x1080 screen.
FUSE_BUSY=('<window><zorder>1000</zorder><controls><include content="Furniture_Busy"><param name="hasspinner">true</param>'
           '<param name="icon">special://skin/extras/icons/kodi.png</param><param name="haslabel">false</param></include>'
           '<control type="progress" id="10"><include>Object_Hidden_Button_Definition</include></control></controls></window>')

class Pages(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();skin=Path(cls.tmp.name)/'skin.arctic.fuse.3';(skin/'1080i').mkdir(parents=True)
  (skin/'addon.xml').write_text('<addon id="skin.arctic.fuse.3"><extension point="xbmc.gui.skin"><res aspect="16:9" default="true" folder="1080i" width="1920" height="1080" /></extension></addon>')
  plain='<window><controls><control type="label" id="1"><label>x</label></control></controls></window>'
  for name in ('Font.xml','Includes.xml','DialogConfirm.xml','AddonBrowser.xml','EventLog.xml','SettingsSystemInfo.xml','FileManager.xml',
               'DialogTextViewer.xml','DialogSettings.xml','Home.xml','VideoOSD.xml','DialogSeekBar.xml','Settings.xml'):
   (skin/'1080i'/name).write_text('<fonts><fontset id="Default" /></fonts>' if name=='Font.xml' else '<includes />' if name=='Includes.xml'
                                 else plain.replace('<window>','<window><views>50</views>') if name in ('AddonBrowser.xml','EventLog.xml') else plain)
  (skin/'1080i/DialogBusy.xml').write_text(FUSE_BUSY)
  cls.profile=Path(cls.tmp.name)/'profile';cls.profile.mkdir()
  navigation.patch_skin(skin);portrait.build(skin,cls.profile);cls.skin=skin
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def ids(self,name):
  root=ET.parse(self.skin/name).getroot();return root,{c.get('id'):c.get('type') for c in root.iter('control') if c.get('id')}
 def test_kodi_control_ids(self):
  for name,need in (('DialogConfirm.xml',{'1':'label','9':'textbox','10':'button','11':'button','12':'button','20':'progress'}),
                    ('DialogTextViewer.xml',{'1':'label','5':'textbox'}),
                    ('AddonBrowser.xml',{'50':'list'}),
                    ('EventLog.xml',{'50':'list','20':'button','21':'button','22':'togglebutton','4':'togglebutton'}),
                    ('SettingsSystemInfo.xml',dict({str(i):'label' for i in range(2,12)},**{'30':'textbox','94':'button','100':'button','52':'label'})),
                    ('FileManager.xml',{'20':'list','21':'list','101':'label','102':'label','12':'label','13':'label'}),
                    ('DialogSettings.xml',{'2':'label','3':'grouplist','5':'grouplist','28':'button','29':'button','7':'button','8':'radiobutton'}),
                    ('source_progress.xml',{'2001':'textbox'})):
   _,ids=self.ids('portrait/'+name)
   self.assertEqual({k:ids.get(k) for k in need},need,name)
 def test_system_info_focuses_a_tab_after_fuse(self):
  root,_=self.ids('portrait/SettingsSystemInfo.xml');self.assertEqual([o.text for o in root.findall('onload')][-1],'SetFocus(95)')
 def test_media_windows_keep_their_views(self):
  for name in ('AddonBrowser.xml','EventLog.xml'):
   self.assertEqual(self.ids('portrait/'+name)[0].findtext('views'),'50',name)
 def test_progress_dialog_focus_reaches_cancel(self):
  # Found in Kodi: with Yes hidden (progress dialogs) nothing had focus, so a remote could not cancel.
  root,_=self.ids('portrait/DialogConfirm.xml');self.assertEqual(root.findtext('defaultcontrol'),'9101')
  relay=[c for c in root.iter('control') if c.get('id')=='9101'][0]
  self.assertEqual([o.text for o in relay.findall('onfocus')],['SetFocus(11)','SetFocus(10)','SetFocus(12)'])
 def test_play_on_tv_is_landscape_only_and_left_alone_by_navigation(self):
  self.assertTrue((self.skin/'1080i/IOSPlayOnTV.xml').is_file());self.assertFalse((self.skin/'portrait/IOSPlayOnTV.xml').exists())
  # Found by test_portrait: the navigation patch framed it and the portrait refresh rewrote it on every start.
  self.assertEqual(navigation.patch_skin(self.skin),[]);self.assertEqual(portrait.refresh(self.skin,self.profile),[])
 def test_play_on_tv_is_centred_for_any_width(self):
  # Found on iPhone: the sheet sat left of centre in the 2340-wide landscape layout (left was worked out for 1920).
  root=ET.parse(self.skin/'1080i/IOSPlayOnTV.xml').getroot();sheet=root.find('controls/control[@type="group"]')
  self.assertEqual(sheet.findtext('centerleft'),'50%');self.assertIsNone(sheet.find('left'))
  self.assertNotIn('1920',(self.skin/'1080i/IOSPlayOnTV.xml').read_text())
 def test_conditions_use_kodi_brackets(self):
  for name in portrait.pages.HANDMADE|{'source_progress.xml'}:
   self.assertNotIn('!(',(self.skin/'portrait'/name).read_text(),name)
  self.assertNotIn('!(',(self.skin/'1080i/IOSPlayOnTV.xml').read_text())
 def test_umbrella_page_reads_the_published_fields(self):
  xml=(self.skin/'portrait/source_progress.xml').read_text()
  for key in ('Provider','Via','Quality','Size','Badges','File','Text','Ready'):self.assertIn('IOSReady.'+key,xml)
  self.assertIn('Window.Property(umbrella.fanart)',xml);self.assertIn('Integer.IsGreaterOrEqual(Window.Property(percent),100)',xml)
 def test_settings_dialog_has_no_empty_category_pill(self):
  root,_=self.ids('portrait/DialogSettings.xml')
  cats=[c for c in root.iter('control') if c.get('id')=='3'][0];self.assertEqual(cats.findtext('visible'),'false')
 def test_no_control_id_twice(self):
  # Found here: System Info used 3 for its tabs and for Kodi's third info line (that line went missing).
  import collections
  names=sorted(portrait.pages.HANDMADE|{'source_progress.xml','Settings.xml','IOSAccounts.xml','SettingsCategory.xml','DialogAddonSettings.xml'})
  for name in names:
   ids=collections.Counter(c.get('id') for c in ET.parse(self.skin/'portrait'/name).getroot().iter('control') if c.get('id'))
   self.assertEqual({k:v for k,v in ids.items() if v>1},{},name)
 def test_busy_is_the_same_centred_pill_in_both_folders(self):
  # Build 191 (owner): Fuse's busy logo, shrunk into portrait, sat as a white Kodi badge on a Library poster's corner,
  # and over landscape video its spinner showed instead of the pill loader.
  shapes=[]
  for rel,font in (('portrait/DialogBusy.xml','p_pill'),('1080i/DialogBusy.xml','font_main_bold')):
   xml=(self.skin/rel).read_text(encoding='utf-8');root=ET.fromstring(xml)
   for stock in ('kodi.png','Furniture_Busy','provider_circle','loading-spinner','landscape window'):self.assertNotIn(stock,xml,rel)
   # No window <visible>: Kodi would open a dialog with one by itself. Roadmap 2.18: the only thing to tap is Cancel
   # (Kodi's Back), in a group that fades in after 2 s.
   self.assertIsNone(root.find('visible'),rel)
   taps=[c for c in root.iter('control') if c.get('type') in ('button','list')]
   self.assertEqual([(c.get('id'),c.findtext('label'),c.findtext('onclick')) for c in taps],[('9850','Cancel','Action(Back)')],rel)
   self.assertIn('delay="2000"',xml,rel)
   pill=root.find('controls/control[@type="group"]')
   self.assertEqual((pill.findtext('centerleft'),pill.findtext('centertop')),('50%','50%'),rel);self.assertIsNone(pill.find('left'),rel)
   # Build 192 (owner): a clean spinning circle in the centre, no pill and no "Loading…".
   self.assertNotIn('pill_glass_124.png',xml);self.assertNotIn('Loading',xml);self.assertIsNone(pill.find('control[@type="label"]'),rel)  # the ring group itself has no words
   ring=[c for c in pill.iter('control') if 'ring.png' in (c.findtext('texture') or '')][0]
   self.assertEqual(ring.find('animation').get('effect'),'rotate')
   # Kodi's progress 10 stays for Kodi, inside a group that is never drawn.
   hidden=[g for g in root.iter('control') if g.get('type')=='group' and g.findtext('visible')=='false'][0]
   self.assertEqual([c.get('id') for c in hidden.iter('control') if c.get('id')],['10'],rel)
   shapes.append([(c.get('type'),c.findtext('left'),c.findtext('top'),c.findtext('width'),c.findtext('height')) for c in pill.iter('control')])
  self.assertEqual(shapes[0],shapes[1])
  self.assertIn('DialogBusy.xml',portrait.OWN_1080I);self.assertIn('DialogBusy.xml',portrait.LOADED_AT_START)
  self.assertIn('Kodi-iOS player controls',(self.skin/'1080i/DialogBusy.xml').read_text(encoding='utf-8'))
 def test_shared_textures(self):
  for name in ('alert.png','sheet_l.png'):self.assertTrue((self.skin/'extras/portrait'/name).read_bytes().startswith(b'\x89PNG'))

class HeroTaps(unittest.TestCase):
 def test_play_and_info_ignore_taps_while_the_spotlight_slides(self):
  # Roadmap 2.10 (owner screenshot): the watch question named another title than the one on screen.
  import portrait
  xml=portrait.hero('home','Home')
  for action in ('PlayMedia($ESCINFO[Container(4000).ListItem.FileNameAndPath])','Action(Info)'):
   onclick=[l for l in xml.split('<onclick') if action in l]
   self.assertTrue(onclick,action)
   self.assertTrue(all('!Container(4000).Scrolling' in l for l in onclick),action)


if __name__=='__main__':unittest.main()
