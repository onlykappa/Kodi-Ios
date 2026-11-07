"""Customisation round 4, first pages (mockups 01, 08 and 10): Poster Badges and Video Controls as native switch pages
in Settings, the values on Customisation, the badges drawn on our own posters and episode rows, and Hide Controls
After on our video controls. Each switch writes the same skin setting as Fuse's box."""
import importlib.util,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap';LIB=BOOT/'resources/lib'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
portrait=load('portrait_c',LIB/'portrait.py');sp=portrait.settings_page;osd=portrait.player_osd
counts=load('customise_counts',BOOT/'customise_counts.py')
# Fuse 3's own switches (Dialog_DialogCustom.xml): DialogCustom_Settings_Items_Indicators and the overlay pair of
# DialogCustom_VideoOSD_Items, with whether Fuse shows them on when the setting is absent.
FUSE={'Indicator.DisableWatched':True,'Indicator.DisableLibrary':True,'Indicator.DisableCollection':True,'Indicator.DisableProgress':True,
      'Indicator.DisableEpisodes':True,'Indicator.EnableUnwatchedCount':False,'Indicator.DisablePVRGuideCatchUp':True,
      'Indicator.TraktWatchlist':False,'Indicator.TraktFavourites':False,'Indicator.EpisodeTypeBanner':False,'Indicator.MovieVersionBanner':False,
      'OSD.InfoOverlay.DisableLandscapeOnInfo':True,'OSD.InfoOverlay.DisablePlotRatingsOnInfo':True}

