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
  self.assertEqual(counts.values(rules,lambda c:c in on),{'custom.badges':'2 on','custom.osd':'0 on','custom.info':'0 on'})
  self.assertEqual(counts.rules(),rules)
  self.assertIn('customise_counts',load('dispatch_c',BOOT/'default.py').PAGES)
 def test_settings_search_finds_the_new_names(self):
  rows=[r[1] for _,rows,_ in sp.CUSTOM for r in rows];self.assertIn('Poster Badges',rows);self.assertIn('Tabs & Rows',rows)

class MorePages(Pages):
 def test_tabs_page_opens_each_tabs_rows(self):
  for id,tab in ((9551,'home'),(9552,'movies'),(9553,'tv')):
   self.assertEqual([o.text for o in self.control(id).findall('onclick')],['RunScript(service.kodi.ios.bootstrap,customise_rows,tab=%s)'%tab])
  self.assertIn('$INFO[Window(10004).Property(custom.rows.movies)]',[l.text for l in self.root.iter('label')])
  rows=load('rows_c',LIB/'rows_editor.py');self.assertEqual([l for _,_,l in rows.TABS],[portrait.HUBS[f][1][0] for f in ('Home.xml','Custom_1102_Hub.xml','Custom_1101_Hub.xml')])
 def test_info_page_switches_match_the_rows_on_our_info_page(self):
  self.assertEqual([sw['setting'] for sw in sp.switches(sp.INFO)],[r[3] for r in portrait.INFO_ROWS])
  for sw in sp.switches(sp.INFO):self.assertEqual([o.text for o in self.control(sw['id']).findall('onclick')],['Skin.ToggleSetting(%s)'%sw['setting']])
 def test_view_types_choices(self):
  self.assertEqual([o.text for o in self.control(9581).findall('onclick')],['Skin.Reset(Portrait.Grid)'])
  self.assertEqual([o.text for o in self.control(9582).findall('onclick')],['Skin.SetString(Portrait.Grid,large)'])
  self.assertEqual(sp.view_name(lambda c:'large' in c),'Large Posters');self.assertEqual(sp.view_name(lambda c:False),'Poster Grid')
 def test_every_subpage_has_back_focus_and_title(self):
  actions=[(o.get('condition'),o.text) for o in self.control(9001).findall('onclick')]
  labels=[l.text for l in self.root.iter('label')]
  for name,cond,first,row,title in sp.SUBPAGES:
   self.assertIn((cond,'SetFocus(%d)'%row),actions);self.assertIn(title,labels);self.control(first)
   self.assertIn((cond,str(first)),[(o.get('condition'),o.text) for o in self.control(9001).findall('ondown')])
  self.assertNotIn('Search Page',labels)   # our Search page never read its widget list
 def test_counts_with_rows(self):
  rows=load('rows_c2',LIB/'rows_editor.py')
  with tempfile.TemporaryDirectory() as d:
   rows.save(d,'homewidgets',[{'label':'A','path':'p'},{'label':'B','path':'q','disabled':'true'}])
   out=counts.values({},lambda c:False,d,sp,rows)
  self.assertEqual((out['custom.rows.home'],out['custom.rows.tv'],out['custom.rows'],out['custom.views']),('2 rows','1 row','4 rows','Poster Grid'))

