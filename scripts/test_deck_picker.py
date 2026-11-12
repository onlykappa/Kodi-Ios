import json
import importlib.util,sys,types,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('deck_picker',ROOT/'migration/deck-picker/deck_picker.py')
dp=importlib.util.module_from_spec(spec);spec.loader.exec_module(dp)
# The streams Elementum listed on the phone for Orange Is the New Black S01E01 (owner's screenshot), in its format.
ITEMS=['[B][COLOR FF5AB3FF]1080p[/COLOR][/B] (75 / 0) [B][1.71 GB][/B] Blu-Ray H.265 AC3 - [B]Torrentio[/B]\nIs the New Black (2013) Season 1-7 S01-S07 (1080p BluRay x265 HEVC 10bit AAC 5.1 Silence) [QxR] Season 1/Orange Is the New Black (2013) - S01E01.mkv\nicon.png',
 '1080p (39 / 0) [347.48 MB] WebDL H.265 AC3 - Torrentio\n[RE-UP] Orange Is The New Black (2013) Season 01 S01 (1080p WEBRip x265 HEVC AAC 5.1 Joy) [UTR] Orange Is The New Black S01E01.mkv\nicon.png',
 '1080p (22 / 0) [1.3 GB] Blu-Ray H.265 - Torrentio\nOrange.Is.The.New.Black.S01-S07.Complete.Series.1080p.Bluray.x265-HiQVE/Orange.Is.The.New.Black.S01E01.mkv\nicon.png',
 '1080p (17 / 0) [3.97 GB] Blu-Ray H.264 - Torrentio\nOrange.is.the.New.Black.S01.1080p.BluRay.x264-ROVERS[rartv] orange.is.the.new.black.s01e01.1080p.bluray.x264-rovers.mkv\nicon.png',
 '1080p (9 / 0) [1.59 GB] Blu-Ray H.265 - Torrentio\nOrange.Is.the.New.Black.S01.1080p.BluRay.x265-YAWNiX Orange.Is.the.New.Black.S01E01.1080p.BluRay.x265-YAWNiX.mkv\nicon.png',
 '1080p (6 / 0) [995.3 MB] WebDL H.264 AC3 - Torrentio\n[moon] Orange is the New Black - Season 1 1080p WEBRip x264 AC3 MultiSubs E01 I Wasn\'t Ready.mp4\nicon.png',
 '1080p (6 / 0) [1.82 GB] Blu-Ray H.264 - Torrentio\nOrange.is.the.New.Black.S01.Season.1.Complete.1080p.BluRay.x264-maximersk [mrsktv] Orange.Is.The.New.Black.S01E01.1080p.BluRa.mkv\nicon.png',
 '1080p (7 / 0) [1.49 GB] H.264 AC3 - Torrentio\nOrange Is The New Black - Season 1 to 6 - Mp4 x264 AC3 1080p Season 1/Orange Is The New Black S01E01.mp4\nicon.png',
 '720p (7 / 0) [278.58 MB] Blu-Ray H.265 AC3 - Torrentio\nOrange Is the New Black S01 Complete 720p HEVC [Hindi 5.1 English] BluRay Dual-Audio x265 - KatmovieHD Orange.is.the.New.Black.S0.mkv\nicon.png']

