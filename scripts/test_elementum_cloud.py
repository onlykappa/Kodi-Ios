"""The source-picker boundary must never start the local Elementum downloader."""
import base64,hashlib,json,sys,tempfile,types,unittest,urllib.parse
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib';sys.path.insert(0,str(LIB))
import elementum_cloud as cloud
import debrid_drive
H='a1'*20

def url(path='/play',**q):return 'plugin://plugin.video.elementum'+path+'?'+urllib.parse.urlencode(q)
def magnet():return 'magnet:?'+urllib.parse.urlencode({'xt':'urn:btih:'+H,'dn':'Show.S01E02.2160p.HDR'})

class Selected(unittest.TestCase):
 def test_movies_shows_download_resume_and_base32(self):
  for path in ('/play','/download'):
   for kind in ('movie','episode'):
    result=cloud.selected(url(path,uri=magnet(),type=kind,season='1',episode='2'))
    self.assertEqual(result['hash'],H);self.assertEqual(result['name'],'Show.S01E02.2160p.HDR')
  self.assertEqual(cloud.selected(url(resume=H))['hash'],H)
  m='magnet:?xt=urn:btih:'+base64.b32encode(bytes.fromhex(H)).decode()
  self.assertEqual(cloud.selected(url(uri=m))['hash'],H)
 def test_torrent_hash_uses_original_info_bytes(self):
  info=b'd4:name5:Movie6:lengthi123ee';torrent=b'd8:announce3:url4:info'+info+b'e'
  choice=cloud.selected(url(uri='/Movie.torrent'),read=lambda _:torrent)
  self.assertEqual(choice['hash'],hashlib.sha1(info).hexdigest());self.assertEqual(choice['name'],'Movie')
 def test_browsing_and_other_plugins_are_ignored(self):
  for value in ('plugin://plugin.video.elementum/movie/3/links','plugin://other/play?uri='+H,'https://example.com/play?uri='+H):
   self.assertIsNone(cloud.selected(value))
 def test_invalid_hash_and_oversize_metadata_fail(self):
  for m in ('magnet:?xt=urn:btih:nope','magnet:?xt=urn:btmh:1220'):
   with self.assertRaises(ValueError):cloud.selected(url(uri=m))
  with self.assertRaises(ValueError):cloud.torrent_hash(b'd'+b'x'*cloud.LIMIT)

