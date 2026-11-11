"""The strict source check (migration/bundled-bootstrap/resources/lib/source_match.py) and the routes that use it:
the Deck's "Choose a version" page (Elementum and Umbrella), Burst's provider results and Umbrella's own list."""
import importlib.util,json,sys,tempfile,types,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0,str(ROOT/'scripts'))

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
sm=load('source_match',LIB/'source_match.py')
dp=load('deck_picker_sm',ROOT/'migration/deck-picker/deck_picker.py')
up=load('umbrella_picker_sm',LIB/'umbrella_picker.py')

def movie(title,year,*alts,others=False,years=()):
 exp=sm.expected('movie',[title]+list(alts),year,years);exp['others']=others;return exp

# (identity, release name, kept?, reason when hidden)
FALL=movie('Fall',2022,others=True)
TABLE=[
 (FALL,'Fall.2022.1080p.WEBRip.x264.AAC5.1-[YTS.MX]',True,''),
 (FALL,'Fall (2022) [2160p] [4K] [WEB] [5.1] [YTS.MX]',True,''),
 (FALL,'[ www.Torrenting.com ] - Fall.2022.720p.BluRay.x264',True,''),
 (FALL,'Fall 2022 MULTi 1080p WEB H264-FW',True,''),
 (FALL,'Fall.2026.1080p.WEB-DL.DDP5.1.H.264-FLUX',False,'wrong year'),
 (FALL,'Fall (2026) 2160p AMZN WEB-DL',False,'wrong year'),
 (FALL,'Free.Fall.2014.1080p.BluRay',False,'wrong title'),
 (FALL,'The.Fall.Guy.2024.2160p.WEB',False,'wrong title'),
 (FALL,'Fall.1080p.WEB.x264',False,'no year, another film has this title'),
 (FALL,'Fall.S01E01.1080p.WEB',False,'an episode, not the film'),
 (FALL,'Nightfall.2022.1080p',False,'wrong title'),
 (movie('Dune',2021),'Dune.2021.2160p.HMAX.WEB-DL',True,''),
 (movie('Dune',2021),'Dune.1984.Extended.Edition.1080p',False,'wrong year'),
 (movie('Dune',2021),'Dune.Part.Two.2024.1080p',False,'wrong title'),
 (movie('Dune',2021,'Dune: Part One'),'Dune.Part.One.2021.1080p.BluRay',True,''),
 (movie('Dune',1984),'Dune.1984.1080p.BluRay.x264',True,''),
 (movie('Dune',1984),'Dune.2021.1080p.WEB',False,'wrong year'),
 (movie('Halloween',1978),'Halloween.1978.REMASTERED.1080p.BluRay',True,''),
 (movie('Halloween',1978),'Halloween.2018.1080p',False,'wrong year'),
 (movie('Halloween',2007),'Halloween.2007.Unrated.Directors.Cut.1080p',True,''),
 (movie('Halloween',2018),'Halloween.2007.1080p',False,'wrong year'),
 (movie('Halloween',2018),'Halloween.Kills.2021.1080p',False,'wrong title'),
 (movie('Halloween',2018),'Halloween.Ends.2022.2160p',False,'wrong title'),
 (movie('It',2017,'It: Chapter One'),'It.2017.1080p.BluRay.x264',True,''),
 (movie('It',2017,'It: Chapter One'),'It.Chapter.One.2017.2160p',True,''),
 (movie('It',2017),'It.1990.1080p.BluRay',False,'wrong year'),
 (movie('It',2017),'It.Chapter.Two.2019.1080p',False,'wrong title'),
 (movie('It',2017),'It.Follows.2014.1080p',False,'wrong title'),
 (movie('It',1990,"Stephen King's It"),'Stephen.Kings.It.1990.1080p',True,''),
 (movie('1917',2019),'1917.2019.1080p.BluRay.x264',True,''),
 (movie('1917',2019),'1917 (2019) [2160p] [HDR]',True,''),
 (movie('1917',2019),'1917.1080p.BluRay',True,''),            # no year, but no other film is called 1917
 (movie('2012',2009),'2012.2009.1080p.BluRay',True,''),
 (movie('2012',2009),'2012.BluRay.720p',True,''),
 (movie('Blade Runner 2049',2017),'Blade.Runner.2049.2017.2160p.UHD.BluRay',True,''),
 (movie('Blade Runner 2049',2017),'Blade.Runner.1982.Final.Cut.1080p',False,'wrong title'),
 (movie('Blade Runner',1982),'Blade.Runner.The.Final.Cut.1982.1080p',True,''),
 (movie('Blade Runner',1982),'Blade.Runner.2049.2017.1080p',False,'wrong title'),
 (movie('Inception',2010),'Inception.2010.PROPER.Bluray.2160p.x265.10bit.HDR',True,''),
 (movie('Inception',2010),'Inception 2010 REPACK 1080p BluRay',True,''),
 (movie('Wonder Woman 1984',2020),'Wonder.Woman.1984.2020.1080p',True,''),
 (movie('Wonder Woman 1984',2020),'Wonder.Woman.1984.1080p.WEB',True,''),
 (movie('Wonder Woman',2017),'Wonder.Woman.1984.2020.1080p',False,'wrong year'),
 (movie('Toy Story 2',1999),'Toy.Story.2.1999.1080p',True,''),
 (movie('Toy Story',1995),'Toy.Story.2.1999.1080p',False,'wrong title'),
 (movie('Rocky II',1979),'Rocky.2.1979.1080p',True,''),
 (movie('Rocky II',1979),'Rocky.III.1982.1080p',False,'wrong title'),
 (movie('The Godfather Part II',1974),'The.Godfather.Part.2.1974.1080p',True,''),
 (movie('The Godfather',1972),'The.Godfather.Part.II.1974',False,'wrong title'),
 (movie('Fast & Furious',2009),'Fast.and.Furious.2009.1080p',True,''),
 (movie('The Matrix',1999),'Matrix.1999.1080p',True,''),
 (movie('Mission: Impossible - Fallout',2018),'Mission.Impossible.Fallout.2018.2160p',True,''),
 (movie("Ocean's Eleven",2001),'Oceans.Eleven.2001.1080p',True,''),
 (movie('Spider-Man',2002),'Spiderman.2002.1080p',True,''),
 (movie('Amélie',2001,"Le Fabuleux Destin d'Amélie Poulain"),'Le.Fabuleux.Destin.dAmelie.Poulain.2001.FRENCH.1080p',True,''),
 (movie('Amélie',2001),'Amelie.2001.1080p',True,''),
 (movie('Parasite',2019,'기생충','Gisaengchung'),'Gisaengchung.2019.1080p.BluRay',True,''),
 (movie('Parasite',2019,'기생충'),'기생충.2019.1080p',True,''),
 (movie('Parasite',2019),'Parasite.2019.1080p.mkv',True,''),
 (movie('Parasite',2019),'Gisaengchung.2019.1080p',False,'wrong title'),
 (movie('Us',2019),'Us.2019.1080p.WEB',True,''),
]
OFFICE_US=sm.expected('episode',['The Office'],season=2,episode=3,countries=['US'])
OFFICE_UK=sm.expected('episode',['The Office'],season=2,episode=3,countries=['GB'])
BB=sm.expected('season',['Breaking Bad'],season=2)
EPISODES=[
 (OFFICE_US,'The.Office.US.S02E03.720p.WEB',True,''),
 (OFFICE_US,'The.Office.S02E03.HDTV.x264',True,''),
 (OFFICE_US,'The Office 2x03 HDTV',True,''),
 (OFFICE_US,'The.Office.US.S02.1080p.BluRay',True,''),           # season pack of the right season
 (OFFICE_US,'The.Office.US.S01-S09.Complete.1080p',True,''),
 (OFFICE_US,'The.Office.US.Complete.Series.1080p',True,''),
 (OFFICE_US,'The.Office.UK.S02E03.1080p',False,"another country's show"),
 (OFFICE_US,'The.Office.US.S02E04.720p',False,'wrong episode'),
 (OFFICE_US,'The.Office.US.S03.1080p',False,'wrong season'),
 (OFFICE_US,'The.Office.US.1080p',False,'no season/episode in the name'),
 (OFFICE_UK,'The.Office.UK.S02E03.720p',True,''),
 (OFFICE_UK,'The.Office.US.S02E03.720p',False,"another country's show"),
 (sm.expected('episode',['Doctor Who'],season=1,episode=1,show_year=2005),'Doctor.Who.2005.S01E01.720p',True,''),
 (sm.expected('episode',['Doctor Who'],season=1,episode=1,show_year=2005),'Doctor.Who.1963.S01E01',False,'wrong show year'),
 (sm.expected('episode',['Orange Is the New Black'],season=1,episode=1),'[moon] Orange is the New Black - Season 1 1080p WEBRip x264',True,''),
 (sm.expected('episode',['Orange Is the New Black'],season=1,episode=1),'Is the New Black (2013) S01-S07 [QxR] Season 1/Orange Is the New Black (2013) - S01E01.mkv',True,''),
 (sm.expected('episode',['Game of Thrones'],season=8,episode=3),'Game.of.Thrones.S08E03.The.Long.Night.1080p',True,''),
 (sm.expected('episode',['Game of Thrones'],season=8,episode=3),'Game.of.Thrones.S08E01E02E03.1080p',True,''),
 (sm.expected('episode',['Game of Thrones'],season=8,episode=3),'House.of.the.Dragon.S01E03',False,'wrong title'),
 (sm.expected('episode',['Game of Thrones'],season=8,episode=3),'Game.of.Thrones.Conquest.and.Rebellion.2017',False,'wrong title'),
 (BB,'Breaking.Bad.S02.1080p.BluRay.x264',True,''),
 (BB,'Breaking.Bad.Season.2.Complete.720p',True,''),
 (BB,'Breaking Bad Seasons 1-5 Complete 1080p',True,''),
 (BB,'Breaking.Bad.S03.1080p',False,'wrong season'),
 (sm.expected('anime',['One Piece'],season=1,episode=5,absolute=5),'[SubsPlease] One Piece - 05 (1080p) [ABCD].mkv',True,''),
 (sm.expected('anime',['One Piece'],season=1,episode=5,absolute=5),'[SubsPlease] One Piece - 06 (1080p)',False,'wrong episode'),
]

