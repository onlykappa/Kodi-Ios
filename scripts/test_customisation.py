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
      'Indicator.DisableEpisodes':True,'Indicator.EnableUnwatchedCount':False,
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
  rules=sp.count_rules();self.assertEqual(len(rules['badges']),10)   # no Live TV Catch-up (owner, 2026-11-12);self.assertEqual(len(rules['osd']),2)
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
  # Owner (build 204): a new row goes at the bottom of the rows Home shows, and the page moves to it (build 202:
  # "when i press add and nothing is added").
  e=self.editor(0);e.click(self.page.ADD);self.assertEqual([r['label'] for r in e.rows],['A','B','Trending Movies'])
  self.assertEqual(e.props()['row.3.title'],'Trending Movies');self.assertEqual(e.props()['row.3.off'],'')   # not judged empty yet
  self.assertEqual(e.focus,self.page.ROW_BASE+3);self.assertEqual(e.ui.note,'Added "Trending Movies" at the bottom of Home')
  e=self.editor(len(self.script.re_.CATALOGUE['home']),'plugin://plugin.video.umbrella/movies/','Umbrella Movies')
  e.click(self.page.ADD);self.assertEqual((e.rows[-1]['label'],e.rows[-1]['path']),('Umbrella Movies','plugin://plugin.video.umbrella/movies/'))
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
 def test_add_row_offers_trending_and_now_playing(self):
  # Owner (build 204): "I want trending movies to be a option and trending shows, and Now Playing under movies".
  c=self.script.re_.CATALOGUE;names=lambda k:[n for n,_ in c[k]]
  for name in ('Trending Movies','Trending Shows','Trakt Trending Movies','Trakt Trending Shows'):self.assertIn(name,names('home'))
  self.assertEqual(names('movies')[:3],['Trending Movies','Trakt Trending Movies','Now Playing'])
  self.assertEqual(names('tv')[:3],['Trending Shows','Trakt Trending Shows','Airing Today'])
  self.assertEqual(dict(c['movies'])['Now Playing'],'plugin://plugin.video.themoviedb.helper/?info=now_playing&tmdb_type=movie')
  self.assertTrue(all(p for _,p in c['home']))
  rows=[{'label':'A','path':'plugin://a/?x'},{'label':'Menu','path':'plugin://b'}]
  self.assertEqual([r['label'] for r in self.script.re_.add(rows,'N','plugin://n/?y')],['A','N','Menu'])   # before rows Home never shows
 def test_row_files_match_the_full_build(self):
  # Build 204 (owner: "ensure its quick"): after a row change only the hub files are rebuilt; they must be exactly what
  # the full refresh makes, or Home would differ from the next start's.
  import os
  skin=os.environ.get('KODI_RIG_SKIN','/root/.cache/kodi-rig-test/home/.kodi/addons/skin.arctic.fuse.3')
  if not os.path.isdir(skin):self.skipTest('no Fuse copy (desktop Kodi rig) on this machine')
  self.script.re_.save(self.p,'homewidgets',[{'label':'Trending Movies','path':self.script.re_.TMDB%('trending_week','movie')}])
  full=portrait.portrait_files(skin,self.p);rows=portrait.row_files(skin,self.p)
  self.assertTrue({'portrait/Home.xml','portrait/Includes.xml','1080i/'+portrait.LANDSCAPE_VARS}<=set(rows))
  for rel,data in rows.items():self.assertEqual(data,full[rel],rel)
  self.assertIn(b'Trending Movies',rows['portrait/Home.xml'])
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

class Released(unittest.TestCase):
 def test_rows_leave_out_unreleased_titles_except_upcoming_rows(self):
  # Owner (2026-11-12): blank cards with red italic titles were TMDb Helper's unreleased titles.
  t='plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=movie'
  self.assertTrue(portrait.released_only({'path':t,'label':'Netflix Original Movies'})['path'].endswith('&hide_unaired=true'))
  for keep in ({'path':t,'label':'Upcoming Movies'},{'path':t+'&info2=upcoming','label':'x'},{'path':t+'&hide_unaired=false','label':'x'},
               {'path':'plugin://plugin.video.umbrella/?a=b','label':'x'}):
   self.assertEqual(portrait.released_only(keep),keep)
 def test_a_card_without_a_poster_shows_its_other_picture(self):
  xml=portrait.poster_item(False)
  self.assertIn('ListItem.Art(thumb)',xml);self.assertIn('ListItem.Art(fanart)',xml)