class Route(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.dialog=Mock();self.dialog.select.return_value=0
  self.account=Mock();self.account.get_accounts.return_value={'account':{'id':'drive'}}
  addon=Mock();addon.getSetting.return_value='synthetic';addon.getAddonInfo.side_effect=lambda key:self.tmp.name
  mods={'xbmc':Mock(),'xbmcgui':types.SimpleNamespace(Dialog=lambda:self.dialog,NOTIFICATION_INFO='info'),
        'xbmcaddon':types.SimpleNamespace(Addon=lambda name:addon),
        'xbmcvfs':types.SimpleNamespace(translatePath=lambda path:self.tmp.name),
        'clouddrive':types.ModuleType('clouddrive'),'clouddrive.common':types.ModuleType('clouddrive.common'),
        'clouddrive.common.account':types.SimpleNamespace(AccountManager=lambda path:self.account),
        'notices':Mock()}
  props={}
  mods['xbmcgui'].Window=lambda ident:types.SimpleNamespace(getProperty=lambda k:props.get(k,''),
      setProperty=lambda k,v:props.__setitem__(k,v),clearProperty=lambda k:props.pop(k,None))
  self.mods=mods;self.addon=addon
  self.patcher=patch.dict(sys.modules,mods);self.patcher.start();self.addCleanup(self.patcher.stop)
  self.existing=patch.object(cloud,'existing_url',return_value=None);self.existing.start();self.addCleanup(self.existing.stop)
 def jobs(self):return debrid_drive.load(self.tmp.name).get('jobs',[])
 def test_paused_uploads_offer_explicit_resume_or_keep_queued(self):
  import transfer_control
  for mode,paused in ((0,False),(2,True)):
   transfer_control.set_paused(self.tmp.name,'up',True)
   self.dialog.select.return_value=mode
   cloud.route(url(uri=magnet(),type='episode',season='1',episode=str(mode+1)))
   self.assertEqual(transfer_control.paused(self.tmp.name,'up'),paused)
   self.assertEqual(self.dialog.select.call_args.args[0],'Uploads are paused')
  self.assertEqual(len(self.jobs()),2)
  self.assertEqual(self.dialog.notification.call_args.args[1],'Queued · uploads paused')
 def test_cancel_paused_download_keeps_pause_and_saves_nothing(self):
  import transfer_control
  transfer_control.set_paused(self.tmp.name,'up',True)
  self.dialog.select.return_value=-1
  cloud.route(url(uri=magnet(),type='episode',season='1',episode='2'))
  self.assertTrue(transfer_control.paused(self.tmp.name,'up'));self.assertFalse(self.jobs())
 def test_prompt_after_each_new_movie_or_episode_selected_and_both_modes_queue(self):
  for mode in (0,1):
   self.dialog.select.return_value=mode
   self.assertTrue(cloud.route(url(uri=magnet(),type='episode',season='1',episode=str(mode+1))))
  self.assertEqual(len(self.jobs()),2)
  self.assertEqual([bool(j.get('watch_requested')) for j in self.jobs()],[False,True])
  self.assertEqual(self.dialog.select.call_count,2)
  self.assertEqual([x.split(' · ')[0] for x in self.dialog.select.call_args.args[1]],['Download only','Download and watch'])
 def test_cancel_never_enqueues_or_starts_a_player(self):
  self.dialog.select.return_value=-1
  self.assertTrue(cloud.route(url(uri=magnet())))
  self.assertEqual(self.jobs(),[]);self.mods['xbmc'].executebuiltin.assert_not_called()
 def test_missing_either_account_fails_closed(self):
  self.addon.getSetting.return_value=''
  self.assertTrue(cloud.route(url(uri=magnet())));self.assertEqual(self.jobs(),[])
  self.addon.getSetting.return_value='synthetic';self.account.get_accounts.return_value={}
  self.assertTrue(cloud.route(url(uri=magnet())));self.assertEqual(self.jobs(),[])
  self.dialog.select.assert_not_called()
 def test_verified_download_skips_prompt_and_opens_drive(self):
  with patch.object(cloud,'existing_url',return_value='plugin://plugin.googledrive/?item_id=ready'):
   self.assertTrue(cloud.route(url(uri=magnet())))
  self.dialog.select.assert_not_called();self.assertEqual(self.jobs(),[])
  self.mods['xbmc'].executebuiltin.assert_called_once()
 def test_browser_and_invalid_uri_do_not_fall_through_to_downloader(self):
  self.assertFalse(cloud.route('plugin://plugin.video.elementum/movie/3/links'))
  self.assertTrue(cloud.route(url(uri='magnet:?xt=urn:btih:broken')))
  self.assertEqual(self.jobs(),[])

class Watch(unittest.TestCase):
 def test_watch_waits_for_preparation_and_idle_and_opens_only_once(self):
  with tempfile.TemporaryDirectory() as p:
   j=debrid_drive.queue(p,{'id':H,'name':'Movie'},'movie',watch=True)
   self.assertIsNone(debrid_drive.next_watch(p,lambda _:True))
   state=debrid_drive.load(p);state['jobs'][0].update(status='done',files=[{'done':True,'drive_id':'f'}]);debrid_drive.save(p,state)
   self.assertIsNone(debrid_drive.next_watch(p,lambda _:False))
   self.assertIsNone(debrid_drive.next_watch(p,lambda _:True,playing=True))
   self.assertEqual(debrid_drive.next_watch(p,lambda _:True),'f')
   self.assertIsNone(debrid_drive.next_watch(p,lambda _:True))
 def test_stale_service_snapshot_does_not_lose_a_new_enqueue_or_watch_handled(self):
  with tempfile.TemporaryDirectory() as p:
   debrid_drive.queue(p,{'id':H},'movie',watch=True)
   old=debrid_drive.load(p)
   debrid_drive.queue(p,{'id':'b'*40},'movie')
   state=debrid_drive.load(p);state['jobs'][0]['watch_handled']=state['jobs'][0]['watch_requested'];debrid_drive.save(p,state)
   debrid_drive.save(p,old)
   state=debrid_drive.load(p);self.assertEqual(len(state['jobs']),2)
   self.assertEqual(state['jobs'][0]['watch_handled'],state['jobs'][0]['watch_requested'])

class PackFileMatch(unittest.TestCase):
 def test_a_file_inside_a_pack_is_the_same_pick(self):
  # Owner log 15e6cbc4 (build 288): every episode of a season build was refused, "0 episodes added".
  import elementum_cloud as ec
  pack='Naruto Shippuden (001-500) [Complete Series + Movies (1080p)] (Dual Audio)'
  self.assertTrue(ec.same_pick(pack+' Season 01 (001-032)/Naruto Shippuden Episode 001 Homecoming.mkv',pack))
  self.assertTrue(ec.same_pick('Naruto.Shippuden.S01E01.1080p','naruto.shippuden.s01e01.1080p'))
  self.assertFalse(ec.same_pick('Naruto Shippuden S01E02','Naruto Shippuden S01E01'))
  self.assertFalse(ec.same_pick('Naruto','Naruto Shippuden S01E01'))   # too short to trust
  self.assertFalse(ec.same_pick('',pack))

class AutomaticRefusals(unittest.TestCase):
 def test_only_fields_in_the_link_are_compared(self):
  # Owner log 5169a460 (build 290): every Build Season episode was refused silently.
  import elementum_cloud as ec
  wanted={'request_id':'r','target':{'tmdb':'31910','season':1,'episode':5}}
  picked={'request_id':'r','found':True,'name':'Naruto Shippuden (001-500) [Complete Series]/Episode 005.mkv'}
  self.assertEqual(ec.refusal(wanted,picked,{'name':'Naruto Shippuden (001-500) [Complete Series]'}),'')
  self.assertEqual(ec.refusal(wanted,picked,{'name':'Naruto Shippuden (001-500) [Complete Series]','season':'1','episode':'05'}),'')
  self.assertEqual(ec.refusal(wanted,picked,{'name':'Naruto Shippuden (001-500) [Complete Series]','episode':'6'}),'different episode')
  self.assertEqual(ec.refusal(wanted,dict(picked,request_id='x'),{'name':'x'}),'another request')
  self.assertTrue(ec.refusal(wanted,picked,{'name':'Something Else S01E05'}).startswith('different version (picked "'))
  # The lane's own lookup: names are not compared, the episode still is.
  self.assertEqual(ec.refusal(wanted,picked,{'name':'Something Else'},own=True),'')
  self.assertEqual(ec.refusal(wanted,picked,{'name':'x','episode':'6'},own=True),'different episode')

class SeasonQueueNames(unittest.TestCase):
 def test_the_season_request_carries_the_show_title(self):
  import season_sources,json
  props={}
  home=types.SimpleNamespace(getProperty=lambda k:props.get(k,''),setProperty=props.__setitem__,clearProperty=lambda k:props.pop(k,None))
  seen={}
  def follow(url,**kw):seen['want']=json.loads(props['KodiIOS.AutoPick']);return url
  season_sources.request(home,31910,1,2,'queue','1080p',follow=follow,title='Naruto Shippūden')
  self.assertEqual(seen['want']['target']['title'],'Naruto Shippūden')

class SeasonQueueThreeLanes(unittest.TestCase):
 """ISSUE-179 (owner log 1138649a, build 302): Build Season found every episode and queued none: each pick was
 "refused (different version)" then "no matching automatic request". Reproduces season_sources.request's queue phase
 for three lanes: deck_picker.run answers each lane, then Elementum's link for each lane reaches auto_season with the
 lane's request id, in any order."""
 def test_each_lane_queues_its_own_pick(self):
  import importlib.util,json,time as t,random
  spec=importlib.util.spec_from_file_location('deck_picker_t',ROOT/'migration/deck-picker/deck_picker.py')
  dp=importlib.util.module_from_spec(spec);spec.loader.exec_module(dp)
  props={}
  home=types.SimpleNamespace(getProperty=lambda k:props.get(k,''),setProperty=props.__setitem__,clearProperty=lambda k:props.pop(k,None))
  pack='Naruto Shippuden (001-500) [Complete Series + Movies (1080p)] (Dual Audio) Season 01 (001-032)/Naruto Shippuden Episode %03d.mkv'
  labels={1:[pack%1],2:['Naruto Shippuuden - 002 [1080p] dual audio 10bit.mkv',pack%2],3:[pack%3]}
  links={}
  with patch.object(dp,'_home',return_value=home),patch.object(dp,'_matcher',return_value=None):
   for lane,ep in (('',1),('.1',2),('.2',3)):
    props[dp.AUTO_PICK+lane]=json.dumps({'request_id':'r%d'%ep,'until':t.time()+600,'purpose':'queue','mode':0,
      'target':{'tmdb':'31910','season':1,'episode':ep},'profile':{'quality':'1080p','strict_quality':True}})
   for lane,ep in (('',1),('.1',2),('.2',3)):
    items=['1080p (%d / 0) [262.85 MB] WebDL H.264 - Torrentio\n%s \U0001F464 10 \U0001F4BE 945.19 MB \u2699\ufe0f NyaaSi\nicon.png'%(200-i,n)
           for i,n in enumerate(labels[ep])]
    idx=dp.run('ナルト 疾風伝 S01E%02d'%ep,items,expect={'tmdb':'31910','season':1,'episode':ep,'label':'S01E%02d'%ep})
    self.assertGreaterEqual(idx,0)
    # Elementum's link names the torrent its own way (here: the search query), never the picker's label line.
    m='magnet:?'+urllib.parse.urlencode({'xt':'urn:btih:'+('%02d'%ep)*20,'dn':'ナルト 疾風伝'})
    links[ep]=url(uri=m,season='1',episode=str(ep),query='ナルト 疾風伝')
  order=[1,2,3];random.Random(7).shuffle(order)
  for ep in order:
   got=cloud.auto_season(home,choice=cloud.selected(links[ep]),request_id='r%d'%ep)
   self.assertIsNotNone(got,'episode %d refused'%ep);self.assertEqual(got['request_id'],'r%d'%ep)
   self.assertEqual(got['_lane'],{1:'',2:'.1',3:'.2'}[ep])
  # Another lane's link for this episode is still refused (wrong episode), and a hand pick still compares names.
  self.assertIsNone(cloud.auto_season(home,choice=cloud.selected(links[2]),request_id='r1'))
  with patch.object(cloud,'_refused') as said:
   self.assertIsNone(cloud.auto_season(home,choice=cloud.selected(links[2])))
  self.assertIn('Elementum "ナルト 疾風伝"',said.call_args[0][0])

 def test_the_picker_label_stats_do_not_stop_a_name_match(self):
  import elementum_cloud as ec
  self.assertTrue(ec.same_pick('Naruto Shippuuden - 002 [1080p] dual audio 10bit.mkv \U0001F464 10 \U0001F4BE 945.19 MB \u2699\ufe0f NyaaSi',
                               'Naruto Shippuuden - 002 [1080p] dual audio 10bit.mkv'))
  self.assertTrue(ec.same_pick('Pack (001-500)/Naruto Shippuden Episode 003.mkv','Naruto Shippuden Episode 003.mkv'))

if __name__=='__main__':unittest.main()