class Names(unittest.TestCase):
 def test_real_world_table(self):
  for exp,name,ok,reason in TABLE+EPISODES:
   with self.subTest(name=name,want=exp['label']):self.assertEqual(sm.check(name,exp),(ok,reason))
 def test_normalisation(self):
  self.assertEqual(sm.normalize('The Lord of the Rings: The Two Towers'),'lord of the rings the two towers')
  self.assertEqual(sm.normalize('Fast & Furious'),sm.normalize('Fast and Furious'))
  self.assertEqual(sm.normalize('Rocky IV'),'rocky 4');self.assertEqual(sm.normalize('Amélie'),'amelie')
 def test_a_year_without_release_span_evidence_is_never_close_enough(self):
  self.assertEqual(sm.check('Fall.2023.1080p',FALL),(False,'wrong year'))
  span=movie('Portrait of a Lady on Fire',2019,years=[2020,2025]);self.assertEqual(sm.allowed_years(span),{2019,2020})
  self.assertTrue(sm.check('Portrait.of.a.Lady.on.Fire.2020.1080p',span)[0]);self.assertFalse(sm.check('Portrait.of.a.Lady.on.Fire.2018',span)[0])
 def test_a_year_less_name_needs_proof_that_no_other_film_shares_the_title(self):
  exp=movie('Fall',2022,others=None);self.assertEqual(sm.check('Fall.1080p.WEB',exp),(False,'no year (cannot verify)'))
  exp['others']=False;self.assertTrue(sm.check('Fall.1080p.WEB',exp)[0])
 def test_ids_from_a_provider_must_match(self):
  exp=movie('Fall',2022);exp['imdb']='tt15325794'
  self.assertEqual(sm.check('Fall.2022.1080p',exp,{'imdb_id':'tt0000001'}),(False,'different IMDb id'))
  self.assertTrue(sm.check('Fall.2022.1080p',exp,{'imdb_id':'tt15325794'})[0])
 def test_split_keeps_order_and_reports(self):
  items=[{'name':n} for n in ('Fall.2026.1080p','Fall.2022.720p','Free.Fall.2014','Fall.2022.2160p')]
  logged=[]
  with mock.patch.object(sm,'log',logged.append):
   kept,hidden=sm.split(items,FALL);sm.report('Test',FALL,kept,hidden)
  self.assertEqual([i['name'] for i in kept],['Fall.2022.720p','Fall.2022.2160p'])
  self.assertEqual([r for _,r in hidden],['wrong year','wrong title'])
  self.assertIn('Fall (2022): kept 2, hidden 2 (wrong title 1, wrong year 1)',logged[0]);self.assertIn('hidden [wrong year] Fall.2026.1080p',logged[0])