class RowsEditor(unittest.TestCase):
 def setUp(self):
  self.rows=load('rows_e',LIB/'rows_editor.py');self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
  self.rows.path_of(self.p,'1102widgets').parent.mkdir(parents=True)
  self.original=[{'label':'Popular','path':'plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie','widget_style':'Poster','icon':'x','extra':1},
                 {'label':'Library','path':'videodb://movies/titles/','target':'videos'}]
  self.rows.path_of(self.p,'1102widgets').write_text(__import__('json').dumps(self.original))
 def tearDown(self):self.tmp.cleanup()
 def test_edits_keep_unknown_keys_and_restore(self):
  r=self.rows;rows=r.load(self.p,'1102widgets')
  rows=r.move(rows,0,1);rows=r.rename(rows,1,'  Popular Now ');rows=r.set_style(rows,0,'Poster');rows[1]=r.set_on(rows[1],False)
  r.save(self.p,'1102widgets',rows);back=r.load(self.p,'1102widgets')
  self.assertEqual([w['label'] for w in back],['Library','Popular Now']);self.assertEqual(back[1]['extra'],1)
  self.assertEqual(back[1]['disabled'],'true');self.assertEqual(r.summary(back[1]),'Off · not on Home');self.assertEqual(r.summary(back[0]),'Poster · Your library')
  self.assertFalse(portrait.usable(back[1]));self.assertTrue(portrait.usable(back[0]))
  r.save(self.p,'1102widgets',r.delete(back,0))   # the kept copy is the first one
  self.assertTrue(r.restore(self.p,'1102widgets'));self.assertEqual(r.load(self.p,'1102widgets'),self.original)
 def test_moves_at_the_ends_do_nothing_and_styles(self):
  r=self.rows;rows=r.load(self.p,'1102widgets')
  self.assertEqual(r.move(rows,0,-1),rows);self.assertEqual(r.move(rows,1,1),rows)
  self.assertEqual(r.style_name(r.set_style(rows,0,'')[0]),'Landscape');self.assertNotIn('widget_style',r.set_style(rows,0,'')[0])
  self.assertEqual(r.source('plugin://plugin.video.umbrella/?x=1'),'Umbrella');self.assertEqual(r.source('special://x.xsp'),'Your library')
 def test_properties(self):
  r=self.rows;props=r.properties(r.load(self.p,'1102widgets'),3)
  self.assertEqual((props['row.1.title'],props['row.1.up'],props['row.1.down'],props['row.2.down'],props['row.3.title'],props['count']),
                   ('Popular','','true','','','3 rows on the page'))
 def test_catalogue_paths_are_rows_portrait_shows(self):
  for key,items in self.rows.CATALOGUE.items():
   self.assertTrue(items,key)
   for label,path in items:self.assertTrue(portrait.usable({'path':path}),path)

class MatchesHome(unittest.TestCase):
 """Owner (build 192): the page said 17 rows, Home had 7 and began with Continue Watching."""
 def setUp(self):self.r=load('rows_m',LIB/'rows_editor.py')
 SAMPLES=[{'label':'In Progress Movies','path':'special://profile/playlists/video/In Progress Movies.xsp'},
          {'label':'Video add-ons','path':'library://video/addons.xml/'},{'label':'Umbrella','path':'plugin://plugin.video.umbrella/'},
          {'label':'Netflix','path':'plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=tv&with_networks=213'},
          {'label':'Run','path':'RunScript(x)'},{'label':'Movies','path':'videodb://movies/titles/'},{'label':'Recently added Tv','path':'videodb://recentlyaddedepisodes/'}]
 def test_same_rules_as_portrait(self):
  for w in self.SAMPLES+[{'label':l,'path':p} for k in self.r.CATALOGUE for l,p in self.r.CATALOGUE[k]]:
   self.assertEqual(not self.r.why_not_shown(w),portrait.usable(w) and not portrait.in_progress(w),w)
 def test_page_order_count_and_moves(self):
  rows=self.SAMPLES;order=self.r.view(rows)
  self.assertEqual([rows[i]['label'] for i in order[:3]],['Netflix','Movies','Recently added Tv'])
  self.assertEqual(self.r.shown_count(rows),4)   # Continue Watching + the three
  props=self.r.properties(rows,10)
  self.assertEqual((props['row.1.up'],props['row.3.down'],props['row.4.up'],props['row.4.off']),('','','','true'))
  self.assertIn('Continue Watching already shows these',props['row.4.sub'])
  moved=self.r.move_shown(rows,5,-1)   # 'Movies' up past the hidden rows, over 'Netflix'
  self.assertEqual([moved[i]['label'] for i in self.r.view(moved)[:3]],['Movies','Netflix','Recently added Tv'])
  self.assertEqual(self.r.move_shown(rows,0,1),rows)   # a row Home never shows does not move