class Dialogs(unittest.TestCase):
 def test_notification_volume_and_info_card(self):
  pages=portrait.pages
  n=pages.notification_dialog('m',43,150,994,'a','b');ET.fromstring(n.split('\n',2)[2])
  for id in ('400','401','402'):self.assertIn('id="%s"'%id,n)
  v=pages.volume_dialog('m',220,150,640,'a');self.assertIn('id="933"',v);self.assertIn('Player.Muted',v)
  # Board 08: Info is the episode card (window 1193), opened by the controls' Info without closing them.
  w=pages.info_card();root=ET.fromstring(w.split('\n',2)[2])
  self.assertEqual(root.get('id'),'1193')
  for info in ('VideoPlayer.TVShowTitle','VideoPlayer.Season','VideoPlayer.Episode','VideoPlayer.Title','VideoPlayer.Plot','Player.FinishTime','Player.Art(thumb)'):self.assertIn(info,w)
  self.assertIn('No description for this video yet.',w);self.assertNotIn('Furniture_Busy',w);self.assertNotIn('ring.png',w)
  self.assertIn('<onclick>Close</onclick>',w)
  self.assertEqual(portrait.player_osd.INFO,'ActivateWindow(1193)')
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
  self.assertEqual(loads,[a for _,a in osd.DEFAULT_ONLOAD]+list(osd.ARM))   # ISSUE-279: the 5 s default comes first
  self.assertIn('Dialog.Close(videoosd)',osd.ARM[1]);self.assertIn('$INFO[Skin.String(OSD_Timeout),00:,]',osd.ARM[1])
  for button in root.iter('control'):
   if button.get('type')=='button' and button.get('id')!='7100':   # the tap-to-hide area closes instead
    self.assertEqual([o.text for o in button.findall('onclick')][:2],list(osd.ARM),button.get('id'))
  self.assertIn('!Player.Paused',osd.ARM_WHEN);self.assertIn('CancelAlarm(osd_timeout,true)',[o.text for o in root.findall('onunload')])

 def test_tap_anywhere_hides_and_five_seconds_by_default(self):
  # ISSUE-279 (owner, build 430 log 72b62563: ten taps on no control, "control 0 (not handled)", and the controls
  # stayed with no tap for 12 s; Fuse ships Hide Controls After empty = never).
  xml=osd.window();root=ET.fromstring(xml.split('\n',2)[2]);top=list(root.find('controls'))
  self.assertEqual((top[0].get('id'),top[0].get('type')),('7100','button'))            # under every other control
  self.assertEqual((top[0].findtext('left'),top[0].findtext('right'),top[0].findtext('top'),top[0].findtext('bottom')),('0','0','0','0'))
  self.assertEqual([o.text for o in top[0].findall('onclick')],['Dialog.Close(videoosd)'])
  self.assertNotIn('7100',[n.text for n in root.iter() if n.tag.startswith('on') and n.text and n.text.isdigit()])   # never reached by arrows
  loads=[(o.get('condition'),o.text) for o in root.findall('onload')]
  self.assertEqual(loads[0],('String.IsEmpty(Skin.String(OSD_Timeout)) + !Skin.HasSetting(ios_osd_timeout_default)','Skin.SetString(OSD_Timeout,3)'))
  # ISSUE-283 (owner, build 442: "hide after 3 s"): installs on the old 5 s default move to 3 s once; a later choice stays.
  self.assertEqual(loads[2],('String.IsEqual(Skin.String(OSD_Timeout),5) + !Skin.HasSetting(ios_osd_timeout_3)','Skin.SetString(OSD_Timeout,3)'))
  self.assertEqual(loads[3],('!Skin.HasSetting(ios_osd_timeout_3)','Skin.SetBool(ios_osd_timeout_3)'))
  self.assertIn('!Player.Paused',osd.ARM_WHEN)                                          # they stay while paused
  self.assertIn('!String.IsEqual(Skin.String(OSD_Timeout),0)',osd.ARM_WHEN)            # 0 still means never

if __name__=='__main__':unittest.main()