class Identity(unittest.TestCase):
 def test_from_elementums_burst_payload(self):
  exp=sm.from_burst({'title':'Fall','year':2022,'years':{'us':2022,'gb':2022},'titles':{'source':'Fall','original':'Fall','ru':'Падение'},'imdb_id':'tt15325794','tmdb_id':985939,'silent':True},'movie')
  self.assertEqual((exp['kind'],exp['year'],exp['imdb'],exp['tmdb']),('movie',2022,'tt15325794','985939'));self.assertIn('Падение',exp['titles'])
  ep=sm.from_burst({'title':'The Office','season':2,'episode':3,'show_tmdb_id':2316,'titles':{}},'episode')
  self.assertEqual((ep['season'],ep['episode'],ep['tmdb'],ep['label']),(2,3,'2316','The Office S02E03'))
  self.assertIsNone(sm.from_burst({'query':'fall'},'general'))
 def test_from_umbrella_meta(self):
  exp=sm.from_meta({'title':'Fall','originaltitle':'Fall','year':'2022','imdb':'tt15325794','tmdb':'985939'})
  self.assertEqual((exp['kind'],exp['year'],exp['label']),('movie',2022,'Fall (2022)'))
  ep=sm.from_meta({'tvshowtitle':'The Office','season':'2','episode':'3','tmdb':'2316'});self.assertEqual((ep['kind'],ep['season'],ep['episode']),('episode',2,3))
  self.assertIsNone(sm.from_meta({}))
 def tmdb(self,pages):
  calls=[]
  def get(url):
   calls.append(url)
   for key,data in pages.items():
    if key in url:return json.dumps(data)
   raise IOError('offline')
  return get,calls
 def test_tmdb_adds_titles_release_span_and_the_other_films(self):
  get,calls=self.tmdb({'/movie/985939?':{'id':985939,'title':'Fall','original_title':'Fall','imdb_id':'tt15325794','release_date':'2022-08-11',
    'alternative_titles':{'titles':[{'title':'Caída'}]},'translations':{'translations':[{'data':{'title':'Падение'}}]},
    'release_dates':{'results':[{'iso_3166_1':'US','release_dates':[{'type':3,'release_date':'2022-08-12T00:00:00.000Z'},{'type':4,'release_date':'2023-01-10T00:00:00.000Z'}]}]}},
   '/search/movie?':{'results':[{'id':985939,'title':'Fall','release_date':'2022-08-11'},{'id':1,'title':'Fall','release_date':'2026-03-01'},{'id':2,'title':'Free Fall','release_date':'2014-01-01'}]}})
  with mock.patch.dict(sm._cache,clear=True),mock.patch.object(sm,'_cache_loaded',[1]),mock.patch.object(sm,'_save_cache',lambda:None):
   exp=sm.enrich(sm.expected('movie',['Fall'],2022,tmdb='985939'),key='k',get=get)
   self.assertTrue(exp['others']);self.assertIn('Caída',exp['titles']);self.assertIn('Падение',exp['titles'])
   self.assertEqual(sm.allowed_years(exp),{2022})          # a later digital release is no year-boundary span
   self.assertFalse(sm.check('Fall.1080p.WEB',exp)[0]);self.assertTrue(sm.check('Caida.2022.1080p',exp)[0])
   n=len(calls);sm.enrich(sm.expected('movie',['Fall'],2022,tmdb='985939'),key='k',get=get);self.assertEqual(len(calls),n)   # cached
   self.assertTrue(all('api_key=k' in c for c in calls));self.assertFalse(any('api_key' in k for k in sm._cache))
 def test_tmdb_release_spanning_new_year(self):
  get,_=self.tmdb({'/movie/7?':{'id':7,'title':'Portrait of a Lady on Fire','release_date':'2019-09-18','release_dates':{'results':[
   {'release_dates':[{'type':1,'release_date':'2019-05-19T00:00:00.000Z'}]},{'release_dates':[{'type':3,'release_date':'2020-02-14T00:00:00.000Z'}]}]}},
   '/search/movie?':{'results':[]}})
  with mock.patch.dict(sm._cache,clear=True),mock.patch.object(sm,'_cache_loaded',[1]),mock.patch.object(sm,'_save_cache',lambda:None):
   exp=sm.enrich(sm.expected('movie',['Portrait of a Lady on Fire'],2019,tmdb='7'),key='k',get=get)
  self.assertEqual(sm.allowed_years(exp),{2019,2020});self.assertIs(exp['others'],False)
 def test_tmdb_show_country_and_year(self):
  get,_=self.tmdb({'/tv/2316?':{'name':'The Office','original_name':'The Office','first_air_date':'2005-03-24','origin_country':['US'],'alternative_titles':{'results':[{'title':'The Office (US)'}]}}})
  with mock.patch.dict(sm._cache,clear=True),mock.patch.object(sm,'_cache_loaded',[1]),mock.patch.object(sm,'_save_cache',lambda:None):
   exp=sm.enrich(sm.expected('episode',['The Office'],season=2,episode=3,tmdb='2316'),key='k',get=get)
  self.assertEqual((exp['countries'],exp['show_year']),(['US'],2005));self.assertFalse(sm.check('The.Office.UK.S02E03',exp)[0])
 def test_offline_leaves_the_identity_as_it_was(self):
  with mock.patch.dict(sm._cache,clear=True),mock.patch.object(sm,'_cache_loaded',[1]):
   exp=sm.enrich(sm.expected('movie',['Fall'],2022),key='')
  self.assertEqual((exp['titles'],exp['others']),(['Fall'],None))
 def test_burst_hands_the_identity_to_the_version_page(self):
  props={};window=types.SimpleNamespace(setProperty=props.__setitem__,getProperty=lambda k:props.get(k,''))
  sm.publish(dict(FALL,_keys={'x'}),hidden=3,window=window,now=1000)
  exp=sm.published('Choose a stream Fall (2022)',window=window,now=1100);self.assertEqual((exp['year'],exp['revealed']),(2022,False))
  self.assertIsNone(sm.published('Choose a stream Inception',window=window,now=1100))
  self.assertIsNone(sm.published('Fall',window=window,now=1000+sm.FRESH+1))
 def test_watch_menu_details_as_identity(self):
  props={'Deck.Picker.Title':'Fall','Deck.Picker.Meta':'2022  |  107 min','Deck.Picker.Time':'1000'}
  window=types.SimpleNamespace(getProperty=lambda k:props.get(k,''))
  exp=sm.from_details('Elementum Fall',window=window,now=1010);self.assertEqual((exp['kind'],exp['year']),('movie',2022))
  props.update({'Deck.Picker.Title':'The Office','Deck.Picker.Meta':'S02E03  |  2005'})
  exp=sm.from_details('The Office S02E03',window=window,now=1010);self.assertEqual((exp['season'],exp['episode']),(2,3))