class DeckPicker(unittest.TestCase):
 def test_reads_every_stream_from_the_phone(self):
  parsed=dp.parse_all(ITEMS);self.assertEqual(len(parsed),len(ITEMS))
  self.assertEqual((parsed[0]['quality'],parsed[0]['seeds'],round(parsed[0]['size'],2),parsed[0]['providers']),('1080p',75,1.71,['Torrentio']))
 def test_quality_first_then_five_best_and_the_choice_maps_back(self):
  seen={}
  def quality(labels,*a):seen['qualities']=labels;return 0
  def source(title,rows,quality,count):seen['rows']=rows;seen['quality']=quality;return 1
  with mock.patch.object(dp,'choose_quality',quality),mock.patch.object(dp,'choose_source',source):
   choice=dp.run('Orange Is the New Black S01E01',ITEMS)
  self.assertIn('1080p Full HD',seen['qualities'][0]);self.assertTrue(seen['qualities'][-1].startswith('Show all 9'))
  self.assertEqual(len(seen['rows']),dp.TOP_N+1)
  shown=dp.pick(dp.group_by_quality(dp.parse_all(ITEMS))[1]['1080p'],dp.TOP_N)
  self.assertEqual(choice,shown[1]['idx']);self.assertTrue(0<=choice<len(ITEMS))
 def test_cancel_and_show_all_fall_back_safely(self):
  with mock.patch.object(dp,'choose_quality',lambda labels,*a:-1):self.assertEqual(dp.run('t',ITEMS),-1)
  with mock.patch.object(dp,'choose_quality',lambda labels,*a:len(labels)-1):self.assertIsNone(dp.run('t',ITEMS))
  self.assertIsNone(dp.run('t',['not a torrent line']*10))
  # Kodi-iOS: a short list gets the page too (its links are checked against the title: source_match.py).
  seen=[]
  with mock.patch.object(dp,'choose_source',lambda title,rows,q,c,*a:seen.append(rows) or 2):self.assertEqual(dp.run('t',ITEMS[:3]),2)
  self.assertEqual(len(seen[0]),3)