class RowsScript(unittest.TestCase):
 class UI:
  def __init__(self,answers):self.answers=list(answers)
  def confirm(self,text):return self.answers.pop(0)
  def notify(self,text):self.note=text
  def text(self,heading,default):return self.answers.pop(0)
  def select(self,heading,names,preselect):self.names=names;return self.answers.pop(0)
  def browse(self,heading):return self.answers.pop(0)
 def setUp(self):
  sys.modules.pop('rows_editor',None);sys.path.insert(0,str(LIB))
  self.script=load('customise_rows_t',BOOT/'customise_rows.py');self.page=self.script.page
  self.tmp=tempfile.TemporaryDirectory();self.p=self.tmp.name
  self.script.re_.save(self.p,'homewidgets',[{'label':'A','path':'plugin://a/?x'},{'label':'B','path':'plugin://b/?y'}])
 def tearDown(self):self.tmp.cleanup()
 def editor(self,*answers):return self.script.Editor(self.p,'home',self.UI(answers))
 def test_edit_mode_moves_and_deletes(self):
  e=self.editor(True);e.click(self.page.EDIT);self.assertEqual(e.props()['edit_label'],'Done')
  e.click(self.page.DOWN+1);self.assertEqual([r['label'] for r in e.rows],['B','A'])
  e.click(self.page.ROW_BASE+1);self.assertIsNone(e.current)   # rows do not open while editing
  e.click(self.page.REMOVE+2);self.assertEqual([r['label'] for r in e.rows],['B']);self.assertTrue(e.changed)
  self.assertFalse(e.back());self.assertTrue(e.back())
 def test_one_row_page(self):
  e=self.editor('New name',0);e.click(self.page.ROW_BASE+2)
  props=e.props();self.assertEqual((props['page'],props['title'],props['one.on']),('row','B','true'))
  e.click(self.page.SHOW);self.assertEqual(e.props()['one.on'],'')
  e.click(self.page.RENAME);e.click(self.page.STYLE)
  self.assertEqual((e.rows[1]['label'],e.rows[1]['widget_style'],e.rows[1]['disabled']),('New name','Poster','true'))
  self.assertFalse(e.back());self.assertEqual(e.props()['page'],'')
 def test_add_from_the_list_and_from_an_addon(self):
  # Owner (build 202: "when i press add and nothing is added"): a new row goes first, under Continue Watching.
  e=self.editor(0);e.click(self.page.ADD);self.assertEqual(e.rows[0]['label'],'Trending Movies')
  self.assertEqual(e.props()['row.1.title'],'Trending Movies');self.assertEqual(e.props()['row.1.off'],'')   # not judged empty yet
  self.assertEqual(e.ui.note,'Added under Continue Watching')
  e=self.editor(len(self.script.re_.CATALOGUE['home']),'plugin://plugin.video.umbrella/movies/','Umbrella Movies')
  e.click(self.page.ADD);self.assertEqual((e.rows[0]['label'],e.rows[0]['path']),('Umbrella Movies','plugin://plugin.video.umbrella/movies/'))
  e=self.editor(-1);before=len(e.rows);e.click(self.page.ADD);self.assertEqual(len(e.rows),before);self.assertEqual(before,4)
 def test_count_matches_what_home_shows(self):
  # Owner (build 202): "Customization still says i have 15 rows on home ... i only have 7 rows". Home hides a row with
  # nothing to show; the page counts and marks only what Home really shows.
  import json
  re_=self.script.re_
  tmdb='plugin://plugin.video.themoviedb.helper/?info=%s&tmdb_type=movie'
  rows=[{'label':'Trending','path':tmdb%'trending_week'},{'label':'Trakt For You','path':tmdb%'trakt_becauseyouwatched'},
        {'label':'Recent','path':'videodb://recentlyaddedmovies/'},{'label':'Library','path':'videodb://movies/titles/'},
        {'label':'Umbrella','path':'plugin://plugin.video.umbrella/?a=1'}]
  re_.save(self.p,'homewidgets',rows)
  copy=Path(self.p)/(re_.LISTINGS%re_.copy_key(tmdb%'trending_week'));copy.parent.mkdir(parents=True,exist_ok=True)
  copy.write_text(json.dumps({'items':[{'path':'x'}]}))   # the service keeps copies of lists that have items
  counts={'videodb://recentlyaddedmovies/':0,'videodb://movies/titles/':40}
  e=self.script.Editor(self.p,'home',self.UI([]),counts.get)
  self.assertEqual(e.empty,{1,2})
  props=e.props()
  self.assertEqual(props['count'],'4 rows on the page · 2 empty right now')   # CW, Trending, Library, Umbrella
  self.assertEqual(props['row.2.sub'],'Empty · sign in to Trakt');self.assertEqual(props['row.2.off'],'true')
  self.assertEqual(props['row.3.sub'],'Empty now · hidden on Home')
  self.assertEqual(re_.count(self.p,'homewidgets',counts.get),4)
  copy.unlink()   # no copies at all (first start, or the rig): TMDb rows are not judged, library rows still are
  self.assertEqual(re_.empty_rows(self.p,re_.load(self.p,'homewidgets'),counts.get),{2})
 def test_folder_counter_asks_kodi_for_one_item(self):
  import json
  asked=[]
  def rpc(text):asked.append(json.loads(text));return json.dumps({'result':{'files':[{}],'limits':{'start':0,'end':1,'total':12}}})
  count=self.script.re_.folder_counter(rpc)
  self.assertEqual(count('videodb://movies/titles/'),12);self.assertEqual(asked[0]['params']['limits'],{'start':0,'end':1})
  self.assertIsNone(count('plugin://plugin.video.umbrella/?a=1'));self.assertEqual(len(asked),1)
 def test_restore(self):
  e=self.editor(True);e.click(self.page.EDIT);e.click(self.page.REMOVE+1)
  e=self.editor(True);e.click(self.page.RESTORE);self.assertEqual([r['label'] for r in e.rows],['A','B'])
 def test_window_has_every_control_the_script_uses(self):
  with tempfile.TemporaryDirectory() as d:
   import types
   xml=self.page.page(types.SimpleNamespace(**{k:getattr(portrait,k) for k in dir(portrait)}))
  root=ET.fromstring(xml.split('\n',2)[2]);ids={c.get('id') for c in root.iter('control')}
  need={self.page.BACK,self.page.EDIT,self.page.ADD,self.page.RESTORE,self.page.SHOW,self.page.RENAME,self.page.STYLE,self.page.DELETE}
  need|={b+n for b in (self.page.ROW_BASE,self.page.UP,self.page.DOWN,self.page.REMOVE) for n in (1,self.page.SLOTS)}
  self.assertTrue({str(i) for i in need}<=ids)
  self.assertIn('customise_rows',load('dispatch_r',BOOT/'default.py').PAGES)