def entry(name,q='1080p',seeds=10,size='2.1 GB'):
 return '%s (%d / 0) [%s] WebDL H.264 - Torrentio\n%s\nicon.png'%(q,seeds,size,name)
GOOD=[entry('Fall.2022.1080p.WEBRip.x264',seeds=50),entry('Fall.2022.2160p.WEB-DL.x265','2160p',30,'9.2 GB'),entry('Fall.2022.720p.BluRay','720p',20,'1.1 GB')]
BAD=[entry('Fall.2026.1080p.WEB-DL.DDP5.1',seeds=90),entry('Free.Fall.2014.1080p.BluRay',seeds=5)]

class VersionPage(unittest.TestCase):
 def run_page(self,items,answers,exp=FALL,quality=None):
  seen=[]
  def source(title,rows,q,count,*a):seen.append({'rows':rows,'quality':q,'count':count});return answers.pop(0)
  with mock.patch.object(dp,'choose_source',source),mock.patch.object(dp,'choose_quality',quality or (lambda labels,*a:seen.append({'labels':labels}) or answers.pop(0))),\
       mock.patch.object(dp,'resume_wanted',lambda:None),mock.patch.object(dp,'remember',lambda *a:True),mock.patch.object(sm,'log',lambda m:None):
   return dp.run('Choose a stream Fall (2022)',items,expect=exp),seen
 def test_short_list_gets_our_page_with_only_this_title_and_a_hidden_row(self):
  items=[BAD[0]]+GOOD+[BAD[1]]          # 3 verified: a "short list" that used to go straight to Elementum's dialog
  choice,seen=self.run_page(items,[0])
  heads=[r['headline'] for r in seen[0]['rows']];self.assertEqual(len(heads),4);self.assertEqual(heads[-1],'2 hidden (wrong title/year)')
  self.assertEqual(choice,1)
  self.assertNotIn('Fall.2026',json.dumps(seen[0]['rows'][:3]))
 def test_the_hidden_row_reveals_them_with_the_reason(self):
  items=[BAD[0]]+GOOD+[BAD[1]]
  choice,seen=self.run_page(items,[3,0])
  self.assertEqual([r['badge'] for r in seen[1]['rows']],['WRONG YEAR','WRONG TITLE']);self.assertIn('Fall.2026',seen[1]['rows'][0]['tags'])
  self.assertEqual(choice,0)            # Elementum's index of the 2026 torrent, chosen knowingly
 def test_show_all_lists_only_verified_links_when_some_are_hidden(self):
  many=[entry('Fall.2022.1080p.%s.x264-G%d'%(src,n),seeds=60-n,size='%d.%d GB'%(n+1,n)) for n,src in enumerate(['WEBRip','BluRay','WEB-DL','HDTV','BRRip','DVDRip','REMUX'])]
  items=BAD+many
  choice,seen=self.run_page(items,[dp.TOP_N,1])       # one quality: the page, then its "Show all links" row
  self.assertEqual(seen[0]['rows'][dp.TOP_N]['headline'],'Show all links');self.assertEqual(seen[0]['rows'][-1]['headline'],'2 hidden (wrong title/year)')
  self.assertEqual(len(seen[1]['rows']),len(many)+1);self.assertEqual(seen[1]['quality'],'All verified links')
  self.assertEqual(choice,3)
 def test_show_all_from_the_quality_menu(self):
  items=GOOD*2+BAD
  choice,seen=self.run_page(items,[-1],quality=lambda labels,*a:len(labels)-1)
  self.assertEqual(choice,-1);self.assertEqual(len(seen[0]['rows']),6+1)
 def test_show_all_with_everything_verified_is_elementums_own_list(self):
  self.assertIsNone(self.run_page(GOOD*2,[],quality=lambda labels,*a:len(labels)-1)[0])
 def test_all_hidden_says_so_and_can_reveal(self):
  choice,seen=self.run_page(BAD,[0,1])
  self.assertEqual([r['headline'] for r in seen[0]['rows']],['2 hidden (wrong title/year)']);self.assertEqual(seen[0]['count'],'All 2 links hidden')
  self.assertEqual(choice,1)
  self.assertEqual(self.run_page(BAD,[-1])[0],-1)
  # Burst already asked "show them anyway?": straight to them.
  choice,seen=self.run_page(BAD,[0],exp=dict(FALL,revealed=True));self.assertEqual((choice,len(seen)),(0,1))
 def test_unknown_title_is_not_filtered_but_short_lists_still_get_the_page(self):
  with mock.patch.object(dp,'identity',lambda title,sm=None:None):
   choice,seen=self.run_page(GOOD+BAD,[4],exp=None)
  self.assertEqual((choice,len(seen[0]['rows'])),(4,5))
 def test_the_page_finds_source_match_beside_it_or_in_the_repository(self):
  self.assertTrue(hasattr(dp._matcher(),'check'))