class Pages(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();skin=Path(cls.tmp.name)/'skin.arctic.fuse.3';(skin/'1080i').mkdir(parents=True)
  (skin/'addon.xml').write_text('<addon id="skin.arctic.fuse.3"><extension point="xbmc.gui.skin"><res aspect="16:9" default="true" folder="1080i" width="1920" height="1080" /></extension></addon>')
  for name,data in {'Font.xml':'<fonts><fontset id="Default" /></fonts>','Includes.xml':'<includes />',
                    'Settings.xml':'<window id="10004"><controls /></window>',
                    'SettingsCategory.xml':'<window><controls /></window>','DialogAddonSettings.xml':'<window><controls /></window>'}.items():(skin/'1080i'/name).write_text(data)
  profile=Path(cls.tmp.name)/'profile';profile.mkdir();portrait.build(skin,profile)
  cls.root=ET.parse(skin/'portrait/Settings.xml').getroot();cls.skin=skin
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def control(self,id):return [c for c in self.root.iter('control') if c.get('id')==str(id)][0]

 def test_switches_write_fuses_settings(self):
  seen={}
  for sw in sp.switches(sp.BADGES)+[r for r in sp.switches(sp.OSD) if isinstance(r,dict)]:
   button=self.control(sw['id']);self.assertEqual([o.text for o in button.findall('onclick')],['Skin.ToggleSetting(%s)'%sw['setting']])
   seen[sw['setting']]=sw['inverted']
  self.assertEqual(seen,FUSE)
 def test_switch_shows_its_state(self):
  xml=ET.tostring(self.root,encoding='unicode')
  self.assertIn('<visible>!Skin.HasSetting(Indicator.DisableWatched)</visible>',xml)
  self.assertIn('<visible>![!Skin.HasSetting(Indicator.DisableWatched)]</visible>',xml)
  self.assertIn('<enable>!Skin.HasSetting(Indicator.DisableEpisodes)</enable>',xml)
 def test_customisation_rows_open_the_pages_and_show_counts(self):
  self.assertEqual([o.text for o in self.control(9414).findall('onclick')],['SetProperty(Settings.Page,badges,10004)','SetFocus(9501)'])
  self.assertEqual([o.text for o in self.control(9411).findall('onclick')],['SetProperty(Settings.Page,osd,10004)','SetFocus(9531)'])
  labels=[l.text for l in self.root.iter('label')]
  for text in ('Poster Badges','Video Controls','Tabs & Rows','$INFO[Window(10004).Property(custom.badges)]','$INFO[Window(10004).Property(custom.osd)]'):
   self.assertIn(text,labels)
  self.assertNotIn('Indicators',labels)
 def test_back_changes_the_page_before_moving_focus(self):
  actions=[(o.get('condition'),o.text) for o in self.control(9001).findall('onclick')]
  page=[i for i,(c,a) in enumerate(actions) if a=='SetProperty(Settings.Page,custom,10004)'][0]
  self.assertLess(page,actions.index((sp.ON_BADGES,'SetFocus(9414)')));self.assertLess(page,actions.index((sp.ON_OSD,'SetFocus(9411)')))
  self.assertEqual(actions[-1],(sp.ON_ROOT,'Action(Back)'))
  downs=[(o.get('condition'),o.text) for o in self.control(9001).findall('ondown')]
  self.assertIn((sp.ON_BADGES,'9501'),downs);self.assertIn((sp.ON_OSD,'9531'),downs)
 def test_first_rows_go_up_to_back_and_ids_are_unique(self):
  self.assertEqual(self.control(9501).findtext('onup'),'9001');self.assertEqual(self.control(9531).findtext('onup'),'9001')
  self.assertEqual(self.control(9501).findtext('ondown'),'9502');self.assertEqual(self.control(9505).findtext('ondown'),'9511')
  ids=[c.get('id') for c in self.root.iter('control') if c.get('id')];self.assertEqual(len(ids),len(set(ids)))
 def test_hide_controls_after(self):
  self.assertEqual([o.text for o in self.control(9531).findall('onclick')],['Skin.SetNumeric(OSD_Timeout)'])
  labels=[l.text for l in self.root.iter('label')];self.assertIn('$INFO[Skin.String(OSD_Timeout),, s]',labels);self.assertIn('Never',labels)
 def test_counts(self):
  rules=sp.count_rules();self.assertEqual(len(rules['badges']),11);self.assertEqual(len(rules['osd']),2)
  on={'!Skin.HasSetting(Indicator.DisableWatched)','Skin.HasSetting(Indicator.TraktWatchlist)'}
  self.assertEqual(counts.values(rules,lambda c:c in on),{'custom.badges':'2 on','custom.osd':'0 on'})
  self.assertEqual(counts.rules(),rules)
  self.assertIn('customise_counts',load('dispatch_c',BOOT/'default.py').PAGES)
 def test_settings_search_finds_the_new_names(self):
  rows=[r[1] for _,rows,_ in sp.CUSTOM for r in rows];self.assertIn('Poster Badges',rows);self.assertIn('Tabs & Rows',rows)

class Badges(unittest.TestCase):
 def test_posters_follow_the_settings(self):
  item=portrait.poster_item(False)
  for key in ('watched','watchlist','favourite','collection','library','episodes','progress','version'):
   self.assertIn(portrait.BADGE[key].split(' + ')[0],item,key)
  ET.fromstring(item)
  self.assertIn('ListItem.Property(UnWatchedEpisodes)',item);self.assertIn('ListItem.PercentPlayed',item)
 def test_one_corner_badge_at_a_time(self):
  item=portrait.poster_item(True)
  self.assertIn('<visible>[%s] + ![%s]</visible>'%(portrait.BADGE['watchlist'],portrait.BADGE['watched']),item)
 def test_library_grid_and_episodes(self):
  grid=portrait.grid();self.assertIn('Indicator.DisableWatched',grid);self.assertNotIn('<visible>ListItem.IsPlayed</visible>',grid)
  ep=portrait.episode_item(False);ET.fromstring(ep)
  self.assertIn('Indicator.EpisodeTypeBanner',ep);self.assertIn('Season Finale',ep);self.assertIn('Indicator.DisableProgress',ep)

class HideControls(unittest.TestCase):
 def test_alarm_on_open_and_every_tap(self):
  xml=osd.window();root=ET.fromstring(xml.split('\n',2)[2])
  loads=[o.text for o in root.findall('onload')]
  self.assertEqual(loads,list(osd.ARM))
  self.assertIn('Dialog.Close(videoosd)',osd.ARM[1]);self.assertIn('$INFO[Skin.String(OSD_Timeout),00:,]',osd.ARM[1])
  for button in root.iter('control'):
   if button.get('type')=='button':
    self.assertEqual([o.text for o in button.findall('onclick')][:2],list(osd.ARM),button.get('id'))
  self.assertIn('!Player.Paused',osd.ARM_WHEN);self.assertIn('CancelAlarm(osd_timeout,true)',[o.text for o in root.findall('onunload')])

if __name__=='__main__':unittest.main()