class InfoRowsAndGrid(unittest.TestCase):
 def test_info_rows_load_only_when_on(self):
  v=portrait.info_variables();ET.fromstring('<a>'+v+'</a>')
  for key,_,info,setting,_,_ in portrait.INFO_ROWS:
   self.assertIn('<variable name="Portrait_Info_%s"><value condition="!Skin.HasSetting(%s)'%(key,setting),v);self.assertIn('info=%s&amp;'%info,v)
  page=portrait.video_info('<window type="dialog" id="2003"><controls/></window>')
  for n in range(len(portrait.INFO_ROWS)):self.assertIn('id="%d"'%(portrait.INFO_ID+n),page)
  self.assertIn('id="4"',page)   # Kodi's plot textbox stays
 def test_grid_two_across(self):
  g=portrait.grid();ET.fromstring('<a>'+g+'</a>')
  self.assertIn('condition="%s"'%portrait.GRID_LARGE,g);self.assertEqual(g.count('<itemlayout'),2)

class Dialogs(unittest.TestCase):
 def test_notification_volume_and_info_wait(self):
  pages=portrait.pages
  n=pages.notification_dialog('m',43,150,994,'a','b');ET.fromstring(n.split('\n',2)[2])
  for id in ('400','401','402'):self.assertIn('id="%s"'%id,n)
  v=pages.volume_dialog('m',220,150,640,'a');self.assertIn('id="933"',v);self.assertIn('Player.Muted',v)
  w=pages.info_wait('<window type="dialog" id="1193"><controls><control type="group"><visible>x</visible><include content="Furniture_Busy" /></control></controls></window>')
  self.assertIn('ring.png',w);self.assertNotIn('Furniture_Busy',w);self.assertIn('<visible>x</visible>',w)
  self.assertTrue({pages.NOTIFY,pages.VOLUME,pages.INFO_WAIT}<=portrait.OWN_1080I)
 def test_fuse_overlay_hides_under_our_controls(self):
  osd=portrait.player_osd;src='<window><controls><control type="label" /></controls></window>'
  self.assertIn('<visible>!Window.IsVisible(videoosd)</visible>',osd.safe_inset(src,True));self.assertNotIn('videoosd',osd.safe_inset(src))
  self.assertEqual(set(osd.HIDE_UNDER_OSD),{'Custom_1152_OSD_VideoInfoOverlay.xml','Custom_1153_OSD_VideoInfoOverlayTop.xml'})

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