class BurstHook(unittest.TestCase):
 def setUp(self):
  import build_customized_ipa as b
  self.b=b
 def fixture(self):
  """The four places BURST_PATCHES change in Burst 0.0.99's burst/burst.py, as a runnable file."""
  return (b'from kodi_six import xbmc, xbmcgui\n'
          b'provider_results = []\n\n'
          b'def search(payload, method="general"):\n'
          b'    global provider_results\n'
          b'    request_time = time.time()\n\n'
          b"    cookie_sync(payload['silent'])\n"
          b'    provider_results = []\n'
          b'    for provider, results in PROVIDERS:\n'
          b'        got_results(provider, results)\n'
          b'    filtered_results = apply_filters(provider_results)\n'
          b'    return filtered_results\n\n'
          b'def got_results(provider, results):\n'
          b'    definition = definitions[provider]\n'
          b'    definition = get_alias(definition, get_setting("%s_alias" % provider))\n\n'
          b'    # 0 "Resolution"\n'
          b'    provider_results.extend(results[:2])\n')
 def burst(self,providers,silent,yes=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/self.b.BURST/'burst').mkdir(parents=True);(root/self.b.BURST/'burst/burst.py').write_bytes(self.fixture())
   receipt=self.b.patch_burst(root);text=(root/self.b.BURST/'burst/burst.py').read_text()
   with self.assertRaises(AssertionError):self.b.patch_burst(root)   # the pinned source only, once
  self.assertEqual(text.count('# KODI-IOS-SOURCE-MATCH'),4);self.assertEqual(receipt[0]['path'],'addons/script.elementum.burst/burst/burst.py')
  notes,dialogs,props=[],[],{}
  xbmcgui=types.ModuleType('xbmcgui');xbmcgui.Dialog=lambda:types.SimpleNamespace(yesno=lambda h,m:dialogs.append(m) or yes)
  xbmcgui.Window=lambda n:types.SimpleNamespace(setProperty=props.__setitem__,getProperty=lambda k:props.get(k,''))
  xbmcvfs=types.ModuleType('xbmcvfs');xbmcvfs.translatePath=lambda p:str(LIB)
  six=types.ModuleType('kodi_six');six.xbmc=types.ModuleType('xbmc');six.xbmcgui=xbmcgui
  log=types.SimpleNamespace(info=lambda m:None,warning=lambda m:notes.append(('warning',m)),debug=lambda m:None)
  ns={'time':__import__('time'),'Thread':__import__('threading').Thread,'cookie_sync':lambda s:None,'apply_filters':lambda r:list(r),'cleanup_results':lambda r:list(r),
      'definitions':{p:{} for p,_ in providers},'get_alias':lambda d,a:d,'get_setting':lambda k:'','PROVIDERS':providers,'PY3':True,
      'log':log,'notify':lambda m,i=None:notes.append(('notify',m)),'ADDON_ICON':'icon'}
  with mock.patch.dict(sys.modules,{'kodi_six':six,'xbmcgui':xbmcgui,'xbmcvfs':xbmcvfs,'source_match':sm}),mock.patch.object(sm,'log',lambda m:None),\
       mock.patch.object(sm,'enrich',lambda exp,**k:dict(exp,others=True,enriched=True)):
   exec(compile(text,'burst.py','exec'),ns)
   out=ns['search']({'title':'Fall','year':2022,'titles':{'source':'Fall'},'silent':silent},'movie')
  return out,notes,dialogs,props
 def test_other_titles_never_reach_elementum_and_cannot_crowd_out_this_one(self):
  # The 2026 film first in the provider's answer: without the check, Burst's per-provider cut would keep only it.
  out,notes,dialogs,props=self.burst([('yts',[{'name':'Fall.2026.1080p'},{'name':'Fall.2026.2160p'},{'name':'Fall.2022.1080p'}]),
   ('tpb',[{'name':'Free.Fall.2014'},{'name':'Fall.2022.720p'}])],silent=True)
  self.assertEqual([r['name'] for r in out],['Fall.2022.1080p','Fall.2022.720p']);self.assertEqual((notes,dialogs),([],[]))
  self.assertEqual(json.loads(props[sm.PROPERTY])['hidden'],3)
 def test_silent_auto_pick_with_only_other_titles_gets_nothing_and_a_notice(self):
  out,notes,dialogs,_=self.burst([('yts',[{'name':'Fall.2026.1080p'}])],silent=True)
  self.assertEqual((out,dialogs),([],[]));self.assertEqual(notes[0][0],'notify');self.assertIn('No source is Fall (2022): 1 hidden (wrong year 1)',notes[0][1])
 def test_interactive_search_asks_before_showing_only_other_titles(self):
  out,notes,dialogs,props=self.burst([('yts',[{'name':'Fall.2026.1080p'}])],silent=False,yes=True)
  self.assertEqual([r['name'] for r in out],['Fall.2026.1080p']);self.assertEqual(len(dialogs),1);self.assertTrue(json.loads(props[sm.PROPERTY])['revealed'])
  out,notes,dialogs,_=self.burst([('yts',[{'name':'Fall.2026.1080p'}])],silent=False,yes=False);self.assertEqual(out,[])
 def test_the_build_ships_source_match_with_the_page(self):
  self.assertEqual(self.b.SOURCE_MATCH,LIB/'source_match.py')