class WatchMenuDetails(unittest.TestCase):
 def test_details_left_for_the_picker(self):
  spec=importlib.util.spec_from_file_location('watch',ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py')
  watch=importlib.util.module_from_spec(spec);spec.loader.exec_module(watch)
  props={};window=types.SimpleNamespace(setProperty=props.__setitem__)
  player=types.SimpleNamespace(tmdb_type='tv',details=types.SimpleNamespace(
   infolabels={'tvshowtitle':'Orange Is the New Black','season':1,'episode':1,'year':2013,'duration':3540,'plot':'Piper goes to prison.'},
   art={'tvshow.poster':'poster.jpg','fanart':'fan.jpg'}))
  watch.share_details(player,window)
  self.assertEqual(props['Deck.Picker.Title'],'Orange Is the New Black');self.assertEqual(props['Deck.Picker.Meta'],'S01E01  |  2013  |  59 min')
  self.assertEqual((props['Deck.Picker.Poster'],props['Deck.Picker.Fanart'],props['Deck.Picker.Plot']),('poster.jpg','fan.jpg','Piper goes to prison.'))

UMB=ROOT/'migration/bundled-bootstrap/resources/lib'
uspec=importlib.util.spec_from_file_location('umbrella_picker',UMB/'umbrella_picker.py')
up=importlib.util.module_from_spec(uspec);uspec.loader.exec_module(up)
def source(q,name,size,info,source='TORRENT UNCHECKED',debrid='AllDebrid'):
 return {'quality':q,'name':name,'size':size,'info':info,'debrid':debrid,'provider':'torrentio','source':source,'seeders':0,'url':'u'}
UMBRELLA=[source('4K','Scary.Movie.2026.2160p.UHD.Blu-ray.REMUX.DV.HDR.HEVC.TrueHD.Atmos.7.1',48.0,'DV | HDR | HEVC | REMUX | ATMOS | 48.0 GB'),
 source('4K','Scary.Movie.2026.2160p.BluRay.x265.10bit.HDR.DDP5.1',47.0,'HDR | HEVC | 10BIT | 47.02 GB'),
 source('4K','Scary.Movie.2026.2160p.UNCACHED',30.0,'30 GB','TORRENT UNCACHED'),
 source('4K','Scary.Movie.2026.2160p.WEB-DL.DV.H.265',18.05,'DV | HEVC | WEB-DL | 18.05 GB'),
 source('4K','Scary.Movie.2026.2160p.WEBRip.x265',9.4,'HEVC | WEBRIP | 9.4 GB'),
 source('4K','Scary.Movie.2026.2160p.AMZN.WEB-DL.H.265',16.2,'HEVC | WEB-DL | 16.2 GB'),
 source('1080p','Scary.Movie.2026.1080p.BluRay.x264',14.8,'AVC | BLURAY | 14.8 GB'),
 source('CAM','Scary.Movie.2026.CAM.x264',1.0,'CAM | 1.0 GB')]

class FakeItem:
 def __init__(self):self.props={}
 def setProperty(self,k,v):self.props[k]=v
 def getProperty(self,k):return self.props.get(k,'')

class UmbrellaPage(unittest.TestCase):
 def deck(self):
  with mock.patch.dict(sys.modules,{'xbmc':types.ModuleType('xbmc'),'xbmcgui':types.ModuleType('xbmcgui')}):
   for name in ('kodi_six','elementum','elementum.dialog','elementum.addon'):sys.modules.pop(name,None)
   return up.load(str(ROOT/'migration/deck-picker/deck_picker.py'),'/addon')
 def test_umbrella_sources_read_as_deck_entries(self):
  deck=self.deck();parsed=[deck.parse_item(up.label(i),n) for n,i in enumerate(UMBRELLA)]
  self.assertTrue(all(parsed))
  self.assertEqual([p['quality'] for p in parsed],['4k','4k','4k','4k','4k','4k','1080p','sd'])
  self.assertEqual(deck.source_type(parsed[0]),'Blu-ray Remux');self.assertTrue(deck.is_bad(parsed[7]))
  self.assertIn('AllDebrid',parsed[0]['providers']);self.assertAlmostEqual(parsed[1]['size'],47.0)
  # No seed counts for debrid links: size and where it comes from.
  self.assertEqual(deck.meta_text(parsed[0]),'48.00 GB  \u2022  AllDebrid, Torrentio, unchecked')
  labels=deck.quality_menu_labels(*deck.group_by_quality(parsed))
  self.assertEqual([l.split('\x1f')[0] for l in labels[:2]],['[B]4K Ultra HD[/B]','[B]1080p Full HD[/B]'])
  # the second line (split off by choose_quality): how many versions and the size they start from
  self.assertTrue(labels[0].split('\x1f')[1].startswith('6 versions \u00b7 ') and ' \u00b7 from ' in labels[0]);self.assertTrue(labels[1].split('\x1f')[1].startswith('1 version \u00b7 from '))
  self.assertFalse(any('top pick' in l or 'seeds' in l for l in labels))
  self.assertEqual(sys.modules.get('elementum'),None)  # stand-ins only lived inside load()
 def test_run_returns_what_umbrellas_window_returns(self):
  deck=types.SimpleNamespace(run=lambda title,labels,expect=None,mode=None:1)
  with mock.patch.object(up,'share',lambda meta:None):
   action,item=up.run(UMBRELLA,{'title':'Scary Movie'},deck,FakeItem)
   self.assertEqual(action,'play_Item')
   # The uncached torrent is left to Umbrella's own list, so the second playable entry is UMBRELLA[1].
   self.assertEqual(json.loads(item.getProperty('umbrella.source_dict')),[UMBRELLA[1]])
   self.assertEqual(up.run(UMBRELLA,{},types.SimpleNamespace(run=lambda t,l,expect=None,mode=None:-1),FakeItem),(None,''))
   self.assertIsNone(up.run(UMBRELLA,{},types.SimpleNamespace(run=lambda t,l,expect=None,mode=None:None),FakeItem))
   self.assertIsNone(up.run([UMBRELLA[2]],{},deck,FakeItem))
 def test_hook_goes_into_umbrellas_window_once(self):
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'source_results.py'
   path.write_text('class SourceResultsXML:\n\tdef run(self):\n\t\tself.doModal()\n\t\tself.clearProperties()\n\t\treturn self.selected\n')
   self.assertTrue(up.umbrella_hook(str(path)));self.assertFalse(up.umbrella_hook(str(path)))
   text=path.read_text();compile(text,'source_results.py','exec')
   self.assertEqual(text.count(up.HOOK_MARK),1);self.assertIn('_kpick.run(self.results, self.meta)',text)
   other=Path(tmp)/'other.py';other.write_text('def run():pass\n');self.assertFalse(up.umbrella_hook(str(other)))
   # A phone with the r1 hook (Umbrella's own list opened after the Deck page) gets the r2 hook in its place.
   old=Path(tmp)/'r1.py';old.write_text('class W:\n'+up.HOOK_R1+'\t\treturn self.selected\n')
   self.assertTrue(up.umbrella_hook(str(old)));text=old.read_text()
   self.assertIn(up.HOOK,text);self.assertNotIn('clearProperties',text);self.assertFalse(up.umbrella_hook(str(old)))
   # The r2 hook returns the Deck choice without touching Umbrella's (never shown) window.
   class Win:
    results=[];meta={};shown=0
    def doModal(self):Win.shown+=1
   ns={};exec('import sys,types\nclass W:\n'+up.HOOK.replace('\t\t\timport sys as _ksys, xbmcvfs as _kvfs\n','\t\t\timport sys as _ksys\n').replace("\t\t\t_klib = _kvfs.translatePath('special://xbmc/addons/service.kodi.ios.bootstrap/resources/lib')\n\t\t\tif _klib not in _ksys.path: _ksys.path.insert(0, _klib)\n",''),ns)
   fake=types.ModuleType('umbrella_picker');fake.run=lambda results,meta:('play_Item','x')
   with mock.patch.dict(sys.modules,{'umbrella_picker':fake}):
    w=Win();self.assertEqual(ns['W'].run(w),('play_Item','x'));self.assertEqual(Win.shown,0)
   self.assertFalse(up.umbrella_hook(str(Path(tmp)/'missing.py')))

 def test_continue_watching_plays_the_same_version(self):
  import json,time
  home=mock.Mock();home.getProperty.return_value=json.dumps({'name':ITEMS and dp.parse_all(ITEMS)[3]['name'],'quality':'1080p','time':time.time()})
  self.assertEqual(dp.find_same(dp.parse_all(ITEMS),dp.resume_wanted(home))['idx'],3);home.clearProperty.assert_called_with(dp.RESUME_PROPERTY)
  stale=mock.Mock();stale.getProperty.return_value=json.dumps({'name':'x','time':time.time()-dp.RESUME_FRESH-5});self.assertIsNone(dp.resume_wanted(stale))
  wanted={'name':dp.parse_all(ITEMS)[3]['name'],'quality':'1080p','time':time.time()}
  with mock.patch.object(dp,'resume_wanted',lambda:wanted),mock.patch.object(dp,'choose_source',side_effect=AssertionError('asked')):
   self.assertEqual(dp.run('Orange Is the New Black S01E01',ITEMS),3)
  # Gone from the list: the normal page.
  with mock.patch.object(dp,'resume_wanted',lambda:{'name':'Not.There','time':time.time()}),mock.patch.object(dp,'choose_quality',lambda labels,*a:-1):
   self.assertEqual(dp.run('Orange Is the New Black S01E01',ITEMS),-1)
 def test_a_pick_is_remembered_for_the_title_just_started(self):
  import json,tempfile,time,os
  with tempfile.TemporaryDirectory() as tmp:
   path=os.path.join(tmp,'continue.json')
   json.dump({'current':'episode:1:1:1','items':{'episode:1:1:1':{'title':'I Wasn\'t Ready','tvshowtitle':'Orange Is the New Black','played':time.time()}}},open(path,'w'))
   item=dp.parse_all(ITEMS)[2]
   self.assertTrue(dp.remember(item,'Orange Is the New Black S01E01',path))
   saved=json.load(open(path))['items']['episode:1:1:1']['version'];self.assertEqual((saved['name'],saved['quality']),(item['name'],'1080p'))
   self.assertFalse(dp.remember(item,'Some Other Show S02E03',path))   # another title: left alone
   self.assertFalse(dp.remember(item,'Orange Is the New Black S01E01',path,now=time.time()+3600))   # too long ago
 def test_disc_copies_and_huge_files_go_last_with_a_warning(self):
  items=['2160p (40 / 0) [72.4 GB] Blu-Ray H.265 - Torrentio\nThe.Dark.Knight.2008.COMPLETE.UHD.BLURAY-GROUP\nicon.png',
         '2160p (30 / 0) [55.0 GB] Remux H.265 - Torrentio\nThe.Dark.Knight.2008.2160p.UHD.BluRay.REMUX-GROUP\nicon.png',
         '2160p (20 / 0) [18.2 GB] WebDL H.265 - Torrentio\nThe.Dark.Knight.2008.2160p.WEB-DL.x265-GROUP\nicon.png',
         '2160p (10 / 0) [9.1 GB] Blu-Ray H.265 - Torrentio\nThe.Dark.Knight.2008.2160p.BluRay.x265-GROUP\nicon.png']
  parsed=dp.parse_all(items)
  self.assertEqual([dp.too_heavy(p) for p in parsed],[True,True,False,False])
  shown=dp.pick(parsed,5);self.assertEqual([p['idx'] for p in shown][:2],[2,3])
  rows=dp.build_rows(shown);self.assertEqual([r['badge'] for r in rows][2:],['MAY STUTTER','MAY STUTTER']);self.assertNotEqual(rows[0]['badge'],'MAY STUTTER')
AV1_ITEMS=['2160p (90 / 0) [8.9 GB] WebDL AV1 - Torrentio\nInception.2010.2160p.WEB-DL.AV1.10bit.HDR.mkv\nicon.png',
 '2160p (40 / 0) [14.2 GB] Blu-Ray H.265 - Torrentio\nInception.2010.2160p.BluRay.x265.10bit.HDR.mkv\nicon.png',
 '1080p (60 / 0) [2.1 GB] Blu-Ray H.264 - Torrentio\nInception.2010.1080p.BluRay.x264.mkv\nicon.png',
 '2160p (30 / 0) [12.0 GB] WebDL H.265 - Torrentio\nInception.2010.2160p.WEB-DL.HEVC.HDR10.mkv\nicon.png']

class SlowToPrepare(unittest.TestCase):
 """Owner (build 184): AV1 movies took hours to prepare; "find the same quality in a different source that won't
 require conversion"."""
 def test_av1_goes_last_and_says_so(self):
  q=dp.group_by_quality(dp.parse_all(AV1_ITEMS))[1]['4k']
  shown=dp.pick(q,dp.TOP_N)
  self.assertEqual([dp.codec(i) for i in shown],['H.265','H.265','AV1'])
  rows=dp.build_rows(shown);self.assertEqual(rows[-1]['badge'],'AV1 \u00b7 SLOW TO PREPARE')
 def test_without_converting_same_quality_only(self):
  seen={}
  def source(title,rows,quality,count):seen['rows']=rows;seen['quality']=quality;return 0
  with mock.patch.object(dp,'avoid_request',lambda:'4k'),mock.patch.object(dp,'choose_source',source):
   choice=dp.run('Inception 2010',AV1_ITEMS,expect={})
  self.assertEqual(len(seen['rows']),2);self.assertTrue(all(r['badge']=='NO CONVERSION NEEDED' for r in seen['rows']))
  self.assertEqual(seen['quality'],dp.quality_label('4k'));self.assertNotEqual(choice,0)   # never the AV1 link
  self.assertIn(choice,(1,3))
 def test_request_expires(self):
  self.assertEqual(dp.avoid_request(now=1000,read=lambda:'4k|900'),'4k')
  self.assertIsNone(dp.avoid_request(now=1000+dp.AVOID_FOR+100,read=lambda:'4k|900'))
  self.assertIsNone(dp.avoid_request(now=1000,read=lambda:''))

class TvReady(unittest.TestCase):
 """Roadmap 1B.1: 10-bit H.264 (Hi10P) is converted for AirPlay; say so on the version row."""
 def item(self,name,tags=''):return {'name':name,'tags_text':tags,'providers':[],'quality':'1080p','seeds':5,'size':1.0,'icon':'','idx':0}
 def test_only_ten_bit_h264(self):
  self.assertTrue(dp.converts_for_tv(self.item('Show.S01E01.1080p.WEB.x264.10bit-GRP')))
  self.assertTrue(dp.converts_for_tv(self.item('Show S01E01 [1080p Hi10P AVC]')))
  self.assertFalse(dp.converts_for_tv(self.item('Show.S01E01.1080p.WEB.x264-GRP')))
  self.assertFalse(dp.converts_for_tv(self.item('Show.S01E01.1080p.WEB.x265.10bit-GRP')))
 def test_row_badge(self):
  rows=dp.build_rows([self.item('Show.S01E01.1080p.WEB.x264-GRP'),self.item('Show.S01E01.1080p.x264.10bit-GRP')])
  self.assertEqual([r['badge'] for r in rows],['BEST MATCH','10-BIT \u00b7 SLOW ON AIRPLAY'])

class AllLinks(unittest.TestCase):
    def test_sorts_keep_the_hidden_row_last(self):
        rows=[{'size':8.4,'seeds':188},{'size':58,'seeds':214},{'size':2.6,'seeds':120},{'headline':'Show hidden'}]
        self.assertEqual(dp.sort_order(rows,u'best'),[0,1,2,3])
        self.assertEqual(dp.sort_order(rows,u'small'),[2,0,1,3])
        self.assertEqual(dp.sort_order(rows,u'seeds'),[1,0,2,3])
    def test_rows_carry_pills_size_and_seeds(self):
        r=dp.build_rows(dp.parse_all(ITEMS[:1]))[0]
        self.assertLessEqual(len(r['pills']),4);self.assertIn('size',r);self.assertIn('seeds',r)


class NoStutter(unittest.TestCase):
    def test_ten_bit_h264_goes_after_versions_that_play_as_they_are(self):
        raw=['1080p (500 / 0) [4.0 GB] WebDL H.264 - Torrentio\nShow.S01.1080p.WEB.10bit.x264-A.mkv\nicon.png',
             '1080p (50 / 0) [3.0 GB] WebDL H.265 - Torrentio\nShow.S01.1080p.WEB.x265-B.mkv\nicon.png']
        self.assertTrue(dp.converts_for_tv(dp.parse_all(raw)[0]))
        try:
            dp.MODE[0]=u'stream'   # Umbrella: live playback, nothing AirPlay must convert first
            self.assertEqual([r['idx'] for r in dp.pick(dp.parse_all(raw),top_n=5)],[1,0])
            dp.MODE[0]=u'download' # Elementum: prepared once on Drive, Elementum's order (best seeded first)
            self.assertEqual([r['idx'] for r in dp.pick(dp.parse_all(raw),top_n=5)],[0,1])
        finally:
            dp.MODE[0]=u'download'
    def test_dolby_vision_without_hdr10_counts_as_live_conversion(self):
        dv=dp.parse_all(['2160p (90 / 0) [12 GB] WebDL H.265 - Torrentio\nShow.S01E01.2160p.WEB-DL.DV.HEVC.mkv\nicon.png',
                         '2160p (90 / 0) [12 GB] WebDL H.265 - Torrentio\nShow.S01E01.2160p.WEB-DL.DV.HDR10.HEVC.mkv\nicon.png'])
        self.assertEqual([dp.dv_only(i) for i in dv],[True,False])


class NothingFoundState(unittest.TestCase):
 def test_all_links_sets_and_clears_the_empty_state_and_try_again_closes(self):
  # Board 09: the page's empty group shows on deck.empty and Try Again is id 32512 (portrait.deck_page).
  code=(ROOT/'migration/deck-picker/deck_picker.py').read_text()
  self.assertIn("self.setProperty('deck.empty', u'' if self.rows or self.mode != u'all' else",code)
  self.assertIn('elif controlId == 32512:',code)
  self.assertIn("SetProperty(deck.retry,true)",(ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py').read_text())

class SeasonBuildPicks(unittest.TestCase):
 def test_whole_series_pack_comes_after_a_single_episode(self):
  # Owner log 15e6cbc4: episode 1 was taken from "Naruto Shippuden (001-500) [Complete Series ...]".
  pack=dp.parse_item('1080p (232 / 0) [262.85 MB] WebDL H.264 - Torrentio\nNaruto Shippuden (001-500) [Complete Series + Movies (1080p)] (Dual Audio)/Naruto Shippuden Episode 001 Homecoming.mkv\nicon.png',0)
  single=dp.parse_item('1080p (12 / 0) [400 MB] WebDL H.264 - Torrentio\nNaruto.Shippuden.S01E01.1080p.WEB.x264\nicon.png',1)
  self.assertEqual(dp.auto_choose([pack,single],{'quality':'1080p','strict_quality':True})['idx'],1)
  self.assertEqual(dp.auto_choose([pack],{'quality':'1080p','strict_quality':True})['idx'],0)   # still used when alone

if __name__=='__main__':unittest.main()
