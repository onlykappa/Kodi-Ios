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
  self.mods=mods;self.addon=addon
  self.patcher=patch.dict(sys.modules,mods);self.patcher.start();self.addCleanup(self.patcher.stop)
  self.existing=patch.object(cloud,'existing_url',return_value=None);self.existing.start();self.addCleanup(self.existing.stop)
 def jobs(self):return debrid_drive.load(self.tmp.name).get('jobs',[])
 def test_prompt_after_each_new_movie_or_episode_selected_and_both_modes_queue(self):
  for mode in (0,1):
   self.dialog.select.return_value=mode
   self.assertTrue(cloud.route(url(uri=magnet(),type='episode',season='1',episode=str(mode+1))))
  self.assertEqual(len(self.jobs()),2)
  self.assertEqual([bool(j.get('watch_requested')) for j in self.jobs()],[False,True])
  self.assertEqual(self.dialog.select.call_count,2)
  self.assertEqual(self.dialog.select.call_args.args[1],['Download only','Download and watch after preparation'])
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

if __name__=='__main__':unittest.main()