class UmbrellaRoute(unittest.TestCase):
 def item(self,name,source='TORRENT CACHED'):
  return {'quality':'1080p','name':name,'size':2.0,'info':'HEVC','debrid':'RD','provider':'torrentio','source':source,'seeders':0,'url':'u'}
 def test_identity_from_meta_reaches_the_page(self):
  got={}
  deck=types.SimpleNamespace(run=lambda title,labels,expect=None:got.update(title=title,expect=expect) or 0)
  results=[self.item('Fall.2022.1080p'),self.item('Fall.2026.1080p')]
  with mock.patch.object(up,'share',lambda meta:None),mock.patch.object(sm,'enrich',lambda exp:exp):
   action,item=up.run(results,{'title':'Fall','year':'2022'},deck,lambda:types.SimpleNamespace(setProperty=lambda k,v:None),sm=sm)
  self.assertEqual(action,'play_Item');self.assertEqual(got['expect']['year'],2022)
 def test_umbrellas_own_list_keeps_only_this_title(self):
  results=[self.item('Fall.2022.1080p'),self.item('Fall.2026.1080p','TORRENT UNCACHED'),self.item('Fall.2022.720p','TORRENT UNCACHED')]
  deck=types.SimpleNamespace(run=lambda title,labels,expect=None:None)
  with mock.patch.object(up,'share',lambda meta:None),mock.patch.object(sm,'enrich',lambda exp:exp),mock.patch.object(sm,'log',lambda m:None):
   self.assertIsNone(up.run(results,{'title':'Fall','year':2022},deck,sm=sm))
  self.assertEqual([r['name'] for r in results],['Fall.2022.1080p','Fall.2022.720p'])
 def test_all_other_titles_in_umbrellas_list_asks_first(self):
  results=[self.item('Fall.2026.1080p','TORRENT UNCACHED')];asked=[]
  with mock.patch.object(sm,'enrich',lambda exp:exp),mock.patch.object(sm,'log',lambda m:None):
   self.assertEqual(up.run(results,{'title':'Fall','year':2022},sm=sm,ask=lambda m:asked.append(m) or False),(None,''))
   self.assertIsNone(up.run(results,{'title':'Fall','year':2022},sm=sm,ask=lambda m:True))
  self.assertIn('All 1 sources look like a different title (wrong year 1)',asked[0]);self.assertEqual(len(results),1)
 def test_the_real_page_filters_umbrella_sources(self):
  with mock.patch.dict(sys.modules,{'xbmc':types.ModuleType('xbmc'),'xbmcgui':types.ModuleType('xbmcgui')}):
   for name in ('kodi_six','elementum','elementum.dialog','elementum.addon'):sys.modules.pop(name,None)
   deck=up.load(str(ROOT/'migration/deck-picker/deck_picker.py'),'/addon')
  rows=[]
  results=[self.item('Fall.2026.2160p'),self.item('Fall.2022.1080p'),self.item('Free.Fall.2014.1080p')]
  with mock.patch.object(up,'share',lambda meta:None),mock.patch.object(sm,'enrich',lambda exp:exp),mock.patch.object(sm,'log',lambda m:None),\
       mock.patch.object(deck,'choose_source',lambda t,r,q,c,*a:rows.append(r) or 0),mock.patch.object(deck,'resume_wanted',lambda:None),mock.patch.object(deck,'remember',lambda *a:True):
   action,item=up.run(results,{'title':'Fall','year':2022},deck,lambda:FakeItem(),sm=sm)
  self.assertEqual(json.loads(item.props['umbrella.source_dict'])[0]['name'],'Fall.2022.1080p')
  self.assertEqual(rows[0][-1]['headline'],'2 hidden (wrong title/year)')

class FakeItem:
 def __init__(self):self.props={}
 def setProperty(self,k,v):self.props[k]=v

class WhatTheTorrentReallyIs(unittest.TestCase):
 """Owner (build 156): Fall (2022) in 4K, "the best one", downloaded Fall.2.Deadpoint.2026. The site's label passed the
 source check; the torrent's real name, known only once Elementum has its metadata, did not."""
 def setUp(self):
  sys.modules['source_match']=sm
  self.g=load('source_guard_t',LIB/'source_guard.py');self.now=[1000.0];self.stopped=[];self.notes=[]
  self.guard=self.g.Guard(self.stopped.append,lambda t,x:self.notes.append((t,x)),clock=lambda:self.now[0])
  self.found=(sm.expected('movie',titles=['Fall'],year=2022),995.0)
 def add(self,name,tid='new'):return [{'id':'old','name':'Something.Else.2019.mkv'},{'id':tid,'name':name}]
 def test_the_wrong_film_is_stopped_once_its_real_name_is_known(self):
  self.guard.tick([{'id':'old','name':'Something.Else.2019.mkv'}],self.found)   # what was there before: never judged
  self.guard.tick(self.add('Fall 2022 2160p'),self.found)                         # the site's label: fine
  self.assertEqual(self.stopped,[])
  self.now[0]+=8
  self.guard.tick(self.add('Fall.2.Deadpoint.2026.2160p.4K.WEB.x265.10bit.AAC5.1-[YTS.GG - YTS.BZ].mkv'),self.found)
  self.assertEqual(self.stopped,['new']);self.assertIn('is not Fall (2022) (wrong title)',self.notes[0][1])
  self.guard.tick(self.add('Fall.2.Deadpoint.2026.2160p.mkv'),self.found);self.assertEqual(self.stopped,['new'])   # once
 def test_the_right_film_and_unclear_names_are_left_alone(self):
  self.guard.tick([{'id':'old','name':'Something.Else.2019.mkv'}],self.found)
  for name in ('Fall.2022.2160p.4K.WEB.x265.10bit.AAC5.1-[YTS.MX].mkv','Fall 2160p WEB','a'*40):
   self.guard.tick(self.add(name),self.found)
  self.assertEqual(self.stopped,[])
 def test_wrong_year_is_stopped(self):
  self.guard.tick([{'id':'old','name':'Something.Else.2019.mkv'}],self.found)
  self.guard.tick(self.add('Fall.2026.1080p.WEB.mkv'),self.found);self.assertEqual(self.stopped,['new'])
 def test_not_after_choosing_a_hidden_source_nor_for_an_old_search(self):
  class W:
   def __init__(self,data):self.data=data
   def getProperty(self,key):return json.dumps(self.data) if key==sm.PROPERTY else ''
  self.assertIsNone(self.g.identity(W({'exp':{'titles':['Fall']},'time':1,'revealed':True})))
  self.assertEqual(self.g.identity(W({'exp':{'titles':['Fall']},'time':5})),({'titles':['Fall']},5.0))
  self.guard.tick([{'id':'old','name':'x'}],self.found);self.now[0]=995+self.g.FRESH+60
  self.guard.tick(self.add('Fall.2026.1080p.WEB.mkv'),self.found);self.assertEqual(self.stopped,[])   # search too old
 def test_a_torrent_started_before_the_search_is_not_judged_by_it(self):
  self.guard.tick([{'id':'old','name':'x'}],self.found)
  self.guard.tick(self.add('Fall.2026.1080p.WEB.mkv'),(self.found[0],2000.0));self.assertEqual(self.stopped,[])
 def test_each_torrent_is_judged_by_the_search_it_came_from(self):
  ep=lambda n:(sm.expected('episode',titles=['Lanterns'],season=1,episode=n),self.now[0])
  self.guard.tick([],ep(1))
  self.guard.tick([{'id':'e1','name':'Lanterns S01E01 label'}],ep(1))   # episode 1 appears during its own search
  self.now[0]+=4
  ep3=ep(3)                                                             # then episode 3 is searched
  self.guard.tick([{'id':'e1','name':'Lanterns.S01E01.2160p.mkv'}],ep3)
  self.assertEqual(self.stopped,[])
  self.guard.tick([{'id':'e1','name':'Lanterns.S01E01.2160p.mkv'},{'id':'x','name':'Other.Show.S01E03.mkv'}],ep3)
  self.assertEqual(self.stopped,['x'])                                   # another show is still stopped
 def test_service_runs_the_guard(self):
  service=(ROOT/'migration/bundled-bootstrap/service.py').read_text()
  self.assertIn('target=source_guard.run,args=(window,notices.torrent_list,driveupload.remove_torrent,',service)

class SeasonCoverage(unittest.TestCase):
 """Owner (build 205): "i pressed full season" for Lanterns season 1 and got S01E01 alone (an 8.4 GB 4K episode):
 a season search lists single episodes too. The version page lists full seasons first and says which is which."""
 exp=sm.expected('season',['Lanterns'],season=1)
 def test_packs_and_single_episodes(self):
  c=lambda n:sm.coverage(n,self.exp)
  self.assertEqual(c('Lanterns.S01.2160p.WEB-DL.DDP5.1.HEVC'),'')
  self.assertEqual(c('Lanterns Season 1 Complete 1080p'),'')
  self.assertEqual(c('Lanterns.S01E01.2160p.HMAX.WEB-DL.DV.HDR.HEVC'),'Episode 1 only')
  self.assertEqual(c('Lanterns.S01E01-E03.1080p'),'Episodes 1-3 only')
  self.assertIsNone(sm.coverage('Lanterns.S01E01.1080p',sm.expected('episode',['Lanterns'],season=1,episode=1)))
 def test_the_page_lists_full_seasons_first_and_labels_them(self):
  base=lambda idx,name,size,cover:dict(idx=idx,quality='4k',seeds=90 if idx==0 else 20,peers=0,size=size,tags_text='',name=name,providers=['x'],icon='',multi=False,coverage=cover)
  items=[base(0,'Lanterns.S01E01.2160p.WEB-DL.HEVC',8.4,'Episode 1 only'),base(1,'Lanterns.S01.2160p.WEB-DL.HEVC',40.0,'')]
  shown=dp.pick([dict(i) for i in items])
  self.assertEqual([i['idx'] for i in shown],[1,0])
  rows=dp.build_rows(shown)
  self.assertEqual([r['badge'] for r in rows],['FULL SEASON','EPISODE 1 ONLY'])

if __name__=='__main__':unittest.main()
